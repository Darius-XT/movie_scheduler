"""场次服务: 抓取猫眼场次/日期/影院 → 解析 → 落库 + 读取。

将原 show/ 下 cinema_client + date_client + show_client + request_helper +
fetcher + gateway + result_builder + entities + service 全部并入此处。
"""

from __future__ import annotations

import asyncio
import json
import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime
from typing import TypedDict, cast

import requests
import urllib3

from movie_scheduler.config import config_manager
from movie_scheduler.core.exceptions import (
    AppError,
    DataParsingError,
    ExternalDependencyError,
    RepositoryError,
)
from movie_scheduler.core.logging import logger
from movie_scheduler.features.movie.repository import movie_repository
from movie_scheduler.features.show.models import MovieShowWriteData
from movie_scheduler.features.show.repository import movie_show_repository

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


# =============================================================================
# 内部数据结构
# =============================================================================

@dataclass(slots=True)
class _FetchedShowItem:
    """上游抓取到的单条原始场次。"""

    movie_id: int | None
    movie_name: str
    show_date: str
    show_time: str
    price: str
    cinema_id: int | None
    cinema_name: str


@dataclass(slots=True)
class _ShowItem:
    date: str
    time: str
    price: str


def _empty_show_items() -> list[_ShowItem]:
    return []


def _empty_cinema_map() -> dict[int, _CinemaShowData]:
    return {}


@dataclass(slots=True)
class _CinemaShowData:
    cinema_id: int
    cinema_name: str
    shows: list[_ShowItem] = field(default_factory=_empty_show_items)


@dataclass(slots=True)
class _MovieShowData:
    movie_id: int
    movie_name: str
    cinemas: dict[int, _CinemaShowData] = field(default_factory=_empty_cinema_map)


@dataclass(slots=True)
class _FinalMovieShowData:
    movie_id: int
    cinemas: list[_CinemaShowData]


_DegradableError = (ExternalDependencyError, DataParsingError)


# =============================================================================
# 外部 HTTP 请求公共配置
# =============================================================================

_SHOW_REQUEST_HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7",
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.maoyan.com/",
    "Origin": "https://www.maoyan.com",
}

_SHOW_API_TIMEOUT = 30
_SHOW_DATES_BASE = "https://apis.netstart.cn/maoyan/movie/showdays"
_CINEMA_LIST_BASE = "https://apis.netstart.cn/maoyan/movie/select/cinemas"
_CINEMA_SHOWS_BASE = "https://apis.netstart.cn/maoyan/cinema/shows"


def _http_get_text(url: str, log_label: str) -> str | None:
    """抓取外部接口文本,失败返回 None。"""
    try:
        logger.debug("开始%s: %s", log_label, url)
        response = requests.get(url, headers=_SHOW_REQUEST_HEADERS, timeout=_SHOW_API_TIMEOUT, verify=False)
        logger.debug("%s响应状态码: %s,响应长度: %s 字符", log_label, response.status_code, len(response.text))
        if response.status_code == 200:
            return response.text
        logger.error(
            "%s请求失败: status=%s, url=%s, response=%s",
            log_label, response.status_code, url, response.text[:1000],
        )
        return None
    except Exception as error:
        logger.error("%s异常: url=%s, error=%s", log_label, url, error, exc_info=True)
        return None


# =============================================================================
# JSON 解析类型(date/cinema/show 三个上游接口)
# =============================================================================

class _CinemaItemForList(TypedDict, total=False):
    id: int


class _CinemaListPaging(TypedDict, total=False):
    hasMore: bool


class _CinemaListDataSection(TypedDict, total=False):
    cinemas: list[_CinemaItemForList]
    paging: _CinemaListPaging


class _CinemaListRoot(TypedDict, total=False):
    data: _CinemaListDataSection


class _ShowItemRaw(TypedDict, total=False):
    tm: str
    discountSellPrice: str | int | float
    vipDisPrice: str | int | float
    vipPrice: str | int | float


class _ShowDateGroupRaw(TypedDict, total=False):
    showDate: str
    plist: list[_ShowItemRaw]


class _MovieShowRaw(TypedDict, total=False):
    id: int
    nm: str
    shows: list[_ShowDateGroupRaw]


class _CinemaShowsRaw(TypedDict, total=False):
    cinemaId: int
    cinemaName: str
    movies: list[_MovieShowRaw]


class _CinemaShowsRoot(TypedDict, total=False):
    data: _CinemaShowsRaw


# =============================================================================
# Service
# =============================================================================

class ShowService:
    """聚合场次抓取与持久化能力。"""

    # ---------- 对外: 定时抓取 + 单片抓取 ----------

    async def refresh_wished_movie_shows(self, city_id: int | None = None) -> int:
        """抓取所有想看电影的场次并写入数据库,返回有场次的电影数。"""
        normalized_city_id = self._normalize_city_id(city_id)
        wished_movies = await asyncio.to_thread(movie_repository.list_wished_movies)
        movie_ids = [int(mid) for m in wished_movies if (mid := cast(int | None, getattr(m, "id", None))) is not None]

        if not movie_ids:
            logger.info("场次定时抓取:想看列表为空,跳过")
            return 0

        try:
            results = await self._fetch_shows_for_selected_movies(movie_ids, city_id=normalized_city_id)
            success_count = await self._persist_results(movie_ids, results)
            logger.info("场次定时抓取完成: %s/%s 部电影有场次", success_count, len(movie_ids))
            return success_count
        except Exception as error:
            logger.error("场次定时抓取失败: %s", error)
            return 0

    async def refresh_movie_shows(self, movie_id: int, city_id: int | None = None) -> int:
        """抓取单部想看电影的场次并写入数据库。"""
        normalized_city_id = self._normalize_city_id(city_id)
        movie = await asyncio.to_thread(movie_repository.get_movie_by_id, movie_id)
        if movie is None:
            logger.warning("单片场次抓取跳过,电影不存在: %s", movie_id)
            return 0
        if not bool(movie.is_wished):
            await asyncio.to_thread(movie_show_repository.delete_for_movie, movie_id)
            logger.info("单片场次抓取跳过,电影不在想看: %s", movie_id)
            return 0

        try:
            results = await self._fetch_shows_for_selected_movies([movie_id], city_id=normalized_city_id)
            success_count = await self._persist_results([movie_id], results)
            logger.info("单片场次抓取完成: 电影 %s, 成功数 %s", movie_id, success_count)
            return success_count
        except Exception as error:
            logger.error("单片场次抓取失败,电影 %s: %s", movie_id, error)
            return 0

    # ---------- 对外: 读 ----------

    async def get_shows_for_wished_movies(self, movie_id: int | None = None) -> dict[str, object]:
        """返回前端需要的 wishMovies 场次结构 + 最近一次抓取完成时间。"""
        if movie_id is not None:
            return await self._get_shows_for_single_wished_movie(movie_id)

        wished_movies = await asyncio.to_thread(movie_repository.list_wished_movies)
        movie_ids = [int(mid) for m in wished_movies if (mid := cast(int | None, getattr(m, "id", None))) is not None]
        shows = await asyncio.to_thread(movie_show_repository.list_for_movies, movie_ids)
        latest = await asyncio.to_thread(movie_repository.get_latest_shows_updated_at, movie_ids)

        return {
            "movies": self._build_movies_payload(movie_ids, shows),
            "last_fetched_at": self._serialize_datetime(latest),
        }

    async def _get_shows_for_single_wished_movie(self, movie_id: int) -> dict[str, object]:
        movie = await asyncio.to_thread(movie_repository.get_movie_by_id, movie_id)
        if movie is None:
            raise AppError(f"电影不存在: {movie_id}", status_code=404)
        if not bool(movie.is_wished):
            return {"movies": [], "last_fetched_at": None}

        shows = await asyncio.to_thread(movie_show_repository.list_for_movies, [movie_id])
        shows_updated_at = cast(datetime | None, getattr(movie, "shows_updated_at", None))
        return {
            "movies": self._build_movies_payload([movie_id], shows),
            "last_fetched_at": self._serialize_datetime(shows_updated_at),
        }

    # ---------- 内部: 批量抓取编排 ----------

    async def _fetch_shows_for_selected_movies(
        self,
        movie_ids: list[int],
        city_id: int,
    ) -> list[_FinalMovieShowData]:
        """异步抓取选中电影的所有场次。"""
        logger.info("开始异步获取 %s 部电影在城市 %s 的场次信息", len(movie_ids), city_id)

        tasks = [self._process_single_movie(movie_id, city_id) for movie_id in movie_ids]
        movie_results = await asyncio.gather(*tasks, return_exceptions=True)

        result = self._collect_valid_movie_results(movie_results)
        total_shows = sum(len(c.shows) for m in result for c in m.cinemas)
        logger.info("总共找到 %s 部电影, %s 个场次信息", len(result), total_shows)
        return result

    async def _process_single_movie(
        self,
        movie_id: int,
        city_id: int,
    ) -> _FinalMovieShowData | None:
        try:
            movie_name = await asyncio.to_thread(self._get_movie_name, movie_id)
            if not movie_name:
                logger.warning("无法获取电影名称,跳过电影 ID: %s", movie_id)
                return None

            movie_data = _MovieShowData(movie_id=movie_id, movie_name=movie_name)
            show_dates = await asyncio.to_thread(self._get_show_dates, movie_id, city_id)
            logger.debug("找到 %s 个排片日期: %s", len(show_dates), show_dates)

            date_tasks = [
                self._process_single_date(movie_id, movie_name, city_id, show_date)
                for show_date in show_dates
            ]
            date_results = await asyncio.gather(*date_tasks, return_exceptions=True)

            for date_result in date_results:
                if isinstance(date_result, BaseException):
                    if isinstance(date_result, _DegradableError):
                        logger.warning("处理日期时发生可降级错误,跳过当前日期: %s", date_result)
                        continue
                    raise date_result
                if isinstance(date_result, dict):
                    self._merge_cinemas(movie_data, date_result)

            return self._finalize_movie(movie_data)
        except BaseException as error:
            if isinstance(error, _DegradableError):
                logger.warning("处理电影 ID %s 时发生可降级错误,跳过当前电影: %s", movie_id, error)
                return None
            logger.error("处理电影 ID %s 时发生不可恢复错误: %s", movie_id, error)
            raise

    async def _process_single_date(
        self,
        movie_id: int,
        movie_name: str,
        city_id: int,
        show_date: str,
    ) -> dict[int, _CinemaShowData] | None:
        try:
            cinema_ids = await asyncio.to_thread(self._get_cinemas, movie_id, show_date, city_id)
            if not cinema_ids:
                return None

            cinema_tasks = [
                asyncio.to_thread(self._get_cinema_shows, cinema_id, city_id, movie_name, show_date)
                for cinema_id in cinema_ids
            ]
            cinema_results = await asyncio.gather(*cinema_tasks, return_exceptions=True)

            valid: list[list[_FetchedShowItem]] = []
            for cinema_result in cinema_results:
                if isinstance(cinema_result, BaseException):
                    if isinstance(cinema_result, _DegradableError):
                        logger.warning("获取影院场次时发生可降级错误,跳过当前影院: %s", cinema_result)
                        continue
                    raise cinema_result
                valid.append(cinema_result)

            return self._build_cinemas_from_shows(valid)
        except BaseException as error:
            if isinstance(error, _DegradableError):
                logger.warning("处理日期 %s 时发生可降级错误,跳过当前日期: %s", show_date, error)
                return None
            logger.error("处理日期 %s 时发生不可恢复错误: %s", show_date, error)
            raise

    # ---------- 内部: 上游 HTTP 调用 ----------

    def _get_movie_name(self, movie_id: int) -> str | None:
        movie = movie_repository.get_movie_by_id(movie_id)
        if movie is None:
            return None
        return cast(str | None, getattr(movie, "title", None))

    def _get_show_dates(self, movie_id: int, city_id: int) -> list[str]:
        url = f"{_SHOW_DATES_BASE}?movieId={movie_id}&cityId={int(city_id)}"
        text = _http_get_text(url, "抓取放映日期信息")
        if text is None:
            raise ExternalDependencyError(f"获取电影 {movie_id} 在城市 {city_id} 的排片日期失败")
        dates = self._parse_show_dates(text)
        if not dates:
            raise DataParsingError(f"电影 {movie_id} 在城市 {city_id} 的排片日期解析结果为空")
        return dates

    def _get_cinemas(self, movie_id: int, show_date: str, city_id: int) -> list[int]:
        all_cinema_ids: list[int] = []
        limit = 20
        offset = 0
        while True:
            cinema_ids, is_last_page = self._fetch_cinema_page(movie_id, show_date, city_id, limit, offset)
            all_cinema_ids.extend(cinema_ids)
            if is_last_page:
                return all_cinema_ids
            offset += limit

    def _fetch_cinema_page(
        self,
        movie_id: int,
        show_date: str,
        city_id: int,
        limit: int,
        offset: int,
    ) -> tuple[list[int], bool]:
        url = (
            f"{_CINEMA_LIST_BASE}?limit={limit}&offset={offset}"
            f"&showDate={show_date}&movieId={movie_id}&cityId={int(city_id)}"
        )
        text = _http_get_text(url, "获取影院信息")
        if text is None:
            raise ExternalDependencyError(
                f"获取影院信息失败,movie_id={movie_id}, city_id={city_id}, show_date={show_date}, offset={offset}"
            )
        cinema_ids, is_last_page = self._parse_cinema_list(text)
        if not cinema_ids and not is_last_page:
            raise DataParsingError(
                f"影院分页解析结果为空,movie_id={movie_id}, city_id={city_id}, show_date={show_date}, offset={offset}"
            )
        return cinema_ids, is_last_page

    def _get_cinema_shows(
        self,
        cinema_id: int,
        city_id: int,
        movie_name: str,
        show_date: str | None = None,
    ) -> list[_FetchedShowItem]:
        url = f"{_CINEMA_SHOWS_BASE}?cinemaId={cinema_id}&ci={int(city_id)}"
        text = _http_get_text(url, "获取影院场次信息")
        if text is None:
            raise ExternalDependencyError(f"获取影院 {cinema_id} 在城市 {city_id} 的场次信息失败")
        items = self._parse_cinema_shows(text, movie_name, show_date)
        if not items:
            raise DataParsingError(
                f"影院 {cinema_id} 在城市 {city_id} 的场次信息解析结果为空, show_date={show_date}"
            )
        return items

    # ---------- 内部: JSON 解析 ----------

    def _parse_show_dates(self, json_content: str) -> list[str]:
        try:
            payload = json.loads(json_content)
        except json.JSONDecodeError as error:
            logger.error("解析放映日期 JSON 失败: %s", error)
            return []
        if not isinstance(payload, dict):
            return []
        payload_dict = cast(dict[str, object], payload)
        if payload_dict.get("success") is not True:
            return []
        data = payload_dict.get("data")
        if not isinstance(data, dict):
            return []
        raw_dates = cast(dict[str, object], data).get("dates")
        if not isinstance(raw_dates, list):
            return []
        dates: list[str] = []
        for raw_date in cast(list[object], raw_dates):
            if not isinstance(raw_date, dict):
                continue
            date_value = cast(dict[str, object], raw_date).get("date")
            if isinstance(date_value, str) and date_value:
                dates.append(date_value)
        return dates

    def _parse_cinema_list(self, json_content: str) -> tuple[list[int], bool]:
        try:
            if not json_content or not json_content.strip():
                return [], False
            parsed = json.loads(json_content)
            if not parsed or not isinstance(parsed, dict) or "data" not in parsed:
                return [], False
            root = cast(_CinemaListRoot, parsed)
            data_section = root.get("data")
            if data_section is None or "cinemas" not in data_section:
                return [], False
            cinemas_data = data_section.get("cinemas", [])
            if not cinemas_data:
                return [], False
            cinema_ids = [int(cid) for c in cinemas_data if (cid := c.get("id")) is not None]
            has_more = data_section.get("paging", {}).get("hasMore", True)
            return cinema_ids, has_more is False
        except json.JSONDecodeError as error:
            logger.error("解析 JSON 失败: %s", error)
            return [], False
        except Exception as error:
            logger.error("解析影院列表失败: %s", error)
            return [], False

    def _parse_cinema_shows(
        self,
        json_content: str,
        movie_name: str,
        target_show_date: str | None,
    ) -> list[_FetchedShowItem]:
        try:
            if not json_content or not json_content.strip():
                return []
            parsed = json.loads(json_content)
            if not parsed or not isinstance(parsed, dict) or "data" not in parsed:
                return []
            root = cast(_CinemaShowsRoot, parsed)
            data_section = root.get("data")
            if data_section is None:
                return []
            cinema_id = data_section.get("cinemaId")
            cinema_name = str(data_section.get("cinemaName", ""))
            movies = data_section.get("movies", [])

            target_movie: _MovieShowRaw | None = None
            for movie in movies:
                if movie.get("nm", "") == movie_name:
                    target_movie = movie
                    break
            if target_movie is None:
                logger.warning("未找到电影: %s", movie_name)
                return []

            return self._build_show_items(
                target_movie.get("shows", []),
                target_movie.get("id"),
                movie_name,
                cinema_id,
                cinema_name,
                target_show_date,
            )
        except json.JSONDecodeError as error:
            logger.error("解析 JSON 失败: %s", error)
            return []
        except Exception as error:
            logger.error("解析场次信息失败: %s", error)
            return []

    def _build_show_items(
        self,
        shows: list[_ShowDateGroupRaw],
        movie_id: int | None,
        movie_name: str,
        cinema_id: int | None,
        cinema_name: str,
        target_show_date: str | None,
    ) -> list[_FetchedShowItem]:
        result: list[_FetchedShowItem] = []
        for show_date_group in shows:
            show_date = show_date_group.get("showDate", "")
            if target_show_date is not None and show_date != target_show_date:
                continue
            for show_item in show_date_group.get("plist", []):
                result.append(_FetchedShowItem(
                    movie_id=movie_id,
                    movie_name=movie_name,
                    show_date=show_date,
                    show_time=str(show_item.get("tm", "")),
                    price=self._extract_price(show_item),
                    cinema_id=cinema_id,
                    cinema_name=cinema_name,
                ))
        return result

    def _extract_price(self, show_item: _ShowItemRaw) -> str:
        for field_name in ("discountSellPrice", "vipDisPrice", "vipPrice"):
            price = self._normalize_price_value(show_item.get(field_name))  # type: ignore[literal-required]
            if price is not None:
                return price
        return "0"

    def _normalize_price_value(self, raw_value: str | int | float | None) -> str | None:
        if raw_value is None:
            return None
        if isinstance(raw_value, (int, float)):
            return str(raw_value)
        normalized = raw_value.strip()
        if not normalized or "stonefont" in normalized:
            return None
        match = re.search(r"\d+(?:\.\d+)?", normalized)
        return match.group(0) if match is not None else normalized

    # ---------- 内部: 结果聚合 ----------

    def _build_cinemas_from_shows(
        self,
        cinema_results: list[list[_FetchedShowItem]],
    ) -> dict[int, _CinemaShowData]:
        cinemas: dict[int, _CinemaShowData] = {}
        for shows in cinema_results:
            for show in shows:
                if show.cinema_id is None:
                    continue
                cinema = cinemas.setdefault(
                    show.cinema_id,
                    _CinemaShowData(cinema_id=show.cinema_id, cinema_name=show.cinema_name),
                )
                cinema.shows.append(_ShowItem(date=show.show_date, time=show.show_time, price=show.price))
        return cinemas

    def _merge_cinemas(self, movie_data: _MovieShowData, cinemas: dict[int, _CinemaShowData]) -> None:
        for cinema_id, cinema_info in cinemas.items():
            if cinema_id not in movie_data.cinemas:
                movie_data.cinemas[cinema_id] = cinema_info
                continue
            movie_data.cinemas[cinema_id].shows.extend(cinema_info.shows)

    def _finalize_movie(self, movie_data: _MovieShowData) -> _FinalMovieShowData | None:
        result = _FinalMovieShowData(movie_id=movie_data.movie_id, cinemas=list(movie_data.cinemas.values()))
        total_shows = sum(len(c.shows) for c in result.cinemas)
        logger.info(
            "电影 %s (ID: %s) 共找到 %s 个场次,分布在 %s 个影院",
            movie_data.movie_name, result.movie_id, total_shows, len(result.cinemas),
        )
        return result if result.cinemas else None

    def _collect_valid_movie_results(
        self,
        movie_results: Sequence[_FinalMovieShowData | None | BaseException],
    ) -> list[_FinalMovieShowData]:
        result: list[_FinalMovieShowData] = []
        for movie_result in movie_results:
            if isinstance(movie_result, BaseException):
                if isinstance(movie_result, _DegradableError):
                    logger.warning("处理电影时发生可降级错误,跳过当前电影: %s", movie_result)
                    continue
                raise movie_result
            if isinstance(movie_result, _FinalMovieShowData) and movie_result.cinemas:
                result.append(movie_result)
        return result

    # ---------- 内部: 持久化 ----------

    async def _persist_results(
        self,
        movie_ids: list[int],
        results: list[_FinalMovieShowData],
    ) -> int:
        results_by_movie: dict[int, _FinalMovieShowData] = {r.movie_id: r for r in results}
        success_count = 0
        for movie_id in movie_ids:
            if not await self._is_movie_wished(movie_id):
                await asyncio.to_thread(movie_show_repository.delete_for_movie, movie_id)
                continue
            result = results_by_movie.get(movie_id)
            shows: list[MovieShowWriteData] = []
            if result is not None:
                for cinema in result.cinemas:
                    for show in cinema.shows:
                        shows.append({
                            "movie_id": movie_id,
                            "cinema_id": cinema.cinema_id,
                            "cinema_name": cinema.cinema_name,
                            "date": show.date,
                            "time": show.time,
                            "price": show.price,
                        })
            await asyncio.to_thread(movie_show_repository.replace_for_movie, movie_id, shows)
            await asyncio.to_thread(movie_repository.touch_shows_updated_at, movie_id)
            if shows:
                success_count += 1
        return success_count

    async def _is_movie_wished(self, movie_id: int) -> bool:
        movie = await asyncio.to_thread(movie_repository.get_movie_by_id, movie_id)
        return bool(movie and movie.is_wished)

    # ---------- 内部: 工具 ----------

    def _normalize_city_id(self, city_id: int | None) -> int:
        normalized = city_id if city_id is not None else config_manager.city_id
        if normalized <= 0:
            raise AppError("city_id 必须是正整数", status_code=422)
        if normalized not in config_manager.city_mapping.values():
            raise AppError("city_id 不在当前支持的城市范围内", status_code=422)
        return normalized

    def _build_movies_payload(
        self,
        movie_ids: list[int],
        shows: Sequence[object],
    ) -> list[dict[str, object]]:
        movie_shows_map: dict[int, list[dict[str, object]]] = {mid: [] for mid in movie_ids}
        for show in shows:
            mid = int(getattr(show, "movie_id"))
            if mid in movie_shows_map:
                movie_shows_map[mid].append({
                    "cinema_id": int(getattr(show, "cinema_id")),
                    "cinema_name": str(getattr(show, "cinema_name")),
                    "date": str(getattr(show, "date")),
                    "time": str(getattr(show, "time")),
                    "price": None if getattr(show, "price") is None else str(getattr(show, "price")),
                })
        return [{"movie_id": mid, "shows": movie_shows_map.get(mid, [])} for mid in movie_ids]

    def _serialize_datetime(self, value: datetime | None) -> str | None:
        return value.isoformat() if value else None


show_service = ShowService()


# 抑制循环依赖: 旧代码用 RepositoryError 的钩子保留, 给上游捕获
__all__ = ["show_service", "ShowService", "RepositoryError"]
