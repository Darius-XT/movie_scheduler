"""电影基础信息解析器测试。"""

from __future__ import annotations

from app.update.movie.base.client import MovieBaseInfoClient


def test_base_info_parser_extracts_release_date() -> None:
    """应从电影悬浮信息中提取完整上映日期。"""
    client = MovieBaseInfoClient()
    html = """
    <dl class="movie-list">
      <dd>
        <a href="/films/1324725"></a>
        <div class="movie-item-title"><a>测试电影</a></div>
        <div class="movie-hover-info">
          <div class="movie-hover-title">
            <span class="hover-tag">类型:</span>
            剧情
          </div>
          <div class="movie-hover-title">
            <span class="hover-tag">主演:</span>
            演员A
          </div>
          <div class="movie-hover-title movie-hover-brief">
            <span class="hover-tag">上映时间:</span>
            2026-03-20
          </div>
        </div>
      </dd>
    </dl>
    """

    movies, is_expected_empty = client.parse(html)

    assert is_expected_empty is False
    assert len(movies) == 1
    assert movies[0].id == 1324725
    assert movies[0].title == "测试电影"
    assert movies[0].release_date == "2026-03-20"
