"""抓取电影列表页的基础信息 HTML。"""

from __future__ import annotations

from http.cookiejar import Cookie, CookieJar
from typing import cast

import requests

from app.core.config import config_manager
from app.core.logger import logger

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


class MovieBaseInfoScraper:
    def __init__(self) -> None:
        self.headers = DEFAULT_HEADERS.copy()
        self.session = requests.Session()
        self._warmed_up = False
        self._current_city_id: int | None = None

    def scrape_movies(
        self,
        show_type: int,
        page: int = 1,
        city_id: int = 10,
    ) -> tuple[bool, str]:
        """抓取指定分页的电影列表 HTML。"""
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
                return True, response.text

            logger.warning("请求失败，状态码: %s", response.status_code)
            return False, ""
        except Exception as error:
            logger.error("获取 HTML 失败: %s", error)
            return False, ""

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


movie_base_info_scraper = MovieBaseInfoScraper()
