"""日志记录"""

import logging
import colorlog
from src.config_manager import config_manager


# 创建并配置logger
def setup_logger(level: str | None = None) -> logging.Logger:
    # 获取日志级别
    log_level = level or config_manager.log_level or "info"
    level_int = getattr(logging, log_level.upper(), logging.INFO)

    # 创建logger
    logger = logging.getLogger(config_manager.logger_name or "movie_scheduler")
    logger.setLevel(level_int)

    # 清除已有的 handler，避免重复添加
    logger.handlers.clear()

    # 控制台输出（彩色）
    console_handler = logging.StreamHandler()
    console_format = (
        config_manager.log_console_format or "%(asctime)s - %(levelname)s - %(message)s"
    )

    # 定义颜色体系（日期和等级使用相同的颜色）
    log_colors = {
        "DEBUG": "cyan",
        "INFO": "green",
        "WARNING": "yellow",
        "ERROR": "red",
        "CRITICAL": "red,bg_white",
    }

    # 如果格式中没有颜色标记，自动添加
    if "%(log_color)s" not in console_format:
        # 在 asctime 周围添加颜色标记
        console_format = console_format.replace(
            "%(asctime)s", "%(asctime_log_color)s%(asctime)s%(reset)s"
        )
        # 在 levelname 周围添加颜色标记
        console_format = console_format.replace(
            "%(levelname)s", "%(log_color)s%(levelname)s%(reset)s"
        )

    console_handler.setFormatter(
        colorlog.ColoredFormatter(
            console_format,
            datefmt="%Y-%m-%d %H:%M:%S",
            reset=True,
            log_colors=log_colors,
            secondary_log_colors={"asctime": log_colors},
        )
    )
    logger.addHandler(console_handler)

    return logger


# 创建默认logger实例
logger = setup_logger()
