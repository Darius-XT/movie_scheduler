"""更新电影详情用爬取器(由 get_movie_details 迁移并内联)"""

import requests
import urllib3
from src.utils.logger import logger
from src.utils.file_saver import file_saver


urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class JsonWithSingleMovieExtraInfoScraper:
    def __init__(self):
        self.base_url = "https://apis.netstart.cn/maoyan/movie/intro"
        self.timeout = 30

    def scrape_json_with_single_movie_extra_info(
        self, movie_id: int
    ) -> tuple[bool, str]:
        """爬取单个电影的详情JSON数据

        Args:
            movie_id (int): 电影ID。
                示例值: 123456

        Returns:
            tuple[bool, str]: (是否成功, JSON内容)
                第一个元素是布尔值，True 表示请求成功（HTTP状态码200），False 表示失败。
                第二个元素是JSON内容字符串，如果失败则为空字符串 ""。
                示例返回值: (True, '{"data": {"movie": {...}}}') 或 (False, "")
        """
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


json_with_single_movie_extra_info_scraper = JsonWithSingleMovieExtraInfoScraper()

if __name__ == "__main__":
    success, json_content = (
        json_with_single_movie_extra_info_scraper.scrape_json_with_single_movie_extra_info(
            1292180
        )
    )
    if success:
        file_saver.save_file(json_content, file_type="json")
