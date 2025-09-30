"""更新电影列表用解析器(由 get_movie_list 迁移并内联)"""

import re
from typing import List, Dict, Optional
from bs4 import BeautifulSoup
from src.logger import logger


class UpdateMovieItemParser:
    def __init__(self):
        self.movies = []

    def parse_movie_list(self, html_content: str) -> List[Dict]:
        try:
            logger.debug("解析HTML内容")
            soup = BeautifulSoup(html_content, "html.parser")

            city_name = self._extract_city_name(soup)
            if city_name:
                logger.debug(f"解析HTML内容，当前选择的城市为: {city_name}")
            else:
                logger.warning("未能从HTML中提取到城市名称")

            movies: List[Dict] = []

            movie_items = soup.find_all("dd")
            for item in movie_items:
                movie_info = self._extract_movie_info(item)
                if movie_info:
                    movies.append(movie_info)

            logger.debug(f"成功解析 {len(movies)} 部电影信息")
            return movies
        except Exception as e:
            logger.error(f"解析HTML内容失败: {e}")
            return []

    def is_empty_page(self, html_content: str) -> bool:
        try:
            empty_indicators = [
                "抱歉，当前城市暂未找到相关结果。",
            ]
            for indicator in empty_indicators:
                if indicator in html_content:
                    logger.debug(f"检测到空页面标识: {indicator}")
                    return True
            return False
        except Exception as e:
            logger.error(f"检测空页面失败: {e}")
            return False

    def _extract_city_name(self, soup) -> Optional[str]:
        try:
            city_name_element = soup.find("div", class_="city-name")
            if city_name_element:
                city_name = city_name_element.get_text().strip()
                city_name = city_name.replace("▼", "").strip()
                return city_name
            else:
                logger.warning("未找到城市名称元素")
                return None
        except Exception as e:
            logger.error(f"提取城市名称失败: {e}")
            return None

    def _extract_movie_info(self, item) -> Optional[Dict]:
        try:
            movie_info: Dict = {}

            movie_link = item.find("a", href=re.compile(r"/films/\d+"))
            if movie_link:
                href = movie_link.get("href")
                movie_id_match = re.search(r"/films/(\d+)", href)
                if movie_id_match:
                    movie_id = int(movie_id_match.group(1))
                    movie_info["id"] = movie_id
                else:
                    logger.warning("没有在 href 中匹配到电影 id, href: {href}")
                    return None
            else:
                logger.warning("没有在 dd 中匹配到有效链接, dd: {item}")
                return None

            title_element = item.find("div", class_="movie-item-title")
            if title_element and title_element.find("a"):
                movie_info["title"] = title_element.find("a").text.strip()
            else:
                logger.warning("没有在 dd 中找到标题, dd: {item}")

            score_container = item.find("span", class_="score") or item.find(
                "div", class_="channel-detail channel-detail-orange"
            )
            if score_container:
                container_text = score_container.get_text().strip()
                if any(keyword in container_text for keyword in ["暂无评分", "人想看"]):
                    movie_info["score"] = "暂无评分"
                    logger.debug(f"当前电影暂无评分: 容器内容: {container_text}")
                else:
                    integer_elem = score_container.find("i", class_="integer")
                    fraction_elem = score_container.find("i", class_="fraction")
                    if integer_elem and fraction_elem:
                        integer_part = integer_elem.text.strip().rstrip(".")
                        fraction_part = fraction_elem.text.strip()
                        movie_info["score"] = f"{integer_part}.{fraction_part}"
                    else:
                        logger.warning(
                            f"没有在评分容器中找到评分信息, 容器内容: {container_text}"
                        )
            else:
                logger.warning("没有在 dd 中找到有效的评分容器, dd: {item}")

            hover_info = item.find("div", class_="movie-hover-info")
            if hover_info:
                for title_elem in hover_info.find_all(
                    "div", class_="movie-hover-title"
                ):
                    hover_tag = title_elem.find("span", class_="hover-tag")
                    if not hover_tag:
                        continue
                    tag_text = hover_tag.text.strip()
                    content = title_elem.get_text().replace(tag_text, "").strip()

                    if "类型:" in tag_text:
                        movie_info["genres"] = content
                    elif "主演:" in tag_text:
                        movie_info["actors"] = content
                    elif "上映时间:" in tag_text:
                        movie_info["release_date"] = content

            return movie_info
        except Exception as e:
            logger.error(f"提取单个电影信息失败: {e}")
            return None


update_movie_item_parser = UpdateMovieItemParser()
