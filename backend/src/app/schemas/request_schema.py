"""API 请求体定义。"""

from typing import Literal

from pydantic import BaseModel


class UpdateCinemaRequest(BaseModel):
    """更新影院信息请求。"""

    city_id: int


class UpdateMovieRequest(BaseModel):
    """更新电影信息请求。"""

    city_id: int
    force_update_all: bool = False


class SelectMovieRequest(BaseModel):
    """筛选电影请求。"""

    selection_mode: Literal["showing", "upcoming", "all"] = "all"
