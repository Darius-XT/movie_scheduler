import { defineStore } from 'pinia'
import { ref, watch } from 'vue'
import { getMovieUpdateStatus } from '@/api'
import { loadFromStorage, saveToStorage } from './storage'

const CINEMA_UPDATE_META_KEY = 'cinemaUpdateMeta'
const CINEMA_UPDATE_RESULT_KEY = 'cinemaUpdateResult'
const EMPTY_UPDATE_META = { lastUpdatedAt: null, durationMs: null }

export const useUpdateMetaStore = defineStore('updateMeta', () => {
  // 影院:保留手动按钮,本地状态持久化
  const cinemaUpdateMeta = ref(loadFromStorage(CINEMA_UPDATE_META_KEY, EMPTY_UPDATE_META))
  const cinemaUpdateResult = ref(loadFromStorage(CINEMA_UPDATE_RESULT_KEY, null))

  watch(cinemaUpdateMeta, (val) => saveToStorage(CINEMA_UPDATE_META_KEY, val), { deep: true })
  watch(cinemaUpdateResult, (val) => saveToStorage(CINEMA_UPDATE_RESULT_KEY, val), { deep: true })

  const recordCinemaUpdate = (result, durationMs) => {
    cinemaUpdateResult.value = result
    cinemaUpdateMeta.value = { lastUpdatedAt: Date.now(), durationMs }
  }

  // 电影:后端每小时自动更新,前端只读 GET /update/movies/status 的 last_updated_at
  const movieLastUpdatedAt = ref(null)
  const movieStatusError = ref('')

  const refreshMovieStatus = async () => {
    try {
      const response = await getMovieUpdateStatus()
      movieLastUpdatedAt.value = response?.data?.data?.last_updated_at || null
      movieStatusError.value = ''
    } catch (error) {
      movieStatusError.value = error?.response?.data?.error || error?.message || '获取电影更新状态失败'
      console.error('获取电影更新状态失败:', error)
    }
  }

  return {
    cinemaUpdateMeta,
    cinemaUpdateResult,
    recordCinemaUpdate,
    movieLastUpdatedAt,
    movieStatusError,
    refreshMovieStatus,
  }
})
