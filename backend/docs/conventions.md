# 编码规范

## 命名规范

| 类型 | 规范 | 示例 |
|------|------|------|
| 类 | PascalCase | `MovieRepository` |
| 文件/函数/变量 | snake_case | `get_movie_by_id` |
| TypedDict | PascalCase + `WriteData` 后缀 | `MovieWriteData` |
| 常量 | UPPER_SNAKE_CASE | `DEMO_MOVIE_ID` |
| 类型别名 | PascalCase | `SelectionMode` |
| 私有模块/符号 | 下划线前缀 | `_FetchedShowItem`, `_http_get_text` |

## 单例模式

有状态对象(repository、service)在模块底部实例化为单例,通过 import 注入。测试用 `monkeypatch` 替换。纯函数工具不需要单例:

```python
class MovieRepository:
    ...

movie_repository = MovieRepository()
```

## 依赖注入

禁止在函数内部实例化有状态的对象:

```python
# 正确
from movie_scheduler.features.movie.repository import movie_repository

# 错误
def get_movies():
    repo = MovieRepository()  # 禁止
```

## 数据在层间的传递形式

| 边界 | 传递形式 |
|------|----------|
| router → service | Pydantic schema |
| service → repository(写) | TypedDict(如 `MovieWriteData`) |
| repository → service(读) | ORM 对象 |
| service 内部流转 | dataclass(`@dataclass(slots=True)`) |

ORM 对象不出 service,Pydantic schema 不进 repository。

## 类型标注

- 所有 public 函数必须有完整类型标注
- 内部数据结构用 `@dataclass(slots=True)`,数据库写入用 `TypedDict`
- 禁止使用 `Any`
- `cast()` 只用于 Pyright 无法推断的动态属性(如 SQLAlchemy ORM 字段、`getattr()` 返回值)

## 异步约定

- `service` 方法用 `async def`,`repository` 方法用同步 `def`(SQLite 不支持真正的异步)
- async 上下文中调用同步 IO 必须用 `asyncio.to_thread()`:

```python
result = await asyncio.to_thread(movie_repository.get_all_movies)
```

## 异常体系

| 异常 | 含义 | 处理方式 |
|------|------|----------|
| `AppError` | 可预期的业务异常(带 `status_code`,默认 400) | 由全局异常处理器返回 `{"success": false, "error": ...}` |
| `ExternalDependencyError` | 外部 HTTP 失败 | 在 fetch 流程内可降级,跳过当前条目;冒泡到 router 时返回 502 |
| `DataParsingError` | 解析结果为空 | 在 fetch 流程内可降级,跳过当前条目;冒泡到 router 时返回 502 |
| `RepositoryError` | 数据库操作失败 | 向上传播;router 层统一映射为 500 |

异常类型与全局 handler 注册都在 `movie_scheduler/core/exceptions.py`。

## API 响应格式

**所有 JSON 响应必须使用统一包装**(流式 SSE 帧除外)。

成功响应:

```json
{"success": true, "data": {...}}
```

失败响应(由异常处理器自动返回):

```json
{"success": false, "error": "..."}
```

实现方式: 每个 feature 在 `schemas.py` 中定义 `XxxResponse(SuccessEnvelope)`,`SuccessEnvelope` 在 `movie_scheduler/shared/types.py`:

```python
class SuccessEnvelope(BaseModel):
    success: bool = True


class CityListResponse(SuccessEnvelope):
    data: CityListData
```

状态码: `200` 成功 / `400` 客户端错误 / `404` 不存在 / `422` 参数校验失败 / `500` 服务器错误(不暴露细节) / `502` 外部依赖失败。

### SSE 流式接口的事件结构

SSE 帧不包在 `success/data` 中,但每帧仍是结构化 JSON:

- `{"type": "progress", ...}`
- `{"type": "complete", "data": {...}}`
- `{"type": "error", "error": "..."}`

## 日志规范

| 级别 | 用途 |
|------|------|
| `DEBUG` | 正常流程的细节(响应长度、解析分支等) |
| `INFO` | 关键节点(开始/完成更新、内部接口调用、外部请求 URL) |
| `WARNING` | 可降级的失败(单条抓取失败,整体流程继续) |
| `ERROR` | 需要关注的问题(DB 写入失败、未预期异常) |

### 接口与外部 URL 链路日志

- 每一次后端内部 HTTP 接口调用都必须打印开始与完成日志,包含 `request_id`、`method`、`path`、完成状态码与耗时。
- 每一次内部接口触发的外部 HTTP 请求都必须打印外部 URL,日志必须包含同一个 `request_id` 与 `internal_api`,用于定位"哪个内部接口请求了哪个外部 URL"。
- 外部请求日志只记录 `method`、`url`、`purpose` 等排障必要信息,禁止打印 headers、Cookie、token 等敏感信息。
- 新增外部 HTTP 调用时,必须在真正发起请求前调用 `log_external_http_request(...)`;不能只在失败分支打印 URL。
- 同一个外部 URL 在正常路径中只由 `log_external_http_request(...)` 打印一次;响应、解析、失败日志不得重复打印 URL。
- 内部接口调用由项目中间件统一记录,不要再依赖或新增重复的 access log。
- 定时任务或后台任务没有入口 HTTP 请求时,外部请求日志中的 `internal_api` 统一记为 `background`。

### 猫眼页面请求

- 所有猫眼 HTML 页面请求必须通过 `movie_scheduler.shared.maoyan.maoyan_get_text(...)` 发起,不要在业务模块中直接 `requests.get` 访问猫眼页面。
- 业务模块不得直接拼接或打印猫眼 Cookie header;Cookie 统一由共享猫眼 Session 根据 `MOVIE_SCHEDULER_MAOYAN_COOKIE` 和运行时 `hotMovieIds` 管理。
- 当前猫眼 Session 设计基于单用户、单城市、单设备使用场景,不支持多城市并发隔离。

## 环境变量

所有项目自有变量使用 `MOVIE_SCHEDULER_` 前缀,模板维护在 `backend/.env.example`。

| 变量 | 用途 |
|------|------|
| `MOVIE_SCHEDULER_LOG_LEVEL` | 后端日志级别 |
| `MOVIE_SCHEDULER_DB_PATH` | SQLite 数据库路径;相对路径按 `backend/` 解析 |
| `MOVIE_SCHEDULER_DEFAULT_CITY_ID` | 未显式传入 `city_id` 时使用的默认城市 |
| `MOVIE_SCHEDULER_CITY_MAPPING` | 可选城市名到城市 ID 的 JSON 对象 |
| `MOVIE_SCHEDULER_TIMEOUT` | 外部请求超时时间,单位秒 |
| `MOVIE_SCHEDULER_DOUBAN_API_BASE_URL` | 豆瓣信息补充服务的基础 URL;读取时会移除末尾 `/` |
| `MOVIE_SCHEDULER_MAOYAN_COOKIE` | 可选猫眼浏览器种子 Cookie;猫眼共享 Session 会移除旧 `hotMovieIds`,预热后复用 Session Cookie,场次抓取会刷新 `hotMovieIds` |
| `MOVIE_SCHEDULER_HOST` / `MOVIE_SCHEDULER_PORT` | 后端监听地址与端口 |
| `MOVIE_SCHEDULER_CORS_ORIGINS` | CORS 允许来源 JSON 数组 |

## 代码规模

- **函数**不超过 50 行,超出则拆私有方法
- **文件**没有硬性上限,但出现以下信号时考虑拆嵌套子 feature:
  - 多个稳定的外部数据源放在同一个 service 里
  - 多种业务用例平行存在,彼此独立演化
- 不允许新增"按角色再分一层"的文件(`helper.py`、`builder.py`、`client.py` 等),要么并入 service.py,要么拆子 feature

## 注释规范

注释说明**为什么**,不重复代码说明的**做什么**。没有需要解释的"为什么"时,不写注释。
