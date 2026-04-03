"""场次抓取网关测试。"""

from __future__ import annotations

import pytest

from app.core.exceptions import DataParsingError, ExternalDependencyError
from app.use_cases.show_fetching.show_fetching_gateway import (
    show_date_parser,
    show_date_scraper,
    show_fetching_gateway,
)


def test_get_show_dates_raises_external_dependency_error_on_scrape_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """抓取失败时应抛出外部依赖异常。"""

    def fake_scrape_showdate(movie_id: int, city_id: int | None = None) -> tuple[bool, str]:
        del movie_id, city_id
        return False, ""

    monkeypatch.setattr(show_date_scraper, "scrape_showdate", fake_scrape_showdate)

    with pytest.raises(ExternalDependencyError):
        show_fetching_gateway.get_show_dates(1, 10)


def test_get_show_dates_raises_data_parsing_error_on_empty_parse_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """解析结果为空时应抛出解析异常。"""

    def fake_scrape_showdate(movie_id: int, city_id: int | None = None) -> tuple[bool, str]:
        del movie_id, city_id
        return True, '{"showDates": []}'

    def fake_parse_showdate(raw_content: str) -> list[str]:
        del raw_content
        return []

    monkeypatch.setattr(show_date_scraper, "scrape_showdate", fake_scrape_showdate)
    monkeypatch.setattr(show_date_parser, "parse_showdate", fake_parse_showdate)

    with pytest.raises(DataParsingError):
        show_fetching_gateway.get_show_dates(1, 10)
