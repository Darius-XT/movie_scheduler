"""日期客户端：抓取电影在城市内有哪些上映日期。"""

from __future__ import annotations

import json
from typing import cast

from app.core.exceptions import DataParsingError, ExternalDependencyError
from app.core.logger import logger
from app.show.request_helper import fetch_show_api_text


class DateClient:
    """合并 HTTP 抓取与 JSON 解析，直接返回放映日期列表。"""

    def __init__(self) -> None:
        self.base_url = "https://apis.netstart.cn/maoyan/movie/showdays"
        self.timeout = 30

    def get_show_dates(self, movie_id: int, city_id: int) -> list[str]:
        """获取指定电影在指定城市的可用放映日期。

        Raises:
            ExternalDependencyError: HTTP 请求失败。
            DataParsingError: 解析结果为空或无效。
        """
        json_content = self._fetch(movie_id, city_id)
        if json_content is None:
            raise ExternalDependencyError(
                f"获取电影 {movie_id} 在城市 {city_id} 的排片日期失败"
            )

        dates = self.parse(json_content)
        if not dates:
            raise DataParsingError(
                f"电影 {movie_id} 在城市 {city_id} 的排片日期解析结果为空"
            )

        return dates

    # ------------------------------------------------------------------
    # 私有：HTTP
    # ------------------------------------------------------------------

    def _fetch(self, movie_id: int, city_id: int) -> str | None:
        """发起 HTTP 请求，失败返回 None。"""
        normalized_city_id = int(city_id)
        url = f"{self.base_url}?movieId={movie_id}&cityId={normalized_city_id}"
        return fetch_show_api_text(url, self.timeout, "抓取放映日期信息")

    # ------------------------------------------------------------------
    # 解析（public，供测试直接调用）
    # ------------------------------------------------------------------

    def parse(self, json_content: str) -> list[str]:
        """提取响应中的全部可用放映日期。"""
        try:
            logger.debug("开始解析放映日期 JSON")
            payload = json.loads(json_content)
        except json.JSONDecodeError as error:
            logger.error("解析放映日期 JSON 失败: %s", error)
            return []

        if not isinstance(payload, dict):
            logger.warning("放映日期响应不是对象结构")
            return []

        payload_dict = cast(dict[str, object], payload)
        if payload_dict.get("success") is not True:
            logger.warning("放映日期接口未返回成功结果: %s", payload_dict.get("errMsg", ""))
            return []

        data = payload_dict.get("data")
        if not isinstance(data, dict):
            logger.warning("放映日期响应缺少 data 对象")
            return []

        data_dict = cast(dict[str, object], data)
        raw_dates = data_dict.get("dates")
        if not isinstance(raw_dates, list):
            logger.warning("放映日期响应缺少 dates 列表")
            return []

        raw_dates_list = cast(list[object], raw_dates)
        dates: list[str] = []
        for raw_date in raw_dates_list:
            if not isinstance(raw_date, dict):
                continue
            raw_date_dict = cast(dict[str, object], raw_date)
            date_value = raw_date_dict.get("date")
            if isinstance(date_value, str) and date_value:
                dates.append(date_value)

        logger.debug("成功解析 %s 个放映日期", len(dates))
        return dates


date_client = DateClient()
