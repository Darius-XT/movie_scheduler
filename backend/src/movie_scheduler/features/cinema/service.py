"""影院服务: 抓取猫眼影院 API → 解析 → 写库, 同时暴露更新进度。"""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator, Callable
from dataclasses import asdict, dataclass
from typing import TypedDict, cast

import requests
import urllib3

from movie_scheduler.config import config_manager
from movie_scheduler.core.exceptions import AppError, RepositoryError
from movie_scheduler.core.logging import logger
from movie_scheduler.features.cinema.models import CinemaWriteData
from movie_scheduler.features.cinema.repository import cinema_repository
from movie_scheduler.features.cinema.schemas import CinemaUpdateResult, CinemaUpsertData

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


@dataclass(slots=True)
class _CinemaUpdateProgressEvent:
    """更新过程中向 SSE 推送的进度事件(内部)。"""

    message: str
    stage: str
    city_id: int | None = None
    page: int | None = None


class _FirstPageCinemaInfo(TypedDict, total=False):
    name: str
    address: str
    price: str | int | float
    tags: list[str]


class _FirstPageCinemaData(TypedDict, total=False):
    id: int
    info: _FirstPageCinemaInfo


class _OtherPageCinemaData(TypedDict, total=False):
    id: int
    nm: str
    addr: str
    sellPrice: str | int | float
    allowRefund: int | bool
    endorse: int | bool


class _OtherPagePayload(TypedDict, total=False):
    total: int
    cinemas: list[_OtherPageCinemaData]


_CINEMA_REQUEST_HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7",
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.maoyan.com/",
    "Origin": "https://www.maoyan.com",
}

_CINEMA_API_BASE = "https://apis.netstart.cn/maoyan/search/cinemas"
_CINEMA_API_TIMEOUT = 30


class CinemaService:
    """聚合影院抓取与更新能力(原 update/cinema 子领域整体并入)。"""

    def __init__(self) -> None:
        self.session_url = _CINEMA_API_BASE
        self.timeout = _CINEMA_API_TIMEOUT

    # ---------- 对外: 同步入口 ----------

    async def update_cinemas(
        self,
        city_id: int | None,
        progress_callback: Callable[[_CinemaUpdateProgressEvent], None] | None = None,
    ) -> CinemaUpdateResult:
        """异步更新指定城市的影院信息(增量 upsert)。"""
        normalized_city_id = self._normalize_city_id(city_id)
        success_count, failure_count = await asyncio.to_thread(
            self._update_all_cinema_info,
            normalized_city_id,
            progress_callback,
        )
        return CinemaUpdateResult(success_count=success_count, failure_count=failure_count)

    async def stream_cinema_update(self, city_id: int) -> AsyncIterator[str]:
        """将影院更新过程编码为 SSE 文本帧。"""
        event_queue: asyncio.Queue[dict[str, object] | None] = asyncio.Queue()
        loop = asyncio.get_running_loop()

        def push_progress(event: _CinemaUpdateProgressEvent) -> None:
            payload: dict[str, object] = {
                "type": "progress",
                "stage": event.stage,
                "message": event.message,
                "city_id": event.city_id,
                "page": event.page,
            }
            loop.call_soon_threadsafe(event_queue.put_nowait, payload)

        async def run_update() -> None:
            try:
                result = await self.update_cinemas(city_id=city_id, progress_callback=push_progress)
                payload: dict[str, object] = {
                    "type": "complete",
                    "data": {"success_count": result.success_count, "failure_count": result.failure_count},
                }
                loop.call_soon_threadsafe(event_queue.put_nowait, payload)
            except Exception as error:
                error_payload: dict[str, object] = {"type": "error", "error": self._map_stream_error(error)}
                loop.call_soon_threadsafe(event_queue.put_nowait, error_payload)
            finally:
                loop.call_soon_threadsafe(event_queue.put_nowait, None)

        task = asyncio.create_task(run_update())
        try:
            while True:
                event = await event_queue.get()
                if event is None:
                    break
                yield f"data: {json.dumps(event, ensure_ascii=False, separators=(',', ':'))}\n\n"
        finally:
            if not task.done():
                task.cancel()

    # ---------- 内部: 抓取 + 落库 ----------

    def _update_all_cinema_info(
        self,
        city_id: int,
        progress_callback: Callable[[_CinemaUpdateProgressEvent], None] | None,
    ) -> tuple[int, int]:
        logger.info("开始采集城市 ID=%s 的影院数据", city_id)
        all_cinemas_data = self._scrape_all_cinema_pages(city_id, progress_callback)
        if not all_cinemas_data:
            logger.warning("没有获取到任何影院数据")
            return 0, 0
        return self._save_cinemas(all_cinemas_data, city_id, progress_callback)

    def _scrape_all_cinema_pages(
        self,
        city_id: int,
        progress_callback: Callable[[_CinemaUpdateProgressEvent], None] | None,
    ) -> list[CinemaUpsertData]:
        all_cinemas: list[CinemaUpsertData] = []
        page = 1
        while True:
            logger.debug("抓取第 %s 页影院数据", page)
            if progress_callback:
                progress_callback(_CinemaUpdateProgressEvent(
                    message=f"正在更新城市 {city_id} 的影院信息,第 {page} 页",
                    stage="fetching_cinema_page",
                    city_id=city_id,
                    page=page,
                ))
            result = self._fetch_page(city_id=city_id, page=page)
            if result is None:
                logger.warning("获取第 %s 页影院数据失败,结束抓取", page)
                break
            cinemas_data, is_expected_empty = result
            if is_expected_empty:
                logger.debug("影院数据抓取完毕,共 %s 页", page - 1)
                break
            if not cinemas_data:
                logger.error("第 %s 页未解析到影院数据,结束抓取", page)
                break
            all_cinemas.extend(cinemas_data)
            page += 1
        if all_cinemas:
            logger.info("成功解析到 %s 家影院数据,共 %s 页", len(all_cinemas), page - 1)
        return all_cinemas

    def _save_cinemas(
        self,
        all_cinemas: list[CinemaUpsertData],
        city_id: int,
        progress_callback: Callable[[_CinemaUpdateProgressEvent], None] | None,
    ) -> tuple[int, int]:
        if progress_callback:
            progress_callback(_CinemaUpdateProgressEvent(
                message=f"正在保存城市 {city_id} 的影院信息",
                stage="saving_cinema_data",
                city_id=city_id,
            ))
        success_count, failure_count = cinema_repository.save_cinema_batch(
            [cast(CinemaWriteData, asdict(cinema)) for cinema in all_cinemas]
        )
        logger.info("影院数据保存完成: 成功 %s 家,失败 %s 家", success_count, failure_count)
        return success_count, failure_count

    # ---------- 内部: HTTP + 解析 ----------

    def _fetch_page(
        self,
        city_id: int,
        page: int,
    ) -> tuple[list[CinemaUpsertData], bool] | None:
        raw_content = self._http_get(city_id, page)
        if raw_content is None:
            return None
        return self._parse_page(raw_content)

    def _http_get(self, city_id: int, page: int) -> str | None:
        offset = (page - 1) * 20
        url = f"{self.session_url}?keyword=影&ci={city_id}&offset={offset}"
        try:
            logger.debug("开始获取影院数据: page=%s, offset=%s, url=%s", page, offset, url)
            response = requests.get(url, headers=_CINEMA_REQUEST_HEADERS, timeout=self.timeout, verify=False)
            logger.debug("响应状态码: %s, 长度: %s 字符", response.status_code, len(response.text))
            if response.status_code == 200:
                return response.text
            logger.error(
                "获取影院数据请求失败: status=%s, url=%s, response=%s",
                response.status_code, url, response.text[:1000],
            )
            return None
        except Exception as error:
            logger.error("获取影院数据异常: url=%s, error=%s", url, error, exc_info=True)
            return None

    def _parse_page(self, json_content: str) -> tuple[list[CinemaUpsertData], bool]:
        try:
            logger.debug("解析影院 JSON 内容")
            if not json_content or not json_content.strip():
                return [], False

            parsed = json.loads(json_content)
            if not parsed:
                return [], False

            cinemas: list[CinemaUpsertData] = []
            if isinstance(parsed, list):
                for cinema_data in cast(list[_FirstPageCinemaData], parsed):
                    cinema = self._extract_first_page_cinema(cinema_data)
                    if cinema is not None:
                        cinemas.append(cinema)
                return cinemas, False

            if isinstance(parsed, dict) and "cinemas" in parsed:
                payload = cast(_OtherPagePayload, parsed)
                if payload.get("total") == 0:
                    logger.debug("检测到 total 为 0,这是预期中的空页")
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

    def _extract_first_page_cinema(self, cinema_data: _FirstPageCinemaData) -> CinemaUpsertData | None:
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

    def _extract_other_page_cinema(self, cinema_data: _OtherPageCinemaData) -> CinemaUpsertData | None:
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

    # ---------- 内部: 工具 ----------

    def _normalize_city_id(self, city_id: int | None) -> int:
        normalized = city_id if city_id is not None else config_manager.city_id
        if normalized <= 0:
            raise AppError("city_id 必须是正整数", status_code=422)
        if normalized not in config_manager.city_mapping.values():
            raise AppError("city_id 不在当前支持的城市范围内", status_code=422)
        return normalized

    def _map_stream_error(self, error: Exception) -> str:
        if isinstance(error, AppError):
            return error.message
        if isinstance(error, RepositoryError):
            return "数据库访问失败,请稍后重试"
        return "更新失败,请稍后重试"


cinema_service = CinemaService()
