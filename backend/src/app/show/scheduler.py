"""场次定时抓取调度器。

启动时立即触发一次,然后每小时触发一次。任务函数本身已经做了完善的错误隔离,
调度器层面只负责按时间触发,不做额外的错误处理。
"""

from __future__ import annotations

import asyncio

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.core.logger import logger
from app.show.service import show_service

_SHOW_REFRESH_INTERVAL_HOURS = 1


class ShowScheduler:
    """封装场次定时抓取的启停。"""

    def __init__(self) -> None:
        self._scheduler: AsyncIOScheduler | None = None

    def start(self) -> None:
        """注册定时任务并启动调度器。"""
        if self._scheduler is not None:
            return
        scheduler = AsyncIOScheduler(timezone="Asia/Shanghai")
        scheduler.add_job(
            self._run_refresh,
            trigger=IntervalTrigger(hours=_SHOW_REFRESH_INTERVAL_HOURS),
            id="refresh_wished_movie_shows",
            replace_existing=True,
            max_instances=1,
            coalesce=True,
        )
        scheduler.start()
        self._scheduler = scheduler
        logger.info("场次定时抓取调度器已启动:每 %s 小时一次", _SHOW_REFRESH_INTERVAL_HOURS)

        # 启动后立即跑一次,不阻塞调度器启动流程
        asyncio.create_task(self._run_refresh())

    def shutdown(self) -> None:
        """停止调度器。"""
        if self._scheduler is None:
            return
        self._scheduler.shutdown(wait=False)
        self._scheduler = None
        logger.info("场次定时抓取调度器已停止")

    async def _run_refresh(self) -> None:
        """实际触发场次抓取任务。"""
        try:
            await show_service.refresh_wished_movie_shows()
        except Exception as error:  # noqa: BLE001 — 兜底,避免调度器线程退出
            logger.error("场次定时抓取任务异常: %s", error)


show_scheduler = ShowScheduler()
