"""更新影院放映信息用解析器(由 get_movie_cinema_list 迁移并内联)"""

import re
from typing import List, Dict, Optional
from bs4 import BeautifulSoup
from src.logger import logger


class UpdateShowCinemaListParser:
    def parse_movie_cinema_list(self, html_content: str) -> List[Dict]:
        try:
            logger.debug("解析电影-影院列表HTML内容")
            soup = BeautifulSoup(html_content, "html.parser")

            movie_info = self._extract_movie_info(html_content, soup)
            showdate = movie_info.get("showdate")
            movie_id = movie_info.get("movie_id")
            movie_name = movie_info.get("movie_name")

            cinema_cells = soup.find_all("div", class_="cinema-cell")
            if not cinema_cells:
                logger.warning("未找到影院信息")
                return []

            cinemas: List[Dict] = []
            for cell in cinema_cells:
                cinema_info = self._extract_cinema_info(cell)
                if cinema_info:
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
        try:
            cinema_info: Dict = {}
            cinema_info_container = cell.find("div", class_="cinema-info")
            if not cinema_info_container:
                logger.warning("未找到影院信息容器")
                return None

            cinema_name_link = cinema_info_container.find("a", class_="cinema-name")
            if cinema_name_link:
                cinema_info["cinema_name"] = cinema_name_link.text.strip()
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
        try:
            showdate_match = re.search(
                r'"showDate":"(\d{4}-\d{2}-\d{2})"', html_content
            )
            if showdate_match:
                return showdate_match.group(1)
            showdate_match = re.search(r"showDate=(\d{4}-\d{2}-\d{2})", html_content)
            if showdate_match:
                return showdate_match.group(1)
            logger.warning("未找到showdate信息")
            return None
        except Exception as e:
            logger.error(f"提取showdate信息失败: {e}")
            return None

    def _extract_movie_info(self, html_content: str, soup) -> Dict:
        movie_info: Dict = {}
        try:
            movie_id_match = re.search(r'"movieId":"(\d+)"', html_content)
            if movie_id_match:
                movie_info["movie_id"] = int(movie_id_match.group(1))
            else:
                logger.warning("未找到电影ID")
                movie_info["movie_id"] = None

            movie_name_element = soup.find("h1", class_="name")
            if movie_name_element:
                movie_info["movie_name"] = movie_name_element.text.strip()
            else:
                logger.warning("未找到电影名称")
                movie_info["movie_name"] = None

            movie_info["showdate"] = self._extract_showdate(html_content)
            return movie_info
        except Exception as e:
            logger.error(f"提取电影信息失败: {e}")
            return {"movie_id": None, "movie_name": None, "showdate": None}


update_show_cinema_list_parser = UpdateShowCinemaListParser()
