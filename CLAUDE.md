# Movie Scheduler — 项目规范

## 技术栈

- **后端**: Python 3.11+, FastAPI, SQLAlchemy, Alembic, SQLite
- **前端**: Vue 3 (`<script setup>`), Element Plus, Axios, Pinia
- **包管理**: uv(后端), npm(前端)
- **运行**: Docker Compose(开发环境)

## 规范文档索引

- [后端架构](backend/docs/architecture.md) — 包结构、目录职责、文件命名
- [后端领域地图](backend/docs/structure.md) — 当前 features/ 业务边界
- [后端数据库](backend/docs/database.md) — SQLite 表、字段、约束
- [后端编码规范](backend/docs/conventions.md) — 命名、类型、异步、依赖注入、数据传递
- [后端测试规范](backend/docs/testing.md) — 测试目录结构、依赖隔离
- [API 契约](backend/docs/api.md) — JSON 接口、SSE 事件
- [前端规范](frontend/docs/frontend.md) — 组件、状态管理、API 层
- [开发流程](docs/workflow.md) — 测试、Git、启动命令

## 后端禁止事项

- `movie_scheduler/` 顶层只允许 `__main__.py`、`app.py`、`config.py`、`core/`、`shared/`、`features/`
- `core/` 只放基础设施(db.py、exceptions.py、logging.py、scheduler.py),不放业务规则
- 每个 feature 只允许这些文件: `router.py` `schemas.py` `models.py` `service.py` `repository.py`(以及模板列出的 `dependencies.py` `exceptions.py` `constants.py` 在真有需要时新增);**不允许** `helper.py` `builder.py` `client.py` `gateway.py` `fetcher.py` `enricher.py` 等角色文件
- 多个数据源/业务子领域用**嵌套子目录**表达,例如 `features/movie/{update_base, update_douban, update_extra}/`,子目录内同样遵守上面的文件清单
- endpoint(router)只做参数解析、调用 service、组装统一响应,不写业务逻辑
- 模块间循环依赖
- 在源代码中硬编码 URL、ID 等配置值(放 `.env` 或调试常量块)
- 提交 `.runtime/` 下的 `.db` 文件
- 用 `cast()` 绕过类型错误(只允许用于动态属性推断)
- 引入 API 版本目录(v1/v2),永远只有一个版本
- 在 async 函数中直接调用同步 IO(必须用 `asyncio.to_thread()`)
- API 响应必须使用统一的 `success/data` 包装(参见 [后端编码规范](backend/docs/conventions.md#api-响应格式))

## 前端禁止事项

- 组件直接使用 `axios` / `fetch`——所有 API 调用必须封装在 `src/api/index.js`
- 在组件中拼接绝对 URL(`baseURL` 与路径分离)
- 在组件中重复实现已存在于 Pinia store 的状态
- 引入与 `/api/v?` 形式的版本前缀相关的硬编码(永远只有 `/api`)

> 详细前端约定见 [前端规范](frontend/docs/frontend.md)。
