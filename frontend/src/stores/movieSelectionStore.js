import { defineStore } from 'pinia'
import { computed, ref, watch } from 'vue'
import { getWishedMovies, setMovieWished } from '@/api'
import { loadFromStorage, removeFromStorage, saveToStorage } from './storage'

const SELECTED_MOVIES_KEY = 'selectedMovies'
const LEGACY_WISH_MOVIES_KEY = 'wishMovies'

export const useMovieSelectionStore = defineStore('movieSelection', () => {
  // 想看以后端为唯一 source of truth,不再做本地缓存(多设备一致性优先于首屏占位)
  removeFromStorage(LEGACY_WISH_MOVIES_KEY)

  const selectedMovies = ref(loadFromStorage(SELECTED_MOVIES_KEY, []))
  const wishMovies = ref([])
  const wishSyncError = ref('')
  const wishSyncReady = ref(false)

  watch(selectedMovies, (val) => saveToStorage(SELECTED_MOVIES_KEY, val), { deep: true })

  const wishedMovieIds = computed(() => new Set(wishMovies.value.map((m) => m.id)))

  const setSelectedMovies = (movies) => {
    selectedMovies.value = movies
    syncSelectedWishFlags()
  }

  const updateMovieScore = (movieId, score, doubanUrl) => {
    const movie = selectedMovies.value.find((m) => m.id === movieId)
    if (movie) {
      movie.score = score
      movie.douban_url = doubanUrl
    }
    const wishMovie = wishMovies.value.find((m) => m.id === movieId)
    if (wishMovie) {
      wishMovie.score = score
      wishMovie.douban_url = doubanUrl
    }
  }

  const syncSelectedWishFlags = () => {
    if (selectedMovies.value.length === 0) return
    const ids = wishedMovieIds.value
    selectedMovies.value = selectedMovies.value.map((movie) =>
      movie.is_wished === ids.has(movie.id) ? movie : { ...movie, is_wished: ids.has(movie.id) }
    )
  }

  const isInWishMovies = (movieId) => wishedMovieIds.value.has(movieId)

  const setSelectedWishFlag = (movieId, isWished) => {
    selectedMovies.value = selectedMovies.value.map((movie) =>
      movie.id === movieId ? { ...movie, is_wished: isWished } : movie
    )
  }

  const addToWishMovies = async (movie) => {
    if (!movie?.id || isInWishMovies(movie.id)) return
    const optimistic = { ...movie, is_wished: true }
    wishMovies.value = [optimistic, ...wishMovies.value]
    setSelectedWishFlag(movie.id, true)
    try {
      const response = await setMovieWished(movie.id, true)
      const updated = response?.data?.data?.movie
      if (updated) {
        wishMovies.value = wishMovies.value.map((m) => (m.id === movie.id ? updated : m))
      }
      wishSyncError.value = ''
    } catch (error) {
      // rollback
      wishMovies.value = wishMovies.value.filter((m) => m.id !== movie.id)
      setSelectedWishFlag(movie.id, false)
      wishSyncError.value = error?.response?.data?.error || error?.message || '加入想看失败'
      console.error('加入想看失败:', error)
      throw error
    }
  }

  const removeFromWishMovies = async (movieId) => {
    const previous = wishMovies.value.find((m) => m.id === movieId)
    if (!previous) return
    wishMovies.value = wishMovies.value.filter((m) => m.id !== movieId)
    setSelectedWishFlag(movieId, false)
    try {
      await setMovieWished(movieId, false)
      wishSyncError.value = ''
    } catch (error) {
      // rollback
      wishMovies.value = [previous, ...wishMovies.value]
      setSelectedWishFlag(movieId, true)
      wishSyncError.value = error?.response?.data?.error || error?.message || '移出想看失败'
      console.error('移出想看失败:', error)
      throw error
    }
  }

  const initializeWishSync = async () => {
    try {
      const response = await getWishedMovies()
      const movies = response?.data?.data?.movies || []
      wishMovies.value = movies
      syncSelectedWishFlags()
      wishSyncError.value = ''
    } catch (error) {
      wishSyncError.value = error?.response?.data?.error || error?.message || '想看列表同步失败'
      console.error('初始化想看列表失败:', error)
    } finally {
      wishSyncReady.value = true
    }
  }

  return {
    selectedMovies,
    wishMovies,
    wishSyncError,
    wishSyncReady,
    isInWishMovies,
    setSelectedMovies,
    updateMovieScore,
    addToWishMovies,
    removeFromWishMovies,
    initializeWishSync,
  }
})
