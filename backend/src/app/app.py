"""创建并配置 FastAPI 应用实例。"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.bootstrap import bootstrap_runtime
from app.core.config import config_manager
from app.error_handlers import register_exception_handlers
from app.routes import api_router
from app.show.scheduler import show_scheduler


@asynccontextmanager
async def lifespan(_: FastAPI):
    """应用生命周期:启动调度器,关闭时停止。"""
    show_scheduler.start()
    try:
        yield
    finally:
        show_scheduler.shutdown()


def create_app() -> FastAPI:
    """显式完成运行时初始化并创建 FastAPI 应用。"""
    bootstrap_runtime()

    fastapi_app = FastAPI(title="Movie Scheduler API", version="1.0.0", lifespan=lifespan)
    register_exception_handlers(fastapi_app)
    fastapi_app.include_router(api_router)
    fastapi_app.add_middleware(
        CORSMiddleware,
        allow_origins=config_manager.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    return fastapi_app


app = create_app()
