import MovieSelector from '@/pages/MovieSelector.vue'

export const pageRoutes = [
  {
    path: '/',
    redirect: '/movie-selector',
  },
  {
    path: '/movie-selector',
    name: 'movie_selector',
    component: MovieSelector,
    meta: { title: '电影场次查询' },
  },
]
