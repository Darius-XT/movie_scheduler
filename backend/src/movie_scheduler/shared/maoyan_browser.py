"""在专用线程中复用无头浏览器，供同步抓取入口调用。"""

from __future__ import annotations

import socket
from collections.abc import Generator
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from contextvars import ContextVar, copy_context
from dataclasses import dataclass
from threading import Event, Lock
from time import monotonic, sleep
from urllib.parse import urlsplit

from playwright._impl._api_structures import SetCookieParam
from playwright.sync_api import Browser, BrowserContext, Playwright, sync_playwright

from movie_scheduler.config import config_manager
from movie_scheduler.core.exceptions import MaoyanVerificationError
from movie_scheduler.core.logging import logger
from movie_scheduler.core.request_logging import log_external_http_request


@dataclass(frozen=True)
class _PageRequest:
    url: str
    purpose: str
    city_id: int
    cookie: str
    timeout: int
    verify: bool
    mobile: bool
    user_agent: str | None


class MaoyanBrowser:
    """所有 Playwright 操作固定到同一线程；同时最多加载一个页面。"""

    def __init__(self) -> None:
        self._executor: ThreadPoolExecutor | None = None
        self._lock = Lock()
        self._playwright: Playwright | None = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._context_key: tuple[int, bool, bool, str, str | None] | None = None
        self._remote = False
        self._last_request_at: float | None = None
        self._batch_stopped: ContextVar[Event | None] = ContextVar("maoyan_batch_stopped", default=None)

    @contextmanager
    def batch(self) -> Generator[None, None, None]:
        """同一轮及其子任务共享停止状态；下一轮可以重新尝试。"""
        current = self._batch_stopped.get()
        if current is not None:
            if current.is_set():
                raise MaoyanVerificationError()
            yield
            if current.is_set():
                raise MaoyanVerificationError()
            return
        stopped = Event()
        token = self._batch_stopped.set(stopped)
        try:
            yield
            if stopped.is_set():
                raise MaoyanVerificationError()
        except MaoyanVerificationError:
            stopped.set()
            raise
        finally:
            self._batch_stopped.reset(token)

    def get_text(
        self, url: str, purpose: str, city_id: int, *, cookie: str,
        timeout: int, verify: bool, mobile: bool = False, user_agent: str | None = None,
    ) -> str | None:
        """返回 HTML；普通失败返回 None，验证页抛出异常停止本轮，不记录敏感响应。"""
        request = _PageRequest(url, purpose, city_id, cookie, timeout, verify, mobile, user_agent)
        with self._lock:
            if self._executor is None:
                self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="maoyan-browser")
            future = self._executor.submit(copy_context().run, self._get_text, request)
        return future.result()

    def close(self) -> None:
        """等待已排队请求结束并释放浏览器和工作线程。"""
        with self._lock:
            if self._executor is not None:
                try:
                    self._executor.submit(self._close_browser).result()
                finally:
                    self._executor.shutdown(wait=True)
                    self._executor = None

    def _get_text(self, request: _PageRequest) -> str | None:
        stopped = self._batch_stopped.get()
        if stopped is not None and stopped.is_set():
            raise MaoyanVerificationError()
        try:
            context = self._ensure_context(request)
            self._update_cookies(context, request.cookie)
            page = context.new_page()
            try:
                self._wait_for_request_slot()
                log_external_http_request("GET", request.url, purpose=request.purpose)
                self._last_request_at = monotonic()
                response = page.goto(request.url, wait_until="domcontentloaded", timeout=request.timeout * 1000)
                text = page.content()
                if self._is_verification(page.url, page.title(), text):
                    if stopped is not None:
                        stopped.set()
                    logger.warning("%s失败: 猫眼要求身份验证，已停止本轮剩余抓取", request.purpose)
                    raise MaoyanVerificationError()
                if response is None or not response.ok:
                    logger.warning("%s失败: 浏览器 HTTP 状态=%s", request.purpose, response.status if response else None)
                    return None
                return text
            finally:
                page.close()
        except MaoyanVerificationError:
            raise
        except Exception as error:
            # Playwright 异常可能包含带 token 的跳转地址，只记录异常类型。
            logger.warning("%s失败: 无头浏览器 %s", request.purpose, type(error).__name__)
            self._close_browser()
            return None

    def _wait_for_request_slot(self) -> None:
        # 专用线程共用请求间隔；失败或重建浏览器也不重置，空闲不积累突发额度。
        if self._last_request_at is not None:
            delay = self._last_request_at + 1 / config_manager.maoyan_qps - monotonic()
            if delay > 0:
                sleep(delay)

    def _ensure_context(self, request: _PageRequest) -> BrowserContext:
        if self._browser is None or not self._browser.is_connected():
            self._close_browser()
            self._playwright = sync_playwright().start()
            self._remote = bool(config_manager.maoyan_browser_cdp_url)
            if self._remote:
                self._browser = self._playwright.chromium.connect_over_cdp(
                    self._cdp_endpoint(config_manager.maoyan_browser_cdp_url), timeout=request.timeout * 1000,
                )
            else:
                self._browser = self._playwright.chromium.launch(
                    channel=config_manager.maoyan_browser_channel, headless=True,
                )
        key = (request.city_id, request.mobile, request.verify, config_manager.maoyan_cookie, request.user_agent)
        if self._context is not None and self._context_key != key:
            self._context.close()
            self._context = None
        if self._context is None:
            self._context = self._browser.new_context(
                locale="zh-CN", ignore_https_errors=not request.verify,
                is_mobile=request.mobile, has_touch=request.mobile,
                user_agent=request.user_agent,
            )
            self._context_key = key
            self._update_cookies(self._context, config_manager.maoyan_cookie)
        return self._context

    def _cdp_endpoint(self, endpoint: str) -> str:
        # Chrome 的 HTTP 调试入口只接受 localhost 或 IP Host；容器需解析宿主机别名。
        parsed = urlsplit(endpoint)
        if parsed.hostname == "host.docker.internal":
            address = socket.gethostbyname(parsed.hostname)
            return parsed._replace(netloc=f"{address}:{parsed.port or 9223}").geturl()
        return endpoint

    def _update_cookies(self, context: BrowserContext, cookie: str) -> None:
        cookies: list[SetCookieParam] = []
        for item in cookie.split(";"):
            name, separator, value = item.strip().partition("=")
            if separator and name:
                cookies.append({"name": name, "value": value, "domain": ".maoyan.com", "path": "/"})
        if cookies:
            context.add_cookies(cookies)

    def _is_verification(self, url: str, title: str, text: str) -> bool:
        return (
            urlsplit(url).hostname == "verify.meituan.com"
            or any(marker in title for marker in ("验证中心", "身份核实", "安全验证"))
            or ("verify.meituan.com" in text and "身份核实" in text)
        )

    def _close_browser(self) -> None:
        try:
            if self._remote and self._context is not None:
                self._context.close()
            elif self._browser is not None and not self._remote:
                self._browser.close()
        finally:
            self._browser = None
            self._context = None
            self._context_key = None
            if self._playwright is not None:
                try:
                    self._playwright.stop()
                finally:
                    self._playwright = None


maoyan_browser = MaoyanBrowser()
