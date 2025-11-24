# 主函数, 调用需要的业务逻辑
from src.core.info_update_manager.info_update_manager import info_update_manager
from src.core.movie_selector.movie_selector import movie_selector
from src.core.show_for_selected_movie_fetcher.show_for_selected_movie_fetcher import (
    show_for_selected_movie_fetcher,
)


def main():
    # 设置城市ID（默认为10 = 上海）
    city_id = 10

    # 更新全部信息
    info_update_manager.update_movie_info(city_id=city_id)
    info_update_manager.update_cinema_info(city_id=city_id)

    # 筛选电影
    movies = movie_selector.select_movie(filter_china_movies=True, year_threshold=1800)

    # 提取电影ID列表
    movie_ids = [movie["id"] for movie in movies if movie.get("id") is not None]

    # 获取所有场次信息
    show_for_selected_movie_fetcher.fetch_shows_for_selected_movies(
        movie_ids, use_async=False
    )


if __name__ == "__main__":
    main()
