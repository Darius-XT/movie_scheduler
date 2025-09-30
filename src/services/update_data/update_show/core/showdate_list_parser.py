"""更新放映日期列表用解析器(由 get_movie_showdate_list 迁移并内联)"""

from typing import List, Optional, Any, cast
from bs4 import BeautifulSoup
from src.logger import logger


class UpdateShowdateListParser:
    def parse_movie_showdate_list(self, html_content: str) -> List[str]:
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
        try:
            for li in soup.find_all("li", class_="tags-line"):
                title_span = li.find("span", class_="tags-title")
                if title_span and "日期:" in title_span.get_text():
                    return li
            return None
        except Exception:
            return None

    def _extract_show_date_from_href(self, href: str) -> Optional[str]:
        try:
            from urllib.parse import urlparse, parse_qs

            parsed = urlparse(href)
            query_params = parse_qs(parsed.query)
            show_dates = query_params.get("showDate")
            if not show_dates:
                return None
            return show_dates[0]
        except Exception:
            return None


update_showdate_list_parser = UpdateShowdateListParser()
