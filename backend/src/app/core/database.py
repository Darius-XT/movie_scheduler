"""数据库基础设施。"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import config_manager
from app.core.logger import logger


class DatabaseManager:
    """负责数据库连接与会话工厂初始化。"""

    def __init__(self, database_url: str | None = None) -> None:
        self.database_url = database_url
        self.engine: Engine | None = None
        self.session_factory: sessionmaker[Session] | None = None
        self._initialized = False

    def initialize(self) -> None:
        """显式初始化数据库引擎和会话工厂。"""
        if self._initialized:
            return

        try:
            if self.engine is None:
                self.database_url = self.database_url or config_manager.database_url
                self.engine = create_engine(self.database_url)
                # 读取场景下 ORM 实体会在会话结束后继续被访问，
                # 这里关闭提交后过期，避免 DetachedInstanceError。
                self.session_factory = sessionmaker(bind=self.engine, expire_on_commit=False)

            logger.debug("数据库连接器初始化完成，当前使用数据库: %s", self.database_url)
            self._initialized = True
        except Exception as error:
            logger.error("数据库初始化失败: %s", error)
            raise

    @contextmanager
    def session(self) -> Iterator[Session]:
        """提供只读/通用会话上下文，不自动提交事务。"""
        self.initialize()

        if self.session_factory is None:
            raise RuntimeError("数据库会话工厂未初始化")

        session = self.session_factory()
        try:
            yield session
        finally:
            session.close()

    @contextmanager
    def transaction(self) -> Iterator[Session]:
        """提供带自动提交与回滚的事务会话上下文。"""
        self.initialize()

        if self.session_factory is None:
            raise RuntimeError("数据库会话工厂未初始化")

        session = self.session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()


database_manager = DatabaseManager()
