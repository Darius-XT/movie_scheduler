"""日志记录。"""

from __future__ import annotations

import logging

import colorlog

from app.core.config import config_manager

logger = logging.getLogger("movie_scheduler")


def setup_logger(level: str | None = None) -> logging.Logger:
    """配置统一日志实例。"""
    log_level = level or config_manager.log_level or "info"
    level_int = getattr(logging, log_level.upper(), logging.INFO)

    logger.setLevel(level_int)
    logger.propagate = False
    logger.handlers.clear()

    console_handler = logging.StreamHandler()
    console_format = config_manager.log_console_format or "%(asctime)s - %(levelname)s - %(message)s"

    log_colors = {
        "DEBUG": "cyan",
        "INFO": "green",
        "WARNING": "yellow",
        "ERROR": "red",
        "CRITICAL": "red,bg_white",
    }

    if "%(log_color)s" not in console_format:
        console_format = console_format.replace("%(asctime)s", "%(asctime_log_color)s%(asctime)s%(reset)s")
        console_format = console_format.replace("%(levelname)s", "%(log_color)s%(levelname)s%(reset)s")

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
