"""数据库初始化器 - 负责数据库连接、初始化和管理, 静态的部分"""

from typing import Optional
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.config import settings
from src.logger import logger
from src.db.db_models import Base


class DBConnector:
    """数据库初始化器类 - 整合数据库连接和初始化功能"""

    def __init__(self, db_path: Optional[str] = None):
        """初始化数据库初始化器"""
        self.db_path = db_path or settings.database_path  # 数据库存放路径
        self.database_url = f"sqlite:///{self.db_path}"  # 使用什么数据库 + 存放路径
        self.engine = create_engine(self.database_url)  # 数据库引擎, 所有操作的入口
        self.session_factory = sessionmaker(bind=self.engine)  # 会话工厂

        # 自动创建所有表（先显式导入模型模块以注册到 metadata）
        try:
            Base.metadata.create_all(self.engine)
            logger.debug(f"数据库连接器创建完成并已建表: {self.db_path}")
        except Exception as e:
            logger.error(f"数据库建表失败: {e}")
            raise


# 全局数据库连接器实例
db_connector = DBConnector()
