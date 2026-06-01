import { defineStore } from 'pinia'
import { ref } from 'vue'
import { getPlanning, saveScheduleItems } from '@/api'
import { getShowEndDate } from '@/utils/showTime'
import { removeFromStorage } from './storage'

const LEGACY_SCHEDULE_ITEMS_KEY = 'scheduleItems'
const LEGACY_WISH_POOL_KEY = 'wishPool'

export const usePlanningStore = defineStore('planning', () => {
  // 清理历史 localStorage:排片以后端为唯一 source of truth,不再做本地缓存
  // (老版本的 scheduleItems 缓存会在多设备场景下用旧数据覆盖远端,故彻底移除)
  removeFromStorage(LEGACY_WISH_POOL_KEY)
  removeFromStorage(LEGACY_SCHEDULE_ITEMS_KEY)

  const scheduleItems = ref([])
  const scheduleSyncError = ref('')
  const scheduleSyncReady = ref(false)
  const scheduleSyncInFlight = ref(false)

  let suppressSchedulePersist = false
  let scheduleSyncPending = false

  const applyRemoteSchedule = (planning) => {
    suppressSchedulePersist = true
    scheduleItems.value = planning?.schedule_items || []
    suppressSchedulePersist = false
  }

  const persistScheduleToBackend = async () => {
    if (!scheduleSyncReady.value || suppressSchedulePersist) return
    if (scheduleSyncInFlight.value) {
      scheduleSyncPending = true
      return
    }
    scheduleSyncInFlight.value = true
    try {
      await saveScheduleItems(scheduleItems.value)
      scheduleSyncError.value = ''
    } catch (error) {
      scheduleSyncError.value = error?.response?.data?.error || error?.message || '行程同步失败'
      console.error('保存行程失败:', error)
    } finally {
      scheduleSyncInFlight.value = false
      if (scheduleSyncPending) {
        scheduleSyncPending = false
        void persistScheduleToBackend()
      }
    }
  }

  const initializeScheduleSync = async () => {
    try {
      const response = await getPlanning()
      applyRemoteSchedule(response.data.data)
      scheduleSyncError.value = ''
    } catch (error) {
      scheduleSyncError.value = error?.response?.data?.error || error?.message || '行程同步初始化失败'
      console.error('初始化行程同步失败:', error)
    } finally {
      scheduleSyncReady.value = true
    }
  }

  const persistScheduleAfterMutation = () => {
    void persistScheduleToBackend()
  }

  const isInSchedule = (showKey) => scheduleItems.value.some((item) => item.key === showKey)

  const addToSchedule = (showEntry) => {
    if (isInSchedule(showEntry.key)) return
    scheduleItems.value = [...scheduleItems.value, { ...showEntry, purchased: false }]
    persistScheduleAfterMutation()
  }

  const removeFromSchedule = (showKey) => {
    scheduleItems.value = scheduleItems.value.filter((item) => item.key !== showKey)
    persistScheduleAfterMutation()
  }

  const toggleSchedulePurchased = (showKey) => {
    scheduleItems.value = scheduleItems.value.map((item) => {
      if (item.key !== showKey) return item
      return { ...item, purchased: !item.purchased }
    })
    persistScheduleAfterMutation()
  }

  const removePastSchedules = () => {
    const now = new Date()
    const before = scheduleItems.value.length
    scheduleItems.value = scheduleItems.value.filter((item) => {
      const endDate = getShowEndDate(item.date, item.time, item.durationMinutes)
      return endDate == null || endDate >= now
    })
    if (before !== scheduleItems.value.length) persistScheduleAfterMutation()
    return before - scheduleItems.value.length
  }

  const hasScheduleForMovie = (movieId) =>
    scheduleItems.value.some((item) => item.movieId === movieId)

  return {
    scheduleItems,
    scheduleSyncError,
    scheduleSyncReady,
    scheduleSyncInFlight,
    isInSchedule,
    addToSchedule,
    removeFromSchedule,
    toggleSchedulePurchased,
    removePastSchedules,
    hasScheduleForMovie,
    initializeScheduleSync,
    persistScheduleToBackend,
  }
})
