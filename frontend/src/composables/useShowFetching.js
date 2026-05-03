import { streamShows } from '@/api'
import { ElMessage } from 'element-plus'
import { ref } from 'vue'

const COMPLETE_TRANSITION_MS = 1200
const MIDNIGHT_BUFFER_MS = 100

const waitForProgressTransition = () =>
  new Promise((resolve) => window.setTimeout(resolve, COMPLETE_TRANSITION_MS))

const getTotalShows = (movieShowData) => {
  if (!movieShowData || !movieShowData.cinemas) return 0
  return movieShowData.cinemas.reduce((total, cinema) => total + (cinema.shows?.length || 0), 0)
}

export const useShowFetching = (store, updateForm) => {
  const fetchingMovieIds = ref(new Set())
  const movieProgress = ref(new Map())
  const movieFetchDetails = ref(new Map())
  let midnightCleanupTimer = null

  const ensureMovieFetchDetails = (movieId) => {
    if (!movieFetchDetails.value.has(movieId)) {
      movieFetchDetails.value.set(movieId, { dates: {} })
    }
    return movieFetchDetails.value.get(movieId)
  }

  const initializeMovieDates = (movieId, dates) => {
    const details = ensureMovieFetchDetails(movieId)
    const nextDates = {}
    dates.forEach((date) => {
      const current = details.dates[date]
      nextDates[date] = { done: current?.done ?? 0, total: current?.total ?? 0, active: current?.active ?? false }
    })
    details.dates = nextDates
  }

  const updateMovieDateProgress = (movieId, targetDate, patch) => {
    const details = ensureMovieFetchDetails(movieId)
    const dates = { ...details.dates }
    Object.keys(dates).forEach((date) => { dates[date] = { ...dates[date], active: false } })
    const current = dates[targetDate] ?? { done: 0, total: 0, active: false }
    dates[targetDate] = { ...current, ...patch }
    details.dates = dates
  }

  const clearMovieFetchProgress = (movieIds) => {
    movieIds.forEach((movieId) => {
      movieFetchDetails.value.delete(movieId)
      movieProgress.value.delete(movieId)
    })
  }

  const getMovieDateProgressEntries = (movieId) => {
    const details = movieFetchDetails.value.get(movieId)
    if (!details) return []
    return Object.entries(details.dates)
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([date, info]) => ({ date, ...info }))
  }

  const clearAllMovieFetchProgress = () => {
    movieFetchDetails.value.clear()
    movieProgress.value.clear()
  }

  const msUntilNextMidnight = () => {
    const now = new Date()
    const next = new Date(now)
    next.setHours(24, 0, 0, MIDNIGHT_BUFFER_MS)
    return Math.max(next.getTime() - now.getTime(), MIDNIGHT_BUFFER_MS)
  }

  const stopMidnightCleanup = () => {
    if (midnightCleanupTimer != null) {
      window.clearTimeout(midnightCleanupTimer)
      midnightCleanupTimer = null
    }
  }

  const scheduleMidnightCleanup = () => {
    stopMidnightCleanup()
    midnightCleanupTimer = window.setTimeout(() => {
      store.pruneStaleMovieShows()
      scheduleMidnightCleanup()
    }, msUntilNextMidnight())
  }

  const handleFetchSingleShow = async (movie) => {
    if (!movie.id) {
      ElMessage.warning('电影ID无效')
      return
    }

    fetchingMovieIds.value = new Set([...fetchingMovieIds.value, movie.id])
    movieProgress.value.set(movie.id, '开始获取场次信息...')
    movieFetchDetails.value.delete(movie.id)

    try {
      const response = await streamShows([movie.id], updateForm.value.cityId)
      if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`)

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop()

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          const data = JSON.parse(line.substring(6))

          if (data.type === 'dates_found') {
            initializeMovieDates(movie.id, data.dates)
            movieProgress.value.set(movie.id, `找到 ${data.dates.length} 个排片日期`)
          } else if (data.type === 'processing_date') {
            updateMovieDateProgress(movie.id, data.date, { active: true })
            movieProgress.value.set(movie.id, `处理日期 ${data.date_idx}/${data.total_dates}: ${data.date}`)
          } else if (data.type === 'processing_cinema') {
            updateMovieDateProgress(movie.id, data.date, {
              done: data.cinema_idx,
              total: data.total_cinemas,
              active: true,
            })
            movieProgress.value.set(movie.id, `日期 ${data.date} - 影院 ${data.cinema_idx}/${data.total_cinemas}`)
          } else if (data.type === 'complete') {
            const shows = data.data
            const showItem = shows[0]
            const totalShows = showItem ? getTotalShows(showItem) : 0

            movieProgress.value.set(
              movie.id,
              showItem ? `抓取完成，共 ${totalShows} 个场次` : '抓取完成，暂无场次'
            )
            await waitForProgressTransition()
            clearMovieFetchProgress([movie.id])

            if (shows.length > 0) {
              store.setMovieShowsData(movie.id, { ...showItem, cachedAt: Date.now() })
              ElMessage.success(`成功获取《${movie.title}》的场次信息（共 ${totalShows} 个场次）`)
            } else {
              ElMessage.warning(`电影《${movie.title}》暂无场次信息`)
            }
          } else if (data.type === 'error') {
            ElMessage.error('获取失败: ' + data.error)
            clearMovieFetchProgress([movie.id])
          }
        }
      }
    } catch (error) {
      ElMessage.error('获取失败: ' + error.message)
      clearMovieFetchProgress([movie.id])
    } finally {
      const next = new Set(fetchingMovieIds.value)
      next.delete(movie.id)
      fetchingMovieIds.value = next
    }
  }

  return {
    fetchingMovieIds,
    movieProgress,
    getMovieDateProgressEntries,
    clearAllMovieFetchProgress,
    handleFetchSingleShow,
    scheduleMidnightCleanup,
    stopMidnightCleanup,
  }
}
