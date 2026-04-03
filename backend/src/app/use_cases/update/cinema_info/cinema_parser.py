"""解析影院批量更新接口返回的 JSON。"""

from __future__ import annotations

import json
from typing import TypedDict, cast

from app.core.logger import logger
from app.use_cases.update.cinema_info.models import CinemaUpsertData


class FirstPageCinemaInfo(TypedDict, total=False):
    """第一页影院 `info` 字段。"""

    name: str
    address: str
    price: str | int | float
    tags: list[str]


class FirstPageCinemaData(TypedDict, total=False):
    """第一页影院条目。"""

    id: int
    info: FirstPageCinemaInfo


class OtherPageCinemaData(TypedDict, total=False):
    """后续页影院条目。"""

    id: int
    nm: str
    addr: str
    sellPrice: str | int | float
    allowRefund: int | bool
    endorse: int | bool


class OtherPagePayload(TypedDict, total=False):
    """后续页响应体。"""

    total: int
    cinemas: list[OtherPageCinemaData]


class CinemaInfoParser:
    """解析影院批量更新结果。"""

    def parse_cinemas(
        self,
        json_content: str,
    ) -> tuple[list[CinemaUpsertData], bool]:
        """返回影院列表，以及是否遇到预期中的空页。"""
        try:
            logger.debug("解析影院 JSON 内容")
            if not json_content or not json_content.strip():
                logger.debug("JSON 内容为空字符串")
                return [], False

            parsed = json.loads(json_content)
            if not parsed:
                logger.debug("JSON 数据为空")
                return [], False

            cinemas: list[CinemaUpsertData] = []
            if isinstance(parsed, list):
                for cinema_data in cast(list[FirstPageCinemaData], parsed):
                    cinema = self._extract_first_page_cinema(cinema_data)
                    if cinema is not None:
                        cinemas.append(cinema)
                return cinemas, False

            if isinstance(parsed, dict) and "cinemas" in parsed:
                payload = cast(OtherPagePayload, parsed)
                if payload.get("total") == 0:
                    logger.debug("检测到 total 为 0，这是预期中的空页")
                    return [], True

                for cinema_data in payload.get("cinemas", []):
                    cinema = self._extract_other_page_cinema(cinema_data)
                    if cinema is not None:
                        cinemas.append(cinema)
                return cinemas, False

            logger.warning("未知的影院 JSON 结构")
            return [], False
        except json.JSONDecodeError as error:
            logger.error("解析 JSON 失败: %s", error)
            return [], False
        except Exception as error:
            logger.error("解析影院列表失败: %s", error)
            return [], False

    def _extract_first_page_cinema(self, cinema_data: FirstPageCinemaData) -> CinemaUpsertData | None:
        try:
            info = cinema_data.get("info", {})
            price = info.get("price", "0")
            normalized_price = "暂无票价"
            if price and price != "0" and (not isinstance(price, str) or price.strip()):
                normalized_price = str(price)

            tags = info.get("tags", [])
            return CinemaUpsertData(
                id=cinema_data.get("id"),
                name=str(info.get("name") or "暂无名称"),
                address=str(info.get("address") or "暂无地址"),
                price=normalized_price,
                allow_refund="退" in tags,
                allow_endorse="改签" in tags,
            )
        except Exception as error:
            logger.error("解析首页影院数据失败: %s", error)
            return None

    def _extract_other_page_cinema(self, cinema_data: OtherPageCinemaData) -> CinemaUpsertData | None:
        try:
            price = cinema_data.get("sellPrice", "0")
            normalized_price = "暂无票价"
            if price and price != "0" and (not isinstance(price, str) or price.strip()):
                normalized_price = str(price)

            return CinemaUpsertData(
                id=cinema_data.get("id"),
                name=str(cinema_data.get("nm") or "暂无名称"),
                address=str(cinema_data.get("addr") or "暂无地址"),
                price=normalized_price,
                allow_refund=bool(cinema_data.get("allowRefund", 0)),
                allow_endorse=bool(cinema_data.get("endorse", 0)),
            )
        except Exception as error:
            logger.error("解析后续页影院数据失败: %s", error)
            return None


cinema_info_parser = CinemaInfoParser()
