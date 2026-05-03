import { defineStore } from 'pinia'
import { ref, watch } from 'vue'
import { loadFromStorage, saveToStorage } from './storage'

const CINEMA_UPDATE_META_KEY = 'cinemaUpdateMeta'
const MOVIE_UPDATE_META_KEY = 'movieUpdateMeta'
const CINEMA_UPDATE_RESULT_KEY = 'cinemaUpdateResult'
const MOVIE_UPDATE_RESULT_KEY = 'movieUpdateResult'
const EMPTY_UPDATE_META = { lastUpdatedAt: null, durationMs: null }

export const useUpdateMetaStore = defineStore('updateMeta', () => {
  const cinemaUpdateMeta = ref(loadFromStorage(CINEMA_UPDATE_META_KEY, EMPTY_UPDATE_META))
  const movieUpdateMeta = ref(loadFromStorage(MOVIE_UPDATE_META_KEY, EMPTY_UPDATE_META))
  const cinemaUpdateResult = ref(loadFromStorage(CINEMA_UPDATE_RESULT_KEY, null))
  const movieUpdateResult = ref(loadFromStorage(MOVIE_UPDATE_RESULT_KEY, null))

  watch(cinemaUpdateMeta, (val) => saveToStorage(CINEMA_UPDATE_META_KEY, val), { deep: true })
  watch(movieUpdateMeta, (val) => saveToStorage(MOVIE_UPDATE_META_KEY, val), { deep: true })
  watch(cinemaUpdateResult, (val) => saveToStorage(CINEMA_UPDATE_RESULT_KEY, val), { deep: true })
  watch(movieUpdateResult, (val) => saveToStorage(MOVIE_UPDATE_RESULT_KEY, val), { deep: true })

  const recordCinemaUpdate = (result, durationMs) => {
    cinemaUpdateResult.value = result
    cinemaUpdateMeta.value = { lastUpdatedAt: Date.now(), durationMs }
  }

  const recordMovieUpdate = (result, durationMs) => {
    movieUpdateResult.value = result
    movieUpdateMeta.value = { lastUpdatedAt: Date.now(), durationMs }
  }

  return {
    cinemaUpdateMeta,
    movieUpdateMeta,
    cinemaUpdateResult,
    movieUpdateResult,
    recordCinemaUpdate,
    recordMovieUpdate,
  }
})
