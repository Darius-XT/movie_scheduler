import logging
from pathlib import Path
from datetime import datetime
import atexit


# 清理旧的日志文件，只保留最近的文件
def clean_old_logs(log_dir: str, max_files: int = 7):
    log_path = Path(log_dir)
    if not log_path.exists():
        return

    # 查找所有日志文件 (格式: movie_fetcher_YYYY-MM-DD.log)
    log_files = list(log_path.glob("movie_fetcher_*.log"))

    # 按文件修改时间排序，最新的在前
    log_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)

    # 删除超出数量限制的旧文件
    for old_file in log_files[max_files:]:
        try:
            old_file.unlink()
            print(f"已删除旧日志文件: {old_file.name}")
        except Exception as e:
            print(f"删除日志文件失败 {old_file.name}: {e}")


# 初始化日志对象
def setup_logger(level: int = logging.INFO, log_dir: str = "logs") -> logging.Logger:
    # 添加运行分隔符到日志文件
    def add_run_separator(log_file_path: Path):
        try:
            with open(log_file_path, "a", encoding="utf-8") as f:
                if log_file_path.stat().st_size > 0:
                    f.write("\n")
        except Exception as e:
            print(f"添加运行分隔符失败: {e}")

    # 创建日志目录
    Path(log_dir).mkdir(exist_ok=True)

    # 清理旧日志文件
    clean_old_logs(log_dir)

    # 获取logger
    logger = logging.getLogger("movie_fetcher")
    logger.setLevel(level)

    # 清除已有的处理器
    logger.handlers.clear()

    # 控制台输出
    console_handler = logging.StreamHandler()
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 文件输出 - 使用日期命名
    today = datetime.now().strftime("%Y-%m-%d")
    log_file = Path(log_dir) / f"movie_fetcher_{today}.log"
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    atexit.register(add_run_separator, log_file)

    return logger


logger = setup_logger(level=logging.INFO, log_dir="src/data/logs")
