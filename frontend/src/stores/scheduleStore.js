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

  const { selectedMovies } = storeToRefs(movieSelectionStore)
  const {
    wishPool,
    scheduleItems,
    planningSyncError,
    planningSyncReady,
    planningSyncInFlight,
  } = storeToRefs(planningStore)
  const { movieShowsMap } = storeToRefs(showCacheStore)
  const {
    cinemaUpdateMeta,
    movieUpdateMeta,
    cinemaUpdateResult,
    movieUpdateResult,
  } = storeToRefs(updateMetaStore)

  return {
    selectedMovies,
    wishPool,
    scheduleItems,
    movieShowsMap,
    cinemaUpdateMeta,
    movieUpdateMeta,
    cinemaUpdateResult,
    movieUpdateResult,
    planningSyncError,
    planningSyncReady,
    planningSyncInFlight,
    setSelectedMovies: movieSelectionStore.setSelectedMovies,
    updateMovieScore: movieSelectionStore.updateMovieScore,
    setMovieShowsData: showCacheStore.setMovieShowsData,
    removeMovieShowsData: showCacheStore.removeMovieShowsData,
    getMovieShowsData: showCacheStore.getMovieShowsData,
    hasMovieShowsData: showCacheStore.hasMovieShowsData,
    pruneStaleMovieShows: showCacheStore.pruneStaleMovieShows,
    isInWishPool: planningStore.isInWishPool,
    addToWishPool: planningStore.addToWishPool,
    removeFromWishPool: planningStore.removeFromWishPool,
    removeWishMovieGroup: planningStore.removeWishMovieGroup,
    addManyToWishPool: planningStore.addManyToWishPool,
    isInSchedule: planningStore.isInSchedule,
    addToSchedule: planningStore.addToSchedule,
    removeFromSchedule: planningStore.removeFromSchedule,
    moveFromScheduleToWishPool: planningStore.moveFromScheduleToWishPool,
    toggleSchedulePurchased: planningStore.toggleSchedulePurchased,
    removePastSchedules: planningStore.removePastSchedules,
    recordCinemaUpdate: updateMetaStore.recordCinemaUpdate,
    recordMovieUpdate: updateMetaStore.recordMovieUpdate,
    initializePlanningSync: planningStore.initializePlanningSync,
    persistPlanningToBackend: planningStore.persistPlanningToBackend,
  }
})
