"""创建并配置 FastAPI 应用实例。"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.bootstrap import bootstrap_runtime
from app.core.config import config_manager
from app.error_handlers import register_exception_handlers
from app.routes import api_router


def create_app() -> FastAPI:
    """显式完成运行时初始化并创建 FastAPI 应用。"""
    bootstrap_runtime()

    fastapi_app = FastAPI(title="Movie Scheduler API", version="1.0.0")
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
