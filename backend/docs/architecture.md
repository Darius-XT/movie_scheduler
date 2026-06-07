# 架构规范

后端代码位于 `backend/src/movie_scheduler/`。结构按**资源优先**组织,顶层放应用装配与跨切关注点,业务按 feature 拆分。

## 顶层组织

`backend/src/movie_scheduler/` 严格只允许这些文件/目录:

| 文件 / 目录 | 创建条件 | 职责 |
|------------|----------|------|
| `__init__.py` | 必须 | 包标记 |
| `__main__.py` | 必须 | `python -m movie_scheduler` 启动入口,调用 `uvicorn.run` |
| `app.py` | 必须 | 创建 FastAPI 实例、注册路由、异常处理器、生命周期 |
| `config.py` | 必须 | 环境变量读取、Settings 对象 |
| `core/` | 必须 | 基础设施 |
| `shared/` | 跨 feature 工具/类型存在时 | 无业务语义的复用模块 |
| `features/` | 必须 | 业务领域根目录 |

不允许在这一层放任何业务文件、单独的 `routes.py`、`error_handlers.py`、`bootstrap.py`、`schemas.py` 等——这些职责要么进入 `app.py`、要么进入 `core/exceptions.py`、要么进入 `shared/types.py`。

## core/

只放技术基础设施,不放业务规则:

| 文件 | 职责 |
|------|------|
| `db.py` | SQLAlchemy engine、session、`Base` |
| `exceptions.py` | 应用级异常类型 + 全局 handler 注册函数 |
| `logging.py` | logger 配置与全局 logger |
| `scheduler.py` | APScheduler 定时任务编排 |

按需添加(当前未启用): `cache.py`(Redis)、`security.py`(认证)、`middleware.py`(自定义中间件)。新增时与本表保持同样粒度,一职责一文件。

## shared/

跨 feature 复用的工具或类型,无业务语义:

| 文件 | 职责 |
|------|------|
| `types.py` | 跨 feature 的响应包装、类型别名(当前: `SuccessEnvelope`) |
| `utils.py` | 通用工具(当前: `FileSaver`) |

按需添加: `pagination.py`、其他纯工具。

## features/

每个 feature 是一个**资源**(不是用例、不是流程),代表一个业务边界。当前 features 见 [structure.md](structure.md)。

每个 feature 目录严格遵守这份文件清单:

| 文件 | 创建条件 | 职责 |
|------|----------|------|
| `__init__.py` | 必须 | 包标记 |
| `router.py` | 有对外 HTTP 接口时 | 定义路由、解析参数、调用 service、组装统一响应 |
| `schemas.py` | 有请求或响应 schema 时 | 该 feature 私有 Pydantic 契约 + 内部 dataclass |
| `models.py` | 拥有数据库表时 | SQLAlchemy ORM 实体 |
| `service.py` | 必须 | 业务逻辑入口;HTTP 客户端、解析、抓取编排、内部 dataclass 全部并入此处或私有 `_` 前缀符号 |
| `repository.py` | 有数据库读写时 | ORM 增删改查封装,只接收 `TypedDict`,返回 ORM 对象 |
| `dependencies.py` | 真有 FastAPI Depends 注入时 | 模板预留,当前未使用 |
| `exceptions.py` | 真有 feature 特有异常时 | 模板预留,当前用 `core/exceptions.py` |
| `constants.py` | 真有领域常量时 | 模板预留 |

**禁止**新增任何"按角色分层"的文件:`helper.py` `builder.py` `client.py` `gateway.py` `fetcher.py` `enricher.py` `result_builder.py` `request_helper.py` 等。这些代码都应该并入 `service.py`,或在 service 内部用 `_` 前缀私有模块/类拆分。

## 业务子领域(嵌套 features)

当一个 feature 内部确实存在多个稳定的子资源/数据源时,可以建嵌套子目录,**子目录内部遵守相同的文件清单**。当前例子:

```
features/movie/
├── router.py
├── schemas.py
├── models.py
├── service.py        # 编排三个数据源
├── repository.py
├── update_base/      # 猫眼电影列表抓取
│   ├── schemas.py
│   └── service.py
├── update_douban/    # 豆瓣评分补充
│   ├── schemas.py
│   └── service.py
└── update_extra/     # 猫眼详情页补充
    ├── schemas.py
    └── service.py
```

**适合**拆子目录: 数据源/子资源稳定、命名能表达业务、平级文件已很多。
**不适合**: 仅按角色再分一层(不会出现 `clients/`、`builders/`)。

## models 与 repository 的归属

每张表归属一个 feature(数据写入方/owner),其他 feature 跨包 import 读取:

| 表 | 归属 |
|----|------|
| `cinemas` | `features/cinema/` |
| `movies` | `features/movie/` |
| `movie_shows` | `features/show/` |
| `planning_items` | `features/plan/` |

Alembic `migrations/env.py` 在 `target_metadata = Base.metadata` 之前显式 import 各 feature 的 `models` 模块,触发表注册。

## API URL

- 永远只有 `/api`,不引入 `/api/v1` / `/api/v2`
- URL 路径按资源,不按"动作分组"。`/api/cinemas/update-stream`、`/api/movies/update-status`,而不是 `/api/update/cinema-stream`、`/api/update/movies/status`
- `app.py` 用单个 `APIRouter(prefix="/api")` 聚合各 feature router 后挂到 FastAPI
