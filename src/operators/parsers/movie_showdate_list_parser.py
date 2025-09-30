"""解析影院页HTML中的可选放映日期列表"""

from typing import List, Optional, Any, cast
from urllib.parse import urlparse, parse_qs
from bs4 import BeautifulSoup
from src.logger import logger


class MovieShowdateListParser:
    """从影院列表页面(含 movieId 的页面)解析日期筛选项"""

    def __init__(self):
        pass

    def parse_movie_showdate_list(self, html_content: str) -> List[str]:
        """解析HTML，返回日期筛选列表

        Returns:
            List[str]: 日期字符串列表，如 ["2025-09-30", "2025-10-01", ...]
        """
        try:
            logger.debug("解析影院页HTML中的日期筛选...")
            soup = BeautifulSoup(html_content, "html.parser")

            container_li = self._find_date_tags_container(soup)
            if container_li is None:
                logger.warning("未找到日期筛选容器")
                return []

            result: List[str] = []
            li_tag: Any = container_li
            ul = cast(Any, li_tag).find("ul", class_="tags")
            if not ul:
                logger.warning("未找到日期标签列表")
                return []

            for li in cast(Any, ul).find_all("li"):
                li_tag = cast(Any, li)
                anchor = cast(Any, li_tag).find("a")
                if not anchor:
                    continue

                href = str(cast(Any, anchor).get("href", ""))
                date_value = self._extract_show_date_from_href(href)

                if not date_value:
                    logger.debug(f"跳过无 showDate 的链接: {href}")
                    continue

                result.append(date_value)

            logger.debug(f"成功解析 {len(result)} 个日期筛选项")
            return result

        except Exception as e:
            logger.error(f"解析日期筛选失败: {e}")
            return []

    def _find_date_tags_container(self, soup) -> Optional[object]:
        """定位包含“日期:”标题的 li.tags-line 容器"""
        try:
            for li in soup.find_all("li", class_="tags-line"):
                title_div = li.find("div", class_="tags-title")
                if title_div and "日期" in title_div.get_text(strip=True):
                    return li
            return None
        except Exception as e:
            logger.error(f"定位日期筛选容器失败: {e}")
            return None

    def _extract_show_date_from_href(self, href: str) -> Optional[str]:
        """从 href 的查询参数中提取 showDate 值"""
        try:
            # href 形如: ?movieId=361&showDate=2025-09-30
            parsed = urlparse(href)
            # urlparse 对于以 ? 开头的相对链接，query 会在 parsed.query 中
            query = parsed.query
            # 如果直接是 '?a=b&c=d' 这种，urlparse 可用；若是纯文本包含 '?', 也处理
            if not query and "?" in href:
                query = href.split("?", 1)[1]
            params = parse_qs(query)
            values = params.get("showDate")
            if values:
                return values[0]
            return None
        except Exception as e:
            logger.debug(f"从href提取 showDate 失败: {href}, 错误: {e}")
            return None


# 创建解析器实例
movie_showdate_list_parser = MovieShowdateListParser()


if __name__ == "__main__":
    import logging

    logger.setLevel(logging.DEBUG)
    with open("src/datas/demos/movie_showdate_list.html", "r", encoding="utf-8") as f:
        html_content = f.read()
    dates = movie_showdate_list_parser.parse_movie_showdate_list(html_content)
    print(dates)
