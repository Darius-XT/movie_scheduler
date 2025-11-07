"""更新场次日期用解析器"""

import re
from typing import List, Optional
from bs4 import BeautifulSoup
from src.utils.logger import logger


class HtmlWithAllMovieShowDateParser:
    def parse_html_with_all_movie_showdate(self, html_content: str) -> List[str]:
        """解析HTML内容，提取所有上映日期列表

        Args:
            html_content (str): 猫眼电影场次页面的HTML内容。
                示例值: "<html><body>...</body></html>"

        Returns:
            List[str]: 日期列表，每个日期格式为 "YYYY-MM-DD"。
                如果解析失败或HTML为空，返回空列表 []。
                示例返回值: ["2025-11-10", "2025-11-11", "2025-11-12"]
        """
        try:
            logger.debug("解析HTML内容，提取上映日期")
            soup = BeautifulSoup(html_content, "html.parser")

            dates: List[str] = []

            # 找到包含"日期:"的标签标题
            date_title = soup.find(
                "div", class_="tags-title", string=re.compile("日期")
            )
            if not date_title:
                logger.warning("未找到日期标签标题")
                return []

            # 找到日期标签所在的父级容器
            date_tags_line = date_title.find_parent("li", class_="tags-line")
            if not date_tags_line or not hasattr(date_tags_line, "find_all"):
                logger.warning("未找到日期标签容器")
                return []

            # 找到所有日期链接
            # type: ignore - BeautifulSoup 的 find_parent 在找到元素时会返回 Tag 对象，具有 find_all 方法
            date_links = date_tags_line.find_all("a", {"data-act": "tag-click"})  # type: ignore
            for link in date_links:
                date_str = self._extract_date_from_link(link)
                if date_str:
                    dates.append(date_str)

            logger.debug(f"成功解析 {len(dates)} 个上映日期")
            return dates
        except Exception as e:
            logger.error(f"解析HTML内容失败: {e}")
            return []

    def _extract_date_from_link(self, link) -> Optional[str]:
        """从链接元素中提取日期字符串

        Args:
            link: BeautifulSoup 链接元素对象

        Returns:
            Optional[str]: 日期字符串，格式为 "YYYY-MM-DD"，如果提取失败返回 None
        """
        try:
            data_val = link.get("data-val", "")
            if not data_val:
                logger.debug("链接元素缺少 data-val 属性")
                return None

            # 从 data-val="{TagName:'2025-11-10'}" 中提取日期
            # 使用正则表达式匹配日期格式 YYYY-MM-DD
            date_match = re.search(r"'(\d{4}-\d{2}-\d{2})'", data_val)
            if date_match:
                date_str = date_match.group(1)
                return date_str
            else:
                logger.debug(f"未能从 data-val 中提取日期: {data_val}")
                return None
        except Exception as e:
            logger.error(f"提取日期失败: {e}")
            return None


html_with_all_movie_showdate_parser = HtmlWithAllMovieShowDateParser()

if __name__ == "__main__":
    html_content = open(
        "data/demo/html_with_all_movie_showdate.html", "r", encoding="utf-8"
    ).read()
    dates = html_with_all_movie_showdate_parser.parse_html_with_all_movie_showdate(
        html_content
    )
    print(dates)
