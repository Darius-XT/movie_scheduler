"""更新电影列表用解析器(由 get_movie_list 迁移并内联)"""

import re
from typing import List, Dict, Optional
from bs4 import BeautifulSoup
from src.utils.logger import logger


class HtmlWithBatchMovieBaseInfoParser:
    def __init__(self):
        self.movies = []

    # * 注意, 源信息中可能不包括评分, 类型与导演等, 此时要标记为"暂无 xxx", 表示这个字段已经经过处理
    def parse_html_with_batch_movie_base_info(
        self, html_content: str
    ) -> tuple[List[Dict], bool]:
        """解析HTML内容，提取电影基础信息列表

        Args:
            html_content (str): 猫眼电影列表页面的HTML内容。
                示例值: "<html><body><dd>...</dd></body></html>"
                或包含空页面提示的HTML: '<div class="no-movies">抱歉，当前城市暂未找到相关结果。</div>'

        Returns:
            tuple[List[Dict], bool]: (电影信息列表, 是否为预期中的空页面)
                第一个元素是电影信息列表，每个字典包含以下字段：
                    - id (int): 电影ID，例如: 123456
                    - title (str): 电影标题，例如: "肖申克的救赎"
                    - score (str, 可选): 评分，例如: "9.7" 或 "暂无评分"
                    - genres (str, 可选): 类型，例如: "剧情/犯罪"
                    - actors (str, 可选): 主演，例如: "蒂姆·罗宾斯/摩根·弗里曼"
                第二个元素是布尔值，表示是否为预期中的空页面：
                    - True: 表示这是预期中的空页面（包含 no-movies 提示，说明已到最后一页）
                    - False: 表示出现异常或其他情况（HTML解析失败、数据格式错误等）
                如果解析失败，返回 ([], False)。
                如果解析成功且检测到空页面提示（预期中的空页面），返回 ([], True)。
                示例返回值: ([{"id": 123456, ...}], False) 或 ([], True)
        """
        try:
            logger.debug("解析HTML内容")
            soup = BeautifulSoup(html_content, "html.parser")

            # 检查是否为预期中的空页面（包含 no-movies 提示）
            no_movies_div = soup.find("div", class_="no-movies")
            if no_movies_div:
                no_movies_text = no_movies_div.get_text().strip()
                if "抱歉，当前城市暂未找到相关结果。" in no_movies_text:
                    logger.debug(
                        "检测到 no-movies 提示，这是预期中的空页面（已到最后一页）"
                    )
                    return [], True  # 预期中的空页面

            movies: List[Dict] = []

            movie_items = soup.find_all("dd")
            for item in movie_items:
                movie_info = self._extract_movie_info(item)
                if movie_info:
                    movies.append(movie_info)

            logger.debug(f"成功解析 {len(movies)} 部电影信息")
            return movies, False  # 解析成功
        except Exception as e:
            logger.error(f"解析HTML内容失败: {e}")
            return [], False

    def _normalize_field(self, value, default_text: str):
        """统一处理字段：如果为空则设置为"暂无 xxx"

        Args:
            value: 字段值，可能是 None、空字符串等
            default_text: 默认文本，例如 "暂无类型"

        Returns:
            处理后的值
        """
        if value is None:
            return default_text
        if isinstance(value, str) and not value.strip():
            return default_text
        return value

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
                        movie_info["score"] = "暂无评分"
                        logger.warning(
                            f"没有在评分容器中找到评分信息, 容器内容: {container_text}"
                        )
            else:
                movie_info["score"] = "暂无评分"
                logger.warning("没有在 dd 中找到有效的评分容器, dd: {item}")

            # 初始化类型和主演字段，如果找不到则标记为"暂无"
            movie_info["genres"] = "暂无类型"
            movie_info["actors"] = "暂无主演"

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
                        if content:
                            movie_info["genres"] = content
                        # 如果 content 为空，保持 "暂无类型"
                    elif "主演:" in tag_text:
                        if content:
                            movie_info["actors"] = content
                        # 如果 content 为空，保持 "暂无主演"
            # 如果找不到 hover_info，保持默认的 "暂无类型" 和 "暂无主演"

            return movie_info
        except Exception as e:
            logger.error(f"提取单个电影信息失败: {e}")
            return None


html_with_batch_movie_base_info_parser = HtmlWithBatchMovieBaseInfoParser()
