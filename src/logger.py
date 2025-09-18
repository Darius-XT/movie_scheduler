"""日志记录"""

import logging
from pathlib import Path
from datetime import datetime
from src.config import settings


# 清理旧的日志文件
def clean_old_logs(log_dir: str, max_files: int | None = None):
    max_files = max_files or settings.log_file_max_count
    log_path = Path(log_dir)
    if not log_path.exists():
        return

    # 查找所有日志文件
    log_files = list(log_path.glob(f"{settings.logger_name}_*.log"))

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
    log_level = level or settings.log_level
    level_int = getattr(logging, log_level.upper(), logging.INFO)

    # 创建logger
    logger = logging.getLogger(settings.logger_name)
    logger.setLevel(level_int)

    # 控制台输出
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(settings.log_console_format))
    logger.addHandler(console_handler)

    # 文件输出
    log_dir = Path(settings.log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)

    # 清理旧日志文件
    clean_old_logs(str(log_dir))

    # 每天的日志保存在不同文件
    today = datetime.now().strftime("%Y-%m-%d")
    log_file = log_dir / f"{settings.logger_name}_{today}.log"

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(logging.Formatter(settings.log_file_format))
    logger.addHandler(file_handler)

    return logger


# 创建默认logger实例
logger = setup_logger()
