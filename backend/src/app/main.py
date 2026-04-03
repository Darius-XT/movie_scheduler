"""FastAPI 应用入口。"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import api_router
from app.api.error_handlers import register_exception_handlers
from app.core.bootstrap import bootstrap_runtime
from app.core.config import config_manager


def create_app() -> FastAPI:
    """显式完成运行时初始化并创建 FastAPI 应用。"""
    bootstrap_runtime()

    app = FastAPI(title="Movie Scheduler API", version="1.0.0")
    register_exception_handlers(app)
    app.include_router(api_router)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config_manager.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    return app


app = create_app()


def main() -> None:
    """用于本地直接启动后端服务。"""
    import uvicorn

    uvicorn.run(
        app,
        host=config_manager.host,
        port=config_manager.port,
        reload=False,
    )


if __name__ == "__main__":
    main()
