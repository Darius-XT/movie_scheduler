# 后端架构

项目以**领域优先**组织：每个业务域是 `app/` 顶层下的一个平级目录。

## app/ 顶层结构

```
src/app/
├── app.py                    # 创建 FastAPI 实例、注册 router、中间件、异常处理器
├── main.py                   # 本地启动入口（uvicorn.run）
├── routes.py                 # 聚合所有领域 router，挂载 /api 前缀
├── error_handlers.py         # 全局异常处理器
├── schemas.py                # 仅放跨域共享的 schema（如 SuccessEnvelope）
├── core/                     # 技术基础设施：配置、数据库、日志、异常
├── models/                   # 所有 ORM 实体（不区分是否跨域）
├── repositories/             # 所有 ORM repository
├── city/                     # 城市领域
├── movie/                    # 电影筛选领域
├── show/                     # 场次抓取领域
└── update/                   # 更新领域（含 cinema/、movie/{base,douban,extra}/ 子领域）
```

顶层只在有必要时创建文件，不预建空文件：

| 文件 / 目录 | 存在条件 |
|------------|----------|
| `app.py` | **必须有** — 创建 FastAPI 实例，注册路由、中间件、异常处理器 |
| `main.py` | 需要独立启动入口时 — 调用 `uvicorn.run` |
| `routes.py` | **必须有** — 聚合所有领域 router；统一挂载 `/api` 前缀 |
| `error_handlers.py` | **必须有** — 注册全局异常处理器 |
| `schemas.py` | **必须有** — 跨域共享 schema（如 `SuccessEnvelope`）|
| `middlewares.py` | 有自定义中间件时 — CORS 等当前直接在 `app.py` 注册 |
| `tasks.py` | 有后台任务时 — 聚合各领域 task |
| `core/` | **必须有** — 配置、数据库、日志、异常 |
| `models/` | **必须有** — 所有 ORM 实体 |
| `repositories/` | **必须有** — 所有 ORM repository |
| `{domain}/` | 每个业务域一个目录 |

除上述条目外，若有不适合放入任何已有文件的逻辑，可新建命名反映其实际作用的文件。

## {domain}/ 领域目录

每个领域目录内只在有必要时创建文件：

| 文件 | 存在条件 | 职责 |
|------|----------|------|
| `endpoints.py` | 该领域有对外 HTTP 接口时 | 路由定义、参数校验、响应组装；不含业务逻辑 |
| `service.py` | **必须有** | 业务逻辑入口；endpoint 只调这里 |
| `client.py` | 需要调用外部 HTTP 接口时 | 请求 + 解析合并；对外只返回业务对象。接口较多时拆为多个具名 `*_client.py` 文件，与 service 同住领域目录 |
| `gateway.py` | 需要把多个数据源（DB + 多个 client）按业务边界封装为一组用例所需的访问能力时 | 仅做"组合调用"，不实现新的业务规则；与 service 同住领域目录 |
| `result_builder.py` | 需要把内部数据结构组装为 service / 用例返回结果时 | 集中"实体 → 输出对象"的转换逻辑 |
| `entities.py` | 领域内部需要专属数据结构时 | 用 `@dataclass(slots=True)`，不对外暴露；**不是 ORM 实体**，ORM 实体统一放顶层 `models/` |
| `schemas.py` | 领域有私有 Pydantic schema 时 | 请求/响应 schema；跨域共享放顶层 `schemas.py` |
| `tasks.py` | 领域有后台任务时 | 具体任务定义 |
| `*_reset_helper.py` 等辅助文件 | 有特定职责的领域内辅助逻辑时 | 文件名直接反映职责 |

## 领域内允许的子目录

当一个领域天然由若干**子领域**构成时（例如 `update/` 由"影院更新 + 电影更新"组成，
而"电影更新"又由"基础信息 + 豆瓣 + 详情"三种数据源构成），
可以使用与父领域同样的"领域优先"方式拆分子目录：

```
update/
├── service.py               # 聚合电影与影院更新能力
├── updater.py               # 聚合用例对象
├── entities.py              # 共享进度事件
├── result_builder.py        # 聚合结果组装
├── cinema_update_reset_helper.py
├── movie_update_reset_helper.py
├── cinema/                  # 子领域：影院更新
│   ├── client.py
│   ├── entities.py
│   └── updater.py
└── movie/                   # 子领域：电影更新
    ├── updater.py           # 聚合 base/douban/extra
    ├── base/                # 子-子领域：基础信息
    ├── douban/              # 子-子领域：豆瓣
    └── extra/               # 子-子领域：额外详情
```

**子目录命名规则**：

- 名字必须反映"业务子领域"，例如 `cinema/`、`movie/`、`base/`、`douban/`。
- 禁止按"角色"再分一层（如 `clients/`、`gateways/`、`services/`、`builders/`）。
  client 永远与 service 同住领域根。
- 子领域内部仍遵循"每个文件最多承担一个职责"，文件命名规范同上表。

**何时拆子领域**：

- 一个领域内逻辑明显可以按"数据源 / 子用例 / 资源"切分；或
- 领域文件超过约 8 个、且按主题分组后能让阅读路径变短。

非以上情况优先维持平级文件。
