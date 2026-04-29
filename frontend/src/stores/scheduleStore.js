import { defineStore } from 'pinia'
import { ref, watch } from 'vue'

const WISH_POOL_KEY = 'wishPool'
const SCHEDULE_ITEMS_KEY = 'scheduleItems'
const SELECTED_MOVIES_KEY = 'selectedMovies'
const CINEMA_UPDATE_META_KEY = 'cinemaUpdateMeta'
const MOVIE_UPDATE_META_KEY = 'movieUpdateMeta'
const CINEMA_UPDATE_RESULT_KEY = 'cinemaUpdateResult'
const MOVIE_UPDATE_RESULT_KEY = 'movieUpdateResult'
const MOVIE_SHOWS_MAP_KEY = 'movieShowsMap'

const EMPTY_UPDATE_META = { lastUpdatedAt: null, durationMs: null }

const getLocalDateKey = (timestamp) => {
  if (!timestamp) return ''
  const date = new Date(timestamp)
  if (Number.isNaN(date.getTime())) return ''
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

const isShowCacheFromToday = (cachedAt) => {
  if (!cachedAt) return false
  return getLocalDateKey(cachedAt) === getLocalDateKey(Date.now())
}

const loadFromStorage = (key, defaultValue) => {
  try {
    const raw = localStorage.getItem(key)
    if (raw) return JSON.parse(raw)
  } catch {
    // ignore parse errors
  }
  return defaultValue
}

const saveToStorage = (key, value) => {
  try {
    localStorage.setItem(key, JSON.stringify(value))
  } catch {
    // ignore storage errors
  }
}

const loadMovieShowsMap = () => {
  const raw = loadFromStorage(MOVIE_SHOWS_MAP_KEY, null)
  if (!Array.isArray(raw)) return new Map()
  const restored = new Map()
  raw.forEach((entry) => {
    if (!Array.isArray(entry) || entry.length !== 2) return
    const [movieId, showData] = entry
    if (isShowCacheFromToday(showData?.cachedAt)) {
      restored.set(movieId, showData)
    }
  })
  return restored
}

const saveMovieShowsMap = (map) => {
  saveToStorage(MOVIE_SHOWS_MAP_KEY, Array.from(map.entries()))
}

export const useScheduleStore = defineStore('schedule', () => {
  // Persisted state
  const selectedMovies = ref(loadFromStorage(SELECTED_MOVIES_KEY, []))
  const wishPool = ref(loadFromStorage(WISH_POOL_KEY, []))
  const scheduleItems = ref(loadFromStorage(SCHEDULE_ITEMS_KEY, []))
  const cinemaUpdateMeta = ref(loadFromStorage(CINEMA_UPDATE_META_KEY, EMPTY_UPDATE_META))
  const movieUpdateMeta = ref(loadFromStorage(MOVIE_UPDATE_META_KEY, EMPTY_UPDATE_META))
  const cinemaUpdateResult = ref(loadFromStorage(CINEMA_UPDATE_RESULT_KEY, null))
  const movieUpdateResult = ref(loadFromStorage(MOVIE_UPDATE_RESULT_KEY, null))

  // Persisted cache: Map<movieId, showData> —— 同一自然日内有效，跨 0 点失效。
  const movieShowsMap = ref(loadMovieShowsMap())

  // Persist on change
  watch(selectedMovies, (val) => saveToStorage(SELECTED_MOVIES_KEY, val), { deep: true })
  watch(wishPool, (val) => saveToStorage(WISH_POOL_KEY, val), { deep: true })
  watch(scheduleItems, (val) => saveToStorage(SCHEDULE_ITEMS_KEY, val), { deep: true })
  watch(cinemaUpdateMeta, (val) => saveToStorage(CINEMA_UPDATE_META_KEY, val), { deep: true })
  watch(movieUpdateMeta, (val) => saveToStorage(MOVIE_UPDATE_META_KEY, val), { deep: true })
  watch(cinemaUpdateResult, (val) => saveToStorage(CINEMA_UPDATE_RESULT_KEY, val), { deep: true })
  watch(movieUpdateResult, (val) => saveToStorage(MOVIE_UPDATE_RESULT_KEY, val), { deep: true })

  // ===== update meta/result actions =====
  const recordCinemaUpdate = (result, durationMs) => {
    cinemaUpdateResult.value = result
    cinemaUpdateMeta.value = { lastUpdatedAt: Date.now(), durationMs }
  }

  const recordMovieUpdate = (result, durationMs) => {
    movieUpdateResult.value = result
    movieUpdateMeta.value = { lastUpdatedAt: Date.now(), durationMs }
  }

  // ===== selectedMovies actions =====
  const setSelectedMovies = (movies) => {
    selectedMovies.value = movies
  }

  const updateMovieScore = (movieId, score, doubanUrl) => {
    const movie = selectedMovies.value.find((m) => m.id === movieId)
    if (movie) {
      movie.score = score
      movie.douban_url = doubanUrl
    }
  }

  // ===== movieShowsMap actions =====
  const setMovieShowsData = (movieId, showData) => {
    movieShowsMap.value.set(movieId, showData)
    saveMovieShowsMap(movieShowsMap.value)
  }

  const removeMovieShowsData = (movieId) => {
    if (!movieShowsMap.value.has(movieId)) return
    movieShowsMap.value.delete(movieId)
    saveMovieShowsMap(movieShowsMap.value)
  }

  const getMovieShowsData = (movieId) => {
    const showData = movieShowsMap.value.get(movieId)
    if (!showData) return null
    if (!isShowCacheFromToday(showData.cachedAt)) return null
    return showData
  }

  const hasMovieShowsData = (movieId) => {
    return getMovieShowsData(movieId) !== null
  }

  const pruneStaleMovieShows = () => {
    let changed = false
    movieShowsMap.value.forEach((showData, movieId) => {
      if (!isShowCacheFromToday(showData?.cachedAt)) {
        movieShowsMap.value.delete(movieId)
        changed = true
      }
    })
    if (changed) saveMovieShowsMap(movieShowsMap.value)
  }

  // ===== wishPool actions =====
  const isInWishPool = (showKey) => {
    return wishPool.value.some((item) => item.key === showKey)
  }

  const addToWishPool = (showEntry) => {
    if (isInWishPool(showEntry.key)) return
    wishPool.value = [...wishPool.value, showEntry]
  }

  const removeFromWishPool = (showKey) => {
    wishPool.value = wishPool.value.filter((item) => item.key !== showKey)
  }

  const removeWishMovieGroup = (movieId) => {
    wishPool.value = wishPool.value.filter((item) => item.movieId !== movieId)
  }

  const addManyToWishPool = (entries) => {
    const newEntries = entries.filter((e) => !isInWishPool(e.key))
    if (newEntries.length > 0) {
      wishPool.value = [...wishPool.value, ...newEntries]
    }
    return newEntries.length
  }

  // ===== scheduleItems actions =====
  const isInSchedule = (showKey) => {
    return scheduleItems.value.some((item) => item.key === showKey)
  }

  const addToSchedule = (showEntry) => {
    if (isInSchedule(showEntry.key)) return
    scheduleItems.value = [...scheduleItems.value, { ...showEntry, purchased: false }]
  }

  const removeFromSchedule = (showKey) => {
    scheduleItems.value = scheduleItems.value.filter((item) => item.key !== showKey)
  }

  const moveFromScheduleToWishPool = (showKey) => {
    const targetItem = scheduleItems.value.find((item) => item.key === showKey)
    scheduleItems.value = scheduleItems.value.filter((item) => item.key !== showKey)
    if (targetItem && !isInWishPool(showKey)) {
      const { purchased, ...wishEntry } = targetItem
      wishPool.value = [...wishPool.value, wishEntry]
    }
  }

  const toggleSchedulePurchased = (showKey) => {
    scheduleItems.value = scheduleItems.value.map((item) => {
      if (item.key !== showKey) return item
      return { ...item, purchased: !item.purchased }
    })
  }

  const removePastSchedules = () => {
    const today = new Date()
    const yyyy = today.getFullYear()
    const mm = String(today.getMonth() + 1).padStart(2, '0')
    const dd = String(today.getDate()).padStart(2, '0')
    const todayStr = `${yyyy}-${mm}-${dd}`
    const before = scheduleItems.value.length
    scheduleItems.value = scheduleItems.value.filter((item) => String(item.date || '') >= todayStr)
    return before - scheduleItems.value.length
  }

  return {
    // state
    selectedMovies,
    wishPool,
    scheduleItems,
    movieShowsMap,
    cinemaUpdateMeta,
    movieUpdateMeta,
    cinemaUpdateResult,
    movieUpdateResult,
    // selectedMovies
    setSelectedMovies,
    updateMovieScore,
    // movieShowsMap
    setMovieShowsData,
    removeMovieShowsData,
    getMovieShowsData,
    hasMovieShowsData,
    pruneStaleMovieShows,
    // wishPool
    isInWishPool,
    addToWishPool,
    removeFromWishPool,
    removeWishMovieGroup,
    addManyToWishPool,
    // scheduleItems
    isInSchedule,
    addToSchedule,
    removeFromSchedule,
    moveFromScheduleToWishPool,
    toggleSchedulePurchased,
    removePastSchedules,
    // update meta/result
    recordCinemaUpdate,
    recordMovieUpdate,
  }
})
