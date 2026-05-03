"""场次抓取领域的 HTTP 请求辅助。"""

from __future__ import annotations

import requests
import urllib3

from app.core.logger import logger

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

SHOW_REQUEST_HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7",
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.maoyan.com/",
    "Origin": "https://www.maoyan.com",
}


def fetch_show_api_text(url: str, timeout: int, log_label: str) -> str | None:
    """抓取场次相关外部接口文本，失败返回 None。"""
    try:
        logger.debug("开始%s: %s", log_label, url)
        response = requests.get(url, headers=SHOW_REQUEST_HEADERS, timeout=timeout, verify=False)
        logger.debug("%s响应状态码: %s，响应长度: %s 字符", log_label, response.status_code, len(response.text))
        if response.status_code == 200:
            return response.text
        logger.error(
            "%s请求失败: status=%s, url=%s, response=%s",
            log_label,
            response.status_code,
            url,
            response.text[:1000],
        )
        return None
    except Exception as error:
        logger.error("%s异常: url=%s, error=%s", log_label, url, error, exc_info=True)
        return None
