"""配置模块基础测试。"""

import pytest

from app.core.config import ConfigManager, config_manager


def test_city_mapping_is_dict():
    """城市映射应被解析为字典。"""
    assert isinstance(config_manager.city_mapping, dict)


def test_douban_api_base_url_supports_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    """豆瓣 API 服务地址应支持通过环境变量覆盖。"""
    monkeypatch.setenv("MOVIE_SCHEDULER_DOUBAN_API_BASE_URL", "http://127.0.0.1:8085/")

    manager = ConfigManager()
    manager.reload_from_env()

    assert manager.douban_api_base_url == "http://127.0.0.1:8085"
