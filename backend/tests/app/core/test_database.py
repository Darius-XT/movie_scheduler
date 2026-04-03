"""数据库管理器测试。"""

from __future__ import annotations

from pathlib import Path
from typing import cast

from sqlalchemy.orm import Session, sessionmaker

from app.core.database import DatabaseManager


def test_database_manager_disables_expire_on_commit(tmp_path: Path) -> None:
    """会话工厂应关闭提交后过期。"""
    db_path = tmp_path / "movies.db"
    manager = DatabaseManager(database_url=f"sqlite:///{db_path}")

    manager.initialize()

    assert manager.session_factory is not None
    assert manager.session_factory.kw["expire_on_commit"] is False


class FakeSession:
    """用于验证会话行为的假会话。"""

    def __init__(self) -> None:
        self.committed = False
        self.rolled_back = False
        self.closed = False

    def commit(self) -> None:
        self.committed = True

    def rollback(self) -> None:
        self.rolled_back = True

    def close(self) -> None:
        self.closed = True


class FakeSessionFactory:
    """用于替代 sessionmaker 的假工厂。"""

    def __init__(self, session: FakeSession) -> None:
        self._session = session

    def __call__(self) -> FakeSession:
        return self._session


def test_session_context_does_not_commit() -> None:
    """只读会话退出时不应自动提交。"""
    manager = DatabaseManager()
    fake_session = FakeSession()
    manager.initialize = lambda: None
    manager.session_factory = cast(sessionmaker[Session], FakeSessionFactory(fake_session))

    with manager.session() as session:
        assert session is fake_session

    assert fake_session.committed is False
    assert fake_session.rolled_back is False
    assert fake_session.closed is True


def test_transaction_context_commits_on_success() -> None:
    """事务会话在成功结束时应提交并关闭。"""
    manager = DatabaseManager()
    fake_session = FakeSession()
    manager.initialize = lambda: None
    manager.session_factory = cast(sessionmaker[Session], FakeSessionFactory(fake_session))

    with manager.transaction() as session:
        assert session is fake_session

    assert fake_session.committed is True
    assert fake_session.rolled_back is False
    assert fake_session.closed is True


def test_transaction_context_rolls_back_on_error() -> None:
    """事务会话在异常时应回滚并继续抛错。"""
    manager = DatabaseManager()
    fake_session = FakeSession()
    manager.initialize = lambda: None
    manager.session_factory = cast(sessionmaker[Session], FakeSessionFactory(fake_session))

    try:
        with manager.transaction():
            raise RuntimeError("boom")
    except RuntimeError:
        pass
    else:
        raise AssertionError("transaction 应继续抛出原始异常")

    assert fake_session.committed is False
    assert fake_session.rolled_back is True
    assert fake_session.closed is True
