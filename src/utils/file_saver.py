"""保存HTML到文件"""

import os
import glob
from datetime import datetime
from src.utils.logger import logger
from src.config_manager import config_manager


class FileSaver:
    def __init__(self):
        self.file_dir = config_manager.test_file_dir
        os.makedirs(self.file_dir, exist_ok=True)
        self.max_files = config_manager.file_max_count or 10

    def save_file(self, file_content: str, file_type: str = "html") -> bool:
        """保存文件内容到测试文件目录，自动清理旧文件保持最多10个文件

        Args:
            file_content (str): 要保存的文件内容（字符串）。
                示例值: "<html><body>Hello World</body></html>", '{"key": "value"}'
            file_type (str): 文件扩展名（不含点号）。
                默认为 "html"。
                示例值: "html", "json", "txt"

        Returns:
            bool: 保存是否成功。
                True 表示保存成功，
                False 表示保存失败（文件系统错误）。
                保存的文件名格式为: YYYYMMDD_HHMMSS.{file_type}
                例如: 20250930_143645.html
        """
        try:
            # 生成文件名：时间戳 + URL中的关键信息
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            filename = f"{timestamp}.{file_type}"

            filepath = os.path.join(self.file_dir, filename)

            # 保存文件内容
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(file_content)

            logger.debug(f"文件已保存到: {filename}")

            # 清理旧文件，保持最新的10个
            self._cleanup_old_files()

            return True

        except Exception as e:
            logger.error(f"保存文件失败: {e}")
            return False

    def _cleanup_old_files(self):
        """清理旧的文件，保持最新的10个"""
        try:
            # 获取所有文件（任何后缀）
            pattern = os.path.join(self.file_dir, "*")
            all_files = glob.glob(pattern)

            # 过滤出文件（排除目录）
            files = [f for f in all_files if os.path.isfile(f)]

            # 按修改时间排序，最新的在前
            files.sort(key=os.path.getmtime, reverse=True)

            # 如果超过最大文件数，删除最旧的文件
            if len(files) > self.max_files:
                files_to_delete = files[self.max_files :]
                for file_path in files_to_delete:
                    try:
                        os.remove(file_path)
                        filename = os.path.basename(file_path)
                        logger.debug(f"删除旧的文件: {filename}")
                    except Exception as e:
                        logger.error(f"删除文件失败 {file_path}: {e}")

        except Exception as e:
            logger.error(f"清理旧文件失败: {e}")


file_saver = FileSaver()
