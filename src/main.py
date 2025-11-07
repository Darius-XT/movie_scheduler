# 主函数, 调用需要的业务逻辑

from src.core.info_update_manager.info_update_manager import info_update_manager
from src.core.movie_selector.movie_selector import movie_selector
from src.core.show_for_selected_movie_fetcher.show_for_selected_movie_fetcher import (
    show_for_selected_movie_fetcher,
)


def main():
    # # 更新全部信息
    info_update_manager.update_movie_info()
    info_update_manager.update_cinema_info()

    # 筛选电影
    movie_ids = movie_selector.select_movie(
        filter_china_movies=True, year_threshold=2020
    )

    # 获取所有场次信息
    show_for_selected_movie_fetcher.fetch_shows_for_selected_movies(movie_ids)


if __name__ == "__main__":
    main()
