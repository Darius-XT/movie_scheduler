import InfoUpdate from '@/pages/InfoUpdate.vue'
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
  {
    path: '/info-update',
    name: 'info_update',
    component: InfoUpdate,
    meta: { title: '信息更新' },
  },
]
