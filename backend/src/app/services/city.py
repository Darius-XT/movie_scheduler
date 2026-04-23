"""城市服务。"""

from __future__ import annotations

from dataclasses import dataclass

from app.core.config import config_manager


@dataclass(slots=True)
class CityInfo:
    """城市信息。"""

    name: str
    id: int


class CityService:
    """提供城市相关业务能力。"""

    def list_city(self) -> list[CityInfo]:
        """返回当前可用城市列表。"""
        city_mapping = config_manager.city_mapping or {}
        return [CityInfo(name=name, id=city_id) for name, city_id in city_mapping.items()]


city_service = CityService()
