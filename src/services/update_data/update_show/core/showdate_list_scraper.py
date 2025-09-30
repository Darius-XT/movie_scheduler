"""更新放映日期列表用爬取器(由 get_movie_showdate_list 迁移并内联)"""

import requests
from datetime import datetime
from requests.cookies import create_cookie
from src.logger import logger
from src.config import settings


CITY_MAPPING = {
    "北京": 1,
    "上海": 10,
}


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


class UpdateShowdateListScraper:
    def __init__(self):
        self.headers = DEFAULT_HEADERS.copy()
        self.session = requests.Session()
        self._warmed_up = False
        self._current_city = None

    def _get_city_id(self, city: str) -> int:
        return CITY_MAPPING.get(city, CITY_MAPPING[settings.city])

    def _preset_cookies(self, city: str):
        domain = "www.maoyan.com"
        path = "/"
        city_id = self._get_city_id(city)
        city_id_str = str(city_id)
        recent_cis = f"{city_id_str}%3D1%3D50%3D1245%3D1126"

        cookies_to_set = [
            ("uuid_n_v", "v1"),
            (
                "uuid",
                "C8A7D680893511F096935750AB1698AA3C3D4230A5474A638234ED4590859DCA",
            ),
            (
                "_csrf",
                "f9b6559b1b01185a39433a65b188cb83193b343236faa3555dc69a7b5d2a9505",
            ),
            ("_ga", "GA1.1.200491387.1756952456"),
            ("Hm_lvt_e0bacf12e04a7bd88ddbd9c74ef2b533", "1756952460"),
            ("Hm_lpvt_e0bacf12e04a7bd88ddbd9c74ef2b533", "1758166366"),
            ("HMACCOUNT", "FAC79C52BFC838B4"),
            (
                "_lxsdk_cuid",
                "1991286fcf4c8-0502fc73ab8c0c-16525636-384000-1991286fcf5c8",
            ),
            (
                "_lxsdk",
                "C8A7D680893511F096935750AB1698AA3C3D4230A5474A638234ED4590859DCA",
            ),
            ("_lx_utm", "utm_source%3Dgoogle%26utm_medium%3Dorganic"),
            ("ci", city_id_str),
            ("recentCis", recent_cis),
            ("old-moviepage-ci", city_id_str),
            ("global-guide-isclose", "true"),
            ("_ga_WN80P4PSY7", "GS2.1.s1758166366$o42$g0$t1758166366$j60$l0$h0"),
            ("__mta", "216316201.1756952460622.1758114293338.1758166366584.22"),
            ("_lxsdk_s", "1995ae1b8be-4e1-3c1-d13%7C%7C2"),
        ]

        for name, value in cookies_to_set:
            self.session.cookies.set_cookie(
                create_cookie(name=name, value=value, domain=domain, path=path)
            )

    def _warm_up_session(self, movie_id: int, city: str):
        try:
            warmup_url = f"https://www.maoyan.com/cinemas?movieId={movie_id}"
            logger.debug(f"开始预热会话: {warmup_url}, 城市: {city}")
            self.session.get(
                warmup_url,
                headers=self.headers,
                allow_redirects=settings.allow_redirects,
                timeout=settings.timeout,
            )
            logger.debug("预热请求完成")
        except Exception as e:
            logger.debug(f"预热请求失败(忽略): {e}")

    def scrape_movie_showdate_list(
        self, movie_id: int, city: str | None = None
    ) -> tuple[bool, str]:
        try:
            if city is None:
                city = settings.city

            if self._current_city != city:
                logger.debug(f"城市发生变化: {self._current_city} -> {city}")
                self.session.cookies.clear()
                self._preset_cookies(city)
                self._current_city = city
                self._warmed_up = False

            if not self._warmed_up:
                self._warm_up_session(movie_id, city)
                self._warmed_up = True

            today = datetime.now().strftime("%Y-%m-%d")
            url = f"https://www.maoyan.com/cinemas?movieId={movie_id}&showDate={today}"
            logger.debug(f"开始爬取影院页: movieId={movie_id}, city={city}")

            response = self.session.get(
                url,
                headers=self.headers,
                allow_redirects=settings.allow_redirects,
                timeout=settings.timeout,
            )

            logger.debug(f"response状态码: {response.status_code}")
            logger.debug(f"最终URL: {response.url}")
            logger.debug(f"HTML长度: {len(response.text)} 字符")

            if response.status_code == 200:
                logger.debug("成功获取HTML内容")
                return True, response.text
            else:
                logger.warning(f"请求失败，状态码: {response.status_code}")
                return False, ""
        except Exception as e:
            logger.error(f"获取影院页HTML失败: {e}")
            return False, ""


update_showdate_list_scraper = UpdateShowdateListScraper()
