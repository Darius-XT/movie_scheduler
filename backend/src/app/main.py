"""本地启动入口。"""

from __future__ import annotations

import uvicorn

from app.app import app
from app.core.config import config_manager


def main() -> None:
    """用于本地直接启动后端服务。"""
    uvicorn.run(
        app,
        host=config_manager.host,
        port=config_manager.port,
        reload=False,
    )


if __name__ == "__main__":
    main()
