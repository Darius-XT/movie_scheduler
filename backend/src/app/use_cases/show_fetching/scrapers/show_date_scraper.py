"""抓取指定电影可用放映日期的原始 JSON。"""

from __future__ import annotations

import requests
import urllib3

from app.core.config import config_manager
from app.core.logger import logger

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class ShowDateScraper:
    """抓取电影可用放映日期。"""

    def __init__(self) -> None:
        self.base_url = "https://apis.netstart.cn/maoyan/movie/showdays"
        self.timeout = 30
        self.headers = {
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
            "Referer": "https://www.maoyan.com/",
            "Origin": "https://www.maoyan.com",
        }

    def scrape_showdate(
        self,
        movie_id: int,
        city_id: int | None = None,
    ) -> tuple[bool, str]:
        """抓取指定电影的可用放映日期 JSON。"""
        try:
            normalized_city_id = city_id if city_id is not None else (config_manager.city_id or 10)
            normalized_city_id = int(normalized_city_id)
            url = f"{self.base_url}?movieId={movie_id}&cityId={normalized_city_id}"
            logger.debug(
                "开始抓取放映日期信息: movieId=%s, cityId=%s, url=%s",
                movie_id,
                normalized_city_id,
                url,
            )

            response = requests.get(
                url,
                headers=self.headers,
                timeout=self.timeout,
                verify=False,
            )

            logger.debug("响应状态码: %s", response.status_code)
            logger.debug("响应长度: %s 字符", len(response.text))

            if response.status_code == 200:
                logger.debug("成功获取放映日期 JSON")
                return True, response.text

            logger.warning("请求失败，状态码: %s", response.status_code)
            return False, ""
        except Exception as error:
            logger.error("获取放映日期信息失败: %s", error)
            return False, ""


show_date_scraper = ShowDateScraper()
