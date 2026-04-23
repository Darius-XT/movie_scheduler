# 前端规范

## 组件组织

- 页面级组件放 `src/pages/`，通用 UI 组件放 `src/components/`
- 每个组件只做一件事；超过 300 行考虑拆分
- 组件文件名 PascalCase（`MovieCard.vue`），工具文件 camelCase（`formatDate.js`）

## 状态管理

- **Pinia**：跨组件共享的状态，或需要在页面刷新后恢复的状态
- **本地 `ref` / `reactive`**：仅当前组件使用的临时状态（加载中、展开/收起、表单值）

## API 层

所有 API 调用在 `src/api/index.js` 中定义并导出，组件不直接使用 axios 或 fetch：

```javascript
export const selectMovies = (selectionMode = 'all') =>
  api.post('/movies/select', { selection_mode: selectionMode })

// SSE 流式请求同样封装在这里
export const streamMovieUpdate = (cityId, forceUpdate) =>
  fetch(`/api/v1/update/movie-stream?city_id=${cityId}&force_update_all=${forceUpdate}`)
```

后端长时任务通过 **SSE** 推送进度，前端用 `fetch` stream 接收，不用轮询。
