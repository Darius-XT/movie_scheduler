"""配置管理器 - 负责加载和管理所有配置属性"""

from pathlib import Path
from datetime import datetime
import yaml


class ConfigManager:
    """全局配置管理器 - 单例模式，维护所有配置属性"""

    def __init__(self):
        self.log_level = None
        self.log_dir = None
        self.log_max_count = None
        self.logger_name = None
        self.log_console_format = None
        self.log_file_format = None
        self.demo_dir = None
        self.result_dir = None
        self.db_path = None
        self.city_id = None
        self.filter_china_movies = None
        self.year_threshold = None
        # 爬虫配置
        self.allow_redirects = None
        self.timeout = None
        # 文件保存配置
        self.file_max_count = None

        self._load_config()

    def _load_config(self) -> None:
        """加载 YAML 配置文件"""
        # 获取配置文件路径
        project_root = Path(__file__).parent.parent.parent
        config_path = project_root / "config" / "config.yaml"

        try:
            if not config_path.exists():
                print(f"配置文件不存在: {config_path}，使用默认值")
                return

            with open(config_path, "r", encoding="utf-8") as f:
                config_data = yaml.safe_load(f) or {}

            # 加载日志配置
            log_config = config_data.get("log", {})
            self.log_level = log_config.get("level", "debug")
            self.log_dir = log_config.get("dir", "data/log")
            self.log_max_count = log_config.get("max_count", 7)
            self.logger_name = log_config.get("logger_name", "movie_scheduler")
            self.log_console_format = log_config.get(
                "console_format", "%(asctime)s - %(levelname)s - %(message)s"
            )
            self.log_file_format = log_config.get(
                "file_format", "%(asctime)s - %(levelname)s - %(message)s"
            )

            # 加载文件路径配置
            paths_config = config_data.get("paths", {})
            self.demo_dir = paths_config.get("input", {}).get("demo_dir", "data/demo")
            self.result_dir = paths_config.get("output", {}).get(
                "result_dir", "data/result"
            )
            self.db_path = paths_config.get("database", "data/movies.db")

            # 加载城市配置
            city_config = config_data.get("city", {})
            self.city_id = city_config.get("id", 10)

            # 加载电影筛选配置
            filter_config = config_data.get("movie_filter", {})
            self.filter_china_movies = filter_config.get("filter_china_movies", True)
            year_threshold = filter_config.get("year_threshold")
            if year_threshold is None:
                self.year_threshold = datetime.now().year + 1
            else:
                self.year_threshold = year_threshold

            # 加载爬虫配置
            scraper_config = config_data.get("scraper", {})
            self.allow_redirects = scraper_config.get("allow_redirects", True)
            self.timeout = scraper_config.get("timeout", 60)

            # 加载文件保存配置
            file_saver_config = config_data.get("file_saver", {})
            self.file_max_count = file_saver_config.get("max_count", 10)

            self.test_file_dir = self.result_dir
            self.database_path = self.db_path
            self.database_url = f"sqlite:///{self.db_path}"

            print(f"成功加载配置文件: {config_path}")

        except yaml.YAMLError as e:
            print(f"解析 YAML 配置文件失败: {e}")
        except Exception as e:
            print(f"加载配置文件失败: {e}")


# 全局配置管理器实例
config_manager = ConfigManager()
