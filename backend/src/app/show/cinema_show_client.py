"""影院场次客户端：合并 scraper + parser，对外返回业务对象。"""

from __future__ import annotations

import json
import re
from typing import TypedDict, cast

import requests
import urllib3

from app.core.config import config_manager
from app.core.exceptions import DataParsingError, ExternalDependencyError
from app.core.logger import logger
from app.show.entities import FetchedShowItem

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


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


class CinemaShowClient:
    """合并 HTTP 抓取与 JSON 解析，返回场次列表。"""

    def __init__(self) -> None:
        self.base_url = "https://apis.netstart.cn/maoyan/cinema/shows"
        self.timeout = 30

    def get_cinema_shows(
        self,
        cinema_id: int,
        city_id: int,
        movie_name: str,
        show_date: str | None = None,
    ) -> list[FetchedShowItem]:
        """获取指定影院中某部电影的场次，可选限制到指定日期。

        Raises:
            ExternalDependencyError: HTTP 请求失败。
            DataParsingError: 解析结果为空。
        """
        json_content = self._fetch(cinema_id, city_id)
        if json_content is None:
            raise ExternalDependencyError(
                f"获取影院 {cinema_id} 在城市 {city_id} 的场次信息失败"
            )

        show_items = self.parse(json_content, movie_name, show_date)
        if not show_items:
            raise DataParsingError(
                f"影院 {cinema_id} 在城市 {city_id} 的场次信息解析结果为空，show_date={show_date}"
            )

        return show_items

    def fetch_raw(self, cinema_id: int, city_id: int) -> str | None:
        """返回影院场次原始 JSON，供调试采样使用。"""
        return self._fetch(cinema_id, city_id)

    # ------------------------------------------------------------------
    # 私有：HTTP
    # ------------------------------------------------------------------

    def _fetch(self, cinema_id: int, city_id: int | None) -> str | None:
        """发起 HTTP 请求，失败返回 None。"""
        try:
            normalized_city_id = int(city_id if city_id is not None else (config_manager.city_id or 10))

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
                return response.text

            logger.warning("请求失败，状态码: %s", response.status_code)
            return None
        except Exception as error:
            logger.error("获取影院场次信息失败: %s", error)
            return None

    # ------------------------------------------------------------------
    # 解析（public，供测试直接调用）
    # ------------------------------------------------------------------

    def parse(
        self,
        json_content: str,
        movie_name: str,
        target_show_date: str | None = None,
    ) -> list[FetchedShowItem]:
        """按电影名筛选出指定电影的场次，可选限制到指定日期。"""
        try:
            logger.debug("解析影院场次 JSON，筛选电影: %s", movie_name)
            if not json_content or not json_content.strip():
                return []

            parsed = json.loads(json_content)
            if not parsed or not isinstance(parsed, dict) or "data" not in parsed:
                logger.warning("JSON 结构不正确，缺少 data 字段")
                return []

            root_data = cast(RootData, parsed)
            data_section = root_data.get("data")
            if data_section is None:
                return []

            cinema_id = data_section.get("cinemaId")
            cinema_name = str(data_section.get("cinemaName", ""))
            movies = data_section.get("movies", [])

            target_movie = self._find_target_movie(movies, movie_name)
            if target_movie is None:
                logger.warning("未找到电影: %s", movie_name)
                return []

            shows = target_movie.get("shows", [])
            if not shows:
                return []

            result = self._build_show_items(
                shows, target_movie.get("id"), movie_name, cinema_id, cinema_name, target_show_date
            )
            logger.debug("成功解析 %s 个场次", len(result))
            return result
        except json.JSONDecodeError as error:
            logger.error("解析 JSON 失败: %s", error)
            return []
        except Exception as error:
            logger.error("解析场次信息失败: %s", error)
            return []

    def _find_target_movie(
        self,
        movies: list[MovieShowData],
        movie_name: str,
    ) -> MovieShowData | None:
        """从电影列表中找到匹配名称的电影。"""
        for movie in movies:
            if movie.get("nm", "") == movie_name:
                return movie
        return None

    def _build_show_items(
        self,
        shows: list[ShowDateGroupData],
        movie_id: int | None,
        movie_name: str,
        cinema_id: int | None,
        cinema_name: str,
        target_show_date: str | None,
    ) -> list[FetchedShowItem]:
        """从场次分组中构建 FetchedShowItem 列表。"""
        result: list[FetchedShowItem] = []
        for show_date_group in shows:
            show_date = show_date_group.get("showDate", "")
            if target_show_date is not None and show_date != target_show_date:
                continue
            for show_item in show_date_group.get("plist", []):
                result.append(FetchedShowItem(
                    movie_id=movie_id,
                    movie_name=movie_name,
                    show_date=show_date,
                    show_time=str(show_item.get("tm", "")),
                    price=self._extract_price(show_item),
                    cinema_id=cinema_id,
                    cinema_name=cinema_name,
                ))
        return result

    def _extract_price(self, show_item: ShowItemData) -> str:
        """提取可展示的价格文本。"""
        for field in ("discountSellPrice", "vipDisPrice", "vipPrice"):
            price = self._normalize_price_value(show_item.get(field))  # type: ignore[literal-required]
            if price is not None:
                return price
        return "0"

    def _normalize_price_value(self, raw_value: str | int | float | None) -> str | None:
        """归一化价格字段，过滤 stonefont HTML 片段。"""
        if raw_value is None:
            return None
        if isinstance(raw_value, (int, float)):
            return str(raw_value)
        normalized_value = raw_value.strip()
        if not normalized_value or "stonefont" in normalized_value:
            return None
        match = re.search(r"\d+(?:\.\d+)?", normalized_value)
        return match.group(0) if match is not None else normalized_value


cinema_show_client = CinemaShowClient()
