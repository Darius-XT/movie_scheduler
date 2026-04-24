# Movie Scheduler — 项目规范

## 技术栈

- **后端**: Python 3.11+, FastAPI, SQLAlchemy, Alembic, SQLite
- **前端**: Vue 3 (`<script setup>`), Element Plus, Axios, Pinia
- **包管理**: uv（后端），npm（前端）
- **运行**: Docker Compose（开发环境）

## 规范文档索引

- [后端架构](docs/backend-architecture.md) — 目录结构、领域模块、文件职责
- [后端编码规范](docs/backend-conventions.md) — 命名、类型、异步、依赖注入、数据传递等
- [后端测试规范](docs/backend-testing.md) — 测试目录结构、两层分工、依赖隔离约定
- [前端规范](docs/frontend.md) — 组件组织、状态管理、API 层
- [开发流程](docs/workflow.md) — 测试、Git 规范、启动命令、调试样本

## 后端禁止事项

- endpoint 中不写业务逻辑
- client 对外只返回业务对象，不暴露 HTTP 状态码或原始响应
- 模块间循环依赖
- 在源代码中硬编码 URL、ID 等配置值（放 `.env` 或调试常量块）
- 提交 `.runtime/` 下的 `.db` 文件
- 用 `cast()` 绕过类型错误（只允许用于动态属性推断）
- 引入 API 版本目录（v1/v2），永远只有一个版本
- 在 async 函数中直接调用同步 IO（必须用 `asyncio.to_thread()`）
- 在领域目录内单独建 `clients/`、`gateway/` 这种"按角色再分一层"的子目录——
  client 与 service 同住领域根；单文件 `gateway.py` 是允许的
- API 响应必须使用统一的 `success/data` 包装（参见 [后端编码规范](docs/backend-conventions.md#api-响应格式)）

## 前端禁止事项

- 组件直接使用 `axios` / `fetch`——所有 API 调用必须封装在 `src/api/index.js`
- 在组件中拼接绝对 URL（`baseURL` 与路径分离）
- 在组件中重复实现已存在于 Pinia store 的状态
- 引入与 `/api/v?` 形式的版本前缀相关的硬编码（永远只有 `/api`）

> 详细前端约定见 [前端规范](docs/frontend.md)。
