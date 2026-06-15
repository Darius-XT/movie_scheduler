import { defineStore, storeToRefs } from 'pinia'
import { useMovieSelectionStore } from './movieSelectionStore'
import { usePlanningStore } from './planningStore'
import { useShowCacheStore } from './showCacheStore'
import { useUpdateMetaStore } from './updateMetaStore'

export const useScheduleStore = defineStore('schedule', () => {
  const movieSelectionStore = useMovieSelectionStore()
  const planningStore = usePlanningStore()
  const showCacheStore = useShowCacheStore()
  const updateMetaStore = useUpdateMetaStore()

  const { selectedMovies, wishMovies, wishSyncError, wishSyncReady } =
    storeToRefs(movieSelectionStore)
  const {
    scheduleItems,
    scheduleSyncError,
    scheduleSyncReady,
    scheduleSyncInFlight,
  } = storeToRefs(planningStore)
  const {
    movieShowsMap,
    lastFetchedAt: showsLastFetchedAt,
    syncing: showsSyncing,
    syncError: showsSyncError,
    showsUpdateMeta,
    showsUpdateResult,
  } = storeToRefs(showCacheStore)
  const {
    cinemaUpdateMeta,
    cinemaUpdateResult,
    movieUpdateMeta,
    movieUpdateResult,
    movieLastUpdatedAt,
    movieStatusError,
  } = storeToRefs(updateMetaStore)

  return {
    selectedMovies,
    wishMovies,
    scheduleItems,
    movieShowsMap,
    showsLastFetchedAt,
    showsSyncing,
    showsSyncError,
    showsUpdateMeta,
    showsUpdateResult,
    cinemaUpdateMeta,
    cinemaUpdateResult,
    movieUpdateMeta,
    movieUpdateResult,
    movieLastUpdatedAt,
    movieStatusError,
    wishSyncError,
    wishSyncReady,
    scheduleSyncError,
    scheduleSyncReady,
    scheduleSyncInFlight,
    setSelectedMovies: movieSelectionStore.setSelectedMovies,
    updateMovieScore: movieSelectionStore.updateMovieScore,
    refreshShowsFromBackend: showCacheStore.refreshFromBackend,
    refreshMovieShowsFromBackend: showCacheStore.refreshMovieFromBackend,
    pollMovieShowsUntilUpdated: showCacheStore.pollMovieShowsUntilUpdated,
    removeMovieShows: showCacheStore.removeMovieShows,
    getMovieShowsData: showCacheStore.getMovieShowsData,
    hasMovieShowsData: showCacheStore.hasMovieShowsData,
    recordShowUpdate: showCacheStore.recordShowUpdate,
    isInWishMovies: movieSelectionStore.isInWishMovies,
    addToWishMovies: movieSelectionStore.addToWishMovies,
    removeFromWishMovies: movieSelectionStore.removeFromWishMovies,
    initializeWishSync: movieSelectionStore.initializeWishSync,
    isInSchedule: planningStore.isInSchedule,
    addToSchedule: planningStore.addToSchedule,
    removeFromSchedule: planningStore.removeFromSchedule,
    toggleSchedulePurchased: planningStore.toggleSchedulePurchased,
    removePastSchedules: planningStore.removePastSchedules,
    hasScheduleForMovie: planningStore.hasScheduleForMovie,
    recordCinemaUpdate: updateMetaStore.recordCinemaUpdate,
    recordMovieUpdate: updateMetaStore.recordMovieUpdate,
    refreshMovieStatus: updateMetaStore.refreshMovieStatus,
    initializeScheduleSync: planningStore.initializeScheduleSync,
    persistScheduleToBackend: planningStore.persistScheduleToBackend,
  }
})
