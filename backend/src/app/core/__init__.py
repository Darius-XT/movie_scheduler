"""后端基础设施统一出口。"""

from app.core import bootstrap as bootstrap
from app.core.bootstrap import bootstrap_runtime
from app.core.config import ConfigManager, config_manager
from app.core.database import DatabaseManager, database_manager
from app.core.file_saver import FileSaver, file_saver
from app.core.logger import logger, setup_logger

__all__ = [
    "ConfigManager",
    "bootstrap",
    "bootstrap_runtime",
    "config_manager",
    "DatabaseManager",
    "database_manager",
    "FileSaver",
    "file_saver",
    "logger",
    "setup_logger",
]
