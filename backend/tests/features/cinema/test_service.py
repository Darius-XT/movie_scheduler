from __future__ import annotations

import asyncio

from pytest import MonkeyPatch

import movie_scheduler.features.cinema.service as cinema_module
from movie_scheduler.features.cinema.service import CinemaService


def test_update_cinemas_parses_maoyan_html_pages(monkeypatch: MonkeyPatch) -> None:
    service = CinemaService()
    requested_urls: list[str] = []
    saved_rows: list[dict[str, object]] = []

    def fake_maoyan_get_text(url: str, purpose: str, city_id: int, **_: object) -> str | None:
        requested_urls.append(url)
        assert purpose == "获取影院数据"
        assert city_id == 10
        if url == "https://www.maoyan.com/cinemas":
            return _CINEMAS_PAGE_1
        if url == "https://www.maoyan.com/cinemas?offset=12":
            return _CINEMAS_PAGE_2
        return None

    def fake_save_batch(rows: list[dict[str, object]]) -> tuple[int, int]:
        saved_rows.extend(rows)
        return len(rows), 0

    monkeypatch.setattr(cinema_module, "maoyan_get_text", fake_maoyan_get_text)
    monkeypatch.setattr(cinema_module.cinema_repository, "save_cinema_batch", fake_save_batch)

    result = asyncio.run(service.update_cinemas(city_id=10))

    assert result.success_count == 2
    assert result.failure_count == 0
    assert requested_urls == [
        "https://www.maoyan.com/cinemas",
        "https://www.maoyan.com/cinemas?offset=12",
    ]
    assert saved_rows == [
        {
            "id": 16119,
            "name": "0090激光影城",
            "address": "金山区朱泾镇沈浦泾路50号1幢A-01",
            "price": "暂无票价",
            "allow_refund": True,
            "allow_endorse": True,
        },
        {
            "id": 41615,
            "name": "AI CINEMAS VLED 影城",
            "address": "静安区福建北路100号",
            "price": "39.9",
            "allow_refund": False,
            "allow_endorse": True,
        },
    ]


_CINEMAS_PAGE_1 = """
<html>
  <body>
    <div class="cinema-cell">
      <div class="cinema-info">
        <a class="cinema-name" data-val="{city_id: 10, cinema_id: 16119}" href="/cinema/16119?poi=1">
          0090激光影城
        </a>
        <p class="cinema-address">地址：金山区朱泾镇沈浦泾路50号1幢A-01</p>
        <div class="cinema-tags">
          <span class="cinema-tags-item">退</span>
          <span class="cinema-tags-item">改签</span>
        </div>
      </div>
      <div class="price"><span class="price-num"><span class="stonefont"></span></span></div>
    </div>
    <div class="cinema-pager">
      <ul class="list-pager">
        <li><a href="?offset=12">下一页</a></li>
      </ul>
    </div>
  </body>
</html>
"""


_CINEMAS_PAGE_2 = """
<html>
  <body>
    <div class="cinema-cell">
      <div class="cinema-info">
        <a class="cinema-name" data-val="{city_id: 10, cinema_id: 41615}" href="/cinema/41615?poi=2">
          AI CINEMAS VLED 影城
        </a>
        <p class="cinema-address">地址：静安区福建北路100号</p>
        <div class="cinema-tags">
          <span class="cinema-tags-item">改签</span>
        </div>
      </div>
      <div class="price"><span class="price-num">39.9</span></div>
    </div>
    <div class="cinema-pager"></div>
  </body>
</html>
"""
