# pyright: reportPrivateUsage=false
from __future__ import annotations

from types import SimpleNamespace

import requests
from pytest import MonkeyPatch

import movie_scheduler.shared.maoyan as maoyan_module
from movie_scheduler.shared.maoyan import (
    _build_font_headers,
    _extract_stonefont_url,
    build_maoyan_cookie,
    build_maoyan_web_headers,
    maoyan_get_text,
)


def test_extract_stonefont_url_accepts_woff_and_woff2() -> None:
    assert _extract_stonefont_url(
        "@font-face{src:url('//s3plus.meituan.net/font.woff') format('woff')}"
    ) == "https://s3plus.meituan.net/font.woff"
    assert _extract_stonefont_url(
        "@font-face{src:url('https://s3plus.meituan.net/font.woff2') format('woff2')}"
    ) == "https://s3plus.meituan.net/font.woff2"


def test_build_font_headers_has_default_referer() -> None:
    headers = _build_font_headers(None)

    assert headers["User-Agent"]
    assert headers["Referer"] == "https://www.maoyan.com/"


def test_build_maoyan_cookie_can_exclude_stale_hot_movie_ids(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(
        maoyan_module.config_manager,
        "maoyan_cookie",
        "uuid=secret; hotMovieIds=1,2; old-moviepage-ci=1",
    )

    cookie = build_maoyan_cookie(10, exclude_names={"hotMovieIds"})

    assert "uuid=secret" in cookie
    assert "hotMovieIds=" not in cookie
    assert "old-moviepage-ci=10" in cookie
    assert "ci=10" in cookie


def test_build_maoyan_web_headers_can_skip_manual_cookie(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(maoyan_module.config_manager, "maoyan_cookie", "uuid=secret")

    headers = build_maoyan_web_headers(10, include_cookie=False)

    assert "Cookie" not in headers


def test_maoyan_get_text_seeds_cookie_and_warms_up_once(monkeypatch: MonkeyPatch) -> None:
    sent, log_calls = _install_fake_maoyan_session(monkeypatch)
    monkeypatch.setattr(
        maoyan_module.config_manager,
        "maoyan_cookie",
        "uuid=secret; hotMovieIds=1,2; old-moviepage-ci=1",
    )

    first = maoyan_get_text("https://www.maoyan.com/cinemas", "获取影院数据", 10)
    second = maoyan_get_text("https://www.maoyan.com/cinemas?offset=12", "获取影院数据", 10)

    assert first == "<html></html>"
    assert second == "<html></html>"
    assert [call[0] for call in sent] == [
        "https://www.maoyan.com/films?showType=1",
        "https://www.maoyan.com/cinemas",
        "https://www.maoyan.com/cinemas?offset=12",
    ]
    assert "uuid=secret" in sent[0][1]["Cookie"]
    assert "old-moviepage-ci=10" in sent[0][1]["Cookie"]
    assert "ci=10" in sent[0][1]["Cookie"]
    assert "hotMovieIds=" not in sent[0][1]["Cookie"]
    assert log_calls == [
        ("GET", "https://www.maoyan.com/films?showType=1", "预热猫眼会话"),
        ("GET", "https://www.maoyan.com/cinemas", "获取影院数据"),
        ("GET", "https://www.maoyan.com/cinemas?offset=12", "获取影院数据"),
    ]
    assert "Cookie" not in str(log_calls)


def test_maoyan_get_text_updates_hot_movie_ids_only_when_explicit(monkeypatch: MonkeyPatch) -> None:
    sent, _log_calls = _install_fake_maoyan_session(monkeypatch)
    monkeypatch.setattr(maoyan_module.config_manager, "maoyan_cookie", "uuid=secret; hotMovieIds=1,2")

    maoyan_get_text("https://www.maoyan.com/cinemas?movieId=9", "获取影片影院页面", 10, hot_movie_ids=[9, 8])
    maoyan_get_text("https://www.maoyan.com/cinemas", "获取影院数据", 10)

    assert "hotMovieIds=9,8" in sent[1][1]["Cookie"]
    assert "hotMovieIds=" not in sent[2][1]["Cookie"]


def test_maoyan_get_text_supports_mobile_profile_with_same_session(monkeypatch: MonkeyPatch) -> None:
    sent, _log_calls = _install_fake_maoyan_session(monkeypatch)
    monkeypatch.setattr(maoyan_module.config_manager, "maoyan_cookie", "uuid=secret")

    maoyan_get_text(
        "https://www.maoyan.com/films/1522535",
        "获取电影详情页面",
        10,
        headers_profile="mobile",
        hot_movie_ids=[1522535],
    )

    assert "Windows NT" in sent[0][1]["User-Agent"]
    assert "iPhone" in sent[1][1]["User-Agent"]
    assert "uuid=secret" in sent[1][1]["Cookie"]
    assert "hotMovieIds=1522535" in sent[1][1]["Cookie"]


def _install_fake_maoyan_session(
    monkeypatch: MonkeyPatch,
) -> tuple[list[tuple[str, dict[str, str], dict[str, object]]], list[tuple[str, str, str]]]:
    session = requests.Session()
    sent: list[tuple[str, dict[str, str], dict[str, object]]] = []
    log_calls: list[tuple[str, str, str]] = []

    def fake_send(prepared_request: requests.PreparedRequest, **kwargs: object) -> SimpleNamespace:
        sent.append((prepared_request.url or "", dict(prepared_request.headers), kwargs))
        return SimpleNamespace(status_code=200, text="<html></html>")

    def fake_log_external_http_request(method: str, url: str, *, purpose: str | None = None) -> None:
        log_calls.append((method, url, purpose or ""))

    monkeypatch.setattr(session, "send", fake_send)
    monkeypatch.setattr(maoyan_module, "_maoyan_session", session)
    monkeypatch.setattr(maoyan_module, "_maoyan_session_initialized", False)
    monkeypatch.setattr(maoyan_module, "_maoyan_session_warmed_up", False)
    monkeypatch.setattr(maoyan_module, "_maoyan_session_city_id", None)
    monkeypatch.setattr(maoyan_module, "log_external_http_request", fake_log_external_http_request)
    return sent, log_calls
