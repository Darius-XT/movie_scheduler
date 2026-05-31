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

const readSseStream = async (response, onData) => {
  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() || ''
    for (const line of lines) {
      if (!line.startsWith('data: ')) continue
      const data = JSON.parse(line.substring(6))
      onData(data)
    }
  }
}

export const useShowFetching = (store, updateForm) => {
  const fetchingMovieIds = ref(new Set())
  const movieProgress = ref(new Map())
  const movieFetchDetails = ref(new Map())
  const batchFetching = ref(false)
  const batchTotal = ref(0)
  const batchDone = ref(0)
  let midnightCleanupTimer = null

  const markFetchingStart = (movieId) => {
    fetchingMovieIds.value = new Set([...fetchingMovieIds.value, movieId])
  }

  const markFetchingEnd = (movieId) => {
    const next = new Set(fetchingMovieIds.value)
    next.delete(movieId)
    fetchingMovieIds.value = next
  }

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

  // 核心抓取流程:同时服务"单部"与"批量"。movies 数组中每部电影各有独立进度;
  // 后端 SSE 事件都带 movie_id,前端按 movie_id 分发进度。
  const runFetchShows = async (movies) => {
    const valid = (movies || []).filter((m) => m?.id && m.is_showing !== false)
    if (valid.length === 0) {
      ElMessage.warning('没有可抓取的电影')
      return
    }
    const movieIds = valid.map((m) => m.id)
    const movieById = new Map(valid.map((m) => [m.id, m]))

    if (movieIds.length > 1) {
      batchFetching.value = true
      batchTotal.value = movieIds.length
      batchDone.value = 0
    }

    movieIds.forEach((id) => {
      markFetchingStart(id)
      movieProgress.value.set(id, '开始获取场次信息...')
      movieFetchDetails.value.delete(id)
    })

    try {
      const response = await streamShows(movieIds, updateForm?.value?.cityId)
      if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`)

      await readSseStream(response, async (data) => {
        const movieId = data.movie_id
        if (data.type === 'dates_found') {
          if (movieId != null) {
            initializeMovieDates(movieId, data.dates)
            movieProgress.value.set(movieId, `找到 ${data.dates.length} 个排片日期`)
          }
        } else if (data.type === 'processing_date') {
          if (movieId != null) {
            updateMovieDateProgress(movieId, data.date, { active: true })
            movieProgress.value.set(movieId, `处理日期 ${data.date_idx}/${data.total_dates}: ${data.date}`)
          }
        } else if (data.type === 'processing_cinema') {
          if (movieId != null) {
            updateMovieDateProgress(movieId, data.date, {
              done: data.cinema_idx,
              total: data.total_cinemas,
              active: true,
            })
            movieProgress.value.set(movieId, `日期 ${data.date} - 影院 ${data.cinema_idx}/${data.total_cinemas}`)
          }
        } else if (data.type === 'movie_complete') {
          if (movieId != null) {
            const movie = movieById.get(movieId)
            const label = data.has_shows ? '抓取完成' : '暂无场次'
            movieProgress.value.set(movieId, label)
            markFetchingEnd(movieId)
            if (movieIds.length > 1) {
              batchDone.value += 1
            }
            if (movie && !data.has_shows) {
              ElMessage.warning(`电影《${movie.title}》暂无场次信息`)
            }
          }
        } else if (data.type === 'complete') {
          const shows = data.data || []
          shows.forEach((showItem) => {
            const id = showItem?.movie_id
            if (id != null) {
              const totalShows = getTotalShows(showItem)
              store.setMovieShowsData(id, { ...showItem, cachedAt: Date.now() })
              const movie = movieById.get(id)
              if (movie) {
                movieProgress.value.set(id, `抓取完成,共 ${totalShows} 个场次`)
                if (movieIds.length === 1) {
                  ElMessage.success(`成功获取《${movie.title}》的场次信息（共 ${totalShows} 个场次）`)
                }
              }
            }
          })
          await waitForProgressTransition()
          movieIds.forEach((id) => clearMovieFetchProgress([id]))
          if (movieIds.length > 1) {
            batchDone.value = batchTotal.value
            ElMessage.success(`一键抓取完成,共 ${shows.length} 部电影有场次`)
          }
        } else if (data.type === 'error') {
          ElMessage.error('获取失败: ' + data.error)
          movieIds.forEach((id) => clearMovieFetchProgress([id]))
        }
      })
    } catch (error) {
      ElMessage.error('获取失败: ' + error.message)
      movieIds.forEach((id) => clearMovieFetchProgress([id]))
    } finally {
      movieIds.forEach((id) => markFetchingEnd(id))
      if (movieIds.length > 1) {
        batchFetching.value = false
      }
    }
  }

  const handleFetchSingleShow = async (movie) => {
    if (!movie?.id) {
      ElMessage.warning('电影ID无效')
      return
    }
    await runFetchShows([movie])
  }

  const handleBatchFetchShows = async (movies) => {
    await runFetchShows(movies)
  }

  return {
    fetchingMovieIds,
    movieProgress,
    getMovieDateProgressEntries,
    clearAllMovieFetchProgress,
    handleFetchSingleShow,
    handleBatchFetchShows,
    batchFetching,
    batchTotal,
    batchDone,
    scheduleMidnightCleanup,
    stopMidnightCleanup,
  }
}
