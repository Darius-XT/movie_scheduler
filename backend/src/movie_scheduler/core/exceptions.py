"""应用级异常类型与全局 handler 注册。"""

from __future__ import annotations

from typing import cast

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.types import ExceptionHandler

from movie_scheduler.core.logging import logger


class AppError(Exception):
    """用于向接口层传递可预期的业务异常。"""

    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class RepositoryError(Exception):
    """用于表示数据库访问失败。"""


class ExternalDependencyError(Exception):
    """用于表示外部依赖调用失败。"""


class DataParsingError(Exception):
    """用于表示外部数据解析失败。"""


def register_exception_handlers(app: FastAPI) -> None:
    """注册应用的统一异常处理器。"""

    async def handle_app_error(_: Request, error: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=error.status_code,
            content={"success": False, "error": error.message},
        )

    async def handle_repository_error(_: Request, error: RepositoryError) -> JSONResponse:
        logger.exception("接口发生数据库访问异常: %s", error)
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": "数据库访问失败,请稍后重试"},
        )

    async def handle_external_dependency_error(_: Request, error: ExternalDependencyError) -> JSONResponse:
        logger.warning("接口依赖的外部服务调用失败: %s", error)
        return JSONResponse(
            status_code=502,
            content={"success": False, "error": "外部数据源请求失败,请稍后重试"},
        )

    async def handle_data_parsing_error(_: Request, error: DataParsingError) -> JSONResponse:
        logger.warning("接口依赖的外部数据解析失败: %s", error)
        return JSONResponse(
            status_code=502,
            content={"success": False, "error": "外部数据解析失败,请稍后重试"},
        )

    async def handle_unexpected_error(_: Request, error: Exception) -> JSONResponse:
        logger.exception("接口发生未处理异常: %s", error)
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": "服务器内部错误"},
        )

    app.add_exception_handler(AppError, cast(ExceptionHandler, handle_app_error))
    app.add_exception_handler(RepositoryError, cast(ExceptionHandler, handle_repository_error))
    app.add_exception_handler(ExternalDependencyError, cast(ExceptionHandler, handle_external_dependency_error))
    app.add_exception_handler(DataParsingError, cast(ExceptionHandler, handle_data_parsing_error))
    app.add_exception_handler(Exception, cast(ExceptionHandler, handle_unexpected_error))
