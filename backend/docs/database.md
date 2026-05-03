# 数据库表

后端使用 SQLite，数据库路径由 `MOVIE_SCHEDULER_DB_PATH` 控制，默认写入 `backend/.runtime/movies.db`。表结构通过 Alembic 迁移维护，ORM 实体位于 `backend/src/app/models/`。

## 表清单

| 表 | ORM | Repository | 用途 |
|----|-----|------------|------|
| `cinemas` | `app/models/cinema.py` | `app/repositories/cinema.py` | 保存影院基础信息 |
| `movies` | `app/models/movie.py` | `app/repositories/movie.py` | 保存电影基础信息、豆瓣信息和热映状态 |
| `planning_items` | `app/models/planning.py` | `app/repositories/planning.py` | 保存单用户想看池和行程计划 |

## cinemas

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | `Integer` | 主键 | 影院 ID |
| `name` | `String(200)` | 非空 | 影院名称 |
| `address` | `String(500)` | 非空 | 影院地址 |
| `price` | `String(20)` | 可空 | 票价 |
| `allow_refund` | `Boolean` | 可空 | 是否允许退票 |
| `updated_at` | `DateTime` | 默认北京时间 | 更新时间 |

## movies

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | `Integer` | 主键 | 电影 ID |
| `title` | `String(200)` | 非空 | 电影标题 |
| `score` | `String(10)` | 可空 | 豆瓣评分文本 |
| `douban_url` | `String(255)` | 可空 | 豆瓣详情链接 |
| `genres` | `Text` | 可空 | 电影类型 |
| `actors` | `Text` | 可空 | 主演 |
| `release_date` | `String(20)` | 可空 | 上映日期 |
| `is_showing` | `Boolean` | 非空，默认 false | 是否正在热映 |
| `director` | `Text` | 可空 | 导演 |
| `country` | `String(100)` | 可空 | 制片国家 |
| `language` | `String(100)` | 可空 | 语言 |
| `duration` | `String(20)` | 可空 | 片长文本 |
| `description` | `Text` | 可空 | 剧情简介 |
| `first_showing_at` | `DateTime` | 可空 | 最近一次进入正在热映状态的时间 |
| `updated_at` | `DateTime` | 默认北京时间 | 更新时间 |

## planning_items

`planning_items` 是单用户计划表。`list_type` 取值为 `wish` 或 `schedule`，唯一约束为 `(list_type, show_key)`，允许同一场次同时出现在想看池和行程中。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | `Integer` | 主键，自增 | 计划条目 ID |
| `list_type` | `String(20)` | 非空，索引 | 列表类型：`wish` 或 `schedule` |
| `show_key` | `String(255)` | 非空 | 前端场次唯一键 |
| `movie_id` | `Integer` | 非空，索引 | 电影 ID |
| `movie_title` | `String(200)` | 非空 | 电影标题 |
| `date` | `String(20)` | 非空，索引 | 放映日期 |
| `time` | `String(20)` | 非空 | 放映时间 |
| `cinema_id` | `Integer` | 非空，索引 | 影院 ID |
| `cinema_name` | `String(200)` | 非空 | 影院名称 |
| `price` | `String(20)` | 可空 | 票价 |
| `duration_minutes` | `Integer` | 可空 | 片长分钟数 |
| `purchased` | `Boolean` | 非空，默认 false | 是否已购票；只对 `schedule` 生效 |
| `created_at` | `DateTime` | 默认北京时间 | 创建时间 |
| `updated_at` | `DateTime` | 默认北京时间 | 更新时间 |

