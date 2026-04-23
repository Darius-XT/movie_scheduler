"""电影基础信息客户端：合并 scraper + parser，对外返回业务对象。"""

from __future__ import annotations

import re
from http.cookiejar import Cookie, CookieJar
from typing import Any, cast

import requests

from app.core.config import config_manager
from app.core.logger import logger
from app.services.update.movie.base.entities import ScrapedMovieBaseInfo

from bs4 import BeautifulSoup

DEFAULT_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "Accept-Encoding": "gzip, deflate, br, zstd",
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


class MovieBaseInfoClient:
    """合并 HTTP 抓取与 HTML 解析，返回业务对象。"""

    def __init__(self) -> None:
        self.headers = DEFAULT_HEADERS.copy()
        self.session = requests.Session()
        self._warmed_up = False
        self._current_city_id: int | None = None

    def fetch_page(
        self,
        show_type: int,
        page: int,
        city_id: int,
    ) -> tuple[list[ScrapedMovieBaseInfo], bool] | None:
        """抓取并解析一页电影列表。

        Returns:
            None — HTTP 请求失败，调用方应终止翻页。
            (movies_data, is_expected_empty) — 请求成功后的解析结果。
        """
        html_content = self._fetch(show_type, page, city_id)
        if html_content is None:
            return None
        return self.parse(html_content)

    # ------------------------------------------------------------------
    # 私有：HTTP
    # ------------------------------------------------------------------

    def _fetch(self, show_type: int, page: int, city_id: int) -> str | None:
        """发起 HTTP 请求，失败返回 None。"""
        try:
            if self._current_city_id != city_id:
                logger.debug("城市发生变化: %s -> %s", self._current_city_id, city_id)
                self.session.cookies.clear()
                self._preset_cookies(city_id)
                self._current_city_id = city_id
                self._warmed_up = False

            if not self._warmed_up:
                self._warm_up_session(show_type, city_id)
                self._warmed_up = True

            offset = (page - 1) * 18
            url = f"https://www.maoyan.com/films?showType={show_type}&offset={offset}"
            logger.debug(
                "开始抓取电影列表: showType=%s, page=%s, offset=%s, city_id=%s",
                show_type,
                page,
                offset,
                city_id,
            )

            response = self.session.get(
                url,
                headers=self.headers,
                allow_redirects=config_manager.allow_redirects or True,
                timeout=config_manager.timeout or 60,
            )

            logger.debug("response状态码: %s", response.status_code)
            logger.debug("最终URL: %s", response.url)
            logger.debug("HTML长度: %s 字符", len(response.text))

            if response.status_code == 200:
                logger.debug("成功获取 HTML 内容")
                return response.text

            logger.warning("请求失败，状态码: %s", response.status_code)
            return None
        except Exception as error:
            logger.error("获取 HTML 失败: %s", error)
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
            cookie_jar.set_cookie(self._build_cookie(name, value, domain, path))

    def _build_cookie(self, name: str, value: str, domain: str, path: str) -> Cookie:
        return Cookie(
            version=0,
            name=name,
            value=value,
            port=None,
            port_specified=False,
            domain=domain,
            domain_specified=True,
            domain_initial_dot=False,
            path=path,
            path_specified=True,
            secure=False,
            expires=None,
            discard=True,
            comment=None,
            comment_url=None,
            rest={},
            rfc2109=False,
        )

    def _warm_up_session(self, show_type: int, city_id: int) -> None:
        try:
            warmup_url = f"https://www.maoyan.com/films?showType={show_type}&offset=0"
            logger.debug("开始预热会话: %s, city_id=%s", warmup_url, city_id)
            self.session.get(
                warmup_url,
                headers=self.headers,
                allow_redirects=config_manager.allow_redirects or True,
                timeout=config_manager.timeout or 60,
            )
            logger.debug("预热请求完成")
        except Exception as error:
            logger.debug("预热请求失败，已忽略: %s", error)

    # ------------------------------------------------------------------
    # 解析（public，供测试直接调用）
    # ------------------------------------------------------------------

    def parse(self, html_content: str) -> tuple[list[ScrapedMovieBaseInfo], bool]:
        """解析 HTML，返回电影列表和是否为预期空页。"""
        try:
            logger.debug("开始解析电影列表 HTML")
            soup = BeautifulSoup(html_content, "html.parser")

            no_movies_div = soup.find("div", class_="no-movies")
            if no_movies_div:
                no_movies_text = no_movies_div.get_text().strip()
                if "抱歉，当前城市暂未找到相关结果" in no_movies_text:
                    logger.debug("检测到 no-movies 提示，这是预期中的空页面")
                    return [], True

            movies: list[ScrapedMovieBaseInfo] = []
            for item in soup.find_all("dd"):
                movie_info = self._extract_movie_info(item)
                if movie_info is not None:
                    movies.append(movie_info)

            logger.debug("成功解析 %s 部电影信息", len(movies))
            return movies, False
        except Exception as error:
            logger.error("解析电影列表 HTML 失败: %s", error)
            return [], False

    def _extract_movie_info(self, item: Any) -> ScrapedMovieBaseInfo | None:
        """从单个条目中提取电影基础信息。"""
        try:
            movie_id = self._extract_movie_id(item)
            if movie_id is None:
                return None
            title = self._extract_title(item)
            genres, actors, release_date = self._extract_hover_meta(item)
            return ScrapedMovieBaseInfo(
                id=movie_id, title=title, genres=genres,
                actors=actors, release_date=release_date,
            )
        except Exception as error:
            logger.error("提取单部电影基础信息失败: %s", error)
            return None

    def _extract_movie_id(self, item: Any) -> int | None:
        """从条目中提取电影 ID。"""
        movie_link = item.find("a", href=re.compile(r"/films/\d+"))
        if movie_link is None:
            logger.warning("没有在 dd 中匹配到有效电影链接")
            return None
        href = movie_link.get("href")
        if not isinstance(href, str):
            return None
        match = re.search(r"/films/(\d+)", href)
        if match is None:
            logger.warning("没有在 href 中匹配到电影 ID: %s", href)
            return None
        return int(match.group(1))

    def _extract_title(self, item: Any) -> str | None:
        """从条目中提取电影标题。"""
        title_element = item.find("div", class_="movie-item-title")
        title_link = title_element.find("a") if title_element is not None else None
        if title_link is not None:
            return title_link.get_text().strip()
        logger.warning("没有在电影条目中找到标题")
        return None

    def _extract_hover_meta(self, item: Any) -> tuple[str, str, str | None]:
        """从 hover-info 区域提取类型、主演、上映时间。"""
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

    def _normalize_field(self, value: Any, default_text: str) -> str | Any:
        """把空值统一转换成默认文案。"""
        if value is None:
            return default_text
        if isinstance(value, str) and not value.strip():
            return default_text
        return value


movie_base_info_client = MovieBaseInfoClient()
