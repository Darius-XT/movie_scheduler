# API 路由

本文档仅对项目中包括的所有api路由进行总结，不包括任何其他内容。所有路由统一挂载在 `/api` 下，不使用 `/api/v1` 等版本前缀。普通 JSON 接口使用 `success/data` 响应包装；SSE 接口返回 `text/event-stream`。

## 路由总览

| 领域 | 方法 | 路径 | 类型 | 用途 |
|------|------|------|------|------|
| 城市 | `GET` | `/api/cities` | JSON | 获取可选城市列表 |
| 电影 | `POST` | `/api/movies/select` | JSON | 按上映状态筛选电影 |
| 电影 | `POST` | `/api/movies/{movie_id}/fetch-douban` | JSON | 为单部电影抓取豆瓣评分与详情链接 |
| 排片 | `GET` | `/api/shows/fetch-stream` | SSE | 流式抓取选中电影的排片 |
| 更新 | `GET` | `/api/update/movie-stream` | SSE | 流式更新电影基础信息与详情 |
| 更新 | `GET` | `/api/update/cinema-stream` | SSE | 流式更新影院数据 |
| 计划 | `GET` | `/api/planning` | JSON | 读取单用户想看池与行程计划 |
| 计划 | `PUT` | `/api/planning` | JSON | 全量替换单用户想看池与行程计划 |

## 基础数据

| 方法 | 路径 | 参数 / 请求体 | 返回 |
|------|------|---------------|------|
| `GET` | `/api/cities` | 无 | `{"success": true, "data": {"cities": [...]}}` |

## 电影

| 方法 | 路径 | 参数 / 请求体 | 返回 |
|------|------|---------------|------|
| `POST` | `/api/movies/select` | body: `{"selection_mode": "showing" \| "upcoming" \| "all"}` | `{"success": true, "data": {"movies": [...]}}` |
| `POST` | `/api/movies/{movie_id}/fetch-douban` | path: `movie_id` | `{"success": true, "data": {"score": "...", "douban_url": "..."}}` |

## 排片

| 方法 | 路径 | 参数 | 返回 |
|------|------|------|------|
| `GET` | `/api/shows/fetch-stream` | query: `movie_ids=1,2`；可选 `city_id=10` | SSE 事件流 |

## 更新

| 方法 | 路径 | 参数 | 返回 |
|------|------|------|------|
| `GET` | `/api/update/movie-stream` | query: `city_id=10`；可选 `force_update_all=false` | SSE 事件流 |
| `GET` | `/api/update/cinema-stream` | query: `city_id=10`；可选 `force_update_all=false` | SSE 事件流 |

## 计划

| 方法 | 路径 | 参数 / 请求体 | 返回 |
|------|------|---------------|------|
| `GET` | `/api/planning` | 无 | `{"success": true, "data": {"wish_pool": [...], "schedule_items": [...]}}` |
| `PUT` | `/api/planning` | body: `{"wish_pool": [...], "schedule_items": [...]}` | `{"success": true, "data": {"wish_pool": [...], "schedule_items": [...]}}` |

