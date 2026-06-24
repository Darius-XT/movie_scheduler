# pyright: reportPrivateUsage=false
from __future__ import annotations

from movie_scheduler.shared.maoyan import _build_font_headers, _extract_stonefont_url


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
