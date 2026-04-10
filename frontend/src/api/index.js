import axios from 'axios'

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 300000,
})

export const getCities = () => api.get('/cities')

export const selectMovies = (selectionMode = 'all') =>
  api.post('/movies/select', { selection_mode: selectionMode })

export default api
