# 项目结构说明

本文档描述当前已经落地的项目结构，以及后续在复杂度上升时再考虑引入的扩展层。目标是让目录和真实职责保持一致，避免为了“看起来完整”而提前堆叠结构。

## 当前复杂度判断

当前项目属于中小型 Python Web 项目，特点是：

- 一个 FastAPI HTTP 服务入口
- 一个 Vue 前端入口
- 明确的数据抓取与更新流程
- 本地 SQLite 持久化
- 尚未形成独立 worker 运行边界

基于这个复杂度，后端保留 `api / services / use_cases / repositories / models / schemas / core` 已经足够，不额外保留未启用的 `workers` 和 `shared` 目录。

## 当前后端结构

- `backend/src/app/api/v1`
  负责 FastAPI V1 路由，只处理请求解析、响应组织和路由聚合。
- `backend/src/app/services`
  作为应用服务门面，对外提供稳定业务入口，只做参数规范化、异步边界处理和用例调用。
- `backend/src/app/use_cases`
  承载完整业务流程编排，例如电影筛选、信息更新、场次抓取。
- `backend/src/app/repositories`
  负责数据库读写，不承载业务规则。
- `backend/src/app/models`
  数据库模型定义。
- `backend/src/app/schemas`
  API 输入输出契约。
- `backend/src/app/core`
  配置、日志、数据库连接、异常、调试文件保存等基础设施能力。

## 后端依赖方向

默认遵循以下依赖方向：

```text
api -> services -> use_cases -> repositories
services -> core
repositories -> models
api -> schemas
```

约束如下：

- `api` 不写业务编排
- `services` 不直接承载复杂抓取流程
- `use_cases` 负责完整业务流程
- `repositories` 只负责持久化访问
- `core` 只放基础设施，不放业务规则
- `models` 与 `schemas` 分离，前者面向数据库，后者面向接口契约

## 当前前端结构

- `frontend/src/pages`
  页面级组件，与路由一一对应。
- `frontend/src/api`
  前端 HTTP 请求封装，统一调用后端 `/api/v1` 接口。
- `frontend/src/main.js`
  前端应用入口。
- `frontend/src/App.vue`
  前端根组件。

当前前端规模还不需要强制拆出 `components / store / utils`。只有在真正出现复用组件、共享状态或跨页面工具函数后，再引入对应目录。

## 暂不引入的目录

以下目录不是当前必需结构，等复杂度上来再增加：

- `backend/src/workers`
  只有在出现独立后台任务进程、定时任务执行单元或异步消费端时再引入。
- `backend/src/shared`
  只有在 `app` 与独立运行边界之间确实共享大量代码时再引入。
- `frontend/src/components`
  只有在出现稳定复用 UI 组件时再引入。
- `frontend/src/store`
  只有在出现全局状态管理需求时再引入。
- `frontend/src/utils`
  只有在出现明确跨页面复用工具函数时再引入。

## 运行方式

- 后端开发与测试统一在仓库根目录执行，但使用 `backend` 项目环境：
  - `uv run --project backend pytest`
  - `uv run --project backend python -m app.main`
- 数据库表结构通过 Alembic 迁移维护，不依赖应用启动时自动建表
- 前端通过 Vite 开发服务器启动
- 根级 `docker-compose.yml` 负责统一编排前后端服务
