"""电影基础信息更新子领域 (爬猫眼电影列表 → 增量更新 movies 表)。"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from http.cookiejar import Cookie, CookieJar
from typing import Any, cast

import requests
from bs4 import BeautifulSoup

from movie_scheduler.config import config_manager
from movie_scheduler.core.logging import logger
from movie_scheduler.features.movie.models import MovieWriteData
from movie_scheduler.features.movie.repository import movie_repository

_BEIJING_TZ = timezone(timedelta(hours=8))


def _now_beijing_datetime() -> datetime:
    """秒级精度的北京时间, 与 DB server_default 口径对齐。"""
    return datetime.now(_BEIJING_TZ).replace(tzinfo=None, microsecond=0)


# =============================================================================
# 进度事件 / 内部数据结构
# =============================================================================

@dataclass(slots=True)
class UpdateBaseProgressEvent:
    """基础信息抓取过程中的进度事件(供上层 movie service 转发到 SSE)。"""

    message: str
    stage: str
    current: int | None = None
    total: int | None = None
    city_id: int | None = None
    page: int | None = None


@dataclass(slots=True)
class _ScrapedMovieBaseInfo:
    id: int
    title: str | None
    genres: str
    actors: str
    release_date: str | None = None
    is_showing: bool = False


@dataclass(slots=True)
class BaseInfoInputStats:
    scraped_total: int
    showing: int
    upcoming: int
    duplicate: int
    deduplicated_total: int


@dataclass(slots=True)
class BaseInfoResultStats:
    existing: int
    added: int
    added_movie_ids: list[int]
    updated: int
    updated_movie_ids: list[int]
    removed: int
    total: int


@dataclass(slots=True)
class BaseInfoUpdateStats:
    input_stats: BaseInfoInputStats
    result_stats: BaseInfoResultStats


_DEFAULT_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Encoding": "gzip, deflate",
    "Accept-Language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7",
    "Connection": "keep-alive",
    "Host": "www.maoyan.com",
    "sec-ch-ua": '"Chromium";v="140", "Not=A?Brand";v="24", "Google Chrome";v="140"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"macOS"',
    "sec-fetch-dest": "document",
    "sec-fetch-mode": "navigate",
    "sec-fetch-site": "none",
    "sec-fetch-user": "?1",
    "upgrade-insecure-requests": "1",
    "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
}


class UpdateBaseService:
    """抓取猫眼电影列表并执行增量更新。"""

    def __init__(self) -> None:
        self.headers = _DEFAULT_HEADERS.copy()
        self.session = requests.Session()
        self._warmed_up = False
        self._current_city_id: int | None = None

    # ---------- 对外: 主入口 ----------

    def update_all(
        self,
        city_id: int,
        progress_callback: Callable[[UpdateBaseProgressEvent], None] | None = None,
    ) -> BaseInfoUpdateStats:
        """更新电影基础信息。"""
        logger.info("开始更新电影基础信息, city_id=%s", city_id)
        if progress_callback is not None:
            progress_callback(UpdateBaseProgressEvent(
                message="正在抓取电影列表", stage="fetching_movie_list", city_id=city_id,
            ))

        existing_movie_ids = {cast(int, m.id) for m in movie_repository.get_all_movies()}
        logger.debug("数据库当前有 %s 部电影", len(existing_movie_ids))

        all_scraped, showing_ids = self._scrape_all_movies(city_id, progress_callback)
        for movie in all_scraped:
            movie.is_showing = movie.id in showing_ids

        input_stats = self._build_input_stats(all_scraped, showing_ids)
        result_stats = self._perform_incremental_update(existing_movie_ids, all_scraped)
        stats = BaseInfoUpdateStats(input_stats=input_stats, result_stats=result_stats)

        self._log_stats(stats)
        if progress_callback is not None:
            progress_callback(UpdateBaseProgressEvent(
                message=(
                    f"基础信息更新完成: 新增 {stats.result_stats.added} 部, "
                    f"更新 {stats.result_stats.updated} 部, 删除 {stats.result_stats.removed} 部"
                ),
                stage="base_info_completed",
                current=stats.input_stats.deduplicated_total,
                total=stats.input_stats.deduplicated_total,
                city_id=city_id,
            ))
        return stats

    # ---------- 内部: 抓取 ----------

    def _scrape_all_movies(
        self,
        city_id: int,
        progress_callback: Callable[[UpdateBaseProgressEvent], None] | None,
    ) -> tuple[list[_ScrapedMovieBaseInfo], set[int]]:
        all_scraped: list[_ScrapedMovieBaseInfo] = []
        showing_ids: set[int] = set()

        for show_type in range(1, 3):
            show_type_name = "正在热映" if show_type == 1 else "即将上映"
            type_movies = self._scrape_one_type(show_type, show_type_name, city_id, progress_callback)
            if show_type == 1:
                showing_ids = {m.id for m in type_movies}
            all_scraped.extend(type_movies)

        return all_scraped, showing_ids

    def _scrape_one_type(
        self,
        show_type: int,
        show_type_name: str,
        city_id: int,
        progress_callback: Callable[[UpdateBaseProgressEvent], None] | None,
    ) -> list[_ScrapedMovieBaseInfo]:
        logger.debug("开始抓取 %s 电影", show_type_name)
        type_movies: list[_ScrapedMovieBaseInfo] = []
        page = 1
        while True:
            if progress_callback is not None:
                progress_callback(UpdateBaseProgressEvent(
                    message=f"正在抓取{show_type_name}第 {page} 页",
                    stage="fetching_movie_list", city_id=city_id, page=page,
                ))
            result = self._fetch_page(show_type, page, city_id)
            if result is None:
                logger.warning("获取页面失败, 跳过 page=%s", page)
                break
            movies_data, is_expected_empty = result
            if is_expected_empty:
                logger.debug("%s 抓取完成, 共 %s 页", show_type_name, page - 1)
                break
            if not movies_data:
                logger.error("第 %s 页未解析到电影数据, 结束抓取", page)
                break
            type_movies.extend(movies_data)
            page += 1
        logger.info("%s 列表抓取完成, 共抓取 %s 部电影", show_type_name, len(type_movies))
        return type_movies

    def _fetch_page(
        self,
        show_type: int,
        page: int,
        city_id: int,
    ) -> tuple[list[_ScrapedMovieBaseInfo], bool] | None:
        html_content = self._http_get(show_type, page, city_id)
        if html_content is None:
            return None
        return self._parse_html(html_content)

    def _http_get(self, show_type: int, page: int, city_id: int) -> str | None:
        offset = (page - 1) * 18
        url = f"https://www.maoyan.com/films?showType={show_type}&offset={offset}"
        try:
            if self._current_city_id != city_id:
                self.session.cookies.clear()
                self._preset_cookies(city_id)
                self._current_city_id = city_id
                self._warmed_up = False

            if not self._warmed_up:
                self._warm_up_session(show_type, city_id)
                self._warmed_up = True

            response = self.session.get(
                url,
                headers=self.headers,
                allow_redirects=config_manager.allow_redirects or True,
                timeout=config_manager.timeout or 60,
            )

            if response.status_code == 200:
                return response.text

            logger.error(
                "获取电影列表 HTML 请求失败: status=%s, url=%s, response=%s",
                response.status_code, url, response.text[:1000],
            )
            return None
        except Exception as error:
            logger.error("获取电影列表 HTML 异常: url=%s, error=%s", url, error, exc_info=True)
            return None

    def _preset_cookies(self, city_id: int) -> None:
        domain = "www.maoyan.com"
        path = "/"
        city_id_str = str(city_id)
        recent_cis = f"{city_id_str}%3D1%3D50%3D1245%3D1126"
        cookies_to_set = [
            ("uuid_n_v", "v1"),
            ("uuid", "C8A7D680893511F096935750AB1698AA3C3D4230A5474A638234ED4590859DCA"),
            ("_csrf", "f9b6559b1b01185a39433a65b188cb83193b343236faa3555dc69a7b5d2a9505"),
            ("_ga", "GA1.1.200491387.1756952456"),
            ("Hm_lvt_e0bacf12e04a7bd88ddbd9c74ef2b533", "1756952460"),
            ("Hm_lpvt_e0bacf12e04a7bd88ddbd9c74ef2b533", "1758166366"),
            ("HMACCOUNT", "FAC79C52BFC838B4"),
            ("_lxsdk_cuid", "1991286fcf4c8-0502fc73ab8c0c-16525636-384000-1991286fcf5c8"),
            ("_lxsdk", "C8A7D680893511F096935750AB1698AA3C3D4230A5474A638234ED4590859DCA"),
            ("_lx_utm", "utm_source%3Dgoogle%26utm_medium%3Dorganic"),
            ("ci", city_id_str),
            ("recentCis", recent_cis),
            ("old-moviepage-ci", city_id_str),
            ("global-guide-isclose", "true"),
            ("_ga_WN80P4PSY7", "GS2.1.s1758166366$o42$g0$t1758166366$j60$l0$h0"),
            ("__mta", "216316201.1756952460622.1758114293338.1758166366584.22"),
            ("_lxsdk_s", "1995ae1b8be-4e1-3c1-d13%7C%7C2"),
        ]
        cookie_jar = cast(CookieJar, self.session.cookies)
        for name, value in cookies_to_set:
            cookie_jar.set_cookie(Cookie(
                version=0, name=name, value=value,
                port=None, port_specified=False,
                domain=domain, domain_specified=True, domain_initial_dot=False,
                path=path, path_specified=True,
                secure=False, expires=None, discard=True,
                comment=None, comment_url=None, rest={}, rfc2109=False,
            ))

    def _warm_up_session(self, show_type: int, city_id: int) -> None:
        try:
            warmup_url = f"https://www.maoyan.com/films?showType={show_type}&offset=0"
            self.session.get(
                warmup_url, headers=self.headers,
                allow_redirects=config_manager.allow_redirects or True,
                timeout=config_manager.timeout or 60,
            )
        except Exception as error:
            logger.debug("预热请求失败, 已忽略: %s", error)

    # ---------- 内部: 解析 ----------

    def _parse_html(self, html_content: str) -> tuple[list[_ScrapedMovieBaseInfo], bool]:
        try:
            soup = BeautifulSoup(html_content, "html.parser")
            no_movies_div = soup.find("div", class_="no-movies")
            if no_movies_div:
                no_movies_text = no_movies_div.get_text().strip()
                if "抱歉,当前城市暂未找到相关结果" in no_movies_text or "抱歉，当前城市暂未找到相关结果" in no_movies_text:
                    return [], True

            movies: list[_ScrapedMovieBaseInfo] = []
            for item in soup.find_all("dd"):
                movie_info = self._extract_movie_info(item)
                if movie_info is not None:
                    movies.append(movie_info)
            return movies, False
        except Exception as error:
            logger.error("解析电影列表 HTML 失败: %s", error)
            return [], False

    def _extract_movie_info(self, item: Any) -> _ScrapedMovieBaseInfo | None:
        try:
            movie_id = self._extract_movie_id(item)
            if movie_id is None:
                return None
            title = self._extract_title(item)
            genres, actors, release_date = self._extract_hover_meta(item)
            return _ScrapedMovieBaseInfo(
                id=movie_id, title=title, genres=genres, actors=actors, release_date=release_date,
            )
        except Exception as error:
            logger.error("提取单部电影基础信息失败: %s", error)
            return None

    def _extract_movie_id(self, item: Any) -> int | None:
        movie_link = item.find("a", href=re.compile(r"/films/\d+"))
        if movie_link is None:
            return None
        href = movie_link.get("href")
        if not isinstance(href, str):
            return None
        match = re.search(r"/films/(\d+)", href)
        return int(match.group(1)) if match is not None else None

    def _extract_title(self, item: Any) -> str | None:
        title_element = item.find("div", class_="movie-item-title")
        title_link = title_element.find("a") if title_element is not None else None
        return title_link.get_text().strip() if title_link is not None else None

    def _extract_hover_meta(self, item: Any) -> tuple[str, str, str | None]:
        genres = "暂无类型"
        actors = "暂无主演"
        release_date: str | None = None
        hover_info = item.find("div", class_="movie-hover-info")
        if hover_info:
            for title_elem in hover_info.find_all("div", class_="movie-hover-title"):
                hover_tag = title_elem.find("span", class_="hover-tag")
                if hover_tag is None:
                    continue
                tag_text = hover_tag.get_text().strip()
                content = title_elem.get_text().replace(tag_text, "").strip()
                if "类型:" in tag_text and content:
                    genres = content
                elif "主演:" in tag_text and content:
                    actors = content
                elif "上映时间:" in tag_text and content:
                    release_date = content
        return genres, actors, release_date

    # ---------- 内部: 统计 + 落库 ----------

    def _build_input_stats(
        self,
        scraped: list[_ScrapedMovieBaseInfo],
        showing_ids: set[int],
    ) -> BaseInfoInputStats:
        scraped_total = len(scraped)
        scraped_ids = [m.id for m in scraped]
        deduplicated_total = len(set(scraped_ids))
        upcoming_count = sum(1 for mid in set(scraped_ids) if mid not in showing_ids)
        return BaseInfoInputStats(
            scraped_total=scraped_total,
            showing=len(showing_ids),
            upcoming=upcoming_count,
            duplicate=scraped_total - deduplicated_total,
            deduplicated_total=deduplicated_total,
        )

    def _perform_incremental_update(
        self,
        existing_movie_ids: set[int],
        scraped: list[_ScrapedMovieBaseInfo],
    ) -> BaseInfoResultStats:
        unique_scraped = self._deduplicate(scraped)
        scraped_ids = {m.id for m in unique_scraped}
        added_ids = scraped_ids - existing_movie_ids
        removed_ids = existing_movie_ids - scraped_ids
        updated_ids = scraped_ids & existing_movie_ids

        return BaseInfoResultStats(
            existing=len(existing_movie_ids),
            added=self._add_new_movies(unique_scraped, added_ids),
            added_movie_ids=sorted(added_ids),
            updated=self._update_existing_movies(unique_scraped, updated_ids),
            updated_movie_ids=sorted(updated_ids),
            removed=self._remove_stale_movies(removed_ids),
            total=movie_repository.get_movies_count(),
        )

    def _add_new_movies(
        self,
        unique_scraped: list[_ScrapedMovieBaseInfo],
        added_ids: set[int],
    ) -> int:
        count = 0
        for movie in unique_scraped:
            if movie.id not in added_ids:
                continue
            data = asdict(movie)
            if movie.is_showing:
                data["first_showing_at"] = _now_beijing_datetime()
            if movie_repository.save_movie(cast(MovieWriteData, data)):
                count += 1
                logger.info("添加新电影 %s (ID: %s)", movie.title, movie.id)
        return count

    def _update_existing_movies(
        self,
        unique_scraped: list[_ScrapedMovieBaseInfo],
        updated_ids: set[int],
    ) -> int:
        count = 0
        for movie in unique_scraped:
            if movie.id not in updated_ids:
                continue
            existing = movie_repository.get_movie_by_id(movie.id)
            if existing is None:
                continue
            existing_is_showing = cast(bool, existing.is_showing)
            update_data: MovieWriteData = {
                "id": movie.id,
                "is_showing": movie.is_showing,
                "title": movie.title,
                "genres": movie.genres,
                "actors": movie.actors,
                "release_date": movie.release_date,
            }
            if not existing_is_showing and movie.is_showing:
                update_data["first_showing_at"] = _now_beijing_datetime()
            if movie_repository.save_movie(update_data):
                count += 1
        return count

    def _remove_stale_movies(self, removed_ids: set[int]) -> int:
        count = 0
        for movie_id in removed_ids:
            movie = movie_repository.get_movie_by_id(movie_id)
            if movie is not None and movie_repository.delete_movie(movie_id):
                count += 1
                logger.info("删除下架电影: %s (ID: %s)", movie.title, movie_id)
        return count

    def _deduplicate(self, scraped: list[_ScrapedMovieBaseInfo]) -> list[_ScrapedMovieBaseInfo]:
        seen: dict[int, _ScrapedMovieBaseInfo] = {}
        for m in scraped:
            seen[m.id] = m
        return list(seen.values())

    def _log_stats(self, stats: BaseInfoUpdateStats) -> None:
        logger.info(
            "基础电影信息输入统计: 抓取总数=%d, 正在热映=%d, 即将上映=%d, 重复=%d, 去重后总数=%d",
            stats.input_stats.scraped_total,
            stats.input_stats.showing,
            stats.input_stats.upcoming,
            stats.input_stats.duplicate,
            stats.input_stats.deduplicated_total,
        )
        logger.info(
            "基础电影信息更新结果统计: 原有=%d, 新增=%d, 更新=%d, 删除=%d, 当前总数=%d",
            stats.result_stats.existing,
            stats.result_stats.added,
            stats.result_stats.updated,
            stats.result_stats.removed,
            stats.result_stats.total,
        )


update_base_service = UpdateBaseService()
