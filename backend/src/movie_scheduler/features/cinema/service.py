"""影院服务: 抓取猫眼影院 API → 解析 → 写库, 同时暴露更新进度。"""

from __future__ import annotations

import asyncio
import re
from collections.abc import AsyncIterator, Callable
from dataclasses import asdict, dataclass
from typing import cast

import requests
import urllib3
from bs4 import BeautifulSoup
from bs4.element import Tag

from movie_scheduler.config import config_manager
from movie_scheduler.core.exceptions import AppError, RepositoryError
from movie_scheduler.core.logging import logger
from movie_scheduler.features.cinema.models import CinemaWriteData
from movie_scheduler.features.cinema.repository import cinema_repository
from movie_scheduler.features.cinema.schemas import CinemaUpdateResult, CinemaUpsertData
from movie_scheduler.shared.maoyan import build_maoyan_web_headers, decode_maoyan_stonefont_text
from movie_scheduler.shared.sse import stream_with_progress

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


@dataclass(slots=True)
class _CinemaUpdateProgressEvent:
    """更新过程中向 SSE 推送的进度事件(内部)。"""

    message: str
    stage: str
    city_id: int | None = None
    page: int | None = None


_CINEMA_PAGE_BASE = "https://www.maoyan.com/cinemas"
_CINEMA_API_TIMEOUT = 30
_CINEMA_PAGE_SIZE = 12


class CinemaService:
    """聚合影院抓取与更新能力(原 update/cinema 子领域整体并入)。"""

    def __init__(self) -> None:
        self.session_url = _CINEMA_PAGE_BASE
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

        async def run(push_progress: Callable[[dict[str, object]], None]) -> dict[str, object]:
            def forward(event: _CinemaUpdateProgressEvent) -> None:
                push_progress({
                    "stage": event.stage,
                    "message": event.message,
                    "city_id": event.city_id,
                    "page": event.page,
                })

            result = await self.update_cinemas(city_id=city_id, progress_callback=forward)
            return {"success_count": result.success_count, "failure_count": result.failure_count}

        async for frame in stream_with_progress(run, map_error=self._map_stream_error):
            yield frame

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
            cinemas_data, is_last_page = result
            if not cinemas_data:
                if is_last_page:
                    logger.debug("影院数据抓取完毕,共 %s 页", page - 1)
                    break
                logger.error("第 %s 页未解析到影院数据,结束抓取", page)
                break
            all_cinemas.extend(cinemas_data)
            if is_last_page:
                logger.debug("影院数据抓取完毕,共 %s 页", page)
                break
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
        offset = (page - 1) * _CINEMA_PAGE_SIZE
        url = self.session_url if offset == 0 else f"{self.session_url}?offset={offset}"
        try:
            logger.debug("开始获取影院数据: page=%s, offset=%s, url=%s", page, offset, url)
            response = requests.get(
                url,
                headers=build_maoyan_web_headers(city_id),
                timeout=self.timeout,
                verify=False,
            )
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

    def _parse_page(self, html_content: str) -> tuple[list[CinemaUpsertData], bool]:
        try:
            logger.debug("解析影院 HTML 内容")
            if not html_content or not html_content.strip() or "猫眼验证中心" in html_content:
                return [], False

            cinemas: list[CinemaUpsertData] = []
            soup = BeautifulSoup(html_content, "html.parser")
            for cell in soup.select(".cinema-cell"):
                if isinstance(cell, Tag) and (cinema := self._extract_cinema_cell(cell, html_content)) is not None:
                    cinemas.append(cinema)
            return cinemas, not self._has_next_page(soup)
        except Exception as error:
            logger.error("解析影院列表失败: %s", error)
            return [], False

    def _extract_cinema_cell(self, cell: Tag, html_content: str) -> CinemaUpsertData | None:
        try:
            name_node = cell.select_one(".cinema-name")
            if not isinstance(name_node, Tag):
                return None
            tags = [tag.get_text(" ", strip=True) for tag in cell.select(".cinema-tags-item")]
            return CinemaUpsertData(
                id=self._extract_cinema_id(name_node),
                name=name_node.get_text(" ", strip=True) or "暂无名称",
                address=self._extract_cinema_address(cell),
                price=self._extract_cinema_price(cell, html_content),
                allow_refund="退" in tags,
                allow_endorse="改签" in tags,
            )
        except Exception as error:
            logger.error("解析影院 HTML 单元失败: %s", error)
            return None

    def _extract_cinema_id(self, node: Tag) -> int | None:
        for attr_name in ("data-val", "href"):
            raw_value = node.get(attr_name)
            if not isinstance(raw_value, str):
                continue
            match = re.search(r"cinema_id\s*:\s*(\d+)|/cinema/(\d+)", raw_value)
            if match is not None:
                return int(match.group(1) or match.group(2))
        return None

    def _extract_cinema_address(self, cell: Tag) -> str:
        address_node = cell.select_one(".cinema-address")
        if not isinstance(address_node, Tag):
            return "暂无地址"
        address = address_node.get_text(" ", strip=True).removeprefix("地址：").strip()
        return address or "暂无地址"

    def _extract_cinema_price(self, cell: Tag, html_content: str) -> str:
        price_node = cell.select_one(".price-num")
        if not isinstance(price_node, Tag):
            return "暂无票价"
        price = price_node.get_text(" ", strip=True)
        decoded = decode_maoyan_stonefont_text(html_content, price)
        if decoded is not None:
            price = decoded.strip()
        return price if re.fullmatch(r"\d+(?:\.\d+)?", price) else "暂无票价"

    def _has_next_page(self, soup: BeautifulSoup) -> bool:
        for link in soup.select(".list-pager a"):
            href = link.get("href") if isinstance(link, Tag) else None
            if isinstance(href, str) and "offset=" in href and "下一页" in link.get_text(" ", strip=True):
                return True
        return False

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
