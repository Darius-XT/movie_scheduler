"""日志记录"""

import logging
from pathlib import Path
from datetime import datetime
import atexit
from singleton_decorator import singleton
from src.config import settings


def get_log_level_int(level_str: str) -> int:
    """将字符串日志级别转换为整数"""
    level_map = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL,
    }
    return level_map.get(level_str.upper(), logging.INFO)


# 清理旧的日志文件，只保留最近的文件
def clean_old_logs(log_dir: str, max_files: int | None = None):
    max_files = max_files or settings.log_file_max_count
    log_path = Path(log_dir)
    if not log_path.exists():
        return

    # 查找所有日志文件 (格式: movie_fetcher_YYYY-MM-DD.log)
    log_files = list(log_path.glob(f"{settings.logger_name}_*.log"))

    # 按文件修改时间排序，最新的在前
    log_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)

    # 删除超出数量限制的旧文件
    for old_file in log_files[max_files:]:
        try:
            old_file.unlink()
            print(f"已删除旧日志文件: {old_file.name}")
        except Exception as e:
            print(f"删除日志文件失败 {old_file.name}: {e}")


@singleton
def setup_logger(
    level: int | None = None, log_dir: str | None = None
) -> logging.Logger:
    """使用第三方 singleton 装饰器实现惰性单例日志器创建。

    第一次调用时根据传入参数创建 logger，后续无论参数如何，均返回同一实例。
    """
    # 使用配置中的默认值
    level = level or get_log_level_int(settings.log_level)
    log_dir = log_dir or settings.log_dir

    # 添加运行分隔符到日志文件
    def add_run_separator(log_file_path: Path):
        try:
            with open(log_file_path, "a", encoding="utf-8") as f:
                if log_file_path.stat().st_size > 0:
                    f.write("\n")
        except Exception as e:
            print(f"添加运行分隔符失败: {e}")

    # 清理旧日志文件
    clean_old_logs(log_dir)

    # 获取logger
    logger = logging.getLogger(settings.logger_name)
    logger.setLevel(level)

    # 清除已有的处理器
    logger.handlers.clear()

    # 控制台输出
    console_handler = logging.StreamHandler()
    console_formatter = logging.Formatter(settings.log_console_format)
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # 文件输出 - 使用配置中的格式
    if settings.log_file_enabled:
        today = datetime.now().strftime("%Y-%m-%d")
        log_filename = settings.log_file_name_format.format(date=today)
        log_file = Path(log_dir) / log_filename

        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_formatter = logging.Formatter(settings.log_file_format)
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

        atexit.register(add_run_separator, log_file)

    return logger
