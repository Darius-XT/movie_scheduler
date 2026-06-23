"""猫眼网页抓取的公共请求配置。"""

from __future__ import annotations

import logging
import re
from collections.abc import Sequence
from contextlib import redirect_stderr, redirect_stdout
from io import BytesIO, StringIO
from typing import Any

import requests

from movie_scheduler.config import config_manager

try:
    from fontTools.ttLib import TTFont
except ImportError:  # pragma: no cover - runtime dependency, graceful fallback for lean local envs
    TTFont = None  # type: ignore[assignment]

MAOYAN_WEB_HEADERS = {
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,"
        "application/signed-exchange;v=b3;q=0.7"
    ),
    "Accept-Language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7",
    "Cache-Control": "max-age=0",
    "Connection": "keep-alive",
    "Sec-CH-UA": '"Google Chrome";v="149", "Chromium";v="149", "Not)A;Brand";v="24"',
    "Sec-CH-UA-Mobile": "?0",
    "Sec-CH-UA-Platform": '"Windows"',
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36"
    ),
}

MAOYAN_MOBILE_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "Cache-Control": "no-cache",
    "Referer": "https://m.maoyan.com/",
    "User-Agent": (
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
    ),
}

_STONEFONT_GRID_SIZE = 10
_STONEFONT_MAX_DISTANCE = 20.0
_STONEFONT_TEMPLATES: dict[str, tuple[int, float, int]] = {
    "0": (0x2A35AC1A01002050030541078, 0.6881, 31),
    "1": (0xC00C03500C000000000000280, 0.5109, 13),
    "2": (0x22252C1704B01201E01C83E01, 0.6911, 36),
    "3": (0x5A2D6216806C270C01059D4A8, 0.6907, 40),
    "4": (0x500400000000000D0F4100140, 0.7032, 14),
    "5": (0x81208000BC1E306803055D4A8, 0.7117, 31),
    "6": (0x2A2FCC14B015305C130502178, 0.6901, 44),
    "7": (0x8068120020100100802804014, 0.7157, 20),
    "8": (0x222DA82A8A7F050C1704A24F8, 0.6920, 44),
    "9": (0x1A151C1104C15D0CE08551878, 0.6920, 43),
}
_STONEFONT_DECODER_CACHE: dict[str, dict[str, str]] = {}


def build_maoyan_web_headers(
    city_id: int,
    *,
    referer: str | None = None,
    hot_movie_ids: Sequence[int] | None = None,
) -> dict[str, str]:
    headers = dict(MAOYAN_WEB_HEADERS)
    if referer is not None:
        headers["Referer"] = referer
    cookie = build_maoyan_cookie(city_id, hot_movie_ids=hot_movie_ids)
    if cookie:
        headers["Cookie"] = cookie
    return headers


def build_maoyan_mobile_headers(
    city_id: int,
    *,
    referer: str | None = None,
    hot_movie_ids: Sequence[int] | None = None,
) -> dict[str, str]:
    headers = dict(MAOYAN_MOBILE_HEADERS)
    if referer is not None:
        headers["Referer"] = referer
    cookie = build_maoyan_cookie(city_id, hot_movie_ids=hot_movie_ids)
    if cookie:
        headers["Cookie"] = cookie
    return headers


def build_maoyan_cookie(city_id: int, *, hot_movie_ids: Sequence[int] | None = None) -> str:
    pairs = _parse_cookie_pairs(config_manager.maoyan_cookie)
    if hot_movie_ids:
        pairs = _replace_cookie_value(pairs, "hotMovieIds", ",".join(str(mid) for mid in hot_movie_ids))
    pairs = _replace_cookie_value(pairs, "old-moviepage-ci", str(city_id))
    return _format_cookie_pairs(pairs)


def decode_maoyan_stonefont_text(
    html_content: str,
    value: str,
    *,
    headers: dict[str, str] | None = None,
) -> str | None:
    if not value or not _has_private_use_chars(value):
        return value
    decoder = _build_stonefont_decoder(html_content, headers=headers)
    if not decoder:
        return None

    result: list[str] = []
    for char in value:
        if _is_private_use_char(char):
            decoded = decoder.get(char)
            if decoded is None:
                return None
            result.append(decoded)
            continue
        result.append(char)
    return "".join(result)


def _build_stonefont_decoder(
    html_content: str,
    *,
    headers: dict[str, str] | None = None,
) -> dict[str, str] | None:
    font_url = _extract_stonefont_url(html_content)
    if font_url is None:
        return None
    if font_url in _STONEFONT_DECODER_CACHE:
        return _STONEFONT_DECODER_CACHE[font_url]
    if TTFont is None:
        return None

    try:
        response = requests.get(
            font_url,
            headers=_build_font_headers(headers),
            timeout=config_manager.timeout or 60,
        )
        if response.status_code != 200:
            return None
        font_logger = logging.getLogger("fontTools")
        previous_level = font_logger.level
        font_logger.setLevel(logging.ERROR)
        try:
            with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
                font = TTFont(BytesIO(response.content))
                cmap = font.getBestCmap() or {}
                decoder: dict[str, str] = {}
                for codepoint, glyph_name in cmap.items():
                    if not _is_private_use_codepoint(codepoint):
                        continue
                    digit = _classify_stonefont_glyph(font["glyf"][glyph_name])
                    if digit is not None:
                        decoder[chr(codepoint)] = digit
        finally:
            font_logger.setLevel(previous_level)
        if decoder:
            _STONEFONT_DECODER_CACHE[font_url] = decoder
            return decoder
        return None
    except Exception:
        return None


def _extract_stonefont_url(html_content: str) -> str | None:
    match = re.search(r"url\([\"']?(//[^)\"']+\.woff)[\"']?\)", html_content)
    if match is None:
        return None
    return f"https:{match.group(1)}"


def _build_font_headers(headers: dict[str, str] | None) -> dict[str, str]:
    if headers is None:
        return {"User-Agent": MAOYAN_WEB_HEADERS["User-Agent"], "Referer": MAOYAN_WEB_HEADERS["Referer"]}
    result: dict[str, str] = {}
    for name in ("User-Agent", "Referer", "Accept-Language"):
        value = headers.get(name)
        if value:
            result[name] = value
    return result


def _classify_stonefont_glyph(glyph: Any) -> str | None:
    coordinates = list(getattr(glyph, "coordinates", []) or [])
    if not coordinates:
        return None

    x_min = getattr(glyph, "xMin", None)
    y_min = getattr(glyph, "yMin", None)
    x_max = getattr(glyph, "xMax", None)
    y_max = getattr(glyph, "yMax", None)
    if None in (x_min, y_min, x_max, y_max):
        return None

    width = int(x_max) - int(x_min)
    height = int(y_max) - int(y_min)
    if width <= 0 or height <= 0:
        return None

    bitset = 0
    for x, y in coordinates:
        x_index = min(_STONEFONT_GRID_SIZE - 1, max(0, int(((x - x_min) / width) * _STONEFONT_GRID_SIZE)))
        y_index = min(_STONEFONT_GRID_SIZE - 1, max(0, int(((y - y_min) / height) * _STONEFONT_GRID_SIZE)))
        bitset |= 1 << (y_index * _STONEFONT_GRID_SIZE + x_index)

    aspect_ratio = width / height
    point_count = len(coordinates)
    best_digit = None
    best_score = float("inf")
    for digit, (template_bitset, template_aspect, template_points) in _STONEFONT_TEMPLATES.items():
        score = (
            (bitset ^ template_bitset).bit_count()
            + abs(aspect_ratio - template_aspect) * 5
            + abs(point_count - template_points) * 0.2
        )
        if score < best_score:
            best_score = score
            best_digit = digit
    return best_digit if best_score <= _STONEFONT_MAX_DISTANCE else None


def _has_private_use_chars(value: str) -> bool:
    return any(_is_private_use_char(char) for char in value)


def _is_private_use_char(char: str) -> bool:
    return _is_private_use_codepoint(ord(char))


def _is_private_use_codepoint(codepoint: int) -> bool:
    return 0xE000 <= codepoint <= 0xF8FF


def _parse_cookie_pairs(cookie: str) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    for raw_part in cookie.split(";"):
        part = raw_part.strip()
        if not part:
            continue
        if "=" not in part:
            pairs.append((part, ""))
            continue
        name, value = part.split("=", 1)
        pairs.append((name.strip(), value.strip()))
    return pairs


def _replace_cookie_value(
    pairs: list[tuple[str, str]],
    name: str,
    value: str,
) -> list[tuple[str, str]]:
    replaced = False
    result: list[tuple[str, str]] = []
    for current_name, current_value in pairs:
        if current_name != name:
            result.append((current_name, current_value))
            continue
        if not replaced:
            result.append((current_name, value))
            replaced = True
    if not replaced:
        result.append((name, value))
    return result


def _format_cookie_pairs(pairs: Sequence[tuple[str, str]]) -> str:
    return "; ".join(f"{name}={value}" if value else name for name, value in pairs if name)
