"""日期处理工具函数"""

import re
from typing import Optional


def extract_year_from_release_date(release_date: Optional[str]) -> Optional[str]:
    """从各种格式的发行日期中提取年份

    处理逻辑：
    1. 如果有很多个发行日期（用逗号分隔），只保留最开始的那个
    2. 从日期中提取年份（可能是 "1957-12-17"、"1995" 等格式）
    3. 最终只返回年份字符串

    Args:
        release_date (Optional[str]): 发行日期字符串，可能是以下格式：
            - 多个日期用逗号分隔: "1957-12-17,1958-01-30,1958-02-06"
            - 单个完整日期: "1955-12-31"
            - 只有年份: "1995"
            - 可能包含空值和多余逗号: "1957-12-17,1958-01-30,,1958-02-06"
            - None 或空字符串

    Returns:
        Optional[str]: 提取的年份字符串（4位数字），例如: "1957"、"1995"
            如果无法提取年份，返回 None
    """
    if not release_date:
        return None

    # 转换为字符串并去除首尾空白
    date_str = str(release_date).strip()

    if not date_str:
        return None

    # 如果包含逗号，只取第一个日期（去除首尾空白）
    if "," in date_str:
        first_date = date_str.split(",")[0].strip()
        if first_date:
            date_str = first_date
        else:
            # 如果第一个是空的，尝试找下一个非空的
            parts = [p.strip() for p in date_str.split(",") if p.strip()]
            if parts:
                date_str = parts[0]
            else:
                return None

    # 尝试提取年份（4位数字）
    # 优先匹配开头的4位数字（年份通常在开头）
    year_match = re.search(r"^\d{4}", date_str)
    if year_match:
        return year_match.group(0)

    # 如果开头没有，尝试匹配任意位置的4位数字
    year_match = re.search(r"\d{4}", date_str)
    if year_match:
        return year_match.group(0)

    return None
