# 当前领域地图

本文记录后端当前的业务边界与各 feature 目录职责。通用结构规则见 [architecture.md](architecture.md)。具体文件列表以 `backend/src/movie_scheduler/` 源码为准,本文不维护完整目录树。

## features/

| 目录 | 拥有的表 | 职责 |
|------|---------|------|
| `city/` | (无) | 当前可选城市列表(静态,从 `config.city_mapping` 读取) |
| `cinema/` | `cinemas` | 抓取猫眼影院列表 + 增量 upsert;SSE 流式更新接口 |
| `movie/` | `movies` | 电影筛选、想看状态;编排三个数据源的电影信息更新;`update-douban` 单片接口 |
| `plan/` | `planning_items` | 单用户行程(场次维度)的全量读取与全量替换 |
| `show/` | `movie_shows` | 抓取猫眼场次/日期/影院 → 写场次缓存;前端读 wishMovies 场次 |

## features/movie/ 嵌套子领域

```
features/movie/
├── update_base/    # 猫眼 /films 列表抓取 → 增量 upsert movies 基础字段
├── update_douban/  # 豆瓣移动版搜索 → 补充 movies.score, movies.douban_url
└── update_extra/   # 猫眼 /movie/intro → 补充 director/country/language/duration/description
```

三个子领域都不写自己的表(共享 `features/movie/models.py` 里的 `movies`),不暴露 endpoint,各自只有 `service.py`(+ 占位 `schemas.py`)。父 `features/movie/service.py` 负责串联这三个子领域。

## 定时任务

`core/scheduler.py` 用 APScheduler 在每个整点(分钟 0)串行触发:

1. `movie_service.refresh_all_movies()` — 跑 `update_base` + `update_extra`(豆瓣不走定时,只走单片接口)
2. `show_service.refresh_wished_movie_shows()` — 抓所有想看电影的场次

服务启动时立即跑一次,不等下个整点。

## 维护约定

- 新增 feature 或子领域时同步更新本文
- 文件命名/职责约束放 [architecture.md](architecture.md),本文不再列文件树
- 如果出现某个 feature 平级文件接近模板上限(router/schemas/models/service/repository),又有新业务进来,优先拆**嵌套子领域**而不是新增角色文件
