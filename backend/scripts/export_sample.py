"""手动抓取并保存调试样本。"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Literal

from app.core.bootstrap import bootstrap_runtime
from app.core.file_saver import file_saver
from app.use_cases.show_fetching.scrapers.cinema_scraper import cinema_scraper
from app.use_cases.show_fetching.scrapers.cinema_show_scraper import cinema_show_scraper
from app.use_cases.show_fetching.scrapers.show_date_scraper import show_date_scraper
from app.use_cases.update.cinema_info.cinema_scraper import cinema_info_scraper
from app.use_cases.update.movie_info.base_info.base_info_scraper import movie_base_info_scraper
from app.use_cases.update.movie_info.douban.douban_api_client import DoubanApiClient
from app.use_cases.update.movie_info.extra_info.extra_info_scraper import movie_extra_info_scraper

# ── 调试参数统一在此处修改 ──────────────────────────────────────────────────────
DEMO_MOVIE_ID = 1324725
DEMO_MOVIE_TITLE = "挽救计划"
DEMO_CINEMA_ID = 16119
DEMO_SHOW_DATE = "2026-04-22"
DEMO_CITY_ID = 10
DEMO_PAGE = 1
DEMO_CINEMA_LIMIT = 20
DEMO_CINEMA_OFFSET = 0
DEMO_DOUBAN_BASE_URL = "http://localhost:8085"
# ──────────────────────────────────────────────────────────────────────────────

SampleName = Literal[
    "show_dates",
    "cinemas",
    "cinema_shows",
    "movie_base_info",
    "movie_extra_info",
    "cinema_info",
    "douban",
]

SAMPLE_FILENAMES: dict[SampleName, str] = {
    "show_dates": "show_fetching_show_dates.json",
    "cinemas": "show_fetching_cinemas.json",
    "cinema_shows": "show_fetching_cinema_shows.json",
    "movie_base_info": "update_movie_base_info.html",
    "movie_extra_info": "update_movie_extra_info.json",
    "cinema_info": "update_cinema_info.json",
    "douban": "douban_search.json",
}

SAMPLE_GROUPS: dict[str, list[SampleName]] = {
    "show_dates": ["show_dates"],
    "cinemas": ["cinemas"],
    "cinema_shows": ["cinema_shows"],
    "movie_base_info": ["movie_base_info"],
    "movie_extra_info": ["movie_extra_info"],
    "cinema_info": ["cinema_info"],
    "douban": ["douban"],
    "show_fetching_all": ["show_dates", "cinemas", "cinema_shows"],
    "update_all": ["movie_base_info", "movie_extra_info", "cinema_info"],
    "all": [
        "show_dates",
        "cinemas",
        "cinema_shows",
        "movie_base_info",
        "movie_extra_info",
        "cinema_info",
        "douban",
    ],
}


def export_sample(sample_name: SampleName) -> dict[str, str]:
    """根据预设抓取并保存单个调试样本到 demo 目录。"""
    filename = SAMPLE_FILENAMES[sample_name]

    if sample_name == "show_dates":
        success, content = show_date_scraper.scrape_showdate(DEMO_MOVIE_ID, DEMO_CITY_ID)
    elif sample_name == "cinemas":
        success, content = cinema_scraper.scrape_cinemas(
            DEMO_MOVIE_ID, DEMO_SHOW_DATE, DEMO_CITY_ID, DEMO_CINEMA_LIMIT, DEMO_CINEMA_OFFSET
        )
    elif sample_name == "cinema_shows":
        success, content = cinema_show_scraper.scrape_cinema_shows(DEMO_CINEMA_ID, DEMO_CITY_ID)
    elif sample_name == "movie_base_info":
        success, content = movie_base_info_scraper.scrape_movies(1, DEMO_PAGE, DEMO_CITY_ID)
    elif sample_name == "movie_extra_info":
        success, content = movie_extra_info_scraper.scrape_details(DEMO_MOVIE_ID)
    elif sample_name == "cinema_info":
        success, content = cinema_info_scraper.scrape_cinemas(DEMO_CITY_ID, DEMO_PAGE)
    else:
        local_client = DoubanApiClient(base_url=DEMO_DOUBAN_BASE_URL)
        candidates = local_client.search_movies(title=DEMO_MOVIE_TITLE, page=1)
        content = json.dumps(
            [
                {"title": c.title, "rating": c.rating, "cover_link": c.cover_link, "year": c.year}
                for c in candidates
            ],
            ensure_ascii=False,
            indent=2,
        )
        success = bool(candidates)

    if not success or not content:
        raise ValueError(f"{sample_name} 样本抓取失败")
    if not file_saver.save_demo(content, filename):
        raise ValueError(f"{sample_name} 样本保存失败")

    return {"sample_name": sample_name, "filename": filename}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="手动抓取并保存调试样本文件到 .runtime/demo")
    parser.add_argument("sample_list", choices=list(SAMPLE_GROUPS.keys()), help="要执行的样本列表")
    return parser


def main() -> int:
    bootstrap_runtime()
    parser = build_parser()
    args = parser.parse_args()

    try:
        results = [export_sample(sample_name) for sample_name in SAMPLE_GROUPS[args.sample_list]]
    except ValueError as error:
        print(f"导出失败: {error}", file=sys.stderr)
        return 1

    print(json.dumps({"success": True, "sample_list": args.sample_list, "results": results}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
