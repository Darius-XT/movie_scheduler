"""解析指定影院下某部电影的全部场次 JSON。"""

from __future__ import annotations

import json
import re
from typing import TypedDict, cast

from app.core.logger import logger
from app.use_cases.show_fetching.models import FetchedShowItem


class ShowItemData(TypedDict, total=False):
    """单条场次。"""

    tm: str
    discountSellPrice: str | int | float
    vipDisPrice: str | int | float
    vipPrice: str | int | float


class ShowDateGroupData(TypedDict, total=False):
    """按日期分组的场次。"""

    showDate: str
    plist: list[ShowItemData]


class MovieShowData(TypedDict, total=False):
    """单部电影的场次集合。"""

    id: int
    nm: str
    shows: list[ShowDateGroupData]


class CinemaShowsData(TypedDict, total=False):
    """影院场次 data 字段。"""

    cinemaId: int
    cinemaName: str
    movies: list[MovieShowData]


class RootData(TypedDict, total=False):
    """接口根结构。"""

    data: CinemaShowsData


class CinemaShowParser:
    """解析影院场次列表。"""

    def parse_cinema_shows(
        self,
        json_content: str,
        movie_name: str,
        target_show_date: str | None = None,
    ) -> list[FetchedShowItem]:
        """按电影名筛选出指定电影的场次，可选限制到指定日期。"""
        try:
            logger.debug("解析影院场次 JSON，筛选电影: %s", movie_name)

            if not json_content or not json_content.strip():
                logger.debug("JSON 内容为空字符串")
                return []

            parsed = json.loads(json_content)
            if not parsed or not isinstance(parsed, dict) or "data" not in parsed:
                logger.warning("JSON 结构不正确，缺少 data 字段")
                return []

            root_data = cast(RootData, parsed)
            data_section = root_data.get("data")
            if data_section is None:
                logger.warning("data 字段为空")
                return []

            cinema_id = data_section.get("cinemaId")
            cinema_name = data_section.get("cinemaName", "")
            movies = data_section.get("movies", [])
            if not movies:
                logger.warning("movies 字段为空")
                return []

            target_movie: MovieShowData | None = None
            for movie in movies:
                if movie.get("nm", "") == movie_name:
                    target_movie = movie
                    break

            if target_movie is None:
                logger.warning("未找到电影: %s", movie_name)
                return []

            shows = target_movie.get("shows", [])
            if not shows:
                logger.warning("shows 字段为空")
                return []

            movie_id = target_movie.get("id")
            result: list[FetchedShowItem] = []
            for show_date_group in shows:
                show_date = show_date_group.get("showDate", "")
                if target_show_date is not None and show_date != target_show_date:
                    continue
                plist = show_date_group.get("plist", [])
                for show_item in plist:
                    result.append(
                        FetchedShowItem(
                            movie_id=movie_id,
                            movie_name=movie_name,
                            show_date=show_date,
                            show_time=str(show_item.get("tm", "")),
                            price=self._extract_price(show_item),
                            cinema_id=cinema_id,
                            cinema_name=str(cinema_name),
                        )
                    )

            logger.debug("成功解析 %s 个场次", len(result))
            return result
        except json.JSONDecodeError as error:
            logger.error("解析 JSON 失败: %s", error)
            return []
        except Exception as error:
            logger.error("解析场次信息失败: %s", error)
            return []

    def _extract_price(self, show_item: ShowItemData) -> str:
        """提取可展示的价格文本。"""
        raw_price = self._normalize_price_value(show_item.get("discountSellPrice"))
        if raw_price is not None:
            return raw_price

        vip_discount_price = self._normalize_price_value(show_item.get("vipDisPrice"))
        if vip_discount_price is not None:
            return vip_discount_price

        vip_price = self._normalize_price_value(show_item.get("vipPrice"))
        if vip_price is not None:
            return vip_price

        return "0"

    def _normalize_price_value(self, raw_value: str | int | float | None) -> str | None:
        """归一化价格字段，过滤 stonefont HTML 片段。"""
        if raw_value is None:
            return None

        if isinstance(raw_value, (int, float)):
            return str(raw_value)

        normalized_value = raw_value.strip()
        if not normalized_value:
            return None
        if "stonefont" in normalized_value:
            return None

        match = re.search(r"\d+(?:\.\d+)?", normalized_value)
        if match is not None:
            return match.group(0)

        return normalized_value


cinema_show_parser = CinemaShowParser()
