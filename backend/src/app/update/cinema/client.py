"""影院信息客户端：合并 scraper + parser，对外返回业务对象。"""

from __future__ import annotations

import json
from typing import TypedDict, cast

import requests
import urllib3

from app.core.logger import logger
from app.update.cinema.entities import CinemaUpsertData

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


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


class CinemaInfoClient:
    """合并 HTTP 抓取与 JSON 解析，返回业务对象。"""

    def __init__(self) -> None:
        self.base_url = "https://apis.netstart.cn/maoyan/search/cinemas"
        self.timeout = 30
        self.headers = {
            "Accept": "application/json",
            "Accept-Encoding": "gzip, deflate",
            "Accept-Language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7",
            "Connection": "keep-alive",
            "Host": "apis.netstart.cn",
            "sec-ch-ua": '"Chromium";v="140", "Not=A?Brand";v="24", "Google Chrome";v="140"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"macOS"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "cross-site",
            "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
        }

    def fetch_page(
        self,
        city_id: int,
        page: int,
    ) -> tuple[list[CinemaUpsertData], bool] | None:
        """抓取并解析一页影院数据。

        Returns:
            None — HTTP 请求失败，调用方应终止翻页。
            (cinemas_data, is_expected_empty) — 请求成功后的解析结果。
        """
        raw_content = self._fetch(city_id, page)
        if raw_content is None:
            return None
        return self._parse(raw_content)

    # ------------------------------------------------------------------
    # 私有：HTTP
    # ------------------------------------------------------------------

    def _fetch(self, city_id: int, page: int) -> str | None:
        """发起 HTTP 请求，失败返回 None。"""
        offset = (page - 1) * 20
        url = f"{self.base_url}?keyword='影'&ci={city_id}&offset={offset}"
        try:
            logger.debug("开始获取影院数据: page=%s, offset=%s, url=%s", page, offset, url)

            response = requests.get(url, headers=self.headers, timeout=self.timeout, verify=False)

            logger.debug("响应状态码: %s", response.status_code)
            logger.debug("响应长度: %s 字符", len(response.text))

            if response.status_code == 200:
                logger.debug("成功获取影院数据")
                return response.text

            logger.error(
                "获取影院数据请求失败: status=%s, url=%s, response=%s",
                response.status_code,
                url,
                response.text[:1000],
            )
            return None
        except Exception as error:
            logger.error("获取影院数据异常: url=%s, error=%s", url, error, exc_info=True)
            return None

    # ------------------------------------------------------------------
    # 私有：解析
    # ------------------------------------------------------------------

    def _parse(self, json_content: str) -> tuple[list[CinemaUpsertData], bool]:
        """解析 JSON，返回影院列表及是否遇到预期中的空页。"""
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


cinema_info_client = CinemaInfoClient()
