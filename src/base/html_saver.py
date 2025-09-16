"""保存HTML到文件"""

import os
import glob
from datetime import datetime
from src.base.logger import logger


class HTMLSaver:
    def __init__(self):
        self.html_dir = os.path.join(os.path.dirname(__file__), "..", "data", "HTMLs")
        os.makedirs(self.html_dir, exist_ok=True)
        self.max_files = 10

    def save_html(self, html_content: str, url: str) -> bool:
        """保存 HTML 内容，保持最多10个文件

        Args:
            html_content: HTML 内容
            url: 请求的 URL

        Returns:
            bool: 保存是否成功
        """
        try:
            # 生成文件名：时间戳 + URL中的关键信息
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            # 从URL中提取关键信息
            url_info = self._extract_url_info(url)
            filename = f"{timestamp}_{url_info}.html"

            filepath = os.path.join(self.html_dir, filename)

            # 保存HTML内容
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(html_content)

            logger.debug(f"HTML已保存到: {filename}")

            # 清理旧文件，保持最新的10个
            self._cleanup_old_files()

            return True

        except Exception as e:
            logger.error(f"保存HTML失败: {e}")
            return False

    def _extract_url_info(self, url: str) -> str:
        """从URL中提取关键信息作为文件名"""
        try:
            # 提取 showType 和 offset 信息
            parts = []
            if "showType=" in url:
                show_type = url.split("showType=")[1].split("&")[0]
                show_type_name = "热映" if show_type == "1" else "即将"
                parts.append(show_type_name)

            if "offset=" in url:
                offset = url.split("offset=")[1].split("&")[0]
                page = str(int(offset) // 18 + 1)
                parts.append(f"p{page}")

            return "_".join(parts) if parts else "page"

        except Exception:
            return "page"

    def _cleanup_old_files(self):
        """清理旧的HTML文件，保持最新的10个"""
        try:
            # 获取所有HTML文件
            pattern = os.path.join(self.html_dir, "*.html")
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
                        logger.debug(f"删除旧的HTML文件: {filename}")
                    except Exception as e:
                        logger.error(f"删除文件失败 {file_path}: {e}")

        except Exception as e:
            logger.error(f"清理旧文件失败: {e}")


html_saver = HTMLSaver()
