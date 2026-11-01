from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from contextvars import ContextVar
from threading import get_ident
from types import SimpleNamespace

import pytest
from pytest import MonkeyPatch

import movie_scheduler.shared.maoyan_browser as browser_module
from movie_scheduler.core.exceptions import MaoyanVerificationError
from movie_scheduler.shared.maoyan_browser import MaoyanBrowser


class _Clock:
    def __init__(self) -> None:
        self.now = 0.0
        self.sleeps: list[float] = []

    def monotonic(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds


@pytest.fixture(autouse=True)
def clock(monkeypatch: MonkeyPatch) -> _Clock:
    clock = _Clock()
    monkeypatch.setattr(browser_module, "monotonic", clock.monotonic)
    monkeypatch.setattr(browser_module, "sleep", clock.sleep)
    monkeypatch.setattr(browser_module.config_manager, "maoyan_qps", 1.0)
    return clock


def _install_browser(
    monkeypatch: MonkeyPatch, *, title: str = "猫眼电影", status: int = 200,
) -> tuple[list[tuple[str, int]], list[object], SimpleNamespace, list[float]]:
    events: list[tuple[str, int]] = []
    cookies: list[object] = []
    navigation_times: list[float] = []
    def record(name: str) -> None:
        events.append((name, get_ident()))

    def goto(*args: object, **kwargs: object) -> SimpleNamespace:
        navigation_times.append(browser_module.monotonic())
        return SimpleNamespace(ok=status == 200, status=status)

    def add_cookies(values: list[object]) -> None:
        cookies.extend(values)

    page = SimpleNamespace(
        url="https://www.maoyan.com/cinemas",
        goto=goto,
        title=lambda: title,
        content=lambda: "<html>影院列表</html>",
        close=lambda: record("page-close"),
    )
    context = SimpleNamespace(
        new_page=lambda: page, add_cookies=add_cookies,
        close=lambda: record("context-close"),
    )
    def new_context(**kwargs: object) -> SimpleNamespace:
        record("context")
        return context

    browser = SimpleNamespace(
        new_context=new_context, is_connected=lambda: True,
        close=lambda: record("browser-close"),
    )
    def launch(**kwargs: object) -> SimpleNamespace:
        assert kwargs["headless"] is True
        record("launch")
        return browser

    playwright = SimpleNamespace(chromium=SimpleNamespace(launch=launch), stop=lambda: record("stop"))
    monkeypatch.setattr(browser_module, "sync_playwright", lambda: SimpleNamespace(start=lambda: playwright))
    monkeypatch.setattr(browser_module.config_manager, "maoyan_cookie", "uuid=seed")
    monkeypatch.setattr(browser_module.config_manager, "maoyan_browser_cdp_url", "")
    return events, cookies, page, navigation_times


def test_browser_reuses_session_serializes_threads_and_cleans_up(monkeypatch: MonkeyPatch) -> None:
    events, cookies, _, navigation_times = _install_browser(monkeypatch)
    browser = MaoyanBrowser()
    request_id: ContextVar[str] = ContextVar("request_id", default="missing")
    logs: list[str] = []
    def log(*args: object, **kwargs: object) -> None:
        logs.append(request_id.get())

    monkeypatch.setattr(browser_module, "log_external_http_request", log)

    def fetch(city_id: int) -> str | None:
        request_id.set("request-test")
        return browser.get_text("https://www.maoyan.com/cinemas", "影院", city_id,
                                cookie=f"ci={city_id}", timeout=5, verify=True)

    try:
        with ThreadPoolExecutor(max_workers=3) as pool:
            assert list(pool.map(fetch, [10, 10, 10])) == ["<html>影院列表</html>"] * 3
        assert [name for name, _ in events].count("launch") == 1
        assert [name for name, _ in events].count("context") == 1
        assert cookies.count({"name": "uuid", "value": "seed", "domain": ".maoyan.com", "path": "/"}) == 1
        assert fetch(1)
        assert [name for name, _ in events].count("context-close") == 1
    finally:
        browser.close()
    assert logs == ["request-test"] * 4
    assert navigation_times == [0, 1, 2, 3]
    assert len({thread for _, thread in events}) == 1
    assert events[-1][0] == "stop"


def test_browser_http_failure_still_counts_toward_qps(monkeypatch: MonkeyPatch) -> None:
    events, _, _, navigation_times = _install_browser(monkeypatch, status=403)
    browser = MaoyanBrowser()
    try:
        for _ in range(2):
            assert browser.get_text("https://www.maoyan.com/cinemas", "影院", 10,
                                    cookie="", timeout=5, verify=True) is None
        assert navigation_times == [0, 1]
        assert "page-close" in [name for name, _ in events]
    finally:
        browser.close()


@pytest.mark.parametrize("status", [200, 403])
def test_verification_stops_concurrent_batch_and_next_batch_can_retry(monkeypatch: MonkeyPatch, status: int) -> None:
    events, _, page, navigation_times = _install_browser(monkeypatch, title="验证中心", status=status)
    browser = MaoyanBrowser()
    results: list[str | None | BaseException] = []

    def fetch() -> str | None:
        return browser.get_text("https://www.maoyan.com/cinemas", "影院", 10,
                                cookie="", timeout=5, verify=True)

    async def run_batch() -> None:
        with browser.batch():
            results.extend(await asyncio.gather(*(asyncio.to_thread(fetch) for _ in range(4)), return_exceptions=True))

    try:
        with pytest.raises(MaoyanVerificationError, match="已停止本轮"):
            asyncio.run(run_batch())
        assert len(results) == 4
        assert all(isinstance(result, MaoyanVerificationError) for result in results)
        assert navigation_times == [0]
        assert [name for name, _ in events].count("page-close") == 1
        assert "browser-close" not in [name for name, _ in events]
        page.title = lambda: "猫眼电影"
        with browser.batch():
            assert fetch() == ("<html>影院列表</html>" if status == 200 else None)
        assert navigation_times == [0, 1]
    finally:
        browser.close()


def test_nested_batch_cannot_reset_verification_stop(monkeypatch: MonkeyPatch) -> None:
    _, _, _, navigation_times = _install_browser(monkeypatch, title="验证中心")
    browser = MaoyanBrowser()
    try:
        with pytest.raises(MaoyanVerificationError):
            with browser.batch():
                with pytest.raises(MaoyanVerificationError):
                    with browser.batch():
                        browser.get_text("https://www.maoyan.com/cinemas", "影院", 10,
                                         cookie="", timeout=5, verify=True)
                with browser.batch():
                    pytest.fail("同一轮不能重置已触发的验证状态")
        assert navigation_times == [0]
    finally:
        browser.close()


def test_browser_recovers_after_navigation_failure(monkeypatch: MonkeyPatch) -> None:
    events, _, page, navigation_times = _install_browser(monkeypatch)
    original_goto = page.goto
    def fail(*args: object, **kwargs: object) -> None:
        navigation_times.append(browser_module.monotonic())
        raise TimeoutError("private-token-not-for-logs")

    page.goto = fail
    browser = MaoyanBrowser()
    try:
        assert browser.get_text("https://www.maoyan.com/cinemas", "影院", 10,
                                cookie="", timeout=5, verify=True) is None
        page.goto = original_goto
        assert browser.get_text("https://www.maoyan.com/cinemas", "影院", 10,
                                cookie="", timeout=5, verify=True)
        assert [name for name, _ in events].count("launch") == 2
        assert navigation_times == [0, 1]
    finally:
        browser.close()


def test_remote_browser_disconnect_keeps_host_process_alive(monkeypatch: MonkeyPatch) -> None:
    events, _, _, _ = _install_browser(monkeypatch)
    playwright = browser_module.sync_playwright().start()
    connected: list[str] = []

    def connect(endpoint: str, **kwargs: object) -> object:
        connected.append(endpoint)
        return playwright.chromium.launch(headless=True)

    monkeypatch.setattr(playwright.chromium, "connect_over_cdp", connect, raising=False)
    monkeypatch.setattr(browser_module, "sync_playwright", lambda: SimpleNamespace(start=lambda: playwright))
    monkeypatch.setattr(browser_module.config_manager, "maoyan_browser_cdp_url", "http://host.docker.internal:9223")
    def resolve(host: str) -> str:
        return "192.0.2.1"

    monkeypatch.setattr(browser_module.socket, "gethostbyname", resolve)
    browser = MaoyanBrowser()
    try:
        assert browser.get_text("https://www.maoyan.com/cinemas", "影院", 10,
                                cookie="", timeout=5, verify=True)
    finally:
        browser.close()
    assert connected == ["http://192.0.2.1:9223"]
    assert "context-close" in [name for name, _ in events]
    assert "browser-close" not in [name for name, _ in events]


def test_browser_counts_navigation_time_without_accumulating_idle_slots(
    monkeypatch: MonkeyPatch, clock: _Clock,
) -> None:
    _, _, page, navigation_times = _install_browser(monkeypatch)
    original_goto = page.goto
    durations = iter([0.25, 1.25, 0, 0, 0])

    def goto(*args: object, **kwargs: object) -> SimpleNamespace:
        response = original_goto(*args, **kwargs)
        clock.now += next(durations)
        return response

    page.goto = goto
    browser = MaoyanBrowser()
    try:
        for _ in range(3):
            assert browser.get_text("https://www.maoyan.com/cinemas", "影院", 10,
                                    cookie="", timeout=5, verify=True)
        clock.now += 5
        for _ in range(2):
            assert browser.get_text("https://www.maoyan.com/films", "电影", 10,
                                    cookie="", timeout=5, verify=True)
    finally:
        browser.close()
    assert navigation_times == [0, 1, 2.25, 7.25, 8.25]
    assert clock.sleeps == [0.75, 1]


def test_browser_uses_configured_qps(monkeypatch: MonkeyPatch) -> None:
    _, _, _, navigation_times = _install_browser(monkeypatch)
    monkeypatch.setattr(browser_module.config_manager, "maoyan_qps", 0.1)
    browser = MaoyanBrowser()
    try:
        for _ in range(3):
            assert browser.get_text("https://www.maoyan.com/films", "电影", 10,
                                    cookie="", timeout=5, verify=True)
    finally:
        browser.close()
    assert navigation_times == [0, 10, 20]
