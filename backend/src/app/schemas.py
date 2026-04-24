"""跨领域共享的 API 数据契约。

每个领域应在自己的 `schemas.py` 中定义私有 schema；
本模块仅放置真正跨域复用的基础结构（如统一响应包装）。
"""

from __future__ import annotations

from pydantic import BaseModel


class SuccessEnvelope(BaseModel):
    """通用成功响应包装。"""

    success: bool = True


__all__ = ["SuccessEnvelope"]
