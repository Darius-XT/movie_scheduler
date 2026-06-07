# API 路由

本文档仅对项目中包括的所有 api 路由进行总结,不包括其他内容。所有路由统一挂载在 `/api` 下,不使用 `/api/v1` 等版本前缀。普通 JSON 接口使用 `success/data` 响应包装;SSE 接口返回 `text/event-stream`。

## 路由总览

| Feature | 方法 | 路径 | 类型 | 用途 |
|---------|------|------|------|------|
| city | `GET` | `/api/cities` | JSON | 获取可选城市列表 |
| cinema | `GET` | `/api/cinemas/update-stream` | SSE | 流式更新影院数据(手动触发,增量) |
| movie | `POST` | `/api/movies/select` | JSON | 按上映状态筛选电影 |
| movie | `GET` | `/api/movies/wished` | JSON | 读取全部想看电影 |
| movie | `PATCH` | `/api/movies/{movie_id}/wished` | JSON | 更新单部电影的想看状态 |
| movie | `GET` | `/api/movies/update-status` | JSON | 读取电影信息上次自动更新时间 |
| movie | `POST` | `/api/movies/{movie_id}/update-douban` | JSON | 为单部电影抓取豆瓣评分与详情链接 |
| plan | `GET` | `/api/plan` | JSON | 读取单用户行程列表 |
| plan | `PUT` | `/api/plan/items` | JSON | 全量替换单用户行程列表 |
| show | `GET` | `/api/shows` | JSON | 读取想看电影的全部或单部场次(后端每小时自动刷新) |

## City

| 方法 | 路径 | 参数 / 请求体 | 返回 |
|------|------|---------------|------|
| `GET` | `/api/cities` | 无 | `{"success": true, "data": {"cities": [...]}}` |

## Cinema

| 方法 | 路径 | 参数 | 返回 |
|------|------|------|------|
| `GET` | `/api/cinemas/update-stream` | query: `city_id=10` | SSE 事件流(手动触发,增量) |

SSE 事件:`{"type": "progress", "stage": "...", "message": "...", "city_id": ..., "page": ...}` → `{"type": "complete", "data": {"success_count": ..., "failure_count": ...}}` → 结束;失败时一帧 `{"type": "error", "error": "..."}`。

## Movie

| 方法 | 路径 | 参数 / 请求体 | 返回 |
|------|------|---------------|------|
| `POST` | `/api/movies/select` | body: `{"selection_mode": "showing" \| "upcoming" \| "all"}` | `{"success": true, "data": {"movies": [...]}}` |
| `GET` | `/api/movies/wished` | 无 | `{"success": true, "data": {"movies": [...]}}` |
| `PATCH` | `/api/movies/{movie_id}/wished` | path: `movie_id`; body: `{"is_wished": true \| false}` | `{"success": true, "data": {"movie": {...}}}` |
| `GET` | `/api/movies/update-status` | 无 | `{"success": true, "data": {"last_updated_at": "..." \| null}}` |
| `POST` | `/api/movies/{movie_id}/update-douban` | path: `movie_id` | `{"success": true, "data": {"score": "...", "douban_url": "..."}}` |

电影信息与想看电影场次由同一个调度任务串行执行: 每个整点(分钟 0)自动跑一次,服务启动时立即跑一次。前端通过轮询 `GET /api/movies/update-status` 感知更新时间变化,自动重新筛选电影列表。

## Plan

| 方法 | 路径 | 参数 / 请求体 | 返回 |
|------|------|---------------|------|
| `GET` | `/api/plan` | 无 | `{"success": true, "data": {"schedule_items": [...]}}` |
| `PUT` | `/api/plan/items` | body: `{"schedule_items": [...]}` | `{"success": true, "data": {"schedule_items": [...]}}` |

## Show

| 方法 | 路径 | 参数 | 返回 |
|------|------|------|------|
| `GET` | `/api/shows` | 无 | `{"success": true, "data": {"movies": [{"movie_id": 1, "shows": [{...}]}], "last_fetched_at": "..."}}` |
| `GET` | `/api/shows` | query: `movie_id=1` | `{"success": true, "data": {"movies": [{"movie_id": 1, "shows": [...]}], "last_fetched_at": "..."}}` |

排片数据由后端每个整点(分钟 0)自动刷新一次,服务启动时也会立即刷一次。加入想看时后端会后台刷新该电影场次,前端可用 `movie_id` 参数轮询单部电影。
