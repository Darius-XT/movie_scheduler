"""影院信息客户端（场次抓取模块）：合并 scraper + parser，对外返回业务对象。"""

from __future__ import annotations

import json
from typing import TypedDict, cast

import requests
import urllib3

from app.core.exceptions import DataParsingError, ExternalDependencyError
from app.core.logger import logger

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

_HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
    "Referer": "https://www.maoyan.com/",
    "Origin": "https://www.maoyan.com",
}


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


class CinemaClient:
    """合并 HTTP 抓取与 JSON 解析，返回影院 ID 列表及翻页状态。"""

    def __init__(self) -> None:
        self.base_url = "https://apis.netstart.cn/maoyan/movie/select/cinemas"
        self.timeout = 30

    def get_cinema_ids(
        self,
        movie_id: int,
        show_date: str,
        city_id: int,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[int], bool]:
        """获取影院 ID 列表及是否为最后一页。

        Returns:
            (cinema_ids, is_last_page)

        Raises:
            ExternalDependencyError: HTTP 请求失败。
            DataParsingError: 解析失败。
        """
        json_content = self._fetch(movie_id, show_date, city_id, limit, offset)
        if json_content is None:
            raise ExternalDependencyError(
                f"获取影院信息失败，movie_id={movie_id}, city_id={city_id}, show_date={show_date}, offset={offset}"
            )

        cinema_ids, is_last_page = self._parse(json_content)
        if not cinema_ids and not is_last_page:
            raise DataParsingError(
                f"影院分页解析结果为空，movie_id={movie_id}, city_id={city_id}, show_date={show_date}, offset={offset}"
            )

        return cinema_ids, is_last_page

    # ------------------------------------------------------------------
    # 私有：HTTP
    # ------------------------------------------------------------------

    def _fetch(
        self,
        movie_id: int,
        show_date: str,
        city_id: int,
        limit: int,
        offset: int,
    ) -> str | None:
        """发起 HTTP 请求，失败返回 None。"""
        url = (
            f"{self.base_url}?limit={limit}&offset={offset}"
            f"&showDate={show_date}&movieId={movie_id}&cityId={int(city_id)}"
        )
        try:
            logger.debug("开始获取影院信息: %s", url)
            response = requests.get(url, headers=_HEADERS, timeout=self.timeout, verify=False)
            logger.debug("响应状态码: %s，响应长度: %s 字符", response.status_code, len(response.text))
            if response.status_code == 200:
                return response.text
            logger.error(
                "获取影院信息请求失败: status=%s, url=%s, response=%s",
                response.status_code,
                url,
                response.text[:1000],
            )
            return None
        except Exception as error:
            logger.error("获取影院信息异常: url=%s, error=%s", url, error, exc_info=True)
            return None

    # ------------------------------------------------------------------
    # 私有：解析
    # ------------------------------------------------------------------

    def _parse(self, json_content: str) -> tuple[list[int], bool]:
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


cinema_client = CinemaClient()
