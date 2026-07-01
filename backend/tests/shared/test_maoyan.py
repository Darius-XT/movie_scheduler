# pyright: reportPrivateUsage=false
from __future__ import annotations

from pytest import MonkeyPatch

import movie_scheduler.shared.maoyan as maoyan_module
from movie_scheduler.shared.maoyan import (
    _build_font_headers,
    _extract_stonefont_url,
    build_maoyan_cookie,
    build_maoyan_web_headers,
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
