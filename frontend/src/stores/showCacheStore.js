import { defineStore } from 'pinia'
import { ref } from 'vue'
import { loadFromStorage, saveToStorage } from './storage'

const MOVIE_SHOWS_MAP_KEY = 'movieShowsMap'

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

export const useShowCacheStore = defineStore('showCache', () => {
  const movieShowsMap = ref(loadMovieShowsMap())

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

  return {
    movieShowsMap,
    setMovieShowsData,
    removeMovieShowsData,
    getMovieShowsData,
    hasMovieShowsData,
    pruneStaleMovieShows,
  }
})
