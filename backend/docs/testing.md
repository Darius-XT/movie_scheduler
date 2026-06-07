# 测试规范

## 基本原则

- 所有新增的 public 方法必须有对应测试
- 测试目录必须**严格镜像** `src/movie_scheduler/`: 每个 feature/子领域在 `tests/features/` 下都有对应同名目录,文件命名为 `test_{被测模块名}.py`
- 用 `monkeypatch` 或构造函数注入隔离依赖,不做真实网络请求和数据库写入

## 测试目录与 src 结构同步

```
src/movie_scheduler/features/show/{router.py, service.py, repository.py, ...}
tests/features/show/{test_router.py, test_service.py, test_repository.py, ...}
```

`core/` 与 `shared/` 同样镜像:

```
src/movie_scheduler/core/{db.py, exceptions.py, logging.py, scheduler.py}
tests/core/{test_db.py, test_exceptions.py, ...}
```

**当 feature 内部拆出嵌套子领域时,测试目录必须同步拆分**——例如 `features/movie/update_douban/` 对应 `tests/features/movie/update_douban/`。

每个领域子目录都必须包含 `__init__.py`,避免 pytest 出现 "import file mismatch" 的同名冲突。

## 依赖隔离

| 依赖类型 | 隔离方式 |
|---------|---------|
| 构造函数注入的依赖 | 注入 Fake 对象 |
| 模块级单例(`movie_repository` 等) | `monkeypatch.setattr` |
| 外部 HTTP 客户端 | `monkeypatch` 掉 service 内部的 HTTP 函数(如 `_http_get_text`) |

```python
# monkeypatch 替换模块级单例
import movie_scheduler.features.movie.repository as repo_module
monkeypatch.setattr(repo_module.movie_repository, "get_movie_by_id", fake_fn)

# monkeypatch 替换 service 内部的 HTTP 函数
import movie_scheduler.features.show.service as show_module
monkeypatch.setattr(show_module, "_http_get_text", lambda url, label: fake_response)
```

## endpoint 测试归属

每个 feature 的 router 测试归属该 feature 的 `tests/features/{name}/test_router.py`,不集中放在顶层。

## 不测什么

- `@dataclass` / `TypedDict` / `Protocol` 的定义本身
- ORM 字段映射(`models.py`)
- Pydantic schema 定义(`schemas.py`)
- 框架行为(FastAPI 路由注册、SQLAlchemy 会话管理)
- 私有方法/`_`前缀符号(通过公开方法的行为间接验证)
