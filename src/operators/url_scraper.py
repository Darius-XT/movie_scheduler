"""爬取HTML内容"""

import requests
from requests.cookies import create_cookie
from src.logger import logger
from src.config import settings

# 城市映射常量
CITY_MAPPING = {
    "北京": 1,
    "上海": 10,
}

# 请求头配置基础模板（不包含Cookie）
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


class URLScraper:
    def __init__(self, city: str | None = None):
        self.city = city or settings.city
        self.city_id = self._get_city_id(self.city)

        # 会话与Cookie管理
        self.session = requests.Session()  # 连接复用与cookie管理
        self.headers = DEFAULT_HEADERS.copy()  # 不在headers里写Cookie
        # 预置城市相关Cookie到会话
        self._preset_city_cookies()
        # 预热一次，让服务器下发其余Set-Cookie
        self._warm_up_session()

    def _get_city_id(self, city: str) -> int:
        """获取城市ID"""
        return CITY_MAPPING.get(city, CITY_MAPPING[settings.city])

    def _preset_city_cookies(self):
        """在会话中预置城市相关Cookie，以便首个请求即带上正确城市。"""
        domain = "www.maoyan.com"
        path = "/"
        city_id_str = str(self.city_id)
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

    def _warm_up_session(self):
        """访问站点首页以获取服务器下发的其它Cookie: 预热时只预填城市Cookie, 其它 cookie 在请求后获取"""
        try:
            self.session.get(
                "https://www.maoyan.com",
                headers=self.headers,
                allow_redirects=settings.allow_redirects,
                timeout=settings.timeout,
            )
        except Exception as e:
            logger.debug(f"预热请求失败(忽略): {e}")

    def set_city(self, city: str):
        """设置城市并重新初始化相关配置

        Args:
            city: 城市名称
        """
        self.city = city
        self.city_id = self._get_city_id(city)

        # 重新设置城市相关Cookie
        self.session.cookies.clear()
        self._preset_city_cookies()
        # 重新预热
        self._warm_up_session()

    def scrape_url(self, url: str) -> tuple[bool, str]:
        """核心功能：获取URL的HTML内容

        Returns:
            tuple[bool, str]: (是否成功, HTML内容)
        """
        try:
            logger.debug(f"开始爬取URL: {url}")

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
scraper = URLScraper()
