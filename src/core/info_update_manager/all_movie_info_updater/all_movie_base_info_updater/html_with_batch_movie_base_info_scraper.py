"""更新电影列表用爬取器(由 get_movie_list 迁移并内联)"""

import requests
from requests.cookies import create_cookie
from src.utils.logger import logger
from src.config_manager import config_manager
from src.utils.file_saver import file_saver

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


class HtmlWithBatchMovieBaseInfoScraper:
    def __init__(self):
        self.headers = DEFAULT_HEADERS.copy()
        self.session = requests.Session()
        self._warmed_up = False
        self._current_city_id = None

    def scrape_html_with_batch_movie_base_info(
        self, show_type: int, page: int = 1, city_id: int = 10
    ) -> tuple[bool, str]:
        """爬取电影列表页面的HTML内容

        Args:
            show_type (int): 电影类型。
                1 表示"正在热映"，
                2 表示"即将上映"。
                示例值: 1, 2
            page (int): 页码，从1开始。
                默认为 1。
                示例值: 1, 2, 3
            city_id (int | None): 城市ID。
                如果为 None，则使用配置文件中的默认城市ID。
                示例值: None, 1, 10

        Returns:
            tuple[bool, str]: (是否成功, HTML内容)
                第一个元素是布尔值，True 表示请求成功（HTTP状态码200），False 表示失败。
                第二个元素是HTML内容字符串，如果失败则为空字符串 ""。
                示例返回值: (True, "<html>...</html>") 或 (False, "")
        """
        try:
            if self._current_city_id != city_id:
                logger.debug(f"城市发生变化: {self._current_city_id} -> {city_id}")
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
                f"开始爬取电影列表: showType={show_type}, page={page}, offset={offset}, city_id={city_id}"
            )

            response = self.session.get(
                url,
                headers=self.headers,
                allow_redirects=config_manager.allow_redirects or True,
                timeout=config_manager.timeout or 60,
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
            logger.error(f"获取HTML失败: {e}")
            return False, ""

    def _preset_cookies(self, city_id: int):
        domain = "www.maoyan.com"
        path = "/"
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
            (
                "Hm_lvt_e0bacf12e04a7bd88ddbd9c74ef2b533",
                "1756952460",
            ),
            (
                "Hm_lpvt_e0bacf12e04a7bd88ddbd9c74ef2b533",
                "1758166366",
            ),
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
            (
                "_ga_WN80P4PSY7",
                "GS2.1.s1758166366$o42$g0$t1758166366$j60$l0$h0",
            ),
            (
                "__mta",
                "216316201.1756952460622.1758114293338.1758166366584.22",
            ),
            ("_lxsdk_s", "1995ae1b8be-4e1-3c1-d13%7C%7C2"),
        ]

        for name, value in cookies_to_set:
            self.session.cookies.set_cookie(
                create_cookie(name=name, value=value, domain=domain, path=path)
            )

    def _warm_up_session(self, show_type: int, city_id: int):
        try:
            warmup_url = f"https://www.maoyan.com/films?showType={show_type}&offset=0"
            logger.debug(f"开始预热会话: {warmup_url}, city_id={city_id}")
            # * cookie 会自动保存到 session 中
            self.session.get(
                warmup_url,
                headers=self.headers,
                allow_redirects=config_manager.allow_redirects or True,
                timeout=config_manager.timeout or 60,
            )
            logger.debug("预热请求完成")
        except Exception as e:
            logger.debug(f"预热请求失败(忽略): {e}")


html_with_batch_movie_base_info_scraper = HtmlWithBatchMovieBaseInfoScraper()

if __name__ == "__main__":
    success, html_content = (
        html_with_batch_movie_base_info_scraper.scrape_html_with_batch_movie_base_info(
            1, 4
        )
    )
    if success:
        file_saver.save_file(html_content, file_type="html")
