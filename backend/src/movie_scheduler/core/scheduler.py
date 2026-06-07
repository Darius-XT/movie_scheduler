"""跨领域的定时任务调度器。

策略:
- 每个整点(分钟 0)触发一次"全量自动更新":先增量更新电影信息,再为想看电影抓场次。
- 服务启动时立即触发一次相同任务(不必等到下一个整点),前端立刻能看到数据。
- 两个任务串行执行(场次抓取依赖最新的 movies 表与 wishMovies 状态),
  但前端各自显示自己的"上次更新时间"。
"""

from __future__ import annotations

import asyncio

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from movie_scheduler.core.logging import logger
from movie_scheduler.features.movie.service import movie_service
from movie_scheduler.features.show.service import show_service


class AutoUpdateScheduler:
    """编排电影信息更新 + 想看电影场次抓取的定时任务。"""

    def __init__(self) -> None:
        self._scheduler: AsyncIOScheduler | None = None

    def start(self) -> None:
        """注册定时任务并启动调度器。"""
        if self._scheduler is not None:
            return
        scheduler = AsyncIOScheduler(timezone="Asia/Shanghai")
        # apscheduler 3.x 没有 type stubs, add_job 的 **trigger_args 被推断为 Unknown
        scheduler.add_job(  # pyright: ignore[reportUnknownMemberType]
            self._run_all,
            trigger=CronTrigger(minute=0, timezone="Asia/Shanghai"),
            id="auto_update_movies_and_shows",
            replace_existing=True,
            max_instances=1,
            coalesce=True,
        )
        scheduler.start()
        self._scheduler = scheduler
        logger.info("自动更新调度器已启动:每个整点触发一次")
        # 启动后立即跑一次,不等下个整点
        asyncio.create_task(self._run_all())

    def shutdown(self) -> None:
        """停止调度器。"""
        if self._scheduler is None:
            return
        self._scheduler.shutdown(wait=False)
        self._scheduler = None
        logger.info("自动更新调度器已停止")

    async def _run_all(self) -> None:
        """先跑电影更新,再跑场次抓取。两个步骤都不抛异常,失败只记日志。"""
        logger.info("自动更新任务开始")
        try:
            await movie_service.refresh_all_movies()
        except Exception as error:  # noqa: BLE001
            logger.error("电影自动更新异常: %s", error)
        try:
            await show_service.refresh_wished_movie_shows()
        except Exception as error:  # noqa: BLE001
            logger.error("场次自动抓取异常: %s", error)
        logger.info("自动更新任务结束")


auto_update_scheduler = AutoUpdateScheduler()
