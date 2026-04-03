"""配置模块基础测试。"""

from app.core.config import config_manager


def test_city_mapping_is_dict():
    """城市映射应被解析为字典。"""
    assert isinstance(config_manager.city_mapping, dict)
