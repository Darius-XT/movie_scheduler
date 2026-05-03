# 架构规范

本文档仅对通用项目规范进行抽象总结，不指示任何具体文件。后端代码位于 `backend/src/app/`，采用**领域优先**组织：顶层放应用装配、技术基础设施、数据访问层和业务领域；业务代码按领域目录拆分。

## 顶层组织规范

顶层只放应用级装配、跨领域共享能力和领域目录。不要预建空文件；只有出现对应职责时才创建文件。

| 文件 / 目录 | 创建条件 | 职责 |
|------------|----------|------|
| `__init__.py` | Python package 目录 | 包标记；不放业务逻辑 |
| `app.py` | 必须有 | 创建 FastAPI 实例，注册路由、中间件、异常处理器 |
| `main.py` | 需要独立启动入口时 | 调用 `uvicorn.run` |
| `routes.py` | 必须有 | 聚合所有领域 router，统一挂载 `/api` 前缀 |
| `error_handlers.py` | 必须有 | 注册全局异常处理器，输出统一错误响应 |
| `schemas.py` | 存在跨领域共享 schema 时 | 放跨领域复用的 Pydantic schema，例如统一响应 envelope |
| `core/` | 必须有 | 放技术基础设施，不放业务规则 |
| `models/` | 存在数据库表时 | 放 SQLAlchemy ORM 实体，按资源或表主题拆文件 |
| `repositories/` | 存在数据库读写时 | 放 ORM repository，按资源或聚合根拆文件 |
| `{domain}/` | 存在独立业务领域时 | 放该领域的接口、业务逻辑、外部访问和内部数据结构 |

`core/` 下文件按基础设施职责命名：

| 文件 | 职责 |
|------|------|
| `bootstrap.py` | 应用启动前后的初始化、预热或资源准备 |
| `config.py` | 配置读取、环境变量映射、配置对象 |
| `database.py` | 数据库 engine、session、连接生命周期 |
| `exceptions.py` | 应用级异常类型 |
| `file_saver.py` | 通用文件保存能力 |
| `logger.py` | 日志配置与 logger 获取 |

`models/` 与 `repositories/` 使用相同的资源命名方式。ORM 实体统一放 `models/`，数据库访问统一放 `repositories/`，领域目录通过 service 或 gateway 使用它们。

## 领域目录规范

领域目录代表一个业务边界。目录内文件按职责拆分，endpoint 只负责 HTTP 层，service 承担业务入口，client/gateway/repository 负责访问能力，builder/enricher/helper 负责明确的组装或辅助职责。

| 文件 | 创建条件 | 职责 |
|------|----------|------|
| `__init__.py` | Python package 目录 | 包标记；不放业务逻辑 |
| `endpoints.py` | 领域有对外 HTTP 接口时 | 定义路由、解析参数、调用 service、组装统一响应；不写业务逻辑 |
| `schemas.py` | 领域有请求或响应 schema 时 | 放该领域私有 Pydantic schema；跨领域共享 schema 放顶层 `schemas.py` |
| `service.py` | 领域存在业务用例时 | 业务逻辑入口；对 endpoint 提供稳定方法 |
| `entities.py` | 领域内部需要专属数据结构时 | 放 dataclass、TypedDict、Enum 等内部业务对象；不是 ORM 实体 |
| `client.py` | 领域需要访问单一外部数据源或外部接口时 | 封装请求、解析和重试；对外只返回业务对象 |
| `*_client.py` | 同一领域存在多个外部访问职责时 | 以业务含义命名的 client；与 `service.py` 同住领域目录，不再包一层 `clients/` |
| `gateway.py` | 需要组合 DB、repository、client 或多个数据源时 | 封装访问编排；不实现新的业务规则 |
| `result_builder.py` | 需要集中组装 service 返回结果时 | 把内部实体、ORM 对象或中间结果转换为输出对象 |
| `fetcher.py` | 存在批量抓取、流式抓取或抓取流程编排时 | 组织抓取步骤和进度事件；不直接承担 HTTP endpoint 职责 |
| `request_helper.py` | 多个 client 共享请求细节时 | 放同领域内复用的请求头、请求执行、通用解析或日志辅助 |
| `updater.py` | 领域存在数据更新流程时 | 编排更新步骤、进度状态和更新结果 |
| `enricher.py` | 需要为已有数据补充外部详情时 | 聚合补充信息并返回增强后的业务对象 |
| `*_reset_helper.py` | 需要隔离特定重置或清理逻辑时 | 放命名明确的辅助流程，避免 service/updater 过重 |

领域内新增文件时，优先选择上表已有职责。确实不匹配时，可以新增命名能直接表达职责的文件；新增后应同步补充本规范。

## 领域子目录规范

领域子目录只用于表达**业务子领域**，子目录内部与父领域遵循同一套文件规范。

适合拆子目录的情况：

- 逻辑可以稳定地按数据源、子用例或资源拆分。
- 平级文件数量明显变多，按主题分组能缩短阅读路径。
- 子目录名称能表达业务含义。

不适合拆子目录的情况：

- 只是为了按角色分层，例如 `clients/`、`gateways/`、`services/`、`builders/`。
- 只有一两个文件，拆分后反而增加跳转成本。

