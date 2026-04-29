"""电影筛选结果构建器。"""

from __future__ import annotations

from app.movie.entities import MovieRecord, MovieSelectionItem


class MovieSelectionResultBuilder:
    """负责把电影实体转换为用例输出结构。"""

    def build_movie(self, movie: MovieRecord) -> MovieSelectionItem:
        """将电影记录转换为统一的电影筛选结果结构。"""
        return MovieSelectionItem(
            id=int(movie.id) if movie.id is not None else None,
            title=movie.title,
            score=movie.score,
            douban_url=movie.douban_url,
            genres=movie.genres,
            actors=movie.actors,
            release_date=movie.release_date,
            is_showing=movie.is_showing,
            director=movie.director,
            country=movie.country,
            language=movie.language,
            duration=movie.duration,
            description=movie.description,
            first_showing_at=str(movie.first_showing_at) if movie.first_showing_at else None,
        )


movie_result_builder = MovieSelectionResultBuilder()
