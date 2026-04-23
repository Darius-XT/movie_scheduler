import { defineStore } from 'pinia'
import { ref, watch } from 'vue'

const WISH_POOL_KEY = 'wishPool'
const SCHEDULE_ITEMS_KEY = 'scheduleItems'
const SELECTED_MOVIES_KEY = 'selectedMovies'

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

export const useScheduleStore = defineStore('schedule', () => {
  // Persisted state
  const selectedMovies = ref(loadFromStorage(SELECTED_MOVIES_KEY, []))
  const wishPool = ref(loadFromStorage(WISH_POOL_KEY, []))
  const scheduleItems = ref(loadFromStorage(SCHEDULE_ITEMS_KEY, []))

  // Non-persisted cache: Map<movieId, showData>
  const movieShowsMap = ref(new Map())

  // Persist on change
  watch(selectedMovies, (val) => saveToStorage(SELECTED_MOVIES_KEY, val), { deep: true })
  watch(wishPool, (val) => saveToStorage(WISH_POOL_KEY, val), { deep: true })
  watch(scheduleItems, (val) => saveToStorage(SCHEDULE_ITEMS_KEY, val), { deep: true })

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
  }

  const removeMovieShowsData = (movieId) => {
    movieShowsMap.value.delete(movieId)
  }

  const getMovieShowsData = (movieId) => {
    return movieShowsMap.value.get(movieId) || null
  }

  const hasMovieShowsData = (movieId) => {
    return movieShowsMap.value.has(movieId)
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
    // selectedMovies
    setSelectedMovies,
    updateMovieScore,
    // movieShowsMap
    setMovieShowsData,
    removeMovieShowsData,
    getMovieShowsData,
    hasMovieShowsData,
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
  }
})
