"""更新影院用的解析器(由 get_cinema_list 迁移并重命名)"""

import json
from typing import List, Dict, Optional
from src.logger import logger


class UpdateCinemaParser:
    def parse(self, json_content: str) -> List[Dict]:
        try:
            logger.debug("解析影院JSON内容")
            data = json.loads(json_content)
            if not data:
                logger.warning("JSON数据为空")
                return []

            cinemas: List[Dict] = []
            if isinstance(data, list):
                for cinema_data in data:
                    cinema_info = self._extract_first_page_cinema(cinema_data)
                    if cinema_info:
                        cinemas.append(cinema_info)
            elif isinstance(data, dict) and "cinemas" in data:
                for cinema_data in data.get("cinemas", []):
                    cinema_info = self._extract_other_page_cinema(cinema_data)
                    if cinema_info:
                        cinemas.append(cinema_info)
            else:
                logger.warning("未知的数据格式")
                return []

            logger.debug(f"成功解析 {len(cinemas)} 家影院信息")
            return cinemas
        except json.JSONDecodeError as e:
            logger.error(f"解析JSON失败: {e}")
            return []
        except Exception as e:
            logger.error(f"解析影院列表失败: {e}")
            return []

    def _extract_first_page_cinema(self, cinema_data: Dict) -> Optional[Dict]:
        try:
            cinema_info: Dict = {}
            cinema_info["id"] = cinema_data.get("id")
            info = cinema_data.get("info", {})
            cinema_info["name"] = info.get("name", "")
            cinema_info["address"] = info.get("address", "")
            cinema_info["price"] = info.get("price", "0")
            tags = info.get("tags", [])
            cinema_info["allow_refund"] = "退" in tags
            cinema_info["allow_endorse"] = "改签" in tags
            return cinema_info
        except Exception as e:
            logger.error(f"解析首页格式影院数据失败: {e}")
            return None

    def _extract_other_page_cinema(self, cinema_data: Dict) -> Optional[Dict]:
        try:
            cinema_info: Dict = {}
            cinema_info["id"] = cinema_data.get("id")
            cinema_info["name"] = cinema_data.get("nm", "")
            cinema_info["address"] = cinema_data.get("addr", "")
            cinema_info["price"] = cinema_data.get("sellPrice", "0")
            cinema_info["allow_refund"] = bool(cinema_data.get("allowRefund", 0))
            cinema_info["allow_endorse"] = bool(cinema_data.get("endorse", 0))
            return cinema_info
        except Exception as e:
            logger.error(f"解析非首页格式影院数据失败: {e}")
            return None


update_cinema_parser = UpdateCinemaParser()
