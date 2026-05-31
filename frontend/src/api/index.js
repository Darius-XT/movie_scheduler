import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 300000,
})

export const getCities = () => api.get('/cities')

export const getPlanning = () => api.get('/planning')

export const saveScheduleItems = (scheduleItems) =>
  api.put('/planning/schedule-items', { schedule_items: scheduleItems })

export const selectMovies = (selectionMode = 'all') =>
  api.post('/movies/select', { selection_mode: selectionMode })

export const getWishedMovies = () => api.get('/movies/wished')

export const setMovieWished = (movieId, isWished) =>
  api.patch(`/movies/${movieId}/wished`, { is_wished: isWished })

export const fetchMovieDouban = (movieId) =>
  api.post(`/movies/${movieId}/fetch-douban`)

export const getShows = () => api.get('/shows')

export const getMovieUpdateStatus = () => api.get('/update/movies/status')

// SSE streaming functions — return a raw Response for the caller to read
export const streamCinemaUpdate = (cityId) =>
  fetch(
    `/api/update/cinema-stream?city_id=${cityId}`,
    { headers: { Accept: 'text/event-stream' } }
  )

export default api
