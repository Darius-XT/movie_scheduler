"""Douban mobile search client tests."""

from __future__ import annotations

from app.update.movie.douban.client import DoubanApiClient


def test_douban_client_parses_mobile_search_movie_result() -> None:
    client = DoubanApiClient()
    html = """
    <li class="search-module">
      <span class="search-results-modules-name">电影</span>
      <ul class="search_results_subjects">
        <li>
          <a href="/movie/subject/1899280/">
            <span class="subject-title">无夫之妻</span>
            <p class="rating"><span data-rating="79.0"></span><span>7.9</span></p>
          </a>
        </li>
      </ul>
    </li>
    """

    results = client.parse_search_html(html)

    assert len(results) == 1
    assert results[0].title == "无夫之妻"
    assert results[0].rating == "7.9"
    assert results[0].cover_link == "https://m.douban.com/movie/subject/1899280/"


def test_douban_client_keeps_candidate_when_rating_is_missing() -> None:
    client = DoubanApiClient()
    html = """
    <li class="search-module">
      <span class="search-results-modules-name">电影</span>
      <ul class="search_results_subjects">
        <li>
          <a href="https://m.douban.com/movie/subject/1234567/">
            <span class="subject-title">测试电影</span>
          </a>
        </li>
      </ul>
    </li>
    """

    results = client.parse_search_html(html)

    assert len(results) == 1
    assert results[0].rating == ""
    assert results[0].cover_link == "https://m.douban.com/movie/subject/1234567/"


def test_douban_client_returns_empty_when_movie_module_is_missing() -> None:
    client = DoubanApiClient()
    html = """
    <li class="search-module">
      <span class="search-results-modules-name">图书</span>
      <ul class="search_results_subjects">
        <li><a href="/book/subject/1/"><span class="subject-title">书</span></a></li>
      </ul>
    </li>
    """

    assert client.parse_search_html(html) == []


def test_douban_client_returns_empty_for_malformed_candidate() -> None:
    client = DoubanApiClient()
    html = """
    <li class="search-module">
      <span class="search-results-modules-name">电影</span>
      <ul class="search_results_subjects">
        <li><a href="/movie/subject/not-a-number/"><span class="subject-title">坏链接</span></a></li>
      </ul>
    </li>
    """

    assert client.parse_search_html(html) == []
