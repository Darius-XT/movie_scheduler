import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 300000, // 5分钟超时，因为更新操作可能较慢
})

// 获取城市列表
export const getCities = () => api.get('/cities')

// 更新影院信息
export const updateCinema = (cityId) => api.post('/update/cinema', { city_id: cityId })

// 更新电影信息
export const updateMovie = (cityId, forceUpdateAll = false) =>
  api.post('/update/movie', { city_id: cityId, force_update_all: forceUpdateAll })

// 筛选电影
export const selectMovies = (yearThreshold = null) =>
  api.post('/movies/select', { year_threshold: yearThreshold })

// 获取场次信息
export const fetchShows = (movieIds, useAsync = true) =>
  api.post('/shows/fetch', { movie_ids: movieIds, use_async: useAsync })

export default api
