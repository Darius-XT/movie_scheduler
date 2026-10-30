import { defineStore } from 'pinia'
import { computed, ref, watch } from 'vue'
import { createManualMovie, getWishedMovies, setMovieChannels, setMovieLabel, setMovieViewingLocation } from '@/api'
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

  const applyMovie = (updated) => {
    selectedMovies.value = selectedMovies.value.map((movie) =>
      movie.id === updated.id ? { ...movie, ...updated } : movie
    )
    const others = wishMovies.value.filter((movie) => movie.id !== updated.id)
    wishMovies.value = updated.is_wished ? [updated, ...others] : others
  }

  const updateMovieLabel = async (movie, label) => {
    const previous = { ...movie }
    applyMovie({ ...movie, is_wished: label === 'wished', is_skipped: label === 'skipped', is_watched: label === 'watched' })
    try {
      const response = await setMovieLabel(movie.id, label)
      applyMovie(response.data.data.movie)
      wishSyncError.value = ''
    } catch (error) {
      applyMovie(previous)
      wishSyncError.value = error?.response?.data?.error || error?.message || '更新电影标签失败'
      throw error
    }
  }

  const addToWishMovies = async (movie) => {
    if (!movie?.id || isInWishMovies(movie.id)) return
    await updateMovieLabel(movie, 'wished')
  }

  const removeFromWishMovies = async (movieId) => {
    const previous = wishMovies.value.find((m) => m.id === movieId)
    if (!previous) return
    await updateMovieLabel(previous, null)
  }

  const addManualMovie = async (title) => {
    const response = await createManualMovie(title)
    const movie = response.data.data.movie
    wishMovies.value = [movie, ...wishMovies.value]
    wishSyncError.value = ''
    return movie
  }

  const updateMovieChannels = async (movieId, channels) => {
    const response = await setMovieChannels(movieId, channels)
    const savedChannels = response.data.data.movie.channels
    // 只合并渠道字段,避免覆盖同时发生的标签或评分更新。
    selectedMovies.value = selectedMovies.value.map((movie) =>
      movie.id === movieId ? { ...movie, channels: savedChannels } : movie
    )
    wishMovies.value = wishMovies.value.map((movie) =>
      movie.id === movieId ? { ...movie, channels: savedChannels } : movie
    )
  }

  const updateMovieViewingLocation = async (movieId, viewingLocation) => {
    const response = await setMovieViewingLocation(movieId, viewingLocation)
    const saved = response.data.data.movie.viewing_location
    selectedMovies.value = selectedMovies.value.map((movie) =>
      movie.id === movieId ? { ...movie, viewing_location: saved } : movie
    )
    wishMovies.value = wishMovies.value.map((movie) =>
      movie.id === movieId ? { ...movie, viewing_location: saved } : movie
    )
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
    updateMovieLabel,
    updateMovieChannels,
    updateMovieViewingLocation,
    addManualMovie,
    removeFromWishMovies,
    initializeWishSync,
  }
})
