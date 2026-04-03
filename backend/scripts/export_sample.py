"""手动抓取并保存调试样本。"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Literal

from app.core.bootstrap import bootstrap_runtime
from app.core.config import config_manager
from app.core.file_saver import file_saver
from app.use_cases.show_fetching.scrapers.cinema_scraper import cinema_scraper
from app.use_cases.show_fetching.scrapers.cinema_show_scraper import cinema_show_scraper
from app.use_cases.show_fetching.scrapers.show_date_scraper import show_date_scraper
from app.use_cases.update.cinema_info.cinema_scraper import cinema_info_scraper
from app.use_cases.update.movie_info.base_info.base_info_scraper import movie_base_info_scraper
from app.use_cases.update.movie_info.extra_info.extra_info_scraper import movie_extra_info_scraper

SampleType = Literal[
    "show_dates",
    "cinemas",
    "cinema_shows",
    "movie_base_info",
    "movie_extra_info",
    "cinema_info",
]

SampleName = Literal[
    "show_dates",
    "cinemas",
    "cinema_shows",
    "movie_base_info",
    "movie_extra_info",
    "cinema_info",
]

SAMPLE_FILENAMES: dict[SampleType, str] = {
    "show_dates": "show_fetching_show_dates.json",
    "cinemas": "show_fetching_cinemas.json",
    "cinema_shows": "show_fetching_cinema_shows.json",
    "movie_base_info": "update_movie_base_info.html",
    "movie_extra_info": "update_movie_extra_info.json",
    "cinema_info": "update_cinema_info.json",
}

# 调试样本参数固定写在这里，后续如需更换只改这一处即可。
SAMPLE_PRESETS: dict[SampleName, dict[str, int | str]] = {
    "show_dates": {
        "movie_id": 1324725,
        "city_id": 10,
    },
    "cinemas": {
        "movie_id": 1324725,
        "city_id": 10,
        "show_date": "2026-04-08",
        "limit": 20,
        "offset": 0,
    },
    "cinema_shows": {
        "cinema_id": 16119,
        "city_id": 10,
    },
    "movie_base_info": {
        "show_type": 1,
        "city_id": 10,
        "page": 1,
    },
    "movie_extra_info": {
        "movie_id": 1324725,
    },
    "cinema_info": {
        "city_id": 10,
        "page": 1,
    },
}

SAMPLE_GROUPS: dict[str, list[SampleName]] = {
    "show_dates": ["show_dates"],
    "cinemas": ["cinemas"],
    "cinema_shows": ["cinema_shows"],
    "movie_base_info": ["movie_base_info"],
    "movie_extra_info": ["movie_extra_info"],
    "cinema_info": ["cinema_info"],
    "show_fetching_all": ["show_dates", "cinemas", "cinema_shows"],
    "update_all": ["movie_base_info", "movie_extra_info", "cinema_info"],
    "all": [
        "show_dates",
        "cinemas",
        "cinema_shows",
        "movie_base_info",
        "movie_extra_info",
        "cinema_info",
    ],
}


def build_parser() -> argparse.ArgumentParser:
    """构建命令行参数解析器。"""
    parser = argparse.ArgumentParser(description="手动抓取并保存调试样本文件")
    parser.add_argument(
        "sample_list",
        choices=list(SAMPLE_GROUPS.keys()),
        help="要执行的样本列表",
    )
    return parser


def export_sample(sample_name: SampleName) -> dict[str, str]:
    """根据预设抓取并保存单个调试样本。"""
    preset = SAMPLE_PRESETS[sample_name]
    filename = SAMPLE_FILENAMES[sample_name]

    if sample_name == "show_dates":
        movie_id = require_positive_int(preset.get("movie_id"), "movie_id")
        city_id = normalize_city_id(preset.get("city_id"))
        success, content = show_date_scraper.scrape_showdate(movie_id, city_id)
    elif sample_name == "cinemas":
        movie_id = require_positive_int(preset.get("movie_id"), "movie_id")
        city_id = normalize_city_id(preset.get("city_id"))
        show_date = require_non_empty(preset.get("show_date"), "show_date")
        limit = require_positive_int(preset.get("limit"), "limit")
        offset = require_non_negative_int(preset.get("offset"), "offset")
        success, content = cinema_scraper.scrape_cinemas(movie_id, show_date, city_id, limit, offset)
    elif sample_name == "cinema_shows":
        cinema_id = require_positive_int(preset.get("cinema_id"), "cinema_id")
        city_id = normalize_city_id(preset.get("city_id"))
        success, content = cinema_show_scraper.scrape_cinema_shows(cinema_id, city_id)
    elif sample_name == "movie_base_info":
        show_type = require_positive_int(preset.get("show_type"), "show_type")
        city_id = normalize_city_id(preset.get("city_id"))
        page = require_positive_int(preset.get("page"), "page")
        success, content = movie_base_info_scraper.scrape_movies(show_type, page, city_id)
    elif sample_name == "movie_extra_info":
        movie_id = require_positive_int(preset.get("movie_id"), "movie_id")
        success, content = movie_extra_info_scraper.scrape_details(movie_id)
    else:
        city_id = normalize_city_id(preset.get("city_id"))
        page = require_positive_int(preset.get("page"), "page")
        success, content = cinema_info_scraper.scrape_cinemas(city_id, page)

    if not success or not content:
        raise ValueError(f"{sample_name} 样本抓取失败")
    if not file_saver.save_example(content, filename):
        raise ValueError(f"{sample_name} 样本保存失败")

    return {
        "sample_name": sample_name,
        "filename": filename,
        "path": str(Path(config_manager.result_dir) / filename),
    }


def normalize_city_id(city_id: int | str | None) -> int:
    """补齐并校验城市 ID。"""
    normalized_city_id = city_id if city_id is not None else config_manager.city_id
    return require_positive_int(normalized_city_id, "city_id")


def require_positive_int(value: int | str | None, field_name: str) -> int:
    """要求正整数参数。"""
    if value is None:
        raise ValueError(f"{field_name} 必须是正整数")
    normalized_value = int(value)
    if normalized_value <= 0:
        raise ValueError(f"{field_name} 必须是正整数")
    return normalized_value


def require_non_negative_int(value: int | str | None, field_name: str) -> int:
    """要求非负整数参数。"""
    if value is None:
        raise ValueError(f"{field_name} 不能小于 0")
    normalized_value = int(value)
    if normalized_value < 0:
        raise ValueError(f"{field_name} 不能小于 0")
    return normalized_value


def require_non_empty(value: int | str | None, field_name: str) -> str:
    """要求非空字符串参数。"""
    if value is None:
        raise ValueError(f"{field_name} 不能为空")
    normalized_value = str(value).strip()
    if not normalized_value:
        raise ValueError(f"{field_name} 不能为空")
    return normalized_value


def main() -> int:
    """脚本入口。"""
    bootstrap_runtime()
    parser = build_parser()
    args = parser.parse_args()

    try:
        results = [export_sample(sample_name) for sample_name in SAMPLE_GROUPS[args.sample_list]]
    except ValueError as error:
        print(f"导出失败: {error}", file=sys.stderr)
        return 1

    print(
        json.dumps(
            {
                "success": True,
                "sample_list": args.sample_list,
                "results": results,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
