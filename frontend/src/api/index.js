import axios from 'axios'

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 300000,
})

export const getCities = () => api.get('/cities')

export const selectMovies = (selectionMode = 'all') =>
  api.post('/movies/select', { selection_mode: selectionMode })

export const fetchMovieDouban = (movieId) =>
  api.post(`/movies/${movieId}/fetch-douban`)

// SSE streaming functions — return a raw Response for the caller to read
export const streamCinemaUpdate = (cityId, forceUpdate) =>
  fetch(
    `/api/v1/update/cinema-stream?city_id=${cityId}&force_update_all=${forceUpdate}`,
    { headers: { Accept: 'text/event-stream' } }
  )

export const streamMovieUpdate = (cityId, forceUpdate) =>
  fetch(
    `/api/v1/update/movie-stream?city_id=${cityId}&force_update_all=${forceUpdate}`,
    { headers: { Accept: 'text/event-stream' } }
  )

export const streamShows = (movieIds, cityId) => {
  const cityQuery = cityId ? `&city_id=${cityId}` : ''
  return fetch(
    `/api/v1/shows/fetch-stream?movie_ids=${movieIds.join(',')}${cityQuery}`,
    { headers: { Accept: 'text/event-stream' } }
  )
}

export default api
