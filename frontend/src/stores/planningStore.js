import { defineStore } from 'pinia'
import { ref, watch } from 'vue'
import { getPlanning, savePlanning } from '@/api'
import { getShowEndDate } from '@/utils/showTime'
import { loadFromStorage, saveToStorage } from './storage'

const WISH_POOL_KEY = 'wishPool'
const SCHEDULE_ITEMS_KEY = 'scheduleItems'

export const usePlanningStore = defineStore('planning', () => {
  const wishPool = ref(loadFromStorage(WISH_POOL_KEY, []))
  const scheduleItems = ref(loadFromStorage(SCHEDULE_ITEMS_KEY, []))
  const planningSyncError = ref('')
  const planningSyncReady = ref(false)
  const planningSyncInFlight = ref(false)

  let suppressPlanningPersist = false
  let planningSyncPending = false

  watch(wishPool, (val) => saveToStorage(WISH_POOL_KEY, val), { deep: true })
  watch(scheduleItems, (val) => saveToStorage(SCHEDULE_ITEMS_KEY, val), { deep: true })

  const buildPlanningPayload = () => ({
    wish_pool: wishPool.value,
    schedule_items: scheduleItems.value,
  })

  const hasLocalPlanning = () => wishPool.value.length > 0 || scheduleItems.value.length > 0

  const hasRemotePlanning = (planning) =>
    (planning?.wish_pool?.length || 0) > 0 || (planning?.schedule_items?.length || 0) > 0

  const applyRemotePlanning = (planning) => {
    suppressPlanningPersist = true
    wishPool.value = planning?.wish_pool || []
    scheduleItems.value = planning?.schedule_items || []
    suppressPlanningPersist = false
  }

  const persistPlanningToBackend = async () => {
    if (!planningSyncReady.value || suppressPlanningPersist) return
    if (planningSyncInFlight.value) {
      planningSyncPending = true
      return
    }
    planningSyncInFlight.value = true
    try {
      await savePlanning(buildPlanningPayload())
      planningSyncError.value = ''
    } catch (error) {
      planningSyncError.value = error?.response?.data?.error || error?.message || '计划同步失败'
      console.error('保存计划失败:', error)
    } finally {
      planningSyncInFlight.value = false
      if (planningSyncPending) {
        planningSyncPending = false
        void persistPlanningToBackend()
      }
    }
  }

  const initializePlanningSync = async () => {
    try {
      const response = await getPlanning()
      const remotePlanning = response.data.data
      if (hasRemotePlanning(remotePlanning)) {
        applyRemotePlanning(remotePlanning)
      } else if (hasLocalPlanning()) {
        await savePlanning(buildPlanningPayload())
      }
      planningSyncError.value = ''
    } catch (error) {
      planningSyncError.value = error?.response?.data?.error || error?.message || '计划同步初始化失败'
      console.error('初始化计划同步失败:', error)
    } finally {
      planningSyncReady.value = true
    }
  }

  const persistPlanningAfterMutation = () => {
    void persistPlanningToBackend()
  }

  const isInWishPool = (showKey) => {
    return wishPool.value.some((item) => item.key === showKey)
  }

  const addToWishPool = (showEntry) => {
    if (isInWishPool(showEntry.key)) return
    wishPool.value = [...wishPool.value, showEntry]
    persistPlanningAfterMutation()
  }

  const removeFromWishPool = (showKey) => {
    wishPool.value = wishPool.value.filter((item) => item.key !== showKey)
    persistPlanningAfterMutation()
  }

  const removeWishMovieGroup = (movieId) => {
    wishPool.value = wishPool.value.filter((item) => item.movieId !== movieId)
    persistPlanningAfterMutation()
  }

  const addManyToWishPool = (entries) => {
    const newEntries = entries.filter((e) => !isInWishPool(e.key))
    if (newEntries.length > 0) {
      wishPool.value = [...wishPool.value, ...newEntries]
      persistPlanningAfterMutation()
    }
    return newEntries.length
  }

  const isInSchedule = (showKey) => {
    return scheduleItems.value.some((item) => item.key === showKey)
  }

  const addToSchedule = (showEntry) => {
    if (isInSchedule(showEntry.key)) return
    scheduleItems.value = [...scheduleItems.value, { ...showEntry, purchased: false }]
    persistPlanningAfterMutation()
  }

  const removeFromSchedule = (showKey) => {
    scheduleItems.value = scheduleItems.value.filter((item) => item.key !== showKey)
    persistPlanningAfterMutation()
  }

  const moveFromScheduleToWishPool = (showKey) => {
    const targetItem = scheduleItems.value.find((item) => item.key === showKey)
    scheduleItems.value = scheduleItems.value.filter((item) => item.key !== showKey)
    if (targetItem && !isInWishPool(showKey)) {
      const { purchased, ...wishEntry } = targetItem
      wishPool.value = [...wishPool.value, wishEntry]
    }
    persistPlanningAfterMutation()
  }

  const toggleSchedulePurchased = (showKey) => {
    scheduleItems.value = scheduleItems.value.map((item) => {
      if (item.key !== showKey) return item
      return { ...item, purchased: !item.purchased }
    })
    persistPlanningAfterMutation()
  }

  const removePastSchedules = () => {
    const now = new Date()
    const before = scheduleItems.value.length
    scheduleItems.value = scheduleItems.value.filter((item) => {
      const endDate = getShowEndDate(item.date, item.time, item.durationMinutes)
      return endDate == null || endDate >= now
    })
    if (before !== scheduleItems.value.length) persistPlanningAfterMutation()
    return before - scheduleItems.value.length
  }

  return {
    wishPool,
    scheduleItems,
    planningSyncError,
    planningSyncReady,
    planningSyncInFlight,
    isInWishPool,
    addToWishPool,
    removeFromWishPool,
    removeWishMovieGroup,
    addManyToWishPool,
    isInSchedule,
    addToSchedule,
    removeFromSchedule,
    moveFromScheduleToWishPool,
    toggleSchedulePurchased,
    removePastSchedules,
    initializePlanningSync,
    persistPlanningToBackend,
  }
})
