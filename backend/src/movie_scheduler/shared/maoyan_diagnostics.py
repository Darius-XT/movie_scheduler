"""猫眼异常页面的安全摘要,不记录响应正文或会话信息。"""

from __future__ import annotations

import hashlib
import json
import traceback

from bs4 import BeautifulSoup

from movie_scheduler.core.logging import logger


def log_page_diagnostics(stage: str, content: str, **context: int | str | None) -> None:
    """只记录页面结构计数、指纹和调用方提供的业务标识。"""
    soup = BeautifulSoup(content, "html.parser")
    summary = {
        "chars": len(content),
        "sha256": hashlib.sha256(content.encode()).hexdigest()[:16],
        "json_like": content.lstrip().startswith(("{", "[")),
        "movie_cards": len(soup.select("dl.movie-list > dd")),
        "cinema_cards": len(soup.select(".cinema-cell")),
        "movie_sections": len(soup.select(".show-list, .show-list-container")),
        "show_rows": len(soup.select("table.plist tr")),
        "seat_links": len(soup.select('a[href*="/xseats/"], a[href*="/seats/"]')),
        "date_items": len(soup.select(".date-item")),
        "pager_links": len(soup.select(".list-pager a")),
        "empty_markers": len(soup.select(".no-movies, .no-show, .no-shows")),
        "verification_marker": any(marker in content for marker in ("身份核实", "验证中心", "安全验证")),
    }
    logger.warning("猫眼页面诊断: stage=%s context=%s summary=%s", stage,
                   json.dumps(context, ensure_ascii=False), json.dumps(summary, ensure_ascii=False))


def safe_exception_frames(error: BaseException) -> str:
    """仅记录代码位置,不包含可能携带令牌的异常消息、源码或局部变量。"""
    return " > ".join(f"{frame.name}:{frame.lineno}" for frame in traceback.extract_tb(error.__traceback__)[-8:])
