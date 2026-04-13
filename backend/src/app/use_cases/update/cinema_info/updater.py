"""影院数据更新器。"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict
from typing import cast

from app.core.logger import logger
from app.models.cinema import CinemaWriteData
from app.repositories.cinema_repository import cinema_repository
from app.repositories.movie_repository import movie_repository
from app.use_cases.update.cinema_info.cinema_parser import CinemaInfoParser
from app.use_cases.update.cinema_info.cinema_scraper import CinemaInfoScraper
from app.use_cases.update.cinema_info.models import CinemaUpsertData
from app.use_cases.update.cinema_update_reset_helper import CinemaUpdateResetHelper
from app.use_cases.update.models import UpdateProgressEvent


class CinemaInfoUpdater:
    """负责抓取并保存指定城市的影院信息。"""

    def __init__(self) -> None:
        self.scraper = CinemaInfoScraper()
        self.parser = CinemaInfoParser()
        self.reset_helper = CinemaUpdateResetHelper()

    def update_all_cinema_info(
        self,
        city_id: int,
        force_update_all: bool = False,
        progress_callback: Callable[[UpdateProgressEvent], None] | None = None,
    ) -> tuple[int, int]:
        """更新指定城市的全部影院信息。"""
        self.reset_helper.reset_cinemas_if_needed(force_update_all)
        logger.info("开始采集城市 ID=%s 的影院数据", city_id)

        all_cinemas_data: list[CinemaUpsertData] = []
        page = 1

        while True:
            logger.debug("抓取第 %s 页影院数据", page)
            if progress_callback:
                progress_callback(
                    UpdateProgressEvent(
                        message=f"正在更新城市 {city_id} 的影院信息，第 {page} 页",
                        stage="fetching_cinema_page",
                        city_id=city_id,
                        page=page,
                    )
                )

            success, raw_content = self.scraper.scrape_cinemas(
                city_id=city_id,
                page=page,
            )
            if not success or not raw_content:
                logger.warning("获取第 %s 页影院数据失败，结束抓取", page)
                break

            cinemas_data, is_expected_empty = self.parser.parse_cinemas(raw_content)
            if is_expected_empty:
                logger.debug("影院数据抓取完毕，共 %s 页", page - 1)
                break
            if not cinemas_data:
                logger.error("第 %s 页未解析到影院数据，结束抓取", page)
                break

            logger.debug("第 %s 页解析到 %s 家影院", page, len(cinemas_data))
            all_cinemas_data.extend(cinemas_data)
            page += 1

        if not all_cinemas_data:
            logger.warning("没有获取到任何影院数据")
            return 0, 0

        total_pages = page - 1
        logger.info("成功解析到 %s 家影院数据，共 %s 页", len(all_cinemas_data), total_pages)

        if progress_callback:
            progress_callback(
                UpdateProgressEvent(
                    message=f"正在保存城市 {city_id} 的影院信息",
                    stage="saving_cinema_data",
                    city_id=city_id,
                )
            )

        success_count, failure_count = cinema_repository.save_cinema_batch(
            [cast(CinemaWriteData, asdict(cinema)) for cinema in all_cinemas_data]
        )
        logger.info("影院数据保存完成: 成功 %s 家，失败 %s 家", success_count, failure_count)

        total_movies = movie_repository.get_movies_count()
        total_cinemas = cinema_repository.get_cinemas_count()
        logger.info("数据库当前统计: 电影 %s 部，影院 %s 家", total_movies, total_cinemas)

        return success_count, failure_count


cinema_info_updater = CinemaInfoUpdater()
