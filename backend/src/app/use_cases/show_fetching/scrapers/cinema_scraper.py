"""获取指定电影在指定日期和城市的影院信息用爬取器"""

import requests
import urllib3

from app.core.logger import logger

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class CinemaScraper:
    def __init__(self):
        self.base_url = "https://apis.netstart.cn/maoyan/movie/select/cinemas"
        self.timeout = 30

    def scrape_cinemas(
        self,
        movie_id: int,
        show_date: str,
        city_id: int = 10,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[bool, str]:
        """爬取指定电影在指定日期和城市的影院信息JSON数据

        Args:
            movie_id (int): 电影ID。
                示例值: 1505776
            show_date (str): 放映日期，格式为 YYYY-MM-DD。
                示例值: "2025-11-10"
            city_id (int | None): 城市ID。
                如果为 None，则使用配置文件中的默认城市ID。
                示例值: None, 1, 10
            limit (int): 每页返回的数据条数。
                默认为 20。
                示例值: 20, 50
            offset (int): 数据偏移量，用于分页。
                默认为 0。
                示例值: 0, 20, 40

        Returns:
            tuple[bool, str]: (是否成功, JSON内容)
                第一个元素是布尔值，True 表示请求成功（HTTP状态码200），False 表示失败。
                第二个元素是JSON内容字符串，如果失败则为空字符串 ""。
                示例返回值: (True, '{"data": {...}}') 或 (False, "")
        """
        try:
            city_id = int(city_id)

            url = f"{self.base_url}?limit={limit}&offset={offset}&showDate={show_date}&movieId={movie_id}&cityId={city_id}"
            logger.debug(f"开始获取影院信息: {url}")

            headers = {
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7",
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
                "Referer": "https://www.maoyan.com/",
                "Origin": "https://www.maoyan.com",
            }

            response = requests.get(url, headers=headers, timeout=self.timeout, verify=False)

            logger.debug(f"响应状态码: {response.status_code}")
            logger.debug(f"响应长度: {len(response.text)} 字符")

            if response.status_code == 200:
                logger.debug("成功获取影院信息JSON数据")
                return True, response.text
            else:
                logger.warning(f"请求失败，状态码: {response.status_code}")
                return False, response.text
        except Exception as e:
            logger.error(f"获取影院信息失败: {e}")
            return False, ""


cinema_scraper = CinemaScraper()
