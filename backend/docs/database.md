# 数据库表

后端使用 SQLite,数据库路径由 `MOVIE_SCHEDULER_DB_PATH` 控制,默认写入 `backend/.runtime/movies.db`。表结构通过 Alembic 迁移维护,ORM 实体按 feature 所属拆分到 `features/{owner}/models.py`。

## 表清单

| 表 | ORM | Repository | 用途 |
|----|-----|------------|------|
| `cinemas` | `features/cinema/models.py` | `features/cinema/repository.py` | 保存影院基础信息 |
| `movies` | `features/movie/models.py` | `features/movie/repository.py` | 保存电影基础信息、豆瓣信息、热映状态、想看状态、场次刷新时间 |
| `movie_shows` | `features/show/models.py` | `features/show/repository.py` | 想看电影的场次缓存(每小时自动刷新) |
| `planning_items` | `features/plan/models.py` | `features/plan/repository.py` | 保存单用户行程(场次维度) |

所有 ORM 共享同一个 `Base = declarative_base()`,定义在 `movie_scheduler/core/db.py`。Alembic `migrations/env.py` 在读取 `Base.metadata` 之前显式 import 各 feature 的 `models` 模块,触发表注册。

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
| `is_showing` | `Boolean` | 非空,默认 false | 是否正在热映 |
| `is_wished` | `Boolean` | 非空,默认 false | 是否加入想看(电影维度) |
| `director` | `Text` | 可空 | 导演 |
| `country` | `String(100)` | 可空 | 制片国家 |
| `language` | `String(100)` | 可空 | 语言 |
| `duration` | `String(20)` | 可空 | 片长文本 |
| `description` | `Text` | 可空 | 剧情简介 |
| `first_showing_at` | `DateTime` | 可空 | 最近一次进入正在热映状态的时间 |
| `updated_at` | `DateTime` | 默认北京时间 | 更新时间 |
| `shows_updated_at` | `DateTime` | 可空 | 场次最近一次刷新完成时间 |

## movie_shows

`movie_shows` 是想看电影的场次缓存,由后端定时任务每小时刷新。同一电影/影院/日期/时间组合保证唯一。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | `Integer` | 主键,自增 | 场次 ID |
| `movie_id` | `Integer` | 非空,索引 | 电影 ID |
| `cinema_id` | `Integer` | 非空,索引 | 影院 ID |
| `cinema_name` | `String(200)` | 非空 | 影院名称(快照) |
| `date` | `String(20)` | 非空,索引 | 放映日期 |
| `time` | `String(20)` | 非空 | 放映时间 |
| `price` | `String(20)` | 可空 | 票价 |
| `created_at` | `DateTime` | 默认北京时间 | 创建时间 |

唯一约束: `(movie_id, cinema_id, date, time)`。

## planning_items

`planning_items` 是单用户行程表(场次维度),唯一约束为 `show_key`。想看状态由 `movies.is_wished` 承载,不在此表。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | `Integer` | 主键,自增 | 计划条目 ID |
| `show_key` | `String(255)` | 非空,唯一 | 前端场次唯一键 |
| `movie_id` | `Integer` | 非空,索引 | 电影 ID(手动添加的行程为 0) |
| `movie_title` | `String(200)` | 非空 | 电影标题 |
| `date` | `String(20)` | 非空,索引 | 放映日期 |
| `time` | `String(20)` | 非空 | 放映时间 |
| `cinema_id` | `Integer` | 非空,索引 | 影院 ID(手动添加的行程为 0) |
| `cinema_name` | `String(200)` | 非空 | 影院名称 |
| `price` | `String(20)` | 可空 | 票价 |
| `duration_minutes` | `Integer` | 可空 | 片长分钟数 |
| `purchased` | `Boolean` | 非空,默认 false | 是否已购票 |
| `created_at` | `DateTime` | 默认北京时间 | 创建时间 |
| `updated_at` | `DateTime` | 默认北京时间 | 更新时间 |
