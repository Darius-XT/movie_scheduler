"""影院数据爬取器"""

import requests
import urllib3
from src.logger import logger
from src.utils.file_saver import file_saver

# 抑制 SSL 证书验证警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class CinemaListScraper:
    """影院数据爬取器"""

    def __init__(self):
        self.base_url = "https://apis.netstart.cn/maoyan/search/cinemas"
        self.timeout = 30
        self.headers = {
            "Accept": "application/json",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7",
            "Connection": "keep-alive",
            "Host": "apis.netstart.cn",
            "sec-ch-ua": '"Chromium";v="140", "Not=A?Brand";v="24", "Google Chrome";v="140"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"macOS"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "cross-site",
            "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
        }

    def scrape_cinema_page(
        self, keyword: str, city_id: int, offset: int = 0
    ) -> tuple[bool, str]:
        """爬取单页影院数据

        Args:
            keyword: 搜索关键词
            city_id: 城市ID
            offset: 偏移量，默认为0

        Returns:
            tuple[bool, str]: (是否成功, 响应内容)
        """
        try:
            url = f"{self.base_url}?keyword={keyword}&ci={city_id}&offset={offset}"
            logger.debug(f"开始获取影院数据: {url}")

            response = requests.get(
                url, headers=self.headers, timeout=self.timeout, verify=False
            )

            logger.debug(f"响应状态码: {response.status_code}")
            logger.debug(f"响应长度: {len(response.text)} 字符")

            if response.status_code == 200:
                logger.debug("成功获取影院数据")
                return True, response.text
            else:
                logger.warning(f"请求失败，状态码: {response.status_code}")
                return False, response.text

        except Exception as e:
            logger.error(f"获取影院数据失败: {e}")
            return False, ""


# 直接在模块级别实例化 scraper
cinema_list_scraper = CinemaListScraper()

# 单元测试
if __name__ == "__main__":
    import logging

    logger.setLevel(logging.DEBUG)
    success, content = cinema_list_scraper.scrape_cinema_page(
        keyword="影", city_id=10, offset=40
    )
    file_saver.save_file(content, "json")
