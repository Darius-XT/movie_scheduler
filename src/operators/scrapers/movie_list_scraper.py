"""爬取HTML内容"""

import logging
import requests
from requests.cookies import create_cookie
from src.logger import logger
from src.config import settings
from src.utils.file_saver import file_saver

# 城市映射常量
CITY_MAPPING = {
    "北京": 1,
    "上海": 10,
}

# 请求头配置基础模板
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


# * 电影列表爬取器: 注意 cookie 与 header 是分别管理的(在 session 中)
class MovieListScraper:
    def __init__(self):
        self.headers = DEFAULT_HEADERS.copy()
        # session 负责连接复用与 cookie 管理, 注意 cookie 可以直接在 session 中持久化复用, 而 header 则需要每次请求时都设置
        self.session = requests.Session()
        # 标记是否已经预热过
        self._warmed_up = False
        # 当前城市信息
        self._current_city = None

    # 获取城市ID
    def _get_city_id(self, city: str) -> int:
        return CITY_MAPPING.get(city, CITY_MAPPING[settings.city])

    # 在会话中预置城市相关Cookie，以及其它身份验证相关的 cookie, 仅不包括 movie_ids
    def _preset_cookies(self, city: str):
        domain = "www.maoyan.com"
        path = "/"
        city_id = self._get_city_id(city)
        city_id_str = str(city_id)
        recent_cis = f"{city_id_str}%3D1%3D50%3D1245%3D1126"

        # 预置所有关键Cookie（除了动态的movie列表）
        cookies_to_set = [
            # 用户标识相关
            ("uuid_n_v", "v1"),  # UUID版本标识
            (
                "uuid",
                "C8A7D680893511F096935750AB1698AA3C3D4230A5474A638234ED4590859DCA",
            ),  # 用户唯一标识符
            (
                "_csrf",
                "f9b6559b1b01185a39433a65b188cb83193b343236faa3555dc69a7b5d2a9505",
            ),  # CSRF防护令牌
            # Google Analytics
            ("_ga", "GA1.1.200491387.1756952456"),  # Google Analytics客户端ID
            # 百度统计
            (
                "Hm_lvt_e0bacf12e04a7bd88ddbd9c74ef2b533",
                "1756952460",
            ),  # 百度统计访问时间
            (
                "Hm_lpvt_e0bacf12e04a7bd88ddbd9c74ef2b533",
                "1758166366",
            ),  # 百度统计最后访问时间
            # 猫眼内部标识
            ("HMACCOUNT", "FAC79C52BFC838B4"),  # 猫眼账户标识
            (
                "_lxsdk_cuid",
                "1991286fcf4c8-0502fc73ab8c0c-16525636-384000-1991286fcf5c8",
            ),  # 乐心SDK客户端ID
            (
                "_lxsdk",
                "C8A7D680893511F096935750AB1698AA3C3D4230A5474A638234ED4590859DCA",
            ),  # 乐心SDK标识
            ("_lx_utm", "utm_source%3Dgoogle%26utm_medium%3Dorganic"),  # UTM来源追踪
            # 城市相关（核心）
            ("ci", city_id_str),  # 当前城市ID
            ("recentCis", recent_cis),  # 最近访问的城市列表
            ("old-moviepage-ci", city_id_str),  # 电影页面城市ID
            # 界面状态
            ("global-guide-isclose", "true"),  # 全局引导是否关闭
            # 其他追踪
            (
                "_ga_WN80P4PSY7",
                "GS2.1.s1758166366$o42$g0$t1758166366$j60$l0$h0",
            ),  # Google Analytics会话
            (
                "__mta",
                "216316201.1756952460622.1758114293338.1758166366584.22",
            ),  # 腾讯MTA统计
            ("_lxsdk_s", "1995ae1b8be-4e1-3c1-d13%7C%7C2"),  # 乐心SDK会话标识
        ]

        for name, value in cookies_to_set:
            self.session.cookies.set_cookie(
                create_cookie(name=name, value=value, domain=domain, path=path)
            )

    # 预热，获取服务器下发的 movie_ids 相关的 Cookie, 并且由于先访问了列表的第一页, 避免了直接爬取后面的页触发反爬虫检测
    def _warm_up_session(self, show_type: int, city: str):
        try:
            # 使用与要抓取的URL相同的端点，但offset设为0
            warmup_url = f"https://www.maoyan.com/films?showType={show_type}&offset=0"
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

    def scrape_movie_list(
        self, show_type: int, offset: int, city: str | None = None
    ) -> tuple[bool, str]:
        """核心功能：获取电影列表HTML内容

        Args:
            show_type: 显示类型 (1=正在热映, 2=即将上映)
            offset: 偏移量
            city: 城市名称，如果为None则使用默认城市

        Returns:
            tuple[bool, str]: (是否成功, HTML内容)
        """
        try:
            # 处理城市参数
            if city is None:
                city = settings.city

            # 如果城市发生变化，需要重新设置Cookie和预热状态
            if self._current_city != city:
                logger.debug(f"城市发生变化: {self._current_city} -> {city}")
                self.session.cookies.clear()
                self._preset_cookies(city)
                self._current_city = city
                self._warmed_up = False

            # 如果是第一次调用或城市变化后，先进行预热
            if not self._warmed_up:
                self._warm_up_session(show_type, city)
                self._warmed_up = True

            url = f"https://www.maoyan.com/films?showType={show_type}&offset={offset}"
            logger.debug(
                f"开始爬取电影列表: showType={show_type}, offset={offset}, city={city}"
            )

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
            logger.error(f"获取HTML失败: {e}")
            return False, ""


# 直接在模块级别实例化 scraper
movie_list_scraper = MovieListScraper()

# 单元测试
if __name__ == "__main__":
    logger.setLevel(logging.DEBUG)
    show_type = 1
    offset = 36
    city = "上海"
    _, content = movie_list_scraper.scrape_movie_list(show_type, offset, city)
    file_saver.save_file(content, "html")
