"""日志记录"""

import logging
from pathlib import Path
from datetime import datetime
import colorlog
from src.config_manager import config_manager


# 清理旧的日志文件
def clean_old_logs(log_dir: str, max_files: int | None = None):
    max_files = max_files or config_manager.log_max_count
    log_path = Path(log_dir)
    if not log_path.exists():
        return

    # 查找所有日志文件
    logger_name = config_manager.logger_name or "movie_scheduler"
    log_files = list(log_path.glob(f"{logger_name}_*.log"))

    # 按文件修改时间排序，最新的在前
    log_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)

    # 删除超出数量限制的旧文件
    for old_file in log_files[max_files:]:
        try:
            old_file.unlink()
            print(f"已删除旧日志文件: {old_file.name}")
        except Exception as e:
            print(f"删除文件失败 {old_file.name}: {e}")


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

    # 文件输出
    log_dir = Path(config_manager.log_dir or "data/log")
    log_dir.mkdir(parents=True, exist_ok=True)

    # 清理旧日志文件
    clean_old_logs(str(log_dir))

    # 每天的日志保存在不同文件
    today = datetime.now().strftime("%Y-%m-%d")
    logger_name = config_manager.logger_name or "movie_scheduler"
    log_file = log_dir / f"{logger_name}_{today}.log"

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_format = (
        config_manager.log_file_format or "%(asctime)s - %(levelname)s - %(message)s"
    )
    file_handler.setFormatter(
        logging.Formatter(file_format, datefmt="%Y-%m-%d %H:%M:%S")
    )
    logger.addHandler(file_handler)

    return logger


# 创建默认logger实例
logger = setup_logger()
