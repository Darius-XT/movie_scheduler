# 后端测试规范

## 基本原则

- 所有新增的 public 方法必须有对应测试
- 测试目录必须严格镜像 `src/app/`，文件命名 `test_{被测模块名}.py`
- 用 `monkeypatch` 或构造函数注入隔离依赖，不做真实网络请求和数据库写入

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

## 不测什么

- `@dataclass` / `TypedDict` / `Protocol` 的定义本身
- ORM 字段映射（`models/`）
- Pydantic schema 定义（`schemas/`）
- 框架行为（FastAPI 路由注册、SQLAlchemy 会话管理）
- 私有方法（通过公开方法的行为间接验证）
