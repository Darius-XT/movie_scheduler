"""保存HTML到文件"""

import os
import glob
from datetime import datetime
from src.logger import logger
from src.config import settings


class FileSaver:
    def __init__(self):
        self.file_dir = settings.test_file_dir
        os.makedirs(self.file_dir, exist_ok=True)
        self.max_files = settings.file_max_count

    def _cleanup_old_files(self):
        """清理旧的文件，保持最新的10个"""
        try:
            # 获取所有文件
            pattern = os.path.join(self.file_dir, "*.html")
            html_files = glob.glob(pattern)

            # 按修改时间排序，最新的在前
            html_files.sort(key=os.path.getmtime, reverse=True)

            # 如果超过最大文件数，删除最旧的文件
            if len(html_files) > self.max_files:
                files_to_delete = html_files[self.max_files :]
                for file_path in files_to_delete:
                    try:
                        os.remove(file_path)
                        filename = os.path.basename(file_path)
                        logger.debug(f"删除旧的文件: {filename}")
                    except Exception as e:
                        logger.error(f"删除文件失败 {file_path}: {e}")

        except Exception as e:
            logger.error(f"清理旧文件失败: {e}")

    def save_file(self, file_content: str, file_type: str = "html") -> bool:
        """保存文件内容，保持最多10个文件

        Args:
            file_content: 文件内容

        Returns:
            bool: 保存是否成功
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


file_saver = FileSaver()
