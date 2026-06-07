"""跨 feature 共享的响应包装类型。"""

from __future__ import annotations

from pydantic import BaseModel


class SuccessEnvelope(BaseModel):
    """通用成功响应包装。"""

    success: bool = True


__all__ = ["SuccessEnvelope"]
