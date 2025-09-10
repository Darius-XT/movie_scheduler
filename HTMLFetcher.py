import requests
from fake_useragent import UserAgent
from logger_config import logger


class HTMLFetcher:
    def __init__(self):
        # 生成反爬虫请求头
        def get_headers():
            ua = UserAgent()
            return {
                "User-Agent": ua.random,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Cache-Control": "max-age=0",
            }

        self.session = requests.Session()  # 连接复用与cookie管理
        self.headers = get_headers()
        self.city_map = {
            "北京": 1,
            "上海": 10,
        }

    # 设置城市
    def set_city(self, city: str):
        if city not in self.city_map:
            logger.error(f"不支持的城市: {city}")
            return

        self.session.cookies.set("ci", str(self.city_map[city]), domain="maoyan.com")
        self.session.cookies.set(
            "recentCis",
            f"{str(self.city_map[city])}%3D10%3D1245%3D1126%3D150",
            domain="maoyan.com",
        )
        logger.info(f"城市设置为: {city} (ID: {self.city_map[city]})")

    def get_html(self, url: str) -> str:
        """核心功能：获取URL的HTML内容"""
        try:
            logger.info(f"正在访问: {url}")

            # 记录当前session中的所有cookie
            if self.session.cookies:
                logger.debug("当前session中的cookies:")
                for cookie in self.session.cookies:
                    logger.debug(
                        f"  {cookie.name}={cookie.value} (domain={cookie.domain}, path={cookie.path})"
                    )
            else:
                logger.debug("当前session中没有cookies")

            response = self.session.get(
                url,
                headers=self.headers,
                timeout=15,  # 设置超时时间
                allow_redirects=True,  # 允许重定向
            )

            logger.info(f"response状态码: {response.status_code}")
            logger.info(f"最终URL: {response.url}")
            logger.info(f"HTML长度: {len(response.text)} 字符")

            if response.status_code == 200:
                return response.text
            else:
                logger.warning(f"请求失败，状态码: {response.status_code}")
                return ""

        except Exception as e:
            logger.error(f"获取HTML失败: {e}")
            return ""


fetcher = HTMLFetcher()
