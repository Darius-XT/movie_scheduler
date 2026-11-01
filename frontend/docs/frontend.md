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
export const streamCinemaUpdate = (cityId) =>
  fetch(`/api/update/cinema-stream?city_id=${cityId}`)
```

后端长时任务通过 **SSE** 推送进度，前端用 `fetch` stream 接收，不用轮询。

## 想看与行程

- 想看区按手动保存的 `viewing_location` 分为“家里看 / 影院看 / 未分类”，不再按年份自动分类。
  默认未分类；未分类条目右侧显示两个分类按钮，已分类条目只显示切换图标，点击切换到另一观看地点。
  仅修改地点，不改变想看标签和渠道。
  仅影院看显示影院/日期/周末/可加入行程筛选；“仅看本周”按周一至周日筛选场次。
  家里看按“全部、b 站、特狗、电影天堂、腾讯、爱奇艺、优酷、暂无”分类。
  渠道仅支持单选，成功保存后同步列表；清空渠道回到暂无，不改变想看状态。

- 电影标签为“想看 / 不看 / 看过 / 无标签”，分别由 `is_wished`、`is_skipped`、`is_watched`、三者皆 false 表示。
  右侧三个按钮互斥，再点已选标签可取消；“仅看无标签”与搜索、排序组合生效。
  `PATCH /api/movies/{id}/label` 请求 `{ "label": "wished" }`、`"skipped"`、`"watched"` 或 `null`，
  响应为 `success/data.movie`。切换标签同步想看列表，失败回滚；移出想看恢复无标签。
  已有行程的电影需先移除行程才能取消想看、标记不看或看过。定时更新保留标签，已标记的下架电影不删除。

- 想看标题旁的“手动添加”支持输入片名，通过 `POST /api/movies/manual` 保存并加入想看。
  请求为 `{ "title": "电影名称" }`（去除首尾空白后 1–200 字），响应为 `success/data.movie`。
  手动条目不自动获取场次；保存失败时保留输入，可重试。

- **想看(电影维度)**:`movieSelectionStore.wishMovies` 来源于 `GET /api/movies/wished`,
  状态字段为 `movies.is_wished`。加入/移出通过 `PATCH /api/movies/{id}/label` 持久化,
  store 内部做乐观更新 + 失败回滚。
- **行程(场次维度)**:`planningStore.scheduleItems` 通过 `GET /api/planning` 加载、
  `PUT /api/planning/schedule-items` 全量替换。本地 `localStorage` 仍保留作离线回退缓存。
- 旧的"场次维度想看池"已废弃,localStorage 中的 `wishPool` key 由 `planningStore`
  启动时主动清理。

## 场次自动同步

- 后端 APScheduler 在服务启动时立即抓一次,之后每小时刷新一次,所有想看电影的场次写入 `movie_shows` 表。
- 前端 `showCacheStore.refreshFromBackend()` 调 `GET /api/shows` 一次性拿到所有场次,
  按电影分组挂在 `movieShowsMap` 中,并保存 `lastFetchedAt`(想看电影 `shows_updated_at` 的最大值)。
- 用户加入新想看时,后端后台抓该电影场次;前端每 10 秒调用一次
  `GET /api/shows?movie_id={id}`,最多轮询 3 分钟,只更新该电影在 `movieShowsMap` 中的缓存。
- WishPool 顶部展示 `lastFetchedAt`；影院看中每部非手动电影右侧提供“更新场次”，使用当前所选城市，通过 SSE 展示进度，完成后只重新读取该电影的场次缓存；失败保留已有场次。

场次展示统一使用 `src/utils/showTime.js` 处理开始/结束时间:场次列表、想看池和行程板都显示
`HH:mm-HH:mm`。结束时间由场次开始时间加 `durationMinutes` 推算;展示时如果片长缺失或无效,
显示 `HH:mm-未知`。

`removePastSchedules()` 清理旧行程时按场次结束时间判断,而不是只按日期判断。结束时间早于当前时间的
行程会被移除;如果 `durationMinutes` 缺失或无效,按 180 分钟片长计算结束时间。日期或开始时间格式
无法解析的行程会保留,避免误删。

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
