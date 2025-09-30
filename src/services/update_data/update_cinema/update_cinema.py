"""更新影院数据（替代原 get_cinema_list）"""

from src.services.update_data.update_cinema.core.cinema_updater import cinema_updater


def update_cinema(keyword: str = "影", city_id: int = 10):
    return cinema_updater.update_cinema(keyword=keyword, city_id=city_id)
