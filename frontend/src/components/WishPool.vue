<template>
  <el-card
    class="planning-card wish-planning-card"
    :body-style="store.wishMovies.length === 0 ? { display: 'none' } : undefined"
  >
    <template #header>
      <div class="planning-header">
        <div class="planning-header-main">
          <span>想看</span>
          <span class="planning-header-summary">
            {{ store.wishMovies.length }} 部
          </span>
        </div>
        <div v-if="store.wishMovies.length > 0" class="planning-header-actions">
          <el-button
            type="primary"
            size="small"
            :loading="batchFetching"
            @click="handleBatchFetch"
          >
            一键抓取&更新场次
          </el-button>
        </div>
      </div>
      <div v-if="batchFetching || batchTotal > 0" class="batch-progress">
        <el-progress
          :percentage="batchPercentage"
          :status="batchDone >= batchTotal && batchTotal > 0 ? 'success' : undefined"
          :format="() => `${batchDone}/${batchTotal} 部完成`"
        />
      </div>
    </template>

    <div v-if="store.wishMovies.length > 0" class="wish-movie-list">
      <MovieCard
        v-for="(movie, index) in store.wishMovies"
        :key="movie.id"
        :movie="movie"
        :index="index"
        mode="wish"
        :is-fetching="fetchingMovieIds.has(movie.id)"
        :is-douban-fetching="doubanFetchingIds.has(movie.id)"
        :movie-progress-text="movieProgress.get(movie.id) || ''"
        :movie-fetch-date-entries="getMovieDateProgressEntries(movie.id)"
        :shows-data="store.getMovieShowsData(movie.id)"
        :has-valid-shows="store.hasMovieShowsData(movie.id)"
        @fetch-single-show="handleFetchSingleShow"
        @fetch-douban="handleFetchDouban"
        @remove-wish-movie="handleRemoveWishMovie"
        @add-to-schedule="handleAddToSchedule"
      />
    </div>
  </el-card>
</template>

<script setup>
import { fetchMovieDouban } from '@/api'
import { ElMessage, ElMessageBox } from 'element-plus'
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useShowFetching } from '@/composables/useShowFetching'
import { useScheduleStore } from '@/stores/scheduleStore'
import { parseShowTimeToMinutes } from '@/utils/showTime'
import MovieCard from '@/components/MovieCard.vue'

const props = defineProps({
  updateForm: {
    type: Object,
    required: true,
  },
})

const store = useScheduleStore()

const {
  fetchingMovieIds,
  movieProgress,
  getMovieDateProgressEntries,
  handleFetchSingleShow,
  handleBatchFetchShows,
  batchFetching,
  batchTotal,
  batchDone,
  scheduleMidnightCleanup,
  stopMidnightCleanup,
} = useShowFetching(store, props.updateForm)

const doubanFetchingIds = ref(new Set())

onMounted(() => {
  scheduleMidnightCleanup()
})

onBeforeUnmount(() => {
  stopMidnightCleanup()
})

const batchPercentage = computed(() => {
  if (!batchTotal.value) return 0
  return Math.round((batchDone.value / batchTotal.value) * 100)
})

const handleBatchFetch = async () => {
  if (batchFetching.value) return
  const movies = store.wishMovies
  if (movies.length === 0) {
    ElMessage.warning('想看列表为空')
    return
  }
  await handleBatchFetchShows(movies)
}

const parseMovieDurationMinutes = (durationText) => {
  const normalized = String(durationText ?? '').trim()
  const match = normalized.match(/(\d+)/)
  return match ? Number(match[1]) : null
}

const getShowEntryDurationMinutes = (showEntry) => {
  if (typeof showEntry?.durationMinutes === 'number' && !Number.isNaN(showEntry.durationMinutes)) {
    return showEntry.durationMinutes
  }
  const movie = store.wishMovies.find((item) => item.id === showEntry?.movieId)
  return parseMovieDurationMinutes(movie?.duration)
}

const getScheduleConflict = (showEntry) => {
  const targetStart = parseShowTimeToMinutes(showEntry.time)
  const targetDuration = getShowEntryDurationMinutes(showEntry)

  return store.scheduleItems.find((item) => {
    if (item.date !== showEntry.date) return false
    const itemStart = parseShowTimeToMinutes(item.time)
    const itemDuration = getShowEntryDurationMinutes(item)
    if (targetStart == null || itemStart == null || targetDuration == null || itemDuration == null) {
      return item.time === showEntry.time
    }
    const targetEnd = targetStart + targetDuration
    const itemEnd = itemStart + itemDuration
    return targetStart < itemEnd && itemStart < targetEnd
  }) || null
}

const handleAddToSchedule = (showEntry) => {
  if (store.isInSchedule(showEntry.key)) return
  const conflictItem = getScheduleConflict(showEntry)
  if (conflictItem) {
    ElMessage.warning(
      `加入行程失败：${showEntry.date} ${showEntry.time} 与《${conflictItem.movieTitle}》冲突`
    )
    return
  }
  store.addToSchedule(showEntry)
  ElMessage.success(`已将《${showEntry.movieTitle}》加入行程`)
}

const handleRemoveWishMovie = async (movie) => {
  if (!movie?.id) return
  if (store.hasScheduleForMovie(movie.id)) {
    ElMessage.warning(`《${movie.title}》还有场次在行程中,请先从行程移除`)
    return
  }
  try {
    await ElMessageBox.confirm(
      `确认将《${movie.title}》从想看中移除?`,
      '移除想看',
      {
        type: 'warning',
        confirmButtonText: '移除',
        cancelButtonText: '取消',
      }
    )
  } catch {
    return
  }
  try {
    await store.removeFromWishMovies(movie.id)
    store.removeMovieShowsData(movie.id)
    ElMessage.info(`已将《${movie.title}》移出想看`)
  } catch {
    // store 已 rollback;wishSyncError watcher 会提示
  }
}

const handleFetchDouban = async (movie) => {
  if (!movie?.id) return
  doubanFetchingIds.value = new Set([...doubanFetchingIds.value, movie.id])
  try {
    const res = await fetchMovieDouban(movie.id)
    const { score, douban_url } = res.data.data
    store.updateMovieScore(movie.id, score, douban_url)
    if (douban_url) {
      ElMessage.success(`《${movie.title}》豆瓣评分：${score}`)
    } else {
      ElMessage.warning(`《${movie.title}》未找到豆瓣匹配条目`)
    }
  } catch (error) {
    const msg = error?.response?.data?.detail || error?.message || '未知错误'
    ElMessage.error(`获取豆瓣信息失败：${msg}`)
  } finally {
    const next = new Set(doubanFetchingIds.value)
    next.delete(movie.id)
    doubanFetchingIds.value = next
  }
}
</script>

<style scoped>
.planning-card {
  margin-top: 16px;
}

.wish-planning-card {
  margin-bottom: 10px;
}

.planning-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.planning-header-main {
  display: flex;
  align-items: baseline;
  gap: 10px;
  min-width: 0;
  flex-wrap: wrap;
}

.planning-header-summary {
  color: #64748b;
  font-size: 13px;
  font-weight: 500;
  white-space: nowrap;
}

.planning-header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.batch-progress {
  margin-top: 12px;
}

.wish-movie-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

@media (max-width: 960px) {
  .planning-header {
    align-items: flex-start;
    flex-direction: column;
  }

  .planning-header-main {
    width: 100%;
    flex-wrap: wrap;
  }

  .planning-header-actions {
    width: 100%;
    justify-content: flex-start;
    flex-wrap: wrap;
  }
}
</style>
