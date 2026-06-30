"""HTTP 请求链路日志。"""

from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass
from time import perf_counter
from uuid import uuid4

from starlette.datastructures import Headers
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from movie_scheduler.core.logging import logger


@dataclass(slots=True)
class RequestLogContext:
    """当前内部接口请求的日志上下文。"""

    request_id: str
    method: str
    path: str


_request_log_context: ContextVar[RequestLogContext | None] = ContextVar(
    "request_log_context",
    default=None,
)


class RequestLoggingMiddleware:
    """记录每次内部 HTTP 接口调用。"""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        method = str(scope.get("method") or "")
        path = _build_full_path(scope)
        request_id = _extract_request_id(scope) or uuid4().hex[:12]
        context = RequestLogContext(request_id=request_id, method=method, path=path)
        token = _request_log_context.set(context)
        started_at = perf_counter()
        status_code: int | None = None

        async def send_wrapper(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                raw_status = message.get("status")
                if isinstance(raw_status, int):
                    status_code = raw_status
            await send(message)

        logger.info(
            "内部接口调用开始: request_id=%s method=%s path=%s client=%s",
            request_id,
            method,
            path,
            _client_address(scope),
        )
        try:
            await self.app(scope, receive, send_wrapper)
        except Exception as error:
            logger.exception(
                "内部接口调用异常: request_id=%s method=%s path=%s duration_ms=%.1f error=%s",
                request_id,
                method,
                path,
                _elapsed_ms(started_at),
                error,
            )
            raise
        finally:
            logger.info(
                "内部接口调用完成: request_id=%s method=%s path=%s status=%s duration_ms=%.1f",
                request_id,
                method,
                path,
                status_code if status_code is not None else "-",
                _elapsed_ms(started_at),
            )
            _request_log_context.reset(token)


def log_external_http_request(method: str, url: str, *, purpose: str | None = None) -> None:
    """记录外部 HTTP 请求 URL,不记录 headers / Cookie。"""
    context = _request_log_context.get()
    logger.info(
        "外部请求开始: request_id=%s internal_api=%s method=%s url=%s purpose=%s",
        context.request_id if context is not None else "-",
        context.path if context is not None else "background",
        method.upper(),
        url,
        purpose or "-",
    )


def _build_full_path(scope: Scope) -> str:
    path = str(scope.get("path") or "")
    raw_query = scope.get("query_string")
    if not isinstance(raw_query, bytes) or not raw_query:
        return path
    query = raw_query.decode("utf-8", errors="replace")
    return f"{path}?{query}"


def _extract_request_id(scope: Scope) -> str | None:
    raw_request_id = Headers(scope=scope).get("x-request-id")
    if raw_request_id is None:
        return None
    request_id = raw_request_id.strip()
    return request_id or None


def _client_address(scope: Scope) -> str:
    client: object = scope.get("client")
    match client:
        case (str() as host, int()):
            return host
        case _:
            return "-"


def _elapsed_ms(started_at: float) -> float:
    return (perf_counter() - started_at) * 1000
