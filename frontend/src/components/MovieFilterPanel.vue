<template>
  <div class="movie-selector-section">
    <h3 class="section-title">
      <el-icon><Filter /></el-icon>
      <span>电影筛选</span>
    </h3>
    <el-form :model="form" label-width="84px" size="default">
      <el-form-item label="上映状态">
        <div class="threshold-input-wrapper">
          <el-select
            v-model="form.selectionMode"
            placeholder="请选择上映状态"
            style="width: 105px"
          >
            <el-option
              v-for="option in selectionModeOptions"
              :key="option.value"
              :label="option.label"
              :value="option.value"
            />
          </el-select>
        </div>
      </el-form-item>

      <el-form-item class="movie-selector-action-form-item">
        <el-space direction="vertical" :size="8">
          <el-button
            type="primary"
            :loading="selectLoading"
            @click="handleSelectMovies"
            style="width: 130px"
          >
            筛选喜欢的电影
          </el-button>
          <el-button
            type="success"
            :loading="fetchLoading"
            :disabled="hasNoMovies"
            @click="handleFetchShows"
            style="width: 130px"
          >
            批量获取所有场次
          </el-button>
        </el-space>
      </el-form-item>

      <!-- 批量获取进度显示 -->
      <div
        v-if="fetchProgress.visible"
        class="fetch-progress"
        role="status"
        aria-live="polite"
        aria-atomic="true"
      >
        <el-divider style="margin: 12px 0" />
        <div class="progress-content">
          <div class="progress-label">批量抓取进度</div>
          <div class="progress-summary">
            已完成 {{ fetchProgress.completedMovies }} / {{ fetchProgress.totalMovies }} 部电影
          </div>
          <el-progress
            :percentage="getBatchProgressPercent()"
            :stroke-width="10"
            :show-text="false"
            :status="fetchProgress.completedMovies >= fetchProgress.totalMovies && fetchProgress.totalMovies > 0 ? 'success' : undefined"
          />
          <div class="progress-text">{{ fetchProgress.text }}</div>
        </div>
      </div>
    </el-form>
  </div>
</template>

<script setup>
import { streamShows } from '@/api'
import { selectMovies } from '@/api'
import { Filter } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { computed, ref } from 'vue'
import { useScheduleStore } from '@/stores/scheduleStore'

const props = defineProps({
  updateForm: {
    type: Object,
    required: true,
  },
})

const emit = defineEmits([
  'movies-selected',
  'shows-fetched',
  'fetch-progress-update',
])

const store = useScheduleStore()

const form = ref({ selectionMode: 'all' })
const selectLoading = ref(false)
const fetchLoading = ref(false)
const fetchProgress = ref({
  visible: false,
  text: '',
  totalMovies: 0,
  completedMovies: 0,
})

const selectionModeOptions = [
  { label: '正在上映', value: 'showing' },
  { label: '即将上映', value: 'upcoming' },
  { label: '全部', value: 'all' },
]

const hasNoMovies = computed(() => store.selectedMovies.length === 0)

const getBatchProgressPercent = () => {
  if (!fetchProgress.value.totalMovies) return 0
  return Math.min(
    100,
    Math.round((fetchProgress.value.completedMovies / fetchProgress.value.totalMovies) * 100)
  )
}

const COMPLETE_TRANSITION_MS = 1200

const waitForProgressTransition = () =>
  new Promise((resolve) => window.setTimeout(resolve, COMPLETE_TRANSITION_MS))

const handleSelectMovies = async () => {
  selectLoading.value = true
  try {
    const response = await selectMovies(form.value.selectionMode)
    if (response.data.success) {
      const movies = response.data.data.movies
      store.setSelectedMovies(movies)
      ElMessage.success(`成功筛选出 ${movies.length} 部电影`)
      emit('movies-selected', movies)
    } else {
      ElMessage.error('筛选失败: ' + response.data.error)
    }
  } catch (error) {
    ElMessage.error('筛选失败: ' + error.message)
  } finally {
    selectLoading.value = false
  }
}

const handleFetchShows = async () => {
  const moviesToFetch = store.selectedMovies.filter(
    (m) => m.id != null && m.is_showing !== false && !store.hasMovieShowsData(m.id)
  )

  if (moviesToFetch.length === 0) {
    ElMessage.warning('没有需要获取场次的电影')
    return
  }

  fetchLoading.value = true
  fetchProgress.value = {
    visible: true,
    text: `开始批量获取 ${moviesToFetch.length} 部电影的场次...`,
    totalMovies: moviesToFetch.length,
    completedMovies: 0,
  }

  emit('fetch-progress-update', { type: 'start', movieIds: moviesToFetch.map((m) => m.id) })

  const movieIds = moviesToFetch.map((m) => m.id)

  try {
    const response = await streamShows(movieIds, props.updateForm.cityId)
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
          const movie = moviesToFetch.find((m) => m.id === data.movie_id)
          fetchProgress.value.text = `电影《${movie?.title}》找到 ${data.dates.length} 个排片日期`
          emit('fetch-progress-update', { type: 'dates_found', movieId: data.movie_id, dates: data.dates })
        } else if (data.type === 'processing_date') {
          const movie = moviesToFetch.find((m) => m.id === data.movie_id)
          fetchProgress.value.text = `电影《${movie?.title}》处理日期 ${data.date_idx}/${data.total_dates}`
          emit('fetch-progress-update', { type: 'processing_date', movieId: data.movie_id, date: data.date })
        } else if (data.type === 'processing_cinema') {
          const movie = moviesToFetch.find((m) => m.id === data.movie_id)
          fetchProgress.value.text = `电影《${movie?.title}》日期 ${data.date} - 影院 ${data.cinema_idx}/${data.total_cinemas}`
          emit('fetch-progress-update', {
            type: 'processing_cinema',
            movieId: data.movie_id,
            date: data.date,
            cinemaIdx: data.cinema_idx,
            totalCinemas: data.total_cinemas,
          })
        } else if (data.type === 'movie_complete') {
          const movie = moviesToFetch.find((m) => m.id === data.movie_id)
          fetchProgress.value.completedMovies = Math.min(
            fetchProgress.value.totalMovies,
            fetchProgress.value.completedMovies + 1
          )
          fetchProgress.value.text = data.has_shows
            ? `电影《${movie?.title}》场次抓取完成`
            : `电影《${movie?.title}》抓取完成，暂无场次`
        } else if (data.type === 'complete') {
          const shows = data.data
          const successCount = shows.filter((s) => s.cinemas && s.cinemas.length > 0).length
          const noShowsCount = shows.length - successCount

          fetchProgress.value.completedMovies = fetchProgress.value.totalMovies
          fetchProgress.value.text = '批量获取完成'
          await waitForProgressTransition()
          fetchProgress.value.visible = false
          fetchProgress.value.totalMovies = 0
          fetchProgress.value.completedMovies = 0

          shows.forEach((showItem) => {
            store.setMovieShowsData(showItem.movie_id, { ...showItem, cachedAt: Date.now() })
          })
          emit('shows-fetched', shows)
          emit('fetch-progress-update', { type: 'complete', movieIds: moviesToFetch.map((m) => m.id) })

          if (successCount > 0 && noShowsCount === 0) {
            ElMessage.success(`批量获取完成：成功获取 ${successCount} 部电影的场次信息`)
          } else if (successCount > 0) {
            ElMessage.warning(`批量获取完成：${successCount} 部有场次，${noShowsCount} 部暂无场次`)
          } else {
            ElMessage.warning('批量获取完成：所有电影暂无场次信息')
          }
        } else if (data.type === 'error') {
          ElMessage.error('批量获取失败: ' + data.error)
          fetchProgress.value.visible = false
          fetchProgress.value.totalMovies = 0
          fetchProgress.value.completedMovies = 0
          emit('fetch-progress-update', { type: 'error', movieIds: moviesToFetch.map((m) => m.id) })
        }
      }
    }
  } catch (error) {
    ElMessage.error('批量获取失败: ' + error.message)
    fetchProgress.value.visible = false
    fetchProgress.value.totalMovies = 0
    fetchProgress.value.completedMovies = 0
    emit('fetch-progress-update', { type: 'error', movieIds: moviesToFetch.map((m) => m.id) })
  } finally {
    fetchLoading.value = false
  }
}
</script>

<style scoped>
.movie-selector-section {
  min-width: 0;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
}

.movie-selector-section .el-form {
  width: 100%;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
}

.section-title {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0 0 16px 0;
  font-size: 16px;
  font-weight: 500;
  color: #333;
  width: 100%;
  justify-content: flex-start;
}

.threshold-input-wrapper {
  display: flex;
  align-items: center;
  gap: 8px;
}

.movie-selector-section :deep(.el-form-item) {
  width: 100%;
  justify-content: flex-start;
}

.movie-selector-section :deep(.el-form-item__content) {
  width: 100%;
  justify-content: flex-start;
}

.movie-selector-section :deep(.el-form-item__label) {
  white-space: nowrap;
  justify-content: flex-start;
  text-align: left;
  padding-right: 12px;
}

.movie-selector-section :deep(.movie-selector-action-form-item .el-form-item__content) {
  margin-left: 0 !important;
}

.movie-selector-section :deep(.el-space) {
  align-items: flex-start;
}

.fetch-progress {
  margin-top: 12px;
  width: 100%;
}

.progress-content {
  padding: 8px 12px;
  background-color: #f0f9ff;
  border-radius: 4px;
  border-left: 3px solid #409eff;
}

.progress-label {
  margin-bottom: 4px;
  font-size: 12px;
  font-weight: 600;
  color: #1d4ed8;
}

.progress-summary {
  margin-bottom: 8px;
  font-size: 13px;
  color: #475569;
}

.progress-text {
  margin-top: 8px;
  font-size: 13px;
  color: #409eff;
  line-height: 1.5;
}
</style>
