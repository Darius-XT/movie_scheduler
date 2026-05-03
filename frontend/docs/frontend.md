# 前端规范

## 组件组织

- 页面级组件放 `src/pages/`，通用 UI 组件放 `src/components/`
- 每个组件只做一件事；超过 300 行考虑拆分
- 组件文件名 PascalCase（`MovieCard.vue`），工具文件 camelCase（`formatDate.js`）

## 状态管理

- **Pinia**：跨组件共享的状态，或需要在页面刷新后恢复的状态
- **本地 `ref` / `reactive`**：仅当前组件使用的临时状态（加载中、展开/收起、表单值）
- `src/stores/scheduleStore.js` 只作为兼容门面；新增状态优先放入职责更窄的 store，
  如 `planningStore.js`、`showCacheStore.js`、`updateMetaStore.js`。

## API 层

所有 API 调用在 `src/api/index.js` 中定义并导出。组件**禁止**直接使用 `axios` 或 `fetch`，也禁止在组件中拼接绝对 URL：

```javascript
const api = axios.create({
  baseURL: '/api',
  timeout: 300000,
})

export const selectMovies = (selectionMode = 'all') =>
  api.post('/movies/select', { selection_mode: selectionMode })

// SSE 流式请求同样封装在这里
export const streamMovieUpdate = (cityId, forceUpdate) =>
  fetch(`/api/update/movie-stream?city_id=${cityId}&force_update_all=${forceUpdate}`)
```

后端长时任务通过 **SSE** 推送进度，前端用 `fetch` stream 接收，不用轮询。

## 计划数据同步

`wishPool` 和 `scheduleItems` 是单用户计划数据，前端启动时通过 `GET /api/planning`
从后端加载；当后端为空且浏览器已有旧本地数据时，自动通过 `PUT /api/planning`
上传一次。本地 `localStorage` 仍保留为加载回退和离线状态缓存。

`movieShowsMap` 只作为浏览器本地场次缓存使用，同一自然日内有效，跨日失效，不写入后端。

场次展示统一使用 `src/utils/showTime.js` 处理开始/结束时间：场次列表、想看池和行程板都显示
`HH:mm-HH:mm`。结束时间由场次开始时间加 `durationMinutes` 推算；展示时如果片长缺失或无效，
显示 `HH:mm-未知`。

`removePastSchedules()` 清理旧行程时按场次结束时间判断，而不是只按日期判断。结束时间早于当前时间的
行程会被移除；如果 `durationMinutes` 缺失或无效，按 180 分钟片长计算结束时间。日期或开始时间格式
无法解析的行程会保留，避免误删。

## 响应解包

后端所有 JSON 响应都使用统一的 `success/data` 包装。组件中需要从 `response.data.data` 取业务数据：

```javascript
const response = await getCities()
const cities = response.data.data.cities  // axios 第一层 .data 是 HTTP body, 第二层 .data 是业务数据
```

错误情况下后端返回 `{success: false, error: "..."}`，axios 会按状态码自动抛出，可在 catch 中读 `error.response.data.error`。

## URL 命名

- 永远只有 `/api`，不引入 `/api/v1` / `/api/v2` 这类版本前缀。
- 路径在 `api/index.js` 中相对 `baseURL` 写，不在组件中拼接绝对 URL。
