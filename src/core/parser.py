import re
from typing import List, Dict, Optional
from bs4 import BeautifulSoup
from src.core.logger import logger


class MovieParser:
    def __init__(self):
        self.movies = []

    # 解析 html 内容, 返回包含关键信息的字典列表
    def parse_html_content(self, html_content: str) -> List[Dict]:
        try:
            logger.debug("解析HTML内容")
            # 将 html 内容转换为 BeautifulSoup 对象(一个可操作的树状结构)
            soup = BeautifulSoup(html_content, "html.parser")
            movies = []

            # 查找所有电影 dd (描述列表定义)
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

    # 对每个电影 dd, 提取信息
    def _extract_movie_info(self, item) -> Optional[Dict]:
        try:
            movie_info = {}

            # 获取电影 url(如果没有说明不是有效的电影, 直接返回)
            movie_link = item.find("a", href=re.compile(r"/films/\d+"))
            if movie_link:
                # 从链接中提取 href, eg: /films/123456
                href = movie_link.get("href")
                movie_id_match = re.search(r"/films/(\d+)", href)
                # 如果 href 中有电影 id, 则提取 id, 并构建 url
                if movie_id_match:
                    movie_info["id"] = int(movie_id_match.group(1))
                    movie_info["url"] = f"https://www.maoyan.com{href}"
                else:
                    logger.warning("没有在 href 中匹配到电影 id, href: {href}")
            else:
                logger.warning("没有在 dd 中匹配到有效链接, dd: {item}")

            # 获取电影标题
            title_element = item.find("div", class_="movie-item-title")
            if title_element and title_element.find("a"):
                movie_info["title"] = title_element.find("a").text.strip()
            else:
                logger.warning("没有在 dd 中找到标题, dd: {item}")

            # 获取评分容器(span 或 div)
            score_container = item.find("span", class_="score") or item.find(
                "div", class_="channel-detail channel-detail-orange"
            )
            if score_container:
                integer_elem = score_container.find("i", class_="integer")
                fraction_elem = score_container.find("i", class_="fraction")

                if integer_elem and fraction_elem:
                    integer_part = integer_elem.text.strip().rstrip(".")
                    fraction_part = fraction_elem.text.strip()
                    movie_info["score_integer"] = integer_part
                    movie_info["score_fraction"] = fraction_part
                    movie_info["score"] = f"{integer_part}.{fraction_part}"
                else:
                    logger.warning(
                        "没有在评分容器(span / div)中找到评分信息, 容器: {score_container}"
                    )
            else:
                logger.warning("没有在 dd 中找到有效的评分容器, dd: {item}")

            # 提取封面 div(包含类型、主演、上映时间)
            hover_info = item.find("div", class_="movie-hover-info")
            if hover_info:
                # 遍历所有电影 hover 标题 div, 不同的标题 div 包含不同的信息
                for title_elem in hover_info.find_all(
                    "div", class_="movie-hover-title"
                ):
                    # 获取标题标签
                    hover_tag = title_elem.find("span", class_="hover-tag")
                    # 有的标题没有标签, 应当跳过
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


# 创建全局parser实例
parser = MovieParser()
