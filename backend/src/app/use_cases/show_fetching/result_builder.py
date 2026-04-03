"""场次结果数据组装器。"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.use_cases.show_fetching.models import FetchedShowItem


def _empty_show_items() -> list[ShowItem]:
    return []


def _empty_cinema_map() -> dict[int, CinemaShowData]:
    return {}


@dataclass(slots=True)
class ShowItem:
    """单条场次信息。"""

    date: str
    time: str
    price: str


@dataclass(slots=True)
class CinemaShowData:
    """单个影院及其场次集合。"""

    cinema_id: int
    cinema_name: str
    shows: list[ShowItem] = field(default_factory=_empty_show_items)


@dataclass(slots=True)
class MovieShowData:
    """单部电影的内部场次聚合结构。"""

    movie_id: int
    movie_name: str
    cinemas: dict[int, CinemaShowData] = field(default_factory=_empty_cinema_map)


@dataclass(slots=True)
class FinalMovieShowData:
    """单部电影的最终输出结构。"""

    movie_id: int
    cinemas: list[CinemaShowData]


class MovieShowDataBuilder:
    """负责构建和合并电影场次结果结构。"""

    def create_movie_data(self, movie_id: int, movie_name: str) -> MovieShowData:
        """初始化单部电影的结果结构。"""
        return MovieShowData(
            movie_id=movie_id,
            movie_name=movie_name,
        )

    def merge_shows(self, movie_data: MovieShowData, shows: list[FetchedShowItem]) -> None:
        """把根据影院查询到的场次合并到电影结果中。"""
        for show in shows:
            cinema_id = show.cinema_id
            if cinema_id is None:
                continue

            cinema = movie_data.cinemas.setdefault(
                cinema_id,
                CinemaShowData(
                    cinema_id=cinema_id,
                    cinema_name=show.cinema_name,
                ),
            )
            cinema.shows.append(
                ShowItem(
                    date=show.show_date,
                    time=show.show_time,
                    price=show.price,
                )
            )

    def build_cinemas_from_shows(self, cinema_results: list[list[FetchedShowItem]]) -> dict[int, CinemaShowData]:
        """把抓取结果转换为按影院分组的结构。

        返回值是一个以影院 ID 为键、以影院场次聚合结果为值的字典，
        便于在内部处理中按 `cinema_id` 快速合并同一影院的多个场次。
        """
        cinemas: dict[int, CinemaShowData] = {}
        for shows in cinema_results:
            for show in shows:
                cinema_id = show.cinema_id
                if cinema_id is None:
                    continue
                cinema = cinemas.setdefault(
                    cinema_id,
                    CinemaShowData(
                        cinema_id=cinema_id,
                        cinema_name=show.cinema_name,
                    ),
                )
                cinema.shows.append(
                    ShowItem(
                        date=show.show_date,
                        time=show.show_time,
                        price=show.price,
                    )
                )
        return cinemas

    def merge_cinemas(self, movie_data: MovieShowData, cinemas: dict[int, CinemaShowData]) -> None:
        """把按影院聚合后的数据合并到电影结果中。"""
        for cinema_id, cinema_info in cinemas.items():
            if cinema_id not in movie_data.cinemas:
                movie_data.cinemas[cinema_id] = cinema_info
                continue
            movie_data.cinemas[cinema_id].shows.extend(cinema_info.shows)

    def finalize_movie_data(self, movie_data: MovieShowData) -> FinalMovieShowData:
        """把内部字典结构转换为接口输出结构。"""
        return FinalMovieShowData(
            movie_id=movie_data.movie_id,
            cinemas=list(movie_data.cinemas.values()),
        )

    def count_total_shows(self, movies: list[FinalMovieShowData]) -> int:
        """统计电影列表中的总场次数。"""
        return sum(len(cinema.shows) for movie in movies for cinema in movie.cinemas)
