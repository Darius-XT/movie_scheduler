"""解析电影-影院列表HTML，提取影院信息"""

import re
from typing import List, Dict, Optional
from bs4 import BeautifulSoup
from src.logger import logger
import logging


class MovieCinemaListParser:
    """电影-影院列表解析器"""

    def __init__(self):
        pass

    def parse_movie_cinema_list(self, html_content: str) -> List[Dict]:
        """解析HTML，提取影院信息列表

        Args:
            html_content: HTML字符串内容

        Returns:
            List[Dict]: 解析后的影院信息列表，包含cinema_id、cinema_name、poi、showdate、movie_id、movie_name
        """
        try:
            logger.debug("解析电影-影院列表HTML内容")
            soup = BeautifulSoup(html_content, "html.parser")

            # 提取电影信息
            movie_info = self._extract_movie_info(html_content, soup)
            showdate = movie_info.get("showdate")
            movie_id = movie_info.get("movie_id")
            movie_name = movie_info.get("movie_name")

            # 查找所有影院单元格
            cinema_cells = soup.find_all("div", class_="cinema-cell")
            if not cinema_cells:
                logger.warning("未找到影院信息")
                return []

            cinemas = []
            for cell in cinema_cells:
                cinema_info = self._extract_cinema_info(cell)
                if cinema_info:
                    # 添加电影和showdate信息
                    cinema_info["showdate"] = showdate
                    cinema_info["movie_id"] = movie_id
                    cinema_info["movie_name"] = movie_name
                    cinemas.append(cinema_info)

            logger.debug(f"成功解析 {len(cinemas)} 家影院信息")
            return cinemas

        except Exception as e:
            logger.error(f"解析电影-影院列表HTML失败: {e}")
            return []

    def _extract_cinema_info(self, cell) -> Optional[Dict]:
        """从影院单元格中提取影院信息

        Args:
            cell: BeautifulSoup影院单元格元素

        Returns:
            Optional[Dict]: 解析后的影院信息，包含cinema_id、cinema_name、poi
        """
        try:
            cinema_info = {}

            # 提取影院基本信息
            cinema_info_container = cell.find("div", class_="cinema-info")
            if not cinema_info_container:
                logger.warning("未找到影院信息容器")
                return None

            # 提取影院名称和ID
            cinema_name_link = cinema_info_container.find("a", class_="cinema-name")
            if cinema_name_link:
                cinema_info["cinema_name"] = cinema_name_link.text.strip()

                # 从href中提取影院ID
                href = cinema_name_link.get("href", "")
                cinema_id_match = re.search(r"/cinema/(\d+)", href)
                if cinema_id_match:
                    cinema_info["cinema_id"] = int(cinema_id_match.group(1))
                else:
                    logger.warning(f"无法从链接中提取影院ID: {href}")
                    return None
            else:
                logger.warning("未找到影院名称链接")
                return None

            # 提取POI信息（从链接中）
            if cinema_name_link:
                href = cinema_name_link.get("href", "")
                poi_match = re.search(r"poi=(\d+)", href)
                if poi_match:
                    cinema_info["poi"] = int(poi_match.group(1))
                else:
                    cinema_info["poi"] = None

            return cinema_info

        except Exception as e:
            logger.error(f"提取单个影院信息失败: {e}")
            return None

    def _extract_showdate(self, html_content: str) -> Optional[str]:
        """从HTML内容中提取showdate信息

        Args:
            html_content: HTML字符串内容

        Returns:
            Optional[str]: 提取到的showdate，如果未找到则返回None
        """
        try:
            # 从JavaScript的window.system对象中提取showdate
            showdate_match = re.search(
                r'"showDate":"(\d{4}-\d{2}-\d{2})"', html_content
            )
            if showdate_match:
                return showdate_match.group(1)

            # 如果第一种方法失败，尝试从URL参数中提取
            showdate_match = re.search(r"showDate=(\d{4}-\d{2}-\d{2})", html_content)
            if showdate_match:
                return showdate_match.group(1)

            logger.warning("未找到showdate信息")
            return None

        except Exception as e:
            logger.error(f"提取showdate信息失败: {e}")
            return None

    def _extract_movie_info(self, html_content: str, soup) -> Dict:
        """从HTML内容中提取电影信息

        Args:
            html_content: HTML字符串内容
            soup: BeautifulSoup对象

        Returns:
            Dict: 包含movie_id、movie_name、showdate的字典
        """
        movie_info = {}

        try:
            # 提取电影ID
            movie_id_match = re.search(r'"movieId":"(\d+)"', html_content)
            if movie_id_match:
                movie_info["movie_id"] = int(movie_id_match.group(1))
            else:
                logger.warning("未找到电影ID")
                movie_info["movie_id"] = None

            # 提取电影名称
            movie_name_element = soup.find("h1", class_="name")
            if movie_name_element:
                movie_info["movie_name"] = movie_name_element.text.strip()
            else:
                logger.warning("未找到电影名称")
                movie_info["movie_name"] = None

            # 提取showdate信息
            movie_info["showdate"] = self._extract_showdate(html_content)

            return movie_info

        except Exception as e:
            logger.error(f"提取电影信息失败: {e}")
            return {"movie_id": None, "movie_name": None, "showdate": None}


# 创建解析器实例
movie_cinema_list_parser = MovieCinemaListParser()


# 单元测试
if __name__ == "__main__":
    logger.setLevel(logging.DEBUG)

    with open("src/datas/demos/movie_cinema_list.html", "r", encoding="utf-8") as f:
        html_content = f.read()

    cinemas = movie_cinema_list_parser.parse_movie_cinema_list(html_content)

    print(cinemas)
