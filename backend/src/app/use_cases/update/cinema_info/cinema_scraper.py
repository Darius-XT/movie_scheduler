"""更新影院用的爬取器(由 get_cinema_list 迁移并重命名)"""

import requests
import urllib3

from app.core.logger import logger

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class CinemaInfoScraper:
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

    def scrape_cinemas(self, city_id: int, page: int = 1) -> tuple[bool, str]:
        """爬取影院搜索API的JSON数据

        Args:
            city_id (int): 城市ID。
                示例值: 1, 10
            page (int): 页码，从1开始。
                默认为 1。
                每页返回20条数据。
                示例值: 1, 2, 3

        Returns:
            tuple[bool, str]: (是否成功, JSON内容)
                第一个元素是布尔值，True 表示请求成功（HTTP状态码200），False 表示失败。
                第二个元素是JSON内容字符串，如果失败则为空字符串 ""。
                示例返回值: (True, '[{"id": 1001, ...}]') 或 (False, "")
        """
        try:
            offset = (page - 1) * 20
            url = f"{self.base_url}?keyword='影'&ci={city_id}&offset={offset}"
            logger.debug(f"开始获取影院数据: page={page}, offset={offset}, url={url}")

            response = requests.get(url, headers=self.headers, timeout=self.timeout, verify=False)

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


cinema_info_scraper = CinemaInfoScraper()
