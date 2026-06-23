import { defineStore } from 'pinia'
import { computed, ref, watch } from 'vue'
import { getMovieUpdateStatus } from '@/api'
import { loadFromStorage, saveToStorage } from './storage'

const CINEMA_UPDATE_META_KEY = 'cinemaUpdateMeta'
const CINEMA_UPDATE_RESULT_KEY = 'cinemaUpdateResult'
const MOVIE_UPDATE_META_KEY = 'movieUpdateMeta'
const MOVIE_UPDATE_RESULT_KEY = 'movieUpdateResult'
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

  // 电影:既支持手动按钮,也保留只读拉取定时任务时间戳。
  // lastUpdatedAt 优先用后端 SSE complete 事件返回的 ISO 字符串(口径与定时任务一致);
  // 没有手动记录时 fallback 到 GET /movies/update-status 拉到的 backendMovieLastUpdatedAt。
  const movieUpdateMeta = ref(loadFromStorage(MOVIE_UPDATE_META_KEY, EMPTY_UPDATE_META))
  const movieUpdateResult = ref(loadFromStorage(MOVIE_UPDATE_RESULT_KEY, null))
  const backendMovieLastUpdatedAt = ref(null)
  const movieStatusError = ref('')

  watch(movieUpdateMeta, (val) => saveToStorage(MOVIE_UPDATE_META_KEY, val), { deep: true })
  watch(movieUpdateResult, (val) => saveToStorage(MOVIE_UPDATE_RESULT_KEY, val), { deep: true })

  const recordMovieUpdate = (result, durationMs, lastUpdatedAtFromBackend) => {
    movieUpdateResult.value = result
    movieUpdateMeta.value = {
      lastUpdatedAt: lastUpdatedAtFromBackend || null,
      durationMs,
    }
    if (lastUpdatedAtFromBackend) backendMovieLastUpdatedAt.value = lastUpdatedAtFromBackend
  }

  const movieLastUpdatedAt = computed(() => (
    latestTimestamp(movieUpdateMeta.value.lastUpdatedAt, backendMovieLastUpdatedAt.value)
  ))

  const refreshMovieStatus = async () => {
    try {
      const response = await getMovieUpdateStatus()
      backendMovieLastUpdatedAt.value = response?.data?.data?.last_updated_at || null
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
    movieUpdateMeta,
    movieUpdateResult,
    recordMovieUpdate,
    movieLastUpdatedAt,
    movieStatusError,
    refreshMovieStatus,
  }
})

const latestTimestamp = (left, right) => {
  if (!left) return right || null
  if (!right) return left || null
  const leftTime = Date.parse(left)
  const rightTime = Date.parse(right)
  if (Number.isNaN(leftTime) || Number.isNaN(rightTime)) {
    return String(left) > String(right) ? left : right
  }
  return leftTime >= rightTime ? left : right
}
