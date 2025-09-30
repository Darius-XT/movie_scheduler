"""解析影院列表JSON数据，提取影院信息"""

import json
from typing import List, Dict, Optional
from src.logger import logger


class CinemaListParser:
    """影院列表解析器"""

    def __init__(self):
        pass

    def parse_cinema_list(self, json_content: str) -> List[Dict]:
        """解析影院列表JSON数据

        Args:
            json_content: JSON字符串内容

        Returns:
            List[Dict]: 解析后的影院信息列表
        """
        try:
            logger.debug("解析影院JSON内容")

            # 解析JSON
            data = json.loads(json_content)

            # 检查数据结构
            if not data:
                logger.warning("JSON数据为空")
                return []

            # 判断数据格式并解析
            cinemas = []
            if isinstance(data, list):
                # 首页格式: [...cinema objects...]
                logger.debug("检测到首页格式数据")
                for cinema_data in data:
                    cinema_info = self._extract_first_page_cinema(cinema_data)
                    if cinema_info:
                        cinemas.append(cinema_info)

            elif isinstance(data, dict) and "cinemas" in data:
                # 非首页格式: {"type":"cinemas","total":358,"cinemas":[...]}
                logger.debug("检测到非首页格式数据")
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
        """从首页格式数据中提取影院信息

        Args:
            cinema_data: 单个影院数据

        Returns:
            Optional[Dict]: 解析后的影院信息
        """
        try:
            cinema_info = {}

            # 基本信息
            cinema_info["id"] = cinema_data.get("id")

            # 从info对象中提取详细信息
            info = cinema_data.get("info", {})
            cinema_info["name"] = info.get("name", "")
            cinema_info["address"] = info.get("address", "")
            cinema_info["price"] = info.get("price", "0")

            # 处理标签信息
            tags = info.get("tags", [])
            cinema_info["allow_refund"] = "退" in tags
            cinema_info["allow_endorse"] = "改签" in tags

            return cinema_info

        except Exception as e:
            logger.error(f"解析首页格式影院数据失败: {e}")
            return None

    def _extract_other_page_cinema(self, cinema_data: Dict) -> Optional[Dict]:
        """从非首页格式数据中提取影院信息

        Args:
            cinema_data: 单个影院数据

        Returns:
            Optional[Dict]: 解析后的影院信息
        """
        try:
            cinema_info = {}

            # 基本信息
            cinema_info["id"] = cinema_data.get("id")
            cinema_info["name"] = cinema_data.get("nm", "")
            cinema_info["address"] = cinema_data.get("addr", "")
            cinema_info["price"] = cinema_data.get("sellPrice", "0")

            # 布尔值字段
            cinema_info["allow_refund"] = bool(cinema_data.get("allowRefund", 0))
            cinema_info["allow_endorse"] = bool(cinema_data.get("endorse", 0))

            return cinema_info

        except Exception as e:
            logger.error(f"解析非首页格式影院数据失败: {e}")
            return None


# 创建解析器实例
cinema_list_parser = CinemaListParser()

# 单元测试
if __name__ == "__main__":
    import logging

    logger.setLevel(logging.DEBUG)

    with open("src/datas/demos/cinema_list_first.json", "r", encoding="utf-8") as f:
        first_page_content = f.read()

    first_cinemas = cinema_list_parser.parse_cinema_list(first_page_content)

    with open("src/datas/demos/cinema_list_other.json", "r", encoding="utf-8") as f:
        other_page_content = f.read()

    other_cinemas = cinema_list_parser.parse_cinema_list(other_page_content)
