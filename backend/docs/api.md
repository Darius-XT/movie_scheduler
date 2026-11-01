# API 路由

本文档仅对项目中包括的所有 api 路由进行总结,不包括其他内容。所有路由统一挂载在 `/api` 下,不使用 `/api/v1` 等版本前缀。普通 JSON 接口使用 `success/data` 响应包装;SSE 接口返回 `text/event-stream`。

## 路由总览

| Feature | 方法 | 路径 | 类型 | 用途 |
|---------|------|------|------|------|
| city | `GET` | `/api/cities` | JSON | 获取可选城市列表 |
| backup | `GET` | `/api/backups/export` | JSON 附件 | 导出四张业务表的完整备份 |
| backup | `POST` | `/api/backups/import` | JSON | 校验备份后全量覆盖四张业务表，须明确确认 |
| cinema | `GET` | `/api/cinemas/update-stream` | SSE | 流式更新影院数据(手动触发,增量) |
| movie | `POST` | `/api/movies/select` | JSON | 按上映状态筛选电影 |
| movie | `GET` | `/api/movies/wished` | JSON | 读取全部想看电影 |
| movie | `POST` | `/api/movies/manual` | JSON | 手动添加电影并加入想看 |
| movie | `PATCH` | `/api/movies/{movie_id}/wished` | JSON | 更新单部电影的想看状态 |
| movie | `PATCH` | `/api/movies/{movie_id}/label` | JSON | 设置或取消电影标签 |
| movie | `PATCH` | `/api/movies/{movie_id}/channels` | JSON | 保存单个观看渠道，空列表表示暂无 |
| movie | `PATCH` | `/api/movies/{movie_id}/viewing-location` | JSON | 保存或取消观看地点分类 |
| movie | `GET` | `/api/movies/update-status` | JSON | 读取电影信息上次自动更新时间 |
| movie | `POST` | `/api/movies/{movie_id}/update-douban` | JSON | 为单部电影抓取豆瓣评分与详情链接 |
| plan | `GET` | `/api/plan` | JSON | 读取单用户行程列表 |
| plan | `PUT` | `/api/plan/items` | JSON | 全量替换单用户行程列表 |
| show | `GET` | `/api/shows` | JSON | 读取想看电影的全部或单部场次(后端每天北京时间 0 点启动自动更新) |
| show | `GET` | `/api/shows/update-stream` | SSE | `city_id` 指定城市；可选 `movie_id` 仅更新该部想看且归类为影院看的非手动电影，省略则更新全部影院看电影。失败返回 error 并保留原场次 |

电影和场次更新的 SSE `progress` 中，`current/total` 表示当前阶段已处理数，而非全任务百分比。未知总量时为 `null`；电影列表按分页、详情按部数报告，场次在每个影院任务结束后推送 `fetching_cinema_shows`（消息包含电影名、已处理影院数和失败数）。写入阶段使用 `persisting_shows`，整轮成功以 `complete` 为准。

## Backup

- `GET /api/backups/export` 返回 `success/data` 包装的 JSON 附件，文件名为 `movie-scheduler-时间戳.json`，设置 `Cache-Control: no-store`。
- `data` 包含 `application: "movie-scheduler"`、`format_version: 1`、`exported_at`，以及 `movies`、`cinemas`、`movie_shows`、`planning_items` 四个必填数组；各记录保留数据库全部字段、ID 和时间。格式版本仅用于备份文件兼容性，不是 API 版本。
- `POST /api/backups/import` 请求为 `{ "backup": <完整导出文件内容>, "confirm_replace": true }`。不接受缺表或缺字段的部分备份；未知字段、错误类型或不兼容版本返回 422；未确认、重复 ID/唯一键、标签冲突返回 400。
- 导入在单个事务中全量替换，不做合并；空数组会清空对应表，任意写入失败回滚全部修改。成功响应为 `{ "success": true, "data": { "movies": 0, "cinemas": 0, "movie_shows": 0, "planning_items": 0 } }`，数字为实际导入条数。
- 只备份业务数据，不包含 Alembic 版本表、环境配置、Cookie、调试文件或前端缓存。导入前应先备份，并等待更新任务及行程保存完成，暂停其他设备写入；恢复后刷新页面。导入不会取消已经在运行的抓取任务，也不会关闭定时更新。

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

电影更新只为缺少导演、国家、语言、时长或简介的电影补充详情，“暂无”占位值仍视为缺失。
电影、影院与场次更新遇猫眼验证页时返回 SSE `error`，说明本轮剩余抓取已停止；电影更新不写入本轮完成时间，场次更新保留原有场次和更新时间。

| 方法 | 路径 | 参数 / 请求体 | 返回 |
|------|------|---------------|------|
| `POST` | `/api/movies/select` | body: `{"selection_mode": "showing" \| "upcoming" \| "all"}` | `{"success": true, "data": {"movies": [...]}}` |
| `GET` | `/api/movies/wished` | 无 | `{"success": true, "data": {"movies": [...]}}` |
| `PATCH` | `/api/movies/{movie_id}/wished` | path: `movie_id`; body: `{"is_wished": true \| false}` | `{"success": true, "data": {"movie": {...}}}` |
| `PATCH` | `/api/movies/{movie_id}/label` | body: `{"label": "wished" \| "skipped" \| "watched" \| null}` | `{"success": true, "data": {"movie": {...}}}` |
| `PATCH` | `/api/movies/{movie_id}/channels` | body: `{"channels": ["bilibili"]}`，最多一个，可选 bilibili/tegou/dytt/tencent/iqiyi/youku/youtube | `{"success": true, "data": {"movie": {...}}}` |
| `PATCH` | `/api/movies/{movie_id}/viewing-location` | body: `{"viewing_location": "home" \| "cinema" \| null}` | `{"success": true, "data": {"movie": {...}}}` |
| `GET` | `/api/movies/update-status` | 无 | `{"success": true, "data": {"last_updated_at": "..." \| null}}` |
| `POST` | `/api/movies/{movie_id}/update-douban` | path: `movie_id` | `{"success": true, "data": {"score": "...", "douban_url": "..."}}` |

电影信息与想看电影场次由同一个调度任务串行执行: 每天北京时间 0 点自动跑一次,服务启动时只注册任务,不立即执行。前端通过轮询 `GET /api/movies/update-status` 感知更新时间变化,自动重新筛选电影列表。

## Plan

| 方法 | 路径 | 参数 / 请求体 | 返回 |
|------|------|---------------|------|
| `GET` | `/api/plan` | 无 | `{"success": true, "data": {"schedule_items": [...]}}` |
| `PUT` | `/api/plan/items` | body: `{"schedule_items": [...]}` | `{"success": true, "data": {"schedule_items": [...]}}` |

## Show

手动更新、定时更新和单片自动更新只抓取想看列表中 `viewing_location=cinema` 且具有猫眼编号的电影。移入“影院看”会触发单片更新；“家里看”和“未分类”不抓取场次。

| 方法 | 路径 | 参数 | 返回 |
|------|------|------|------|
| `GET` | `/api/shows` | 无 | `{"success": true, "data": {"movies": [{"movie_id": 1, "shows": [{...}]}], "last_fetched_at": "..."}}` |
| `GET` | `/api/shows` | query: `movie_id=1` | `{"success": true, "data": {"movies": [{"movie_id": 1, "shows": [...]}], "last_fetched_at": "..."}}` |

场次更新 SSE 的 `complete.data` 包含 `added`、`removed`、`movies_with_shows`、`failed_movies` 和 `last_fetched_at`。
`failed_movies` 表示抓取不完整且保留旧数据的电影数量；全部抓取失败时返回 `error` 事件，不更新原有场次或抓取时间。

影院数据每月 1 日北京时间 0 点自动更新默认城市,也支持手动更新。月初按影院、电影信息、场次的顺序串行执行。

排片数据由后端每天北京时间 0 点启动的自动更新任务刷新,在电影信息更新之后执行;服务启动时不立即刷新。加入想看时后端会后台刷新该电影场次,前端可用 `movie_id` 参数轮询单部电影。
