import { defineStore } from 'pinia'
import { ref, watch } from 'vue'
import { getShows } from '@/api'
import { loadFromStorage, saveToStorage } from './storage'

const MOVIE_SHOW_POLL_INTERVAL_MS = 15_000
const MOVIE_SHOW_POLL_MAX_ATTEMPTS = 40
const SHOWS_UPDATE_META_KEY = 'showsUpdateMeta'
const SHOWS_UPDATE_RESULT_KEY = 'showsUpdateResult'
const EMPTY_UPDATE_META = { durationMs: null }

export const useShowCacheStore = defineStore('showCache', () => {
  const movieShowsMap = ref(new Map())
  const lastFetchedAt = ref(null)
  const syncing = ref(false)
  const syncError = ref('')
  const moviePollingIds = ref(new Set())

  // 手动「更新场次」按钮的统计 + 用时,本地持久化; lastFetchedAt 仍以后端 last_fetched_at 为权威。
  const loadedShowsUpdateMeta = loadFromStorage(SHOWS_UPDATE_META_KEY, EMPTY_UPDATE_META)
  const showsUpdateMeta = ref({ durationMs: loadedShowsUpdateMeta?.durationMs ?? null })
  const showsUpdateResult = ref(loadFromStorage(SHOWS_UPDATE_RESULT_KEY, null))

  watch(showsUpdateMeta, (val) => saveToStorage(SHOWS_UPDATE_META_KEY, val), { deep: true })
  watch(showsUpdateResult, (val) => saveToStorage(SHOWS_UPDATE_RESULT_KEY, val), { deep: true })

  const recordShowUpdate = (result, durationMs, lastFetchedAtFromBackend) => {
    showsUpdateResult.value = result
    showsUpdateMeta.value = {
      durationMs,
    }
    if (lastFetchedAtFromBackend) {
      lastFetchedAt.value = lastFetchedAtFromBackend
    }
  }

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
      replaceAllMovieShows(data.movies || [])
      lastFetchedAt.value = data.last_fetched_at || null
      syncError.value = ''
    } catch (error) {
      syncError.value = error?.response?.data?.error || error?.message || '场次同步失败'
      console.error('场次同步失败:', error)
    } finally {
      syncing.value = false
    }
  }

  const refreshMovieFromBackend = async (movieId) => {
    try {
      const response = await getShows(movieId)
      const data = response?.data?.data || {}
      applySingleMovieShows(movieId, data.movies || [])
      mergeLastFetchedAt(data.last_fetched_at || null)
      syncError.value = ''
      return data
    } catch (error) {
      syncError.value = error?.response?.data?.error || error?.message || '场次同步失败'
      console.error('单片场次同步失败:', error)
      throw error
    }
  }

  const pollMovieShowsUntilUpdated = async (movieId) => {
    if (!movieId || moviePollingIds.value.has(movieId)) return
    moviePollingIds.value = new Set([...moviePollingIds.value, movieId])
    try {
      for (let attempt = 0; attempt < MOVIE_SHOW_POLL_MAX_ATTEMPTS; attempt += 1) {
        await wait(MOVIE_SHOW_POLL_INTERVAL_MS)
        const data = await refreshMovieFromBackend(movieId)
        if (data.last_fetched_at) return
      }
    } catch {
      // 错误已写入 syncError,由页面统一展示。
    } finally {
      const next = new Set(moviePollingIds.value)
      next.delete(movieId)
      moviePollingIds.value = next
    }
  }

  const replaceAllMovieShows = (movies) => {
    const nextMap = new Map()
    for (const movie of movies) {
      nextMap.set(movie.movie_id, buildMovieShowsByCinema(movie.shows || []))
    }
    movieShowsMap.value = nextMap
  }

  const applySingleMovieShows = (movieId, movies) => {
    const nextMap = new Map(movieShowsMap.value)
    const movie = movies.find((item) => item.movie_id === movieId)
    if (!movie) nextMap.delete(movieId)
    else nextMap.set(movieId, buildMovieShowsByCinema(movie.shows || []))
    movieShowsMap.value = nextMap
  }

  const removeMovieShows = (movieId) => {
    const nextMap = new Map(movieShowsMap.value)
    nextMap.delete(movieId)
    movieShowsMap.value = nextMap
  }

  const mergeLastFetchedAt = (value) => {
    if (!value) return
    if (!lastFetchedAt.value || String(value) > String(lastFetchedAt.value)) {
      lastFetchedAt.value = value
    }
  }

  const wait = (ms) => new Promise((resolve) => window.setTimeout(resolve, ms))

  const getMovieShowsData = (movieId) => movieShowsMap.value.get(movieId) || null

  const hasMovieShowsData = (movieId) => {
    const data = movieShowsMap.value.get(movieId)
    return !!(data && data.cinemas && data.cinemas.length > 0)
  }

  const isMovieShowsPolling = (movieId) => moviePollingIds.value.has(movieId)

  return {
    movieShowsMap,
    lastFetchedAt,
    syncing,
    syncError,
    showsUpdateMeta,
    showsUpdateResult,
    recordShowUpdate,
    refreshFromBackend,
    refreshMovieFromBackend,
    pollMovieShowsUntilUpdated,
    removeMovieShows,
    getMovieShowsData,
    hasMovieShowsData,
    isMovieShowsPolling,
  }
})
