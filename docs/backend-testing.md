# 后端测试规范

## 基本原则

- 所有新增的 public 方法必须有对应测试
- 测试目录必须**严格镜像** `src/app/`：每个领域目录在 `tests/app/` 下都有对应同名目录，文件命名为 `test_{被测模块名}.py`
- 用 `monkeypatch` 或构造函数注入隔离依赖，不做真实网络请求和数据库写入

## 测试目录与 src 结构同步

```
src/app/show/{cinema_client.py, gateway.py, fetcher.py, ...}
tests/app/show/{test_cinema_client.py, test_gateway.py, test_fetcher.py, ...}
```

**当 src 目录拆分时，测试目录必须同步拆分**——不允许"扁平 + 嵌套"两种风格混存。
例如：当 `services/update.py` 被拆为 `update/{cinema,movie/...}` 子领域时，
对应的 `tests/app/services/test_update_service.py` 必须同步拆分到
`tests/app/update/test_service.py` 等位置，不允许保留旧的扁平测试文件。

每个领域子目录都必须包含 `__init__.py`，避免 pytest 出现 "import file mismatch" 的同名冲突。

## 依赖隔离

| 依赖类型 | 隔离方式 |
|---------|---------|
| 构造函数注入的依赖（enricher、gateway 等） | 注入 Fake 对象 |
| 模块级单例（`movie_repository` 等） | `monkeypatch.setattr` |
| 外部 HTTP 客户端 | 注入 Fake client |

```python
# 构造函数注入
enricher = DoubanInfoEnricher(client=cast(DoubanApiClient, FakeClient()))

# monkeypatch 替换模块级单例
import app.repositories.movie as repo_module
monkeypatch.setattr(repo_module.movie_repository, "get_movie_by_id", fake_fn)
```

## endpoint 测试归属

每个领域的 endpoint 测试归属该领域的 `tests/app/{domain}/test_endpoints.py`，
不集中放在顶层 `tests/app/test_routes.py`。

## 不测什么

- `@dataclass` / `TypedDict` / `Protocol` 的定义本身
- ORM 字段映射（`models/`）
- Pydantic schema 定义（领域 `schemas.py`）
- 框架行为（FastAPI 路由注册、SQLAlchemy 会话管理）
- 私有方法（通过公开方法的行为间接验证）
