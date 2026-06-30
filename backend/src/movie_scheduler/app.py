"""创建并配置 FastAPI 应用实例。"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from movie_scheduler.config import config_manager
from movie_scheduler.core.db import database_manager
from movie_scheduler.core.exceptions import register_exception_handlers
from movie_scheduler.core.logging import setup_logger
from movie_scheduler.core.request_logging import RequestLoggingMiddleware
from movie_scheduler.core.scheduler import auto_update_scheduler
from movie_scheduler.features.cinema.router import router as cinema_router
from movie_scheduler.features.city.router import router as city_router
from movie_scheduler.features.movie.router import router as movie_router
from movie_scheduler.features.plan.router import router as plan_router
from movie_scheduler.features.show.router import router as show_router
from movie_scheduler.shared.utils import file_saver


def _bootstrap_runtime() -> None:
    """显式执行配置、目录、日志和数据库初始化。"""
    config_manager.reload_from_env()
    config_manager.ensure_runtime_dirs()
    setup_logger()
    file_saver.initialize()
    database_manager.initialize()


@asynccontextmanager
async def lifespan(_: FastAPI):
    """应用生命周期:启动自动更新调度器,关闭时停止。"""
    auto_update_scheduler.start()
    try:
        yield
    finally:
        auto_update_scheduler.shutdown()


def create_app() -> FastAPI:
    """显式完成运行时初始化并创建 FastAPI 应用。"""
    _bootstrap_runtime()

    fastapi_app = FastAPI(title="Movie Scheduler API", version="1.0.0", lifespan=lifespan)
    register_exception_handlers(fastapi_app)

    api_router = APIRouter(prefix="/api")
    api_router.include_router(city_router)
    api_router.include_router(cinema_router)
    api_router.include_router(movie_router)
    api_router.include_router(plan_router)
    api_router.include_router(show_router)
    fastapi_app.include_router(api_router)

    fastapi_app.add_middleware(
        CORSMiddleware,
        allow_origins=config_manager.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    fastapi_app.add_middleware(RequestLoggingMiddleware)
    return fastapi_app


app = create_app()
