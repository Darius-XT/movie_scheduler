import axios from 'axios'

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 300000,
})

export const getCities = () => api.get('/cities')

export const updateCinema = (cityId) => api.post('/update/cinema', { city_id: cityId })

export const updateMovie = (cityId, forceUpdateAll = false) =>
  api.post('/update/movie', { city_id: cityId, force_update_all: forceUpdateAll })

export const selectMovies = (selectionMode = 'all') =>
  api.post('/movies/select', { selection_mode: selectionMode })

export default api
