"""抓取指定影院的场次 JSON。"""

from __future__ import annotations

import requests
import urllib3

from app.core.config import config_manager
from app.core.logger import logger

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class CinemaShowScraper:
    def __init__(self) -> None:
        self.base_url = "https://apis.netstart.cn/maoyan/cinema/shows"
        self.timeout = 30

    def scrape_cinema_shows(
        self,
        cinema_id: int,
        city_id: int | None = None,
    ) -> tuple[bool, str]:
        """抓取指定影院的全部场次 JSON 数据。"""
        try:
            normalized_city_id = city_id if city_id is not None else (config_manager.city_id or 10)
            normalized_city_id = int(normalized_city_id)

            url = f"{self.base_url}?cinemaId={cinema_id}&ci={normalized_city_id}"
            logger.debug("开始获取影院场次信息: %s", url)

            headers = {
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7",
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
                "Referer": "https://www.maoyan.com/",
                "Origin": "https://www.maoyan.com",
            }

            response = requests.get(url, headers=headers, timeout=self.timeout, verify=False)
            logger.debug("响应状态码: %s", response.status_code)
            logger.debug("响应长度: %s 字符", len(response.text))

            if response.status_code == 200:
                logger.debug("成功获取影院场次 JSON")
                return True, response.text

            logger.warning("请求失败，状态码: %s", response.status_code)
            return False, response.text
        except Exception as error:
            logger.error("获取影院场次信息失败: %s", error)
            return False, ""


cinema_show_scraper = CinemaShowScraper()
