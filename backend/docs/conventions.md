# 编码规范

## 命名规范

| 类型 | 规范 | 示例 |
|------|------|------|
| 类 | PascalCase | `MovieRepository` |
| 文件/函数/变量 | snake_case | `get_movie_by_id` |
| TypedDict | PascalCase + `WriteData` 后缀 | `MovieWriteData` |
| 常量 | UPPER_SNAKE_CASE | `DEMO_MOVIE_ID` |
| 类型别名 | PascalCase | `SelectionMode` |

## 单例模式

有状态对象（repository、service、client、gateway、result_builder）在模块底部实例化为单例，通过 import 注入。测试用 `monkeypatch` 替换。纯函数工具类不需要单例：

```python
class MovieRepository:
    ...

movie_repository = MovieRepository()
```

## 依赖注入

禁止在函数内部实例化有状态的对象：

```python
# 正确
from app.repositories.movie import movie_repository

# 错误
def get_movies():
    repo = MovieRepository()  # 禁止
```

## 数据在层间的传递形式

| 边界 | 传递形式 |
|------|----------|
| endpoint → service | Pydantic schema |
| service → repository（写） | TypedDict（如 `MovieWriteData`）|
| repository → service（读） | ORM 对象 |
| service 内部流转 | dataclass（`@dataclass(slots=True)`）|

ORM 对象不出 service，Pydantic schema 不进 repository。

## 类型标注

- 所有 public 函数必须有完整类型标注
- 内部数据结构用 `@dataclass(slots=True)`，数据库写入用 `TypedDict`
- 禁止使用 `Any`
- `cast()` 只用于 Pyright 无法推断的动态属性（如 SQLAlchemy ORM 字段、`getattr()` 返回值）

## 异步约定

- `service` 方法用 `async def`，`repository` 方法用同步 `def`（SQLite 不支持真正的异步）
- async 上下文中调用同步 IO 必须用 `asyncio.to_thread()`：

```python
result = await asyncio.to_thread(movie_repository.get_all_movies)
```

## 异常体系

| 异常 | 含义 | 处理方式 |
|------|------|----------|
| `AppError` | 可预期的业务异常（带 `status_code`，默认 400）| 由全局异常处理器返回 `{"success": false, "error": ...}` |
| `ExternalDependencyError` | 外部 HTTP 失败 | 在 fetch 流程内可降级，跳过当前条目；冒泡到 endpoint 时返回 502 |
| `DataParsingError` | 解析结果为空 | 在 fetch 流程内可降级，跳过当前条目；冒泡到 endpoint 时返回 502 |
| `RepositoryError` | 数据库操作失败 | 向上传播；endpoint 层统一映射为 500 |

## API 响应格式

**所有 JSON 响应必须使用统一包装**（流式 SSE 帧除外）。

成功响应：

```json
{"success": true, "data": {...}}
```

失败响应（由异常处理器自动返回）：

```json
{"success": false, "error": "..."}
```

实现方式：每个领域在 `schemas.py` 中定义 `XxxResponse(SuccessEnvelope)`，
`SuccessEnvelope` 在顶层 `app/schemas.py`：

```python
class SuccessEnvelope(BaseModel):
    success: bool = True


class CityListResponse(SuccessEnvelope):
    data: CityListData
```

状态码：`200` 成功 / `400` 客户端错误 / `404` 不存在 / `422` 参数校验失败 / `500` 服务器错误（不暴露细节） / `502` 外部依赖失败。

### SSE 流式接口的事件结构

SSE 帧不包在 `success/data` 中，但每帧仍是结构化 JSON：

- `{"type": "progress", ...}`
- `{"type": "complete", "data": {...}}`
- `{"type": "error", "error": "..."}`

## 日志规范

| 级别 | 用途 |
|------|------|
| `DEBUG` | 正常流程的细节（请求 URL、响应长度）|
| `INFO` | 关键节点（开始/完成更新）|
| `WARNING` | 可降级的失败（单条抓取失败，整体流程继续）|
| `ERROR` | 需要关注的问题（DB 写入失败、未预期异常）|

## 环境变量

所有项目自有变量使用 `MOVIE_SCHEDULER_` 前缀，模板维护在 `backend/.env.example`。

| 变量 | 用途 |
|------|------|
| `MOVIE_SCHEDULER_LOG_LEVEL` | 后端日志级别 |
| `MOVIE_SCHEDULER_DB_PATH` | SQLite 数据库路径；相对路径按 `backend/` 解析 |
| `MOVIE_SCHEDULER_DEFAULT_CITY_ID` | 未显式传入 `city_id` 时使用的默认城市 |
| `MOVIE_SCHEDULER_CITY_MAPPING` | 可选城市名到城市 ID 的 JSON 对象 |
| `MOVIE_SCHEDULER_YEAR_THRESHOLD` | 电影年份筛选阈值 |
| `MOVIE_SCHEDULER_TIMEOUT` | 外部请求超时时间，单位秒 |
| `MOVIE_SCHEDULER_DOUBAN_API_BASE_URL` | 豆瓣信息补充服务的基础 URL；读取时会移除末尾 `/` |
| `MOVIE_SCHEDULER_HOST` / `MOVIE_SCHEDULER_PORT` | 后端监听地址与端口 |
| `MOVIE_SCHEDULER_CORS_ORIGINS` | CORS 允许来源 JSON 数组 |

## 代码规模

- **函数**不超过 50 行，超出则拆私有方法
- **文件**不超过 800 行，超出则拆子模块

## 注释规范

注释说明**为什么**，不重复代码说明的**做什么**。没有需要解释的"为什么"时，不写注释。
