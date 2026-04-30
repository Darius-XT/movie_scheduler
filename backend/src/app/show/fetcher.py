"""获取选中电影所有场次的用例。"""

from __future__ import annotations

import asyncio
import json
from collections.abc import Callable, Sequence
from dataclasses import asdict

from app.core.exceptions import DataParsingError, ExternalDependencyError, RepositoryError
from app.core.logger import logger
from app.show.entities import (
    DatesFoundProgress,
    FetchedShowItem,
    MovieCompleteProgress,
    ProcessingCinemaProgress,
    ProcessingDateProgress,
    ShowFetchProgressEvent,
)
from app.show.gateway import ShowGateway
from app.show.result_builder import (
    CinemaShowData,
    FinalMovieShowData,
    MovieShowData,
    MovieShowDataBuilder,
)

ProgressCallback = Callable[[ShowFetchProgressEvent], None]
DegradableShowFetchingError = ExternalDependencyError | DataParsingError
CriticalShowFetchingError = RepositoryError


class ShowForSelectedMovieFetcher:
    """负责调度场次抓取流程。"""

    def __init__(
        self,
        gateway: ShowGateway | None = None,
        builder: MovieShowDataBuilder | None = None,
    ) -> None:
        self.gateway = gateway or ShowGateway()
        self.builder = builder or MovieShowDataBuilder()

    async def fetch_shows_for_selected_movies(
        self,
        movie_ids: list[int],
        city_id: int,
        progress_callback: ProgressCallback | None = None,
    ) -> list[FinalMovieShowData]:
        """获取选中电影的所有场次。"""
        logger.info("开始异步获取 %s 部电影在城市 %s 的场次信息", len(movie_ids), city_id)

        tasks = [self._process_single_movie(movie_id, city_id, progress_callback) for movie_id in movie_ids]
        movie_results = await asyncio.gather(*tasks, return_exceptions=True)

        result = self._collect_valid_movie_results(movie_results)
        self._log_result_summary(result)
        return result

    async def _process_single_movie(
        self,
        movie_id: int,
        city_id: int,
        progress_callback: ProgressCallback | None = None,
    ) -> FinalMovieShowData | None:
        """异步处理单部电影的所有场次信息。"""
        try:
            context = self._prepare_movie_context(movie_id, city_id, progress_callback)
            if context is None:
                return None

            movie_data, show_dates = context
            date_counter = [0]  # 已完成的日期数，由并发任务共享递增
            date_tasks = [
                self._process_single_date(
                    movie_id,
                    movie_data.movie_name,
                    city_id,
                    show_date,
                    len(show_dates),
                    date_counter,
                    progress_callback,
                )
                for show_date in show_dates
            ]
            date_results = await asyncio.gather(*date_tasks, return_exceptions=True)

            for date_result in date_results:
                if isinstance(date_result, BaseException):
                    if self._is_degradable_error(date_result):
                        logger.warning("处理日期时发生可降级错误，跳过当前日期: %s", date_result)
                        continue
                    raise date_result
                if isinstance(date_result, dict):
                    self.builder.merge_cinemas(movie_data, date_result)

            movie_result = self._finish_movie_result(movie_data)
            self._notify_movie_complete(progress_callback, movie_id, movie_result is not None)
            return movie_result
        except BaseException as error:
            if self._is_degradable_error(error):
                logger.warning("处理电影 ID %s 时发生可降级错误，跳过当前电影: %s", movie_id, error)
                self._notify_movie_complete(progress_callback, movie_id, False)
                return None
            logger.error("处理电影 ID %s 时发生不可恢复错误: %s", movie_id, error)
            raise

    def _prepare_movie_context(
        self,
        movie_id: int,
        city_id: int,
        progress_callback: ProgressCallback | None,
    ) -> tuple[MovieShowData, list[str]] | None:
        """准备单部电影抓取所需的共享上下文。"""
        logger.info("正在处理电影 ID: %s", movie_id)
        movie_name = self.gateway.get_movie_name(movie_id)
        if not movie_name:
            logger.warning("无法获取电影名称，跳过电影 ID: %s", movie_id)
            return None

        logger.debug("电影名称: %s", movie_name)
        movie_data = self.builder.create_movie_data(movie_id, movie_name)
        show_dates = self.gateway.get_show_dates(movie_id, city_id)
        logger.debug("找到 %s 个排片日期: %s", len(show_dates), show_dates)
        self._notify_dates_found(progress_callback, movie_id, show_dates)
        return movie_data, show_dates

    async def _process_single_date(
        self,
        movie_id: int,
        movie_name: str,
        city_id: int,
        show_date: str,
        total_dates: int,
        date_counter: list[int],
        progress_callback: ProgressCallback | None = None,
    ) -> dict[int, CinemaShowData] | None:
        """异步处理单个日期，获得该电影在全部影院的场次。"""
        try:
            logger.debug("处理日期: %s", show_date)
            cinema_ids = await asyncio.to_thread(self.gateway.get_cinemas, movie_id, show_date, city_id)
            if not cinema_ids:
                logger.debug("日期 %s 没有找到影院", show_date)
                date_counter[0] += 1
                self._notify_processing_date(
                    progress_callback, movie_id, show_date, date_counter[0], total_dates
                )
                return None

            logger.debug("找到 %s 个影院", len(cinema_ids))
            cinema_counter = [0]  # 已完成的影院数
            cinema_tasks = [
                self._get_cinema_shows(
                    cinema_id,
                    movie_name,
                    city_id,
                    show_date,
                    len(cinema_ids),
                    cinema_counter,
                    progress_callback,
                    movie_id,
                )
                for cinema_id in cinema_ids
            ]
            cinema_results = await asyncio.gather(*cinema_tasks, return_exceptions=True)

            valid_results = self._collect_cinema_results(cinema_results)
            date_counter[0] += 1
            self._notify_processing_date(
                progress_callback, movie_id, show_date, date_counter[0], total_dates
            )
            return self.builder.build_cinemas_from_shows(valid_results)
        except BaseException as error:
            if self._is_degradable_error(error):
                logger.warning("处理日期 %s 时发生可降级错误，跳过当前日期: %s", show_date, error)
                date_counter[0] += 1
                self._notify_processing_date(
                    progress_callback, movie_id, show_date, date_counter[0], total_dates
                )
                return None
            logger.error("处理日期 %s 时发生不可恢复错误: %s", show_date, error)
            raise

    def _collect_cinema_results(
        self,
        cinema_results: list[list[FetchedShowItem] | BaseException],
    ) -> list[list[FetchedShowItem]]:
        """收集有效的影院场次结果，降级处理可忽略的错误。"""
        valid: list[list[FetchedShowItem]] = []
        for cinema_result in cinema_results:
            if isinstance(cinema_result, BaseException):
                if self._is_degradable_error(cinema_result):
                    logger.warning("获取影院场次时发生可降级错误，跳过当前影院: %s", cinema_result)
                    continue
                raise cinema_result
            valid.append(cinema_result)
        return valid

    async def _get_cinema_shows(
        self,
        cinema_id: int,
        movie_name: str,
        city_id: int,
        show_date: str,
        total_cinemas: int,
        cinema_counter: list[int],
        progress_callback: ProgressCallback | None = None,
        movie_id: int | None = None,
    ) -> list[FetchedShowItem]:
        """异步获取指定影院中指定电影的所有场次。"""
        try:
            shows = await asyncio.to_thread(
                self.gateway.get_cinema_shows,
                cinema_id,
                movie_name,
                city_id,
                show_date,
            )
            return shows
        finally:
            cinema_counter[0] += 1
            if progress_callback and movie_id is not None:
                progress_callback(
                    ProcessingCinemaProgress(
                        type="processing_cinema",
                        date=show_date,
                        cinema_idx=cinema_counter[0],
                        total_cinemas=total_cinemas,
                        cinema_id=cinema_id,
                        movie_id=movie_id,
                    )
                )

    def _finish_movie_result(
        self,
        movie_data: MovieShowData,
    ) -> FinalMovieShowData | None:
        """完成单部电影结果整理并输出汇总日志。"""
        movie_result = self.builder.finalize_movie_data(movie_data)
        total_shows = sum(len(cinema.shows) for cinema in movie_result.cinemas)
        logger.info(
            "电影 %s (ID: %s) 共找到 %s 个场次，分布在 %s 个影院",
            movie_data.movie_name,
            movie_result.movie_id,
            total_shows,
            len(movie_result.cinemas),
        )
        return movie_result if movie_result.cinemas else None

    def _collect_valid_movie_results(
        self,
        movie_results: Sequence[FinalMovieShowData | None | BaseException],
    ) -> list[FinalMovieShowData]:
        """收集有效的电影场次结果。"""
        result: list[FinalMovieShowData] = []
        for movie_result in movie_results:
            if isinstance(movie_result, BaseException):
                if self._is_degradable_error(movie_result):
                    logger.warning("处理电影时发生可降级错误，跳过当前电影: %s", movie_result)
                    continue
                raise movie_result
            if isinstance(movie_result, FinalMovieShowData) and movie_result.cinemas:
                result.append(movie_result)
        return result

    def _is_degradable_error(self, error: BaseException) -> bool:
        """判断错误是否允许按电影/日期/影院粒度降级。"""
        return isinstance(error, (ExternalDependencyError, DataParsingError))

    def _log_result_summary(self, result: list[FinalMovieShowData]) -> None:
        """输出抓取结果汇总日志。"""
        total_shows = self.builder.count_total_shows(result)
        logger.info("总共找到 %s 部电影，%s 个场次信息", len(result), total_shows)
        logger.info("场次信息结果:")
        logger.info(json.dumps([asdict(movie) for movie in result], ensure_ascii=False, indent=2))

    def _notify_dates_found(
        self,
        progress_callback: ProgressCallback | None,
        movie_id: int,
        show_dates: list[str],
    ) -> None:
        """通知日期发现进度。"""
        if progress_callback:
            progress_callback(DatesFoundProgress(type="dates_found", dates=show_dates, movie_id=movie_id))

    def _notify_processing_date(
        self,
        progress_callback: ProgressCallback | None,
        movie_id: int,
        show_date: str,
        date_idx: int,
        total_dates: int,
    ) -> None:
        """通知正在处理日期的进度。"""
        if progress_callback:
            progress_callback(
                ProcessingDateProgress(
                    type="processing_date",
                    date=show_date,
                    date_idx=date_idx,
                    total_dates=total_dates,
                    movie_id=movie_id,
                )
            )

    def _notify_movie_complete(
        self,
        progress_callback: ProgressCallback | None,
        movie_id: int,
        has_shows: bool,
    ) -> None:
        """通知单部电影已完成抓取。"""
        if progress_callback:
            progress_callback(
                MovieCompleteProgress(
                    type="movie_complete",
                    movie_id=movie_id,
                    has_shows=has_shows,
                )
            )


show_fetcher = ShowForSelectedMovieFetcher()
