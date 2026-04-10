"""解析电影列表页中的基础电影信息。"""

from __future__ import annotations

import re
from typing import Any

from bs4 import BeautifulSoup
from bs4.element import Tag

from app.core.logger import logger
from app.use_cases.update.movie_info.base_info.models import ScrapedMovieBaseInfo


class MovieBaseInfoParser:
    """负责解析电影列表页中的基础字段。"""

    def parse_movies(
        self,
        html_content: str,
    ) -> tuple[list[ScrapedMovieBaseInfo], bool]:
        """解析 HTML，返回电影列表和是否为预期空页。"""
        try:
            logger.debug("开始解析电影列表 HTML")
            soup = BeautifulSoup(html_content, "html.parser")

            no_movies_div = soup.find("div", class_="no-movies")
            if no_movies_div:
                no_movies_text = no_movies_div.get_text().strip()
                if "抱歉，当前城市暂未找到相关结果" in no_movies_text:
                    logger.debug("检测到 no-movies 提示，这是预期中的空页面")
                    return [], True

            movies: list[ScrapedMovieBaseInfo] = []
            for item in soup.find_all("dd"):
                movie_info = self._extract_movie_info(item)
                if movie_info is not None:
                    movies.append(movie_info)

            logger.debug("成功解析 %s 部电影信息", len(movies))
            return movies, False
        except Exception as error:
            logger.error("解析电影列表 HTML 失败: %s", error)
            return [], False

    def _normalize_field(self, value: Any, default_text: str) -> str | Any:
        """把空值统一转换成默认文案。"""
        if value is None:
            return default_text
        if isinstance(value, str) and not value.strip():
            return default_text
        return value

    def _extract_movie_info(self, item: Tag) -> ScrapedMovieBaseInfo | None:
        """从单个条目中提取电影基础信息。"""
        try:
            movie_link = item.find("a", href=re.compile(r"/films/\d+"))
            if movie_link is None:
                logger.warning("没有在 dd 中匹配到有效电影链接")
                return None

            href = movie_link.get("href")
            if not isinstance(href, str):
                return None

            movie_id_match = re.search(r"/films/(\d+)", href)
            if movie_id_match is None:
                logger.warning("没有在 href 中匹配到电影 ID: %s", href)
                return None
            movie_id = int(movie_id_match.group(1))

            title: str | None = None
            title_element = item.find("div", class_="movie-item-title")
            title_link = title_element.find("a") if title_element is not None else None
            if title_link is not None:
                title = title_link.get_text().strip()
            else:
                logger.warning("没有在电影条目中找到标题")

            genres = "暂无类型"
            actors = "暂无主演"
            release_date: str | None = None
            hover_info = item.find("div", class_="movie-hover-info")
            if hover_info:
                for title_elem in hover_info.find_all("div", class_="movie-hover-title"):
                    hover_tag = title_elem.find("span", class_="hover-tag")
                    if hover_tag is None:
                        continue

                    tag_text = hover_tag.get_text().strip()
                    content = title_elem.get_text().replace(tag_text, "").strip()
                    if "类型:" in tag_text and content:
                        genres = content
                    elif "主演:" in tag_text and content:
                        actors = content
                    elif "上映时间:" in tag_text and content:
                        release_date = content

            return ScrapedMovieBaseInfo(
                id=movie_id,
                title=title,
                genres=genres,
                actors=actors,
                release_date=release_date,
            )
        except Exception as error:
            logger.error("提取单部电影基础信息失败: %s", error)
            return None


movie_base_info_parser = MovieBaseInfoParser()
