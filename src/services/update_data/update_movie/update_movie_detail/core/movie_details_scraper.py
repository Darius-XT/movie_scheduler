"""更新电影详情用爬取器(由 get_movie_details 迁移并内联)"""

import requests
import urllib3
from src.logger import logger


urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class UpdateMovieDetailScraper:
    def __init__(self):
        self.base_url = "https://apis.netstart.cn/maoyan/movie/intro"
        self.timeout = 30

    def scrape_movie_details(self, movie_id: int) -> tuple[bool, str]:
        try:
            url = f"{self.base_url}?movieId={movie_id}"
            logger.debug(f"开始获取电影详情: {url}")

            headers = {
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7",
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
                "Referer": "https://www.maoyan.com/",
                "Origin": "https://www.maoyan.com",
            }

            response = requests.get(
                url, headers=headers, timeout=self.timeout, verify=False
            )

            logger.debug(f"响应状态码: {response.status_code}")
            logger.debug(f"响应长度: {len(response.text)} 字符")

            if response.status_code == 200:
                logger.debug("成功获取电影详情信息")
                return True, response.text
            else:
                logger.warning(f"请求失败，状态码: {response.status_code}")
                return False, response.text
        except Exception as e:
            logger.error(f"获取电影详情失败: {e}")
            return False, ""


update_movie_detail_scraper = UpdateMovieDetailScraper()
