from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from zoneinfo import ZoneInfo

import pytest
from apscheduler.triggers.cron import CronTrigger
from pytest import MonkeyPatch

import movie_scheduler.core.scheduler as scheduler_module
from movie_scheduler.core.exceptions import MaoyanVerificationError
from movie_scheduler.core.scheduler import AutoUpdateScheduler


@pytest.mark.parametrize("failure", ["verification", "ordinary", None])
@pytest.mark.parametrize("month_start", [True, False])
@pytest.mark.parametrize("cinema_failure", ["verification", "ordinary", None])
def test_scheduled_verification_skips_show_phase(
    monkeypatch: MonkeyPatch, failure: str | None, month_start: bool, cinema_failure: str | None,
) -> None:
    callbacks: list[Callable[[], Awaitable[None]]] = []
    # UTC 仍是上月最后一天,北京时间已进入本月 1 日。
    utc_now = datetime(2026, 10, 31, 16, tzinfo=timezone.utc) if month_start else datetime(2026, 11, 1, 16, tzinfo=timezone.utc)

    def now(tz: ZoneInfo) -> datetime:
        return utc_now.astimezone(tz)

    clock = Mock()
    clock.now.side_effect = now
    monkeypatch.setattr(scheduler_module, "datetime", clock)

    def add_job(callback: Callable[[], Awaitable[None]], **kwargs: object) -> None:
        callbacks.append(callback)
        trigger = kwargs["trigger"]
        assert isinstance(trigger, CronTrigger)
        # 容器采用 UTC 时,仍应在北京时间次日零点触发,随后间隔一天。
        now = datetime(2026, 11, 1, 9, 30, tzinfo=timezone.utc)
        # APScheduler 3.x 的此方法缺少类型标注。
        next_fire = trigger.get_next_fire_time(None, now)  # pyright: ignore[reportUnknownVariableType, reportUnknownMemberType]
        assert isinstance(next_fire, datetime)
        assert next_fire == datetime(2026, 11, 1, 16, tzinfo=timezone.utc)
        assert trigger.get_next_fire_time(next_fire, next_fire) == next_fire + timedelta(days=1)  # pyright: ignore[reportUnknownMemberType]

    def scheduler(**kwargs: object) -> SimpleNamespace:
        return SimpleNamespace(add_job=add_job, start=Mock(), shutdown=Mock())

    error = MaoyanVerificationError() if failure == "verification" else RuntimeError("test") if failure else None
    movies = AsyncMock(side_effect=error)
    shows = AsyncMock()
    cinema_error = MaoyanVerificationError() if cinema_failure == "verification" else RuntimeError("test") if cinema_failure else None
    cinemas = AsyncMock(side_effect=cinema_error, return_value=SimpleNamespace(success_count=2, failure_count=0))
    calls = Mock()
    calls.attach_mock(cinemas, "cinemas")
    calls.attach_mock(movies, "movies")
    calls.attach_mock(shows, "shows")
    monkeypatch.setattr(scheduler_module.cinema_service, "update_cinemas", cinemas)
    monkeypatch.setattr(scheduler_module, "AsyncIOScheduler", scheduler)
    monkeypatch.setattr(scheduler_module.movie_service, "refresh_all_movies", movies)
    monkeypatch.setattr(scheduler_module.show_service, "refresh_wished_movie_shows", shows)
    service = AutoUpdateScheduler()
    service.start()

    async def run_registered_job() -> None:
        await callbacks[0]()

    try:
        assert len(callbacks) == 1
        asyncio.run(run_registered_job())
    finally:
        service.shutdown()
    clock.now.assert_called_once_with(ZoneInfo("Asia/Shanghai"))
    assert cinemas.await_count == int(month_start)
    if month_start:
        cinemas.assert_awaited_once_with(city_id=None)
    cinema_blocked = month_start and cinema_failure == "verification"
    assert movies.await_count == int(not cinema_blocked)
    assert shows.await_count == int(not cinema_blocked and failure != "verification")
    expected = ["cinemas"] if month_start else []
    if not cinema_blocked:
        expected.append("movies")
        if failure != "verification":
            expected.append("shows")
    assert [call[0] for call in calls.mock_calls] == expected
