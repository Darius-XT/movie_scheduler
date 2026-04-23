"""场次抓取网关测试。"""

from __future__ import annotations

import pytest

from app.core.exceptions import DataParsingError, ExternalDependencyError
from app.services.show_fetching.show_date_client import show_date_client
from app.services.show_fetching.gateway import show_fetching_gateway


def test_get_show_dates_raises_external_dependency_error_on_scrape_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """抓取失败时应抛出外部依赖异常。"""

    def fake_fetch(movie_id: int, city_id: int) -> None:
        del movie_id, city_id
        return None

    monkeypatch.setattr(show_date_client, "_fetch", fake_fetch)

    with pytest.raises(ExternalDependencyError):
        show_fetching_gateway.get_show_dates(1, 10)


def test_get_show_dates_raises_data_parsing_error_on_empty_parse_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """解析结果为空时应抛出解析异常。"""

    def fake_fetch(movie_id: int, city_id: int) -> str:
        del movie_id, city_id
        return '{"showDates": []}'

    def fake_parse(raw_content: str) -> list[str]:
        del raw_content
        return []

    monkeypatch.setattr(show_date_client, "_fetch", fake_fetch)
    monkeypatch.setattr(show_date_client, "parse", fake_parse)

    with pytest.raises(DataParsingError):
        show_fetching_gateway.get_show_dates(1, 10)
