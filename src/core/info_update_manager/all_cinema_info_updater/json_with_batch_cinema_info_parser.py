"""更新影院用的解析器(由 get_cinema_list 迁移并重命名)"""

import json
from typing import List, Dict, Optional
from src.utils.logger import logger


class JsonWithBatchCinemaInfoParser:
    def parse_json_with_batch_cinema_info(self, json_content: str) -> List[Dict]:
        """解析JSON内容，提取影院信息列表

        Args:
            json_content (str): 影院搜索API返回的JSON字符串。
                可以是列表格式或包含"cinemas"字段的字典格式。
                示例值: '[{"id": 1001, "info": {"name": "万达影城", ...}}]'
                或 '{"cinemas": [{"id": 1001, "nm": "万达影城", ...}]}'

        Returns:
            List[Dict]: 影院信息列表，每个字典包含以下字段：
                - id (int): 影院ID，例如: 1001
                - name (str): 影院名称，例如: "万达影城（上海店）"
                - address (str): 影院地址，例如: "上海市黄浦区南京东路100号"
                - price (str): 票价，例如: "35元起" 或 "0"
                - allow_refund (bool): 是否允许退票，例如: True
                - allow_endorse (bool): 是否允许改签，例如: False
            如果解析失败或JSON为空，返回空列表 []。
            示例返回值: [
                {
                    "id": 1001,
                    "name": "万达影城（上海店）",
                    "address": "上海市黄浦区南京东路100号",
                    "price": "35元起",
                    "allow_refund": True,
                    "allow_endorse": False
                }
            ]
        """
        try:
            logger.debug("解析影院JSON内容")

            # 检查内容是否为空
            if not json_content or not json_content.strip():
                logger.debug("JSON内容为空字符串")
                return []

            # 解析JSON，如果解析后数据为空则返回空列表
            data = json.loads(json_content)
            if not data:
                logger.debug("JSON数据为空")
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

    def _normalize_field(self, value, default_text: str):
        """统一处理字段：如果为空则设置为"暂无 xxx"

        Args:
            value: 字段值，可能是 None、空字符串、0 等
            default_text: 默认文本，例如 "暂无名称"

        Returns:
            处理后的值
        """
        if value is None:
            return default_text
        if isinstance(value, str) and not value.strip():
            return default_text
        if isinstance(value, (int, float)) and value == 0:
            return default_text
        return value

    def _extract_first_page_cinema(self, cinema_data: Dict) -> Optional[Dict]:
        try:
            cinema_info: Dict = {}
            cinema_info["id"] = cinema_data.get("id")
            info = cinema_data.get("info", {})

            # 使用统一处理逻辑
            cinema_info["name"] = self._normalize_field(info.get("name"), "暂无名称")
            cinema_info["address"] = self._normalize_field(
                info.get("address"), "暂无地址"
            )
            price = info.get("price", "0")
            # price 字段特殊处理：如果是 "0" 或空，标记为"暂无票价"
            if (
                not price
                or price == "0"
                or (isinstance(price, str) and not price.strip())
            ):
                cinema_info["price"] = "暂无票价"
            else:
                cinema_info["price"] = price

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

            # 使用统一处理逻辑
            cinema_info["name"] = self._normalize_field(
                cinema_data.get("nm"), "暂无名称"
            )
            cinema_info["address"] = self._normalize_field(
                cinema_data.get("addr"), "暂无地址"
            )
            price = cinema_data.get("sellPrice", "0")
            # price 字段特殊处理：如果是 "0" 或空，标记为"暂无票价"
            if (
                not price
                or price == "0"
                or (isinstance(price, str) and not price.strip())
            ):
                cinema_info["price"] = "暂无票价"
            else:
                cinema_info["price"] = price

            cinema_info["allow_refund"] = bool(cinema_data.get("allowRefund", 0))
            cinema_info["allow_endorse"] = bool(cinema_data.get("endorse", 0))
            return cinema_info
        except Exception as e:
            logger.error(f"解析非首页格式影院数据失败: {e}")
            return None


json_with_batch_cinema_info_parser = JsonWithBatchCinemaInfoParser()
