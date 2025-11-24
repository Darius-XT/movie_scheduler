import { createRouter, createWebHistory } from 'vue-router'
import MovieSelector from '@/views/MovieSelector.vue'

const routes = [
  {
    path: '/',
    redirect: '/movie-selector'
  },
  {
    path: '/movie-selector',
    name: 'MovieSelector',
    component: MovieSelector,
    meta: { title: '电影场次查询' }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
