"""后端启动引导。"""

from __future__ import annotations

from app.core.config import config_manager
from app.core.database import database_manager
from app.core.file_saver import file_saver
from app.core.logger import setup_logger


def bootstrap_runtime() -> None:
    """显式执行配置、目录、日志和数据库初始化。"""
    config_manager.reload_from_env()
    config_manager.ensure_runtime_dirs()
    setup_logger()
    file_saver.initialize()
    database_manager.initialize()
