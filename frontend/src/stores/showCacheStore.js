import { defineStore } from 'pinia'
import { ref } from 'vue'
import { getShows } from '@/api'

export const useShowCacheStore = defineStore('showCache', () => {
  const movieShowsMap = ref(new Map())
  const lastFetchedAt = ref(null)
  const syncing = ref(false)
  const syncError = ref('')

  // 后端 GET /api/shows 返回:
  // { movies: [{ movie_id, shows: [{cinema_id, cinema_name, date, time, price}, ...] }, ...],
  //   last_fetched_at: "..." | null }
  //
  // 这里把 shows 数组重新分组为前端历史结构 { cinemas: [{ cinema_id, cinema_name, shows: [...] }] },
  // 让 WishPool 不需要改字段结构。
  const buildMovieShowsByCinema = (shows) => {
    const cinemaMap = new Map()
    for (const show of shows) {
      const cinemaId = show.cinema_id
      if (cinemaId == null) continue
      if (!cinemaMap.has(cinemaId)) {
        cinemaMap.set(cinemaId, {
          cinema_id: cinemaId,
          cinema_name: show.cinema_name,
          shows: [],
        })
      }
      cinemaMap.get(cinemaId).shows.push({
        date: show.date,
        time: show.time,
        price: show.price,
      })
    }
    return { cinemas: Array.from(cinemaMap.values()) }
  }

  const refreshFromBackend = async () => {
    if (syncing.value) return
    syncing.value = true
    try {
      const response = await getShows()
      const data = response?.data?.data || {}
      const movies = data.movies || []
      const nextMap = new Map()
      for (const movie of movies) {
        nextMap.set(movie.movie_id, buildMovieShowsByCinema(movie.shows || []))
      }
      movieShowsMap.value = nextMap
      lastFetchedAt.value = data.last_fetched_at || null
      syncError.value = ''
    } catch (error) {
      syncError.value = error?.response?.data?.error || error?.message || '场次同步失败'
      console.error('场次同步失败:', error)
    } finally {
      syncing.value = false
    }
  }

  const getMovieShowsData = (movieId) => movieShowsMap.value.get(movieId) || null

  const hasMovieShowsData = (movieId) => {
    const data = movieShowsMap.value.get(movieId)
    return !!(data && data.cinemas && data.cinemas.length > 0)
  }

  return {
    movieShowsMap,
    lastFetchedAt,
    syncing,
    syncError,
    refreshFromBackend,
    getMovieShowsData,
    hasMovieShowsData,
  }
})
