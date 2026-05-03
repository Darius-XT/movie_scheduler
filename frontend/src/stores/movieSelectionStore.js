import { defineStore } from 'pinia'
import { ref, watch } from 'vue'
import { loadFromStorage, saveToStorage } from './storage'

const SELECTED_MOVIES_KEY = 'selectedMovies'

export const useMovieSelectionStore = defineStore('movieSelection', () => {
  const selectedMovies = ref(loadFromStorage(SELECTED_MOVIES_KEY, []))

  watch(selectedMovies, (val) => saveToStorage(SELECTED_MOVIES_KEY, val), { deep: true })

  const setSelectedMovies = (movies) => {
    selectedMovies.value = movies
  }

  const updateMovieScore = (movieId, score, doubanUrl) => {
    const movie = selectedMovies.value.find((m) => m.id === movieId)
    if (movie) {
      movie.score = score
      movie.douban_url = doubanUrl
    }
  }

  return {
    selectedMovies,
    setSelectedMovies,
    updateMovieScore,
  }
})
