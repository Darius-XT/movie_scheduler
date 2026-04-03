"""应用级异常定义。"""

from __future__ import annotations


class AppError(Exception):
    """用于向接口层传递可预期的业务异常。"""

    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class RepositoryError(Exception):
    """用于表示数据库访问失败。"""


class ExternalDependencyError(Exception):
    """用于表示外部依赖调用失败。"""


class DataParsingError(Exception):
    """用于表示外部数据解析失败。"""
