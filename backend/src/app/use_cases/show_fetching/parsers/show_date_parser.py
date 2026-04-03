"""解析电影可用放映日期 JSON。"""

from __future__ import annotations

import json
from typing import cast

from app.core.logger import logger


class ShowDateParser:
    """解析电影可用放映日期。"""

    def parse_showdate(self, json_content: str) -> list[str]:
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


show_date_parser = ShowDateParser()
