# Movie Scheduler

电影排片查询系统。项目包含 FastAPI 后端和 Vue 3 前端，使用 Docker Compose 作为推荐的本地开发启动方式。

## 技术栈

- 后端：Python 3.11、FastAPI、SQLAlchemy、Alembic、SQLite
- 前端：Vue 3、Vite、Element Plus、Pinia、Axios
- 开发环境：Docker Compose

## 目录结构

```text
movie_scheduler/
├── backend/              # 后端服务
│   ├── src/app/          # FastAPI 应用源码
│   ├── migrations/       # Alembic 数据库迁移
│   ├── docs/             # 后端结构、数据库、架构规范、API 文档
│   ├── scripts/          # 启动和辅助脚本
│   ├── .env.example      # 后端环境变量模板
│   └── .runtime/         # 本地运行时文件，包含 SQLite 数据库
├── frontend/             # Vue 前端
│   ├── docs/             # 前端规范文档
│   ├── src/
│   └── package.json
├── docs/                 # 跨端开发流程文档
└── docker-compose.yml    # 本地开发编排
```

## 快速启动

首次启动前复制环境变量文件：

```powershell
Copy-Item backend\.env.example backend\.env
```

启动前后端服务：

```powershell
docker compose up -d --build
```

访问地址：

- 前端：http://localhost:5173
- 后端：http://localhost:8000
- API 文档：http://localhost:8000/docs

查看服务状态和日志：

```powershell
docker compose ps
docker compose logs -f
docker compose logs -f backend
docker compose logs -f frontend
```

停止服务：

```powershell
docker compose down
```

## Docker 挂载说明

开发环境中，后端容器会把本地目录挂载进容器：

```yaml
volumes:
  - ./backend:/app
  - ./backend/.runtime:/app/.runtime
```

因此容器内的 `/app/.runtime/movies.db` 对应本地文件：

```text
backend/.runtime/movies.db
```

容器读写数据库时，实际读写的是本地这份 SQLite 文件。执行 `docker compose down` 不会删除数据库；删除 `backend/.runtime/movies.db` 才会清空本地数据库文件。

当前 SQLite 数据库保存影院、电影、豆瓣补充信息，以及单用户的想看池和行程计划。

## 环境变量

后端配置位于 `backend/.env`，模板见 `backend/.env.example`。

常用配置：

```env
MOVIE_SCHEDULER_LOG_LEVEL=debug
MOVIE_SCHEDULER_DB_PATH=.runtime/movies.db
MOVIE_SCHEDULER_DEFAULT_CITY_ID=10
MOVIE_SCHEDULER_CITY_MAPPING={"北京":1,"上海":10}
MOVIE_SCHEDULER_YEAR_THRESHOLD=2020
MOVIE_SCHEDULER_TIMEOUT=60
MOVIE_SCHEDULER_DOUBAN_API_BASE_URL=http://localhost:8085
MOVIE_SCHEDULER_HOST=0.0.0.0
MOVIE_SCHEDULER_PORT=8000
MOVIE_SCHEDULER_CORS_ORIGINS=["*"]
```

其中 `MOVIE_SCHEDULER_CITY_MAPPING` 控制前端可选城市及后端允许的城市 ID；
`MOVIE_SCHEDULER_DEFAULT_CITY_ID` 必须存在于该映射值中。Docker 环境中后端工作目录是 `/app`，
所以 `.runtime/movies.db` 会解析为 `/app/.runtime/movies.db`。
`MOVIE_SCHEDULER_DOUBAN_API_BASE_URL` 指向豆瓣信息补充服务，代码读取时会自动移除末尾 `/`。

## 主要功能

- 获取城市列表：`GET /api/cities`
- 更新影院数据：`GET /api/update/cinema-stream?city_id=10&force_update_all=false`
- 更新电影数据：`GET /api/update/movie-stream?city_id=10&force_update_all=false`
- 选择待查询电影：`POST /api/movies/select`
- 获取豆瓣信息：`POST /api/movies/{movie_id}/fetch-douban`
- 拉取排片数据：`GET /api/shows/fetch-stream?movie_ids=1,2&city_id=10`
- 读取/保存单用户排片计划：`GET /api/planning` / `PUT /api/planning`

部分接口使用 SSE 流式返回，前端会逐步展示更新进度。

## 本地非 Docker 开发

后端：

```powershell
cd backend
uv run alembic upgrade head
uv run python -m app.main
```

前端：

```powershell
cd frontend
npm install
npm run dev
```

前端开发服务器默认会把 `/api` 代理到 `http://localhost:8000`。Docker Compose 中会通过 `VITE_API_PROXY_TARGET=http://backend:8000` 改为容器内服务地址。

## 测试

后端测试：

```powershell
cd backend
uv run pytest
```

## 常见问题

### backend/.env not found

首次启动前需要复制环境变量模板：

```powershell
Copy-Item backend\.env.example backend\.env
```

### Docker 拉取基础镜像失败

如果构建时卡在 `python:3.11-slim` 或 `node:20-alpine`，通常是 Docker Hub 网络访问问题。可以先手动测试：

```powershell
docker pull python:3.11-slim
docker pull node:20-alpine
```

必要时在 Docker Desktop 中配置 registry mirror 后重试。

### shell 脚本在容器中报 Illegal option

Linux 容器执行 `.sh` 文件需要 LF 行尾。仓库通过 `.gitattributes` 固定了：

```gitattributes
*.sh text eol=lf
```

如果仍然遇到类似问题，重新检出或手动把脚本转换为 LF。

## 更多文档

- 后端领域地图：[backend/docs/structure.md](backend/docs/structure.md)
- 后端数据库：[backend/docs/database.md](backend/docs/database.md)
- 后端架构规范：[backend/docs/architecture.md](backend/docs/architecture.md)
- 后端编码规范：[backend/docs/conventions.md](backend/docs/conventions.md)
- 后端测试规范：[backend/docs/testing.md](backend/docs/testing.md)
- API 契约：[backend/docs/api.md](backend/docs/api.md)
- 前端规范：[frontend/docs/frontend.md](frontend/docs/frontend.md)
- 开发流程：[docs/workflow.md](docs/workflow.md)
