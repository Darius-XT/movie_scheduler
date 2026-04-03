"""解析指定电影在指定日期下的影院分页 JSON。"""

from __future__ import annotations

import json
from typing import TypedDict, cast

from app.core.logger import logger


class PagingData(TypedDict, total=False):
    """分页信息。"""

    hasMore: bool


class CinemaData(TypedDict, total=False):
    """单个影院条目。"""

    id: int


class DataSection(TypedDict, total=False):
    """接口 data 字段。"""

    cinemas: list[CinemaData]
    paging: PagingData


class RootData(TypedDict, total=False):
    """接口根结构。"""

    data: DataSection


class CinemaParser:
    """解析影院分页结果。"""

    def parse_cinemas(self, json_content: str) -> tuple[list[int], bool]:
        """提取影院 ID 列表，并判断是否为最后一页。"""
        try:
            logger.debug("解析影院 JSON 内容")

            if not json_content or not json_content.strip():
                logger.debug("JSON 内容为空字符串")
                return [], False

            parsed = json.loads(json_content)
            if not parsed or not isinstance(parsed, dict) or "data" not in parsed:
                logger.warning("JSON 结构不正确，缺少 data 字段")
                return [], False

            root_data = cast(RootData, parsed)
            data_section = root_data.get("data")
            if data_section is None or "cinemas" not in data_section:
                logger.warning("JSON 结构不正确，缺少 data.cinemas 字段")
                return [], False

            cinemas_data = data_section.get("cinemas", [])
            if not cinemas_data:
                logger.warning("cinemas 字段为空")
                return [], False

            cinema_ids: list[int] = []
            for cinema_data in cinemas_data:
                cinema_id = cinema_data.get("id")
                if cinema_id is not None:
                    cinema_ids.append(int(cinema_id))

            paging = data_section.get("paging", {})
            has_more = paging.get("hasMore", True)
            is_last_page = has_more is False

            if is_last_page:
                logger.debug("检测到 hasMore 为 false，这表示最后一页")

            logger.debug("成功解析 %s 个影院 ID", len(cinema_ids))
            return cinema_ids, is_last_page
        except json.JSONDecodeError as error:
            logger.error("解析 JSON 失败: %s", error)
            return [], False
        except Exception as error:
            logger.error("解析影院列表失败: %s", error)
            return [], False


cinema_parser = CinemaParser()
