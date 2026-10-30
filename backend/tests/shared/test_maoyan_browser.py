from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from contextvars import ContextVar
from threading import get_ident
from types import SimpleNamespace

import pytest
from pytest import MonkeyPatch

import movie_scheduler.shared.maoyan_browser as browser_module
from movie_scheduler.shared.maoyan_browser import MaoyanBrowser


def _install_browser(
    monkeypatch: MonkeyPatch, *, title: str = "猫眼电影", status: int = 200,
) -> tuple[list[tuple[str, int]], list[object], SimpleNamespace]:
    events: list[tuple[str, int]] = []
    cookies: list[object] = []
    def record(name: str) -> None:
        events.append((name, get_ident()))

    def goto(*args: object, **kwargs: object) -> SimpleNamespace:
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
    return events, cookies, page


def test_browser_reuses_session_serializes_threads_and_cleans_up(monkeypatch: MonkeyPatch) -> None:
    events, cookies, _ = _install_browser(monkeypatch)
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
    assert len({thread for _, thread in events}) == 1
    assert events[-1][0] == "stop"


@pytest.mark.parametrize("title,status", [("验证中心", 200), ("猫眼电影", 403)])
def test_browser_rejects_verification_and_http_failure(monkeypatch: MonkeyPatch, title: str, status: int) -> None:
    events, _, _ = _install_browser(monkeypatch, title=title, status=status)
    browser = MaoyanBrowser()
    try:
        assert browser.get_text("https://www.maoyan.com/cinemas", "影院", 10,
                                cookie="", timeout=5, verify=True) is None
        assert "page-close" in [name for name, _ in events]
    finally:
        browser.close()


def test_browser_recovers_after_navigation_failure(monkeypatch: MonkeyPatch) -> None:
    events, _, page = _install_browser(monkeypatch)
    original_goto = page.goto
    def fail(*args: object, **kwargs: object) -> None:
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
    finally:
        browser.close()


def test_remote_browser_disconnect_keeps_host_process_alive(monkeypatch: MonkeyPatch) -> None:
    events, _, _ = _install_browser(monkeypatch)
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
