import { defineStore } from 'pinia'
import { computed, ref, watch } from 'vue'
import { loadFromStorage, saveToStorage } from './storage'

const STARRED_MOVIES_KEY = 'starredMovieIds'

export const useStarredMoviesStore = defineStore('starredMovies', () => {
  const starredMovieIds = ref(loadFromStorage(STARRED_MOVIES_KEY, []))

  watch(starredMovieIds, (val) => saveToStorage(STARRED_MOVIES_KEY, val), { deep: true })

  const starredMovieIdSet = computed(() => new Set(starredMovieIds.value))

  const isMovieStarred = (movieId) => starredMovieIdSet.value.has(movieId)

  const toggleMovieStarred = (movieId) => {
    if (movieId == null) return
    if (starredMovieIdSet.value.has(movieId)) {
      starredMovieIds.value = starredMovieIds.value.filter((id) => id !== movieId)
    } else {
      starredMovieIds.value = [...starredMovieIds.value, movieId]
    }
  }

  return {
    starredMovieIds,
    isMovieStarred,
    toggleMovieStarred,
  }
})
