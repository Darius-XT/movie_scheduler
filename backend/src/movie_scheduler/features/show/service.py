"""场次服务: 抓取猫眼场次/日期/影院 → 解析 → 落库 + 读取。

将原 show/ 下 cinema_client + date_client + show_client + request_helper +
fetcher + gateway + result_builder + entities + service 全部并入此处。
"""

from __future__ import annotations

import asyncio
import html
import json
import re
from collections.abc import AsyncIterator, Callable, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from time import monotonic
from typing import TypedDict, cast

import requests
import urllib3
from bs4 import BeautifulSoup
from bs4.element import Tag

from movie_scheduler.config import config_manager
from movie_scheduler.core.exceptions import (
    AppError,
    DataParsingError,
    ExternalDependencyError,
    RepositoryError,
)
from movie_scheduler.core.logging import logger
from movie_scheduler.core.request_logging import log_external_http_request
from movie_scheduler.features.movie.repository import movie_repository
from movie_scheduler.features.show.models import MovieShowWriteData
from movie_scheduler.features.show.repository import movie_show_repository
from movie_scheduler.shared.maoyan import (
    build_maoyan_web_headers,
    decode_maoyan_stonefont_text,
)
from movie_scheduler.shared.sse import stream_with_progress

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


# =============================================================================
# 内部数据结构
# =============================================================================

@dataclass(slots=True)
class ShowUpdateProgressEvent:
    """场次更新过程中向 SSE 推送的进度事件。"""

    message: str
    stage: str
    current: int | None = None
    total: int | None = None
    city_id: int | None = None


@dataclass(slots=True)
class ShowUpdateStats:
    """场次更新结果(对外暴露)。"""

    added: int
    removed: int
    movies_with_shows: int


@dataclass(slots=True)
class _FetchedShowItem:
    """上游抓取到的单条原始场次。"""

    movie_id: int | None
    movie_name: str
    show_date: str
    show_time: str
    price: str
    cinema_id: int | None
    cinema_name: str


@dataclass(slots=True)
class _ShowItem:
    date: str
    time: str
    price: str


def _empty_show_items() -> list[_ShowItem]:
    return []


def _empty_cinema_map() -> dict[int, _CinemaShowData]:
    return {}


@dataclass(slots=True)
class _CinemaShowData:
    cinema_id: int
    cinema_name: str
    shows: list[_ShowItem] = field(default_factory=_empty_show_items)


@dataclass(slots=True)
class _MovieShowData:
    movie_id: int
    movie_name: str
    cinemas: dict[int, _CinemaShowData] = field(default_factory=_empty_cinema_map)


@dataclass(slots=True)
class _FinalMovieShowData:
    movie_id: int
    cinemas: list[_CinemaShowData]


_DegradableError = (ExternalDependencyError, DataParsingError)


# =============================================================================
# 外部 HTTP 请求公共配置
# =============================================================================

_SHOW_REQUEST_HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7",
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.maoyan.com/",
    "Origin": "https://www.maoyan.com",
}

_SHOW_API_TIMEOUT = 30
_MAOYAN_WEB_HOME = "https://www.maoyan.com/"
_MAOYAN_WEB_CINEMA_BASE = "https://www.maoyan.com/cinema"
_MAOYAN_WEB_CINEMAS_BASE = "https://www.maoyan.com/cinemas"
_CINEMA_PAGE_SIZE = 12
_HOT_MOVIE_IDS_CACHE_TTL_SECONDS = 60 * 60


def _http_get_text(url: str, log_label: str, headers: dict[str, str] | None = None) -> str | None:
    """抓取外部接口文本,失败返回 None。"""
    try:
        effective_headers = headers or _SHOW_REQUEST_HEADERS
        logger.debug("开始%s", log_label)
        log_external_http_request("GET", url, purpose=log_label)
        response = requests.get(
            url,
            headers=effective_headers,
            timeout=_SHOW_API_TIMEOUT,
            verify=False,
        )
        logger.debug("%s响应状态码: %s,响应长度: %s 字符", log_label, response.status_code, len(response.text))
        if response.status_code == 200:
            return response.text
        logger.error(
            "%s请求失败: status=%s, response=%s",
            log_label, response.status_code, response.text[:1000],
        )
        return None
    except Exception as error:
        logger.error("%s异常: error=%s", log_label, error, exc_info=True)
        return None


# =============================================================================
# JSON 解析类型(date/cinema/show 三个上游接口)
# =============================================================================

class _CinemaItemForList(TypedDict, total=False):
    id: int


class _CinemaListPaging(TypedDict, total=False):
    hasMore: bool


class _CinemaListDataSection(TypedDict, total=False):
    cinemas: list[_CinemaItemForList]
    paging: _CinemaListPaging


class _CinemaListRoot(TypedDict, total=False):
    data: _CinemaListDataSection


class _ShowItemRaw(TypedDict, total=False):
    tm: str
    discountSellPrice: str | int | float
    vipDisPrice: str | int | float
    vipPrice: str | int | float


class _ShowDateGroupRaw(TypedDict, total=False):
    showDate: str
    plist: list[_ShowItemRaw]


class _MovieShowRaw(TypedDict, total=False):
    id: int
    nm: str
    shows: list[_ShowDateGroupRaw]


class _CinemaShowsRaw(TypedDict, total=False):
    cinemaId: int
    cinemaName: str
    movies: list[_MovieShowRaw]


class _CinemaShowsRoot(TypedDict, total=False):
    data: _CinemaShowsRaw


# =============================================================================
# Service
# =============================================================================

class ShowService:
    """聚合场次抓取与持久化能力。"""

    def __init__(self) -> None:
        self._hot_movie_ids_cache: dict[int, tuple[float, list[int]]] = {}
        self._movie_persist_locks: dict[int, asyncio.Lock] = {}

    # ---------- 对外: 定时抓取 + 单片抓取 ----------

    async def refresh_wished_movie_shows(
        self,
        city_id: int | None = None,
        progress_callback: Callable[[ShowUpdateProgressEvent], None] | None = None,
    ) -> ShowUpdateStats:
        """抓取所有想看电影的场次并写入数据库,返回新增/删除场次统计与有场次的电影数。"""
        normalized_city_id = self._normalize_city_id(city_id)
        wished_movies = await asyncio.to_thread(movie_repository.list_wished_movies)
        movie_ids = [int(mid) for m in wished_movies if (mid := cast(int | None, getattr(m, "id", None))) is not None]

        if not movie_ids:
            logger.info("场次定时抓取:想看列表为空,跳过")
            if progress_callback is not None:
                progress_callback(ShowUpdateProgressEvent(
                    message="想看列表为空,无需抓取场次",
                    stage="empty_wishlist",
                    city_id=normalized_city_id,
                ))
            return ShowUpdateStats(added=0, removed=0, movies_with_shows=0)

        try:
            if progress_callback is not None:
                progress_callback(ShowUpdateProgressEvent(
                    message=f"开始抓取 {len(movie_ids)} 部想看电影的场次",
                    stage="fetching_shows",
                    total=len(movie_ids),
                    city_id=normalized_city_id,
                ))
            results = await self._fetch_shows_for_selected_movies(movie_ids, city_id=normalized_city_id)

            if progress_callback is not None:
                progress_callback(ShowUpdateProgressEvent(
                    message="正在写入数据库", stage="persisting_shows",
                    city_id=normalized_city_id,
                ))
            stats = await self._persist_results(movie_ids, results)
            logger.info(
                "场次定时抓取完成: %s/%s 部电影有场次, 新增 %s 场, 删除 %s 场",
                stats.movies_with_shows, len(movie_ids), stats.added, stats.removed,
            )
            return stats
        except Exception as error:
            logger.error("场次定时抓取失败: %s", error)
            raise

    async def stream_show_update(self, city_id: int) -> AsyncIterator[str]:
        """将场次更新过程编码为 SSE 文本帧。"""

        async def run(push_progress: Callable[[dict[str, object]], None]) -> dict[str, object]:
            def forward(event: ShowUpdateProgressEvent) -> None:
                push_progress({
                    "stage": event.stage,
                    "message": event.message,
                    "current": event.current,
                    "total": event.total,
                    "city_id": event.city_id,
                })

            stats = await self.refresh_wished_movie_shows(
                city_id=city_id, progress_callback=forward,
            )
            wished_movies = await asyncio.to_thread(movie_repository.list_wished_movies)
            movie_ids = [int(mid) for m in wished_movies if (mid := cast(int | None, getattr(m, "id", None))) is not None]
            last_fetched_at = await asyncio.to_thread(movie_repository.get_latest_shows_updated_at, movie_ids)
            return {
                "added": stats.added,
                "removed": stats.removed,
                "movies_with_shows": stats.movies_with_shows,
                "last_fetched_at": self._serialize_datetime(last_fetched_at),
            }

        async for frame in stream_with_progress(run, map_error=self._map_stream_error):
            yield frame

    async def refresh_movie_shows(self, movie_id: int, city_id: int | None = None) -> int:
        """抓取单部想看电影的场次并写入数据库。"""
        normalized_city_id = self._normalize_city_id(city_id)
        movie = await asyncio.to_thread(movie_repository.get_movie_by_id, movie_id)
        if movie is None:
            logger.warning("单片场次抓取跳过,电影不存在: %s", movie_id)
            return 0
        if not bool(movie.is_wished):
            await asyncio.to_thread(movie_show_repository.delete_for_movie, movie_id)
            logger.info("单片场次抓取跳过,电影不在想看: %s", movie_id)
            return 0

        try:
            results = await self._fetch_shows_for_selected_movies([movie_id], city_id=normalized_city_id)
            stats = await self._persist_results([movie_id], results)
            logger.info("单片场次抓取完成: 电影 %s, 成功数 %s", movie_id, stats.movies_with_shows)
            return stats.movies_with_shows
        except Exception as error:
            logger.error("单片场次抓取失败,电影 %s: %s", movie_id, error)
            return 0

    # ---------- 对外: 读 ----------

    async def get_shows_for_wished_movies(self, movie_id: int | None = None) -> dict[str, object]:
        """返回前端需要的 wishMovies 场次结构 + 最近一次抓取完成时间。"""
        if movie_id is not None:
            return await self._get_shows_for_single_wished_movie(movie_id)

        wished_movies = await asyncio.to_thread(movie_repository.list_wished_movies)
        movie_ids = [int(mid) for m in wished_movies if (mid := cast(int | None, getattr(m, "id", None))) is not None]
        shows = await asyncio.to_thread(movie_show_repository.list_for_movies, movie_ids)
        latest = await asyncio.to_thread(movie_repository.get_latest_shows_updated_at, movie_ids)

        return {
            "movies": self._build_movies_payload(movie_ids, shows),
            "last_fetched_at": self._serialize_datetime(latest),
        }

    async def _get_shows_for_single_wished_movie(self, movie_id: int) -> dict[str, object]:
        movie = await asyncio.to_thread(movie_repository.get_movie_by_id, movie_id)
        if movie is None:
            raise AppError(f"电影不存在: {movie_id}", status_code=404)
        if not bool(movie.is_wished):
            return {"movies": [], "last_fetched_at": None}

        shows = await asyncio.to_thread(movie_show_repository.list_for_movies, [movie_id])
        shows_updated_at = cast(datetime | None, getattr(movie, "shows_updated_at", None))
        return {
            "movies": self._build_movies_payload([movie_id], shows),
            "last_fetched_at": self._serialize_datetime(shows_updated_at),
        }

    # ---------- 内部: 批量抓取编排 ----------

    async def _fetch_shows_for_selected_movies(
        self,
        movie_ids: list[int],
        city_id: int,
    ) -> list[_FinalMovieShowData]:
        """异步抓取选中电影的所有场次。"""
        logger.info("开始异步获取 %s 部电影在城市 %s 的场次信息", len(movie_ids), city_id)

        async def fetch_movie(movie_id: int) -> _FinalMovieShowData | None:
            return await self._process_single_movie(movie_id, city_id)

        tasks = [fetch_movie(movie_id) for movie_id in movie_ids]
        movie_results = await asyncio.gather(*tasks, return_exceptions=True)

        result = self._collect_valid_movie_results(movie_results)
        total_shows = sum(len(c.shows) for m in result for c in m.cinemas)
        logger.info("总共找到 %s 部电影, %s 个场次信息", len(result), total_shows)
        return result

    async def _process_single_movie(
        self,
        movie_id: int,
        city_id: int,
    ) -> _FinalMovieShowData | None:
        try:
            movie_name = await asyncio.to_thread(self._get_movie_name, movie_id)
            if not movie_name:
                logger.warning("无法获取电影名称,跳过电影 ID: %s", movie_id)
                return None

            movie_data = _MovieShowData(movie_id=movie_id, movie_name=movie_name)
            show_dates = await asyncio.to_thread(self._get_show_dates, movie_id, city_id)
            logger.debug("找到 %s 个排片日期: %s", len(show_dates), show_dates)

            cinema_ids = await self._collect_movie_cinema_ids(movie_id, city_id, show_dates)
            cinemas = await self._fetch_movie_cinema_shows(movie_id, movie_name, city_id, cinema_ids, set(show_dates))
            self._merge_cinemas(movie_data, cinemas)

            return self._finalize_movie(movie_data)
        except asyncio.CancelledError:
            logger.info("处理电影 ID %s 的场次任务被取消", movie_id)
            raise
        except Exception as error:
            if isinstance(error, _DegradableError):
                logger.warning("处理电影 ID %s 时发生可降级错误,跳过当前电影: %s", movie_id, error)
                return None
            logger.exception("处理电影 ID %s 时发生不可恢复错误: %s: %r", movie_id, type(error).__name__, error)
            raise

    async def _collect_movie_cinema_ids(self, movie_id: int, city_id: int, show_dates: list[str]) -> list[int]:
        async def fetch_date_cinemas(show_date: str) -> list[int]:
            return await asyncio.to_thread(self._get_cinemas, movie_id, show_date, city_id)

        date_tasks = [fetch_date_cinemas(show_date) for show_date in show_dates]
        date_results = await asyncio.gather(*date_tasks, return_exceptions=True)

        cinema_ids: list[int] = []
        seen_cinema_ids: set[int] = set()
        for date_result in date_results:
            if isinstance(date_result, BaseException):
                if isinstance(date_result, _DegradableError):
                    logger.warning("获取日期影院列表时发生可降级错误,跳过当前日期: %s", date_result)
                    continue
                raise date_result
            for cinema_id in date_result:
                if cinema_id in seen_cinema_ids:
                    continue
                seen_cinema_ids.add(cinema_id)
                cinema_ids.append(cinema_id)
        logger.debug("电影 %s 共收集到 %s 个唯一影院", movie_id, len(cinema_ids))
        return cinema_ids

    async def _fetch_movie_cinema_shows(
        self,
        movie_id: int,
        movie_name: str,
        city_id: int,
        cinema_ids: list[int],
        allowed_dates: set[str],
    ) -> dict[int, _CinemaShowData]:
        async def fetch_cinema(cinema_id: int) -> list[_FetchedShowItem]:
            return await asyncio.to_thread(self._get_cinema_shows, cinema_id, city_id, movie_id, movie_name, None)

        cinema_tasks = [fetch_cinema(cinema_id) for cinema_id in cinema_ids]
        cinema_results = await asyncio.gather(*cinema_tasks, return_exceptions=True)

        valid: list[list[_FetchedShowItem]] = []
        for cinema_result in cinema_results:
            if isinstance(cinema_result, BaseException):
                if isinstance(cinema_result, _DegradableError):
                    logger.warning("获取影院场次时发生可降级错误,跳过当前影院: %s", cinema_result)
                    continue
                raise cinema_result
            valid.append(cinema_result)

        return self._filter_cinemas_to_dates(self._build_cinemas_from_shows(valid), allowed_dates)

    def _filter_cinemas_to_dates(
        self,
        cinemas: dict[int, _CinemaShowData],
        allowed_dates: set[str],
    ) -> dict[int, _CinemaShowData]:
        if not allowed_dates:
            return cinemas
        result: dict[int, _CinemaShowData] = {}
        for cinema_id, cinema in cinemas.items():
            filtered_shows = [show for show in cinema.shows if show.date in allowed_dates]
            if filtered_shows:
                cinema.shows = filtered_shows
                result[cinema_id] = cinema
        return result

    async def _process_single_date(
        self,
        movie_id: int,
        movie_name: str,
        city_id: int,
        show_date: str,
    ) -> dict[int, _CinemaShowData] | None:
        try:
            cinema_ids = await asyncio.to_thread(self._get_cinemas, movie_id, show_date, city_id)
            if not cinema_ids:
                return None

            async def fetch_cinema(cinema_id: int) -> list[_FetchedShowItem]:
                return await asyncio.to_thread(
                    self._get_cinema_shows, cinema_id, city_id, movie_id, movie_name, show_date
                )

            cinema_tasks = [fetch_cinema(cinema_id) for cinema_id in cinema_ids]
            cinema_results = await asyncio.gather(*cinema_tasks, return_exceptions=True)

            valid: list[list[_FetchedShowItem]] = []
            for cinema_result in cinema_results:
                if isinstance(cinema_result, BaseException):
                    if isinstance(cinema_result, _DegradableError):
                        logger.warning("获取影院场次时发生可降级错误,跳过当前影院: %s", cinema_result)
                        continue
                    raise cinema_result
                valid.append(cinema_result)

            return self._build_cinemas_from_shows(valid)
        except asyncio.CancelledError:
            logger.info("处理日期 %s 的场次任务被取消", show_date)
            raise
        except Exception as error:
            if isinstance(error, _DegradableError):
                logger.warning("处理日期 %s 时发生可降级错误,跳过当前日期: %s", show_date, error)
                return None
            logger.exception("处理日期 %s 时发生不可恢复错误: %s: %r", show_date, type(error).__name__, error)
            raise

    # ---------- 内部: 上游 HTTP 调用 ----------

    def _get_movie_name(self, movie_id: int) -> str | None:
        movie = movie_repository.get_movie_by_id(movie_id)
        if movie is None:
            return None
        return cast(str | None, getattr(movie, "title", None))

    def _get_show_dates(self, movie_id: int, city_id: int) -> list[str]:
        url = f"{_MAOYAN_WEB_CINEMAS_BASE}?movieId={movie_id}"
        text = _http_get_text(url, "抓取放映日期页面", headers=self._build_maoyan_movie_headers(city_id, movie_id))
        if text is None:
            raise ExternalDependencyError(f"获取电影 {movie_id} 在城市 {city_id} 的排片日期失败")
        dates = self._parse_show_dates(text)
        if not dates:
            raise DataParsingError(f"电影 {movie_id} 在城市 {city_id} 的排片日期解析结果为空")
        return dates

    def _get_cinemas(self, movie_id: int, show_date: str, city_id: int) -> list[int]:
        all_cinema_ids: list[int] = []
        seen_cinema_ids: set[int] = set()
        limit = _CINEMA_PAGE_SIZE
        offset = 0
        while True:
            cinema_ids, is_last_page = self._fetch_cinema_page(movie_id, show_date, city_id, limit, offset)
            for cinema_id in cinema_ids:
                if cinema_id in seen_cinema_ids:
                    continue
                seen_cinema_ids.add(cinema_id)
                all_cinema_ids.append(cinema_id)
            if is_last_page:
                return all_cinema_ids
            offset += _CINEMA_PAGE_SIZE

    def _fetch_cinema_page(
        self,
        movie_id: int,
        show_date: str,
        city_id: int,
        limit: int,
        offset: int,
    ) -> tuple[list[int], bool]:
        params = f"movieId={movie_id}&showDate={show_date}"
        if offset > 0:
            params = f"{params}&offset={offset}"
        url = f"{_MAOYAN_WEB_CINEMAS_BASE}?{params}"
        text = _http_get_text(url, "获取影片影院页面", headers=self._build_maoyan_movie_headers(city_id, movie_id))
        if text is None:
            raise ExternalDependencyError(
                f"获取影院信息失败,movie_id={movie_id}, city_id={city_id}, show_date={show_date}, offset={offset}"
            )
        cinema_ids, is_last_page = self._parse_cinema_list(text)
        if not cinema_ids and not is_last_page:
            raise DataParsingError(
                f"影院分页解析结果为空,movie_id={movie_id}, city_id={city_id}, show_date={show_date}, offset={offset}"
            )
        return cinema_ids, is_last_page

    def _get_cinema_shows(
        self,
        cinema_id: int,
        city_id: int,
        movie_id: int,
        movie_name: str,
        show_date: str | None = None,
    ) -> list[_FetchedShowItem]:
        url = f"{_MAOYAN_WEB_CINEMA_BASE}/{cinema_id}"
        headers = self._build_maoyan_web_headers(city_id, cinema_id, movie_id)
        text = _http_get_text(url, "获取影院场次页面", headers=headers)
        if text is None:
            raise ExternalDependencyError(f"获取影院 {cinema_id} 在城市 {city_id} 的场次页面失败")
        items = self._parse_cinema_shows(text, movie_id, movie_name, show_date, cinema_id)
        if not items:
            raise DataParsingError(
                f"影院 {cinema_id} 在城市 {city_id} 的场次页面解析结果为空, movie_id={movie_id}, show_date={show_date}"
            )
        return items

    def _build_maoyan_web_headers(self, city_id: int, cinema_id: int, movie_id: int) -> dict[str, str]:
        hot_movie_ids = self._get_hot_movie_ids(city_id)
        return build_maoyan_web_headers(city_id, hot_movie_ids=self._prepend_movie_id(hot_movie_ids, movie_id))

    def _build_maoyan_movie_headers(self, city_id: int, movie_id: int) -> dict[str, str]:
        hot_movie_ids = self._get_hot_movie_ids(city_id)
        return build_maoyan_web_headers(city_id, hot_movie_ids=self._prepend_movie_id(hot_movie_ids, movie_id))

    def _get_hot_movie_ids(self, city_id: int) -> list[int]:
        cached = self._hot_movie_ids_cache.get(city_id)
        now = monotonic()
        if cached is not None:
            cached_at, cached_ids = cached
            if now - cached_at < _HOT_MOVIE_IDS_CACHE_TTL_SECONDS:
                return cached_ids

        headers = build_maoyan_web_headers(city_id)
        text = _http_get_text(_MAOYAN_WEB_HOME, "获取猫眼首页热映电影数据", headers=headers)
        hot_movie_ids = self._parse_hot_movie_ids(text or "")
        if not hot_movie_ids:
            if cached is not None:
                logger.warning("猫眼首页 hotMovieIds 解析为空,沿用过期缓存")
                return cached[1]
            hot_movie_ids = self._parse_hot_movie_ids_from_cookie(config_manager.maoyan_cookie)
        if hot_movie_ids:
            self._hot_movie_ids_cache[city_id] = (now, hot_movie_ids)
        return hot_movie_ids

    def _prepend_movie_id(self, hot_movie_ids: list[int], movie_id: int) -> list[int]:
        if movie_id in hot_movie_ids:
            return hot_movie_ids
        return [movie_id, *hot_movie_ids]

    def _parse_hot_movie_ids(self, html_content: str) -> list[int]:
        result: list[int] = []
        for pattern in (
            r'data-movie-ids=["\']([^"\']+)["\']',
            r"/cinemas\?movieId=(\d+)",
            r"data-val=[\"']\{movieid:(\d+)\}[\"']",
            r"/films/(\d+)",
        ):
            matches: list[str] = re.findall(pattern, html_content, flags=re.IGNORECASE)
            for match in matches:
                if "," in match:
                    self._append_movie_ids(result, match.split(","))
                else:
                    self._append_movie_ids(result, [match])
        return result

    def _parse_hot_movie_ids_from_cookie(self, cookie: str) -> list[int]:
        match = re.search(r"(?:^|;\s*)hotMovieIds=([^;]+)", cookie)
        if match is None:
            return []
        result: list[int] = []
        self._append_movie_ids(result, match.group(1).split(","))
        return result

    def _append_movie_ids(self, result: list[int], raw_ids: Sequence[str]) -> None:
        for raw_id in raw_ids:
            normalized = raw_id.strip()
            if normalized.isdigit():
                movie_id = int(normalized)
                if movie_id not in result:
                    result.append(movie_id)

    # ---------- 内部: JSON 解析 ----------

    def _parse_show_dates(self, json_content: str) -> list[str]:
        if json_content.lstrip().startswith("<"):
            return self._parse_show_dates_html(json_content)
        try:
            payload = json.loads(json_content)
        except json.JSONDecodeError as error:
            logger.error("解析放映日期 JSON 失败: %s", error)
            return []
        if not isinstance(payload, dict):
            return []
        payload_dict = cast(dict[str, object], payload)
        if payload_dict.get("success") is not True:
            return []
        data = payload_dict.get("data")
        if not isinstance(data, dict):
            return []
        raw_dates = cast(dict[str, object], data).get("dates")
        if not isinstance(raw_dates, list):
            return []
        dates: list[str] = []
        for raw_date in cast(list[object], raw_dates):
            if not isinstance(raw_date, dict):
                continue
            date_value = cast(dict[str, object], raw_date).get("date")
            if isinstance(date_value, str) and date_value:
                dates.append(date_value)
        return dates

    def _parse_show_dates_html(self, html_content: str) -> list[str]:
        if "猫眼验证中心" in html_content:
            return []
        soup = BeautifulSoup(html_content, "html.parser")
        result: list[str] = []
        seen: set[str] = set()
        for link in soup.select('a[href*="showDate="], a[data-val*="TagName"]'):
            raw_values = [str(value) for value in (link.get("href"), link.get("data-val")) if isinstance(value, str)]
            for raw_value in raw_values:
                match = re.search(r"(?:showDate=|TagName:'?)(\d{4}-\d{2}-\d{2})", html.unescape(raw_value))
                if match is None:
                    continue
                show_date = match.group(1)
                if show_date not in seen:
                    seen.add(show_date)
                    result.append(show_date)
        return result

    def _parse_cinema_list(self, json_content: str) -> tuple[list[int], bool]:
        if json_content.lstrip().startswith("<"):
            return self._parse_cinema_list_html(json_content)
        try:
            if not json_content or not json_content.strip():
                return [], False
            parsed = json.loads(json_content)
            if not parsed or not isinstance(parsed, dict) or "data" not in parsed:
                return [], False
            root = cast(_CinemaListRoot, parsed)
            data_section = root.get("data")
            if data_section is None or "cinemas" not in data_section:
                return [], False
            cinemas_data = data_section.get("cinemas", [])
            if not cinemas_data:
                return [], False
            cinema_ids = [int(cid) for c in cinemas_data if (cid := c.get("id")) is not None]
            has_more = data_section.get("paging", {}).get("hasMore", True)
            return cinema_ids, has_more is False
        except json.JSONDecodeError as error:
            logger.error("解析 JSON 失败: %s", error)
            return [], False
        except Exception as error:
            logger.error("解析影院列表失败: %s", error)
            return [], False

    def _parse_cinema_list_html(self, html_content: str) -> tuple[list[int], bool]:
        if "猫眼验证中心" in html_content:
            return [], False
        soup = BeautifulSoup(html_content, "html.parser")
        cinema_ids: list[int] = []
        for link in soup.select(".cinema-cell .cinema-name, .cinema-cell a[href*='/cinema/']"):
            cinema_id = self._extract_cinema_id_from_html(link)
            if cinema_id is not None and cinema_id not in cinema_ids:
                cinema_ids.append(cinema_id)
        return cinema_ids, not self._has_next_cinema_page(soup)

    def _extract_cinema_id_from_html(self, node: Tag) -> int | None:
        for attr_name in ("data-val", "href"):
            raw_value = node.get(attr_name)
            if not isinstance(raw_value, str):
                continue
            match = re.search(r"cinema_id\s*:\s*(\d+)|/cinema/(\d+)", html.unescape(raw_value))
            if match is not None:
                return int(match.group(1) or match.group(2))
        return None

    def _has_next_cinema_page(self, soup: BeautifulSoup) -> bool:
        for link in soup.select(".list-pager a"):
            href = link.get("href")
            if isinstance(href, str) and "offset=" in href and "下一页" in link.get_text(" ", strip=True):
                return True
        return False

    def _parse_cinema_shows(
        self,
        content: str,
        movie_id: int,
        movie_name: str,
        target_show_date: str | None,
        fallback_cinema_id: int | None = None,
    ) -> list[_FetchedShowItem]:
        stripped = content.strip()
        if not stripped:
            return []
        if stripped.startswith("{"):
            return self._parse_cinema_shows_json(stripped, movie_id, movie_name, target_show_date)
        return self._parse_cinema_shows_html(stripped, movie_id, movie_name, target_show_date, fallback_cinema_id)

    def _parse_cinema_shows_json(
        self,
        json_content: str,
        movie_id: int,
        movie_name: str,
        target_show_date: str | None,
    ) -> list[_FetchedShowItem]:
        try:
            parsed = json.loads(json_content)
            if not parsed or not isinstance(parsed, dict) or "data" not in parsed:
                return []
            root = cast(_CinemaShowsRoot, parsed)
            data_section = root.get("data")
            if data_section is None:
                return []
            cinema_id = data_section.get("cinemaId")
            cinema_name = str(data_section.get("cinemaName", ""))
            movies = data_section.get("movies", [])

            target_movie: _MovieShowRaw | None = None
            for movie in movies:
                raw_movie_id = movie.get("id")
                if raw_movie_id == movie_id or movie.get("nm", "") == movie_name:
                    target_movie = movie
                    break
            if target_movie is None:
                logger.warning("未找到电影: %s", movie_name)
                return []

            return self._build_show_items(
                target_movie.get("shows", []),
                target_movie.get("id"),
                movie_name,
                cinema_id,
                cinema_name,
                target_show_date,
            )
        except json.JSONDecodeError as error:
            logger.error("解析 JSON 失败: %s", error)
            return []
        except Exception as error:
            logger.error("解析场次信息失败: %s", error)
            return []

    def _parse_cinema_shows_html(
        self,
        html_content: str,
        movie_id: int,
        movie_name: str,
        target_show_date: str | None,
        fallback_cinema_id: int | None,
    ) -> list[_FetchedShowItem]:
        if "猫眼验证中心" in html_content:
            logger.warning("猫眼影院页面返回验证中心,跳过解析")
            return []

        soup = BeautifulSoup(html_content, "html.parser")
        cinema_name = self._extract_html_cinema_name(soup)
        sections = self._find_html_movie_sections(soup, movie_id, movie_name)
        result: list[_FetchedShowItem] = []
        for section in sections:
            section_matches = section is not soup and self._html_section_matches_movie(section, movie_id, movie_name)
            for row in section.select("table.plist tbody tr, table.plist tr"):
                show_item = self._build_html_show_item(
                    row,
                    movie_id,
                    movie_name,
                    fallback_cinema_id,
                    cinema_name,
                    target_show_date,
                    section_matches,
                    html_content,
                )
                if show_item is not None:
                    result.append(show_item)
        return result

    def _find_html_movie_sections(self, soup: BeautifulSoup, movie_id: int, movie_name: str) -> list[Tag]:
        sections = list(soup.select(".show-list, .show-list-container"))
        matched_sections = [
            section for section in sections if self._html_section_matches_movie(section, movie_id, movie_name)
        ]
        if matched_sections:
            return matched_sections
        return sections if sections else [soup]

    def _html_section_matches_movie(self, section: Tag, movie_id: int, movie_name: str) -> bool:
        for row in section.select("table.plist tr"):
            if self._extract_html_movie_id(row) == movie_id:
                return True
        normalized_movie_name = self._normalize_html_text(movie_name)
        section_text = self._normalize_html_text(section.get_text(" ", strip=True))
        return bool(normalized_movie_name and normalized_movie_name in section_text)

    def _build_html_show_item(
        self,
        row: Tag,
        movie_id: int,
        movie_name: str,
        cinema_id: int | None,
        cinema_name: str,
        target_show_date: str | None,
        section_matches: bool,
        html_content: str,
    ) -> _FetchedShowItem | None:
        row_movie_id = self._extract_html_movie_id(row)
        if row_movie_id is not None and row_movie_id != movie_id:
            return None
        if row_movie_id is None and not section_matches:
            return None

        show_date = self._extract_html_show_date(row, target_show_date)
        if not show_date:
            return None
        if target_show_date is not None and show_date != target_show_date:
            return None

        show_time = self._extract_html_show_time(row)
        if not show_time:
            return None

        return _FetchedShowItem(
            movie_id=movie_id,
            movie_name=movie_name,
            show_date=show_date,
            show_time=show_time,
            price=self._extract_html_price(row, html_content),
            cinema_id=cinema_id,
            cinema_name=cinema_name,
        )

    def _extract_html_cinema_name(self, soup: BeautifulSoup) -> str:
        for selector in (".cinema-brief-container .name", ".cinema-info .name", "h3.name", ".cinema-name"):
            element = soup.select_one(selector)
            if isinstance(element, Tag):
                text = element.get_text(" ", strip=True)
                if text:
                    return text
        title = soup.title.get_text(" ", strip=True) if soup.title else ""
        return title.split("_", 1)[0].strip()

    def _extract_html_movie_id(self, element: Tag) -> int | None:
        candidates = [element, *element.select("[href], [data-val], [data-lab]")]
        for candidate in candidates:
            for attr_name in ("href", "data-val", "data-lab"):
                raw_value = candidate.get(attr_name)
                if isinstance(raw_value, str):
                    movie_id = self._extract_movie_id_from_text(raw_value)
                    if movie_id is not None:
                        return movie_id
        return None

    def _extract_movie_id_from_text(self, raw_value: str) -> int | None:
        text = html.unescape(raw_value)
        for pattern in (r"[?&]movieId=(\d+)", r"movie_id[\"'\s:]+(\d+)", r"movie_id\s*:\s*(\d+)"):
            match = re.search(pattern, text)
            if match is not None:
                return int(match.group(1))
        return None

    def _extract_html_show_date(self, row: Tag, target_show_date: str | None) -> str | None:
        href_date = self._extract_html_show_date_from_href(row)
        if href_date is not None:
            return href_date
        return self._extract_html_show_date_from_container(row, target_show_date)

    def _extract_html_show_date_from_href(self, row: Tag) -> str | None:
        for link in row.select('a[href*="/xseats/"], a[href*="/seats/"]'):
            href = link.get("href")
            if not isinstance(href, str):
                continue
            match = re.search(r"/(?:xseats|seats)/(\d{8})", html.unescape(href))
            if match is not None:
                raw_date = match.group(1)
                return f"{raw_date[:4]}-{raw_date[4:6]}-{raw_date[6:8]}"
        return None

    def _extract_html_show_date_from_container(self, row: Tag, target_show_date: str | None) -> str | None:
        container = row.find_parent("div", class_=re.compile(r"\bplist-container\b"))
        if not isinstance(container, Tag):
            return target_show_date
        show_list = container.find_parent(class_=re.compile(r"\bshow-list\b"))
        if not isinstance(show_list, Tag):
            return target_show_date
        containers = list(show_list.select(".plist-container"))
        date_items = list(show_list.select(".date-item"))
        if container not in containers:
            return target_show_date
        index = containers.index(container)
        if index >= len(date_items):
            return target_show_date
        return self._normalize_html_show_date(date_items[index].get_text(" ", strip=True), target_show_date)

    def _normalize_html_show_date(self, raw_date: str, target_show_date: str | None) -> str | None:
        match = re.search(r"(\d{1,2})月(\d{1,2})", raw_date)
        if match is None:
            return target_show_date
        month = int(match.group(1))
        day = int(match.group(2))
        if target_show_date is not None:
            target_match = re.match(r"(\d{4})-(\d{2})-(\d{2})", target_show_date)
            if target_match is not None and int(target_match.group(2)) == month and int(target_match.group(3)) == day:
                return target_show_date
        today = datetime.now()
        year = today.year + (1 if month < today.month - 6 else 0)
        return f"{year:04d}-{month:02d}-{day:02d}"

    def _extract_html_show_time(self, row: Tag) -> str:
        for selector in (".begin-time", ".start-time", ".time"):
            element = row.select_one(selector)
            if isinstance(element, Tag):
                text = element.get_text(" ", strip=True)
                if re.fullmatch(r"\d{1,2}:\d{2}", text):
                    return text
        match = re.search(r"\b(\d{1,2}:\d{2})\b", row.get_text(" ", strip=True))
        return match.group(1) if match is not None else ""

    def _extract_html_price(self, row: Tag, html_content: str) -> str:
        for selector in (".sell-price", ".price", ".discount-price", ".stonefont"):
            element = row.select_one(selector)
            if isinstance(element, Tag):
                price = self._normalize_price_value(element.get_text(" ", strip=True), html_content)
                if price is not None:
                    return price
        cells = list(row.select("td"))
        if len(cells) >= 4:
            price = self._normalize_price_value(cells[3].get_text(" ", strip=True), html_content)
            if price is not None:
                return price
        return "0"

    def _normalize_html_text(self, value: str) -> str:
        return re.sub(r"\s+", "", value)

    def _build_show_items(
        self,
        shows: list[_ShowDateGroupRaw],
        movie_id: int | None,
        movie_name: str,
        cinema_id: int | None,
        cinema_name: str,
        target_show_date: str | None,
    ) -> list[_FetchedShowItem]:
        result: list[_FetchedShowItem] = []
        for show_date_group in shows:
            show_date = show_date_group.get("showDate", "")
            if target_show_date is not None and show_date != target_show_date:
                continue
            for show_item in show_date_group.get("plist", []):
                result.append(_FetchedShowItem(
                    movie_id=movie_id,
                    movie_name=movie_name,
                    show_date=show_date,
                    show_time=str(show_item.get("tm", "")),
                    price=self._extract_price(show_item),
                    cinema_id=cinema_id,
                    cinema_name=cinema_name,
                ))
        return result

    def _extract_price(self, show_item: _ShowItemRaw) -> str:
        for field_name in ("discountSellPrice", "vipDisPrice", "vipPrice"):
            price = self._normalize_price_value(show_item.get(field_name))  # type: ignore[literal-required]
            if price is not None:
                return price
        return "0"

    def _normalize_price_value(
        self,
        raw_value: str | int | float | None,
        html_content: str | None = None,
    ) -> str | None:
        if raw_value is None:
            return None
        if isinstance(raw_value, (int, float)):
            return str(raw_value)
        normalized = raw_value.strip()
        if html_content is not None:
            decoded = decode_maoyan_stonefont_text(html_content, normalized)
            if decoded is None:
                return None
            normalized = decoded.strip()
        if not normalized or "stonefont" in normalized:
            return None
        match = re.search(r"\d+(?:\.\d+)?", normalized)
        return match.group(0) if match is not None else normalized

    # ---------- 内部: 结果聚合 ----------

    def _build_cinemas_from_shows(
        self,
        cinema_results: list[list[_FetchedShowItem]],
    ) -> dict[int, _CinemaShowData]:
        cinemas: dict[int, _CinemaShowData] = {}
        for shows in cinema_results:
            for show in shows:
                if show.cinema_id is None:
                    continue
                cinema = cinemas.setdefault(
                    show.cinema_id,
                    _CinemaShowData(cinema_id=show.cinema_id, cinema_name=show.cinema_name),
                )
                cinema.shows.append(_ShowItem(date=show.show_date, time=show.show_time, price=show.price))
        return cinemas

    def _merge_cinemas(self, movie_data: _MovieShowData, cinemas: dict[int, _CinemaShowData]) -> None:
        for cinema_id, cinema_info in cinemas.items():
            if cinema_id not in movie_data.cinemas:
                movie_data.cinemas[cinema_id] = cinema_info
                continue
            movie_data.cinemas[cinema_id].shows.extend(cinema_info.shows)

    def _finalize_movie(self, movie_data: _MovieShowData) -> _FinalMovieShowData | None:
        result = _FinalMovieShowData(movie_id=movie_data.movie_id, cinemas=list(movie_data.cinemas.values()))
        total_shows = sum(len(c.shows) for c in result.cinemas)
        logger.info(
            "电影 %s (ID: %s) 共找到 %s 个场次,分布在 %s 个影院",
            movie_data.movie_name, result.movie_id, total_shows, len(result.cinemas),
        )
        return result if result.cinemas else None

    def _collect_valid_movie_results(
        self,
        movie_results: Sequence[_FinalMovieShowData | None | BaseException],
    ) -> list[_FinalMovieShowData]:
        result: list[_FinalMovieShowData] = []
        for movie_result in movie_results:
            if isinstance(movie_result, BaseException):
                if isinstance(movie_result, asyncio.CancelledError):
                    logger.info("场次抓取任务被取消")
                    raise movie_result
                if isinstance(movie_result, _DegradableError):
                    logger.warning("处理电影时发生可降级错误,跳过当前电影: %s", movie_result)
                    continue
                logger.exception(
                    "处理电影时发生不可恢复错误: %s: %r",
                    type(movie_result).__name__,
                    movie_result,
                    exc_info=(type(movie_result), movie_result, movie_result.__traceback__),
                )
                raise movie_result
            if isinstance(movie_result, _FinalMovieShowData) and movie_result.cinemas:
                result.append(movie_result)
        return result

    # ---------- 内部: 持久化 ----------

    async def _persist_results(
        self,
        movie_ids: list[int],
        results: list[_FinalMovieShowData],
    ) -> ShowUpdateStats:
        results_by_movie: dict[int, _FinalMovieShowData] = {r.movie_id: r for r in results}
        added_total = 0
        removed_total = 0
        movies_with_shows = 0
        for movie_id in movie_ids:
            async with self._get_movie_persist_lock(movie_id):
                existing_keys = await asyncio.to_thread(self._collect_existing_show_keys, movie_id)
                if not await self._is_movie_wished(movie_id):
                    await asyncio.to_thread(movie_show_repository.delete_for_movie, movie_id)
                    removed_total += len(existing_keys)
                    continue
                result = results_by_movie.get(movie_id)
                shows: list[MovieShowWriteData] = []
                if result is not None:
                    for cinema in result.cinemas:
                        for show in cinema.shows:
                            shows.append({
                                "movie_id": movie_id,
                                "cinema_id": cinema.cinema_id,
                                "cinema_name": cinema.cinema_name,
                                "date": show.date,
                                "time": show.time,
                                "price": show.price,
                            })
                shows = self._deduplicate_show_rows(movie_id, shows)
                new_keys = {(s["cinema_id"], s["date"], s["time"]) for s in shows}
                added_total += len(new_keys - existing_keys)
                removed_total += len(existing_keys - new_keys)
                await asyncio.to_thread(movie_show_repository.replace_for_movie, movie_id, shows)
                await asyncio.to_thread(movie_repository.touch_shows_updated_at, movie_id)
                if shows:
                    movies_with_shows += 1
        return ShowUpdateStats(
            added=added_total, removed=removed_total, movies_with_shows=movies_with_shows,
        )

    def _get_movie_persist_lock(self, movie_id: int) -> asyncio.Lock:
        lock = self._movie_persist_locks.get(movie_id)
        if lock is None:
            lock = asyncio.Lock()
            self._movie_persist_locks[movie_id] = lock
        return lock

    def _deduplicate_show_rows(
        self,
        movie_id: int,
        shows: list[MovieShowWriteData],
    ) -> list[MovieShowWriteData]:
        ordered_keys: list[tuple[int, int, str, str]] = []
        rows_by_key: dict[tuple[int, int, str, str], MovieShowWriteData] = {}
        for show in shows:
            key = (show["movie_id"], show["cinema_id"], show["date"], show["time"])
            current = rows_by_key.get(key)
            if current is None:
                ordered_keys.append(key)
                rows_by_key[key] = show
                continue
            if self._has_better_price(show.get("price"), current.get("price")):
                rows_by_key[key] = show

        deduplicated = [rows_by_key[key] for key in ordered_keys]
        duplicate_count = len(shows) - len(deduplicated)
        if duplicate_count > 0:
            logger.debug("电影 %s 场次写入前去重: 移除 %s 条重复场次", movie_id, duplicate_count)
        return deduplicated

    def _has_better_price(self, candidate: str | None, current: str | None) -> bool:
        return self._is_meaningful_price(candidate) and not self._is_meaningful_price(current)

    def _is_meaningful_price(self, price: str | None) -> bool:
        normalized = str(price or "").strip()
        return bool(normalized and normalized not in {"0", "0.0", "0.00"})

    def _collect_existing_show_keys(self, movie_id: int) -> set[tuple[int, str, str]]:
        existing = movie_show_repository.list_for_movies([movie_id])
        return {
            (int(getattr(s, "cinema_id")), str(getattr(s, "date")), str(getattr(s, "time")))
            for s in existing
        }

    async def _is_movie_wished(self, movie_id: int) -> bool:
        movie = await asyncio.to_thread(movie_repository.get_movie_by_id, movie_id)
        return bool(movie and movie.is_wished)

    # ---------- 内部: 工具 ----------

    def _normalize_city_id(self, city_id: int | None) -> int:
        normalized = city_id if city_id is not None else config_manager.city_id
        if normalized <= 0:
            raise AppError("city_id 必须是正整数", status_code=422)
        if normalized not in config_manager.city_mapping.values():
            raise AppError("city_id 不在当前支持的城市范围内", status_code=422)
        return normalized

    def _build_movies_payload(
        self,
        movie_ids: list[int],
        shows: Sequence[object],
    ) -> list[dict[str, object]]:
        movie_shows_map: dict[int, list[dict[str, object]]] = {mid: [] for mid in movie_ids}
        for show in shows:
            mid = int(getattr(show, "movie_id"))
            if mid in movie_shows_map:
                movie_shows_map[mid].append({
                    "cinema_id": int(getattr(show, "cinema_id")),
                    "cinema_name": str(getattr(show, "cinema_name")),
                    "date": str(getattr(show, "date")),
                    "time": str(getattr(show, "time")),
                    "price": None if getattr(show, "price") is None else str(getattr(show, "price")),
                })
        return [{"movie_id": mid, "shows": movie_shows_map.get(mid, [])} for mid in movie_ids]

    def _serialize_datetime(self, value: datetime | None) -> str | None:
        return value.isoformat() if value else None

    def _map_stream_error(self, error: Exception) -> str:
        if isinstance(error, AppError):
            return error.message
        if isinstance(error, RepositoryError):
            return "数据库访问失败,请稍后重试"
        return "更新失败,请稍后重试"


show_service = ShowService()


# 抑制循环依赖: 旧代码用 RepositoryError 的钩子保留, 给上游捕获
__all__ = ["show_service", "ShowService", "RepositoryError"]
