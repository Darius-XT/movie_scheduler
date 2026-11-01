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

export const createManualMovie = (title) => api.post('/movies/manual', { title })

export const setMovieWished = (movieId, isWished) =>
  api.patch(`/movies/${movieId}/wished`, { is_wished: isWished })

export const setMovieLabel = (movieId, label) =>
  api.patch(`/movies/${movieId}/label`, { label })

export const setMovieChannels = (movieId, channels) =>
  api.patch(`/movies/${movieId}/channels`, { channels })

export const setMovieViewingLocation = (movieId, viewingLocation) =>
  api.patch(`/movies/${movieId}/viewing-location`, { viewing_location: viewingLocation })

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

export const streamMovieUpdate = (cityId) =>
  fetch(
    `/api/movies/update-stream?city_id=${cityId}`,
    { headers: { Accept: 'text/event-stream' } }
  )

export const streamShowUpdate = (cityId, movieId = null) =>
  fetch(
    `/api/shows/update-stream?city_id=${encodeURIComponent(cityId)}${movieId == null ? '' : `&movie_id=${encodeURIComponent(movieId)}`}`,
    { headers: { Accept: 'text/event-stream' } }
  )

export default api
