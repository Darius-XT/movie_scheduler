import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 300000,
})

export const getCities = () => api.get('/cities')

export const getPlanning = () => api.get('/plan')

export const saveScheduleItems = (scheduleItems) =>
  api.put('/plan/items', { schedule_items: scheduleItems })

export const selectMovies = (selectionMode = 'all') =>
  api.post('/movies/select', { selection_mode: selectionMode })

export const getWishedMovies = () => api.get('/movies/wished')

export const setMovieWished = (movieId, isWished) =>
  api.patch(`/movies/${movieId}/wished`, { is_wished: isWished })

export const fetchMovieDouban = (movieId) =>
  api.post(`/movies/${movieId}/update-douban`)

export const getShows = (movieId = null) =>
  api.get('/shows', movieId == null ? undefined : { params: { movie_id: movieId } })

export const getMovieUpdateStatus = () => api.get('/movies/update-status')

// SSE streaming functions — return a raw Response for the caller to read
export const streamCinemaUpdate = (cityId) =>
  fetch(
    `/api/cinemas/update-stream?city_id=${cityId}`,
    { headers: { Accept: 'text/event-stream' } }
  )

export default api
