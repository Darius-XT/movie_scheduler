"""环境变量配置管理器。"""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import cast


class ConfigManager:
    """统一读取并暴露后端运行配置。"""

    def __init__(self) -> None:
        self.backend_root = Path(__file__).resolve().parents[3]
        self.runtime_root = self.backend_root / ".runtime"
        self.env_path = self.backend_root / ".env"
        self.load_defaults()

    def load_defaults(self) -> None:
        """加载不依赖环境文件的默认值。"""
        self.log_level = "debug"
        self.logger_name = "movie_scheduler"
        self.log_console_format = "%(asctime)s - %(levelname)s - %(message)s"
        self.demo_dir = str(self.backend_root / ".runtime/demo")
        self.result_dir = str(self.backend_root / ".runtime/result")
        self.db_path = str(self.backend_root / ".runtime/movies.db")
        self.city_id = 10
        self.year_threshold = datetime.now().year + 1
        self.allow_redirects = True
        self.timeout = 60
        self.file_max_count = 10
        self.city_mapping = {"北京": 1, "上海": 10}
        self.host = "0.0.0.0"
        self.port = 8000
        self.cors_origins = ["*"]
        self.database_url = f"sqlite:///{self.db_path}"

    def reload_from_env(self) -> None:
        """显式加载 .env 和当前进程环境变量。"""
        self.load_defaults()
        self._load_env_file()

        # 只让真正随环境变化的配置接受覆盖；稳定默认值保留在代码中。
        self.log_level = self._get_str("MOVIE_SCHEDULER_LOG_LEVEL", self.log_level)
        self.db_path = self._resolve_path("MOVIE_SCHEDULER_DB_PATH", self.db_path)
        self.city_id = self._get_int("MOVIE_SCHEDULER_DEFAULT_CITY_ID", self.city_id)
        self.year_threshold = self._get_int("MOVIE_SCHEDULER_YEAR_THRESHOLD", self.year_threshold)
        self.timeout = self._get_int("MOVIE_SCHEDULER_TIMEOUT", self.timeout)
        self.city_mapping = self._get_json_dict("MOVIE_SCHEDULER_CITY_MAPPING", self.city_mapping)
        self.host = self._get_str("MOVIE_SCHEDULER_HOST", self.host)
        self.port = self._get_int("MOVIE_SCHEDULER_PORT", self.port)
        self.cors_origins = self._get_json_list("MOVIE_SCHEDULER_CORS_ORIGINS", self.cors_origins)
        self.database_url = f"sqlite:///{self.db_path}"

    def ensure_runtime_dirs(self) -> None:
        """显式创建运行时目录。"""
        self.runtime_root.mkdir(parents=True, exist_ok=True)
        Path(self.demo_dir).mkdir(parents=True, exist_ok=True)
        Path(self.result_dir).mkdir(parents=True, exist_ok=True)
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

    def _load_env_file(self) -> None:
        """优先把 backend/.env 合并到当前进程环境变量。"""
        if not self.env_path.exists():
            return

        for raw_line in self.env_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            os.environ.setdefault(key, value)

    def _get_str(self, key: str, default: str) -> str:
        return os.getenv(key, default)

    def _get_int(self, key: str, default: int) -> int:
        value = os.getenv(key)
        if value is None or value == "":
            return default
        return int(value)

    def _get_bool(self, key: str, default: bool) -> bool:
        value = os.getenv(key)
        if value is None or value == "":
            return default
        return value.strip().lower() in {"1", "true", "yes", "on"}

    def _get_json_dict(self, key: str, default: dict[str, int]) -> dict[str, int]:
        value = os.getenv(key)
        if not value:
            return default
        parsed = cast(object, json.loads(value))
        if not isinstance(parsed, dict):
            raise ValueError(f"{key} 必须是 JSON 对象")
        parsed_dict = cast(dict[str, object], parsed)
        result: dict[str, int] = {}
        for raw_name, raw_city_id in parsed_dict.items():
            if isinstance(raw_city_id, bool):
                result[str(raw_name)] = int(raw_city_id)
                continue
            if isinstance(raw_city_id, int | str):
                result[str(raw_name)] = int(raw_city_id)
                continue
            raise ValueError(f"{key} 中的城市 ID 必须是整数")
        return result

    def _get_json_list(self, key: str, default: list[str]) -> list[str]:
        value = os.getenv(key)
        if not value:
            return default
        parsed = cast(object, json.loads(value))
        if not isinstance(parsed, list):
            raise ValueError(f"{key} 必须是 JSON 数组")
        parsed_list = cast(list[object], parsed)
        result: list[str] = []
        for raw_item in parsed_list:
            result.append(str(raw_item))
        return result

    def _resolve_path(self, key: str, default: str) -> str:
        raw_value = os.getenv(key, default)
        path = Path(raw_value)
        if not path.is_absolute():
            path = self.backend_root / path
        return str(path)

    def get_city_id(self, city_name: str) -> int | None:
        """根据城市名称获取城市 ID。"""
        return self.city_mapping.get(city_name)

    def get_city_names(self) -> list[str]:
        """获取所有城市名称。"""
        return list(self.city_mapping.keys())


config_manager = ConfigManager()
