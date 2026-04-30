"""Douban mobile search client."""

from __future__ import annotations

import re
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from bs4.element import Tag

from app.core.config import config_manager
from app.core.logger import logger
from app.update.movie.douban.entities import DoubanMovieSearchItem

DOUBAN_MOBILE_SEARCH_URL = "https://m.douban.com/search/"
DOUBAN_MOBILE_BASE_URL = "https://m.douban.com"
DOUBAN_REQUEST_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
}
MAX_SEARCH_ATTEMPTS = 2


class DoubanApiClient:
    """Fetches Douban movie candidates from the mobile search HTML page."""

    def __init__(self, base_url: str | None = None) -> None:
        self._base_url_override = base_url
        self.session = requests.Session()

    @property
    def base_url(self) -> str:
        return (self._base_url_override or DOUBAN_MOBILE_SEARCH_URL).rstrip("/")

    @property
    def timeout(self) -> int:
        return config_manager.timeout or 60

    def search_movies(self, title: str, page: int = 1) -> list[DoubanMovieSearchItem]:
        """Search Douban mobile by movie title and return candidate items."""
        normalized_title = title.strip()
        if not normalized_title:
            return []

        url = self.base_url
        for attempt in range(1, MAX_SEARCH_ATTEMPTS + 1):
            try:
                response = self.session.get(
                    url,
                    params={"query": normalized_title},
                    headers=DOUBAN_REQUEST_HEADERS,
                    timeout=self.timeout,
                )
            except Exception as error:
                logger.error(
                    "Douban mobile search request failed: title=%s, url=%s, attempt=%s, error=%s",
                    normalized_title,
                    url,
                    attempt,
                    error,
                    exc_info=True,
                )
                continue

            if not response.ok:
                logger.error(
                    "Douban mobile search returned non-200: title=%s, status=%s, url=%s, attempt=%s, response=%s",
                    normalized_title,
                    response.status_code,
                    response.url,
                    attempt,
                    response.text[:1000],
                )
                continue

            return self.parse_search_html(response.text)

        logger.warning("Douban mobile search failed after retries: title=%s, page=%s", normalized_title, page)
        return []

    def parse_search_html(self, html_content: str) -> list[DoubanMovieSearchItem]:
        """Parse Douban mobile search HTML into movie candidates."""
        try:
            soup = BeautifulSoup(html_content, "html.parser")
            movie_module = self._find_movie_module(soup)
            if movie_module is None:
                logger.debug("Douban mobile search HTML has no movie module")
                return []

            candidates: list[DoubanMovieSearchItem] = []
            for link in movie_module.select("ul.search_results_subjects > li > a"):
                candidate = self._build_search_item_from_link(link)
                if candidate is not None:
                    candidates.append(candidate)
            return candidates
        except Exception as error:
            logger.error("Douban mobile search HTML parse failed: %s", error, exc_info=True)
            return []

    def _find_movie_module(self, soup: BeautifulSoup) -> Tag | None:
        for module in soup.select("li.search-module"):
            name_element = module.select_one(".search-results-modules-name")
            module_name = name_element.get_text(strip=True) if name_element is not None else ""
            if module_name == "电影":
                return module
        return None

    def _build_search_item_from_link(self, link: Tag) -> DoubanMovieSearchItem | None:
        href = link.get("href")
        if not isinstance(href, str):
            return None

        douban_url = self._normalize_subject_url(href)
        if douban_url is None:
            return None

        title_element = link.select_one("span.subject-title")
        title = title_element.get_text(strip=True) if title_element is not None else ""
        if not title:
            return None

        return DoubanMovieSearchItem(
            title=title,
            rating=self._extract_rating(link),
            cover_link=douban_url,
            year="",
            country="",
            actors=[],
        )

    def _normalize_subject_url(self, href: str) -> str | None:
        absolute_url = urljoin(DOUBAN_MOBILE_BASE_URL, href)
        match = re.search(r"/movie/subject/(\d+)/?", absolute_url)
        if match is None:
            return None
        return f"{DOUBAN_MOBILE_BASE_URL}/movie/subject/{match.group(1)}/"

    def _extract_rating(self, link: Tag) -> str:
        rating_element = link.select_one("p.rating")
        if rating_element is None:
            return ""
        rating_text = rating_element.get_text(" ", strip=True)
        match = re.search(r"\d+(?:\.\d+)?", rating_text)
        return match.group(0) if match is not None else ""


douban_api_client = DoubanApiClient()
