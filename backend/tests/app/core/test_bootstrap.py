"""启动编排测试。"""

from __future__ import annotations

import pytest

from app.core import bootstrap


def test_bootstrap_runtime_runs_explicit_initializers_in_order(monkeypatch: pytest.MonkeyPatch) -> None:
    """启动编排应按固定顺序执行显式初始化。"""
    call_order: list[str] = []

    monkeypatch.setattr(bootstrap.config_manager, "reload_from_env", lambda: call_order.append("reload_from_env"))
    monkeypatch.setattr(
        bootstrap.config_manager,
        "ensure_runtime_dirs",
        lambda: call_order.append("ensure_runtime_dirs"),
    )
    monkeypatch.setattr(bootstrap, "setup_logger", lambda: call_order.append("setup_logger"))
    monkeypatch.setattr(bootstrap.file_saver, "initialize", lambda: call_order.append("file_saver.initialize"))
    monkeypatch.setattr(
        bootstrap.database_manager,
        "initialize",
        lambda: call_order.append("database_manager.initialize"),
    )

    bootstrap.bootstrap_runtime()

    assert call_order == [
        "reload_from_env",
        "ensure_runtime_dirs",
        "setup_logger",
        "file_saver.initialize",
        "database_manager.initialize",
    ]
