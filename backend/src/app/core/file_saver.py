"""保存抓取结果文件。"""

from __future__ import annotations

import glob
import os
from datetime import datetime

from app.core.config import config_manager
from app.core.logger import logger


class FileSaver:
    """负责保存调试和示例结果文件。"""

    def __init__(self) -> None:
        self.file_dir = config_manager.result_dir
        self.max_files = config_manager.file_max_count

    def initialize(self) -> None:
        """显式创建输出目录。"""
        self.file_dir = config_manager.result_dir
        self.max_files = config_manager.file_max_count
        os.makedirs(self.file_dir, exist_ok=True)

    def save_file(self, file_content: str, file_type: str = "html") -> bool:
        """按时间戳保存结果文件。"""
        try:
            self.initialize()

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{timestamp}.{file_type}"
            filepath = os.path.join(self.file_dir, filename)

            with open(filepath, "w", encoding="utf-8") as file:
                file.write(file_content)

            logger.debug("文件已保存到: %s", filename)
            self._cleanup_old_files()
            return True
        except Exception as error:
            logger.error("保存文件失败: %s", error)
            return False

    def save_demo(self, file_content: str, filename: str) -> bool:
        """按固定文件名保存调试样本到 demo 目录。"""
        try:
            demo_dir = config_manager.demo_dir
            os.makedirs(demo_dir, exist_ok=True)
            filepath = os.path.join(demo_dir, filename)
            with open(filepath, "w", encoding="utf-8") as file:
                file.write(file_content)
            logger.debug("样本文件已保存到: %s", filename)
            return True
        except Exception as error:
            logger.error("保存样本文件失败: %s", error)
            return False

    def save_example(self, file_content: str, filename: str) -> bool:
        """按固定文件名保存抓取结果示例。"""
        try:
            self.initialize()

            filepath = os.path.join(self.file_dir, filename)
            with open(filepath, "w", encoding="utf-8") as file:
                file.write(file_content)

            logger.debug("示例文件已保存到: %s", filename)
            return True
        except Exception as error:
            logger.error("保存示例文件失败: %s", error)
            return False

    def _cleanup_old_files(self) -> None:
        """清理旧文件，仅保留最近的结果文件。"""
        try:
            pattern = os.path.join(self.file_dir, "*")
            all_files = glob.glob(pattern)
            files = [file_path for file_path in all_files if os.path.isfile(file_path)]
            files.sort(key=os.path.getmtime, reverse=True)

            if len(files) > self.max_files:
                files_to_delete = files[self.max_files :]
                for file_path in files_to_delete:
                    try:
                        os.remove(file_path)
                        logger.debug("删除旧文件: %s", os.path.basename(file_path))
                    except Exception as error:
                        logger.error("删除文件失败 %s: %s", file_path, error)
        except Exception as error:
            logger.error("清理旧文件失败: %s", error)


file_saver = FileSaver()
