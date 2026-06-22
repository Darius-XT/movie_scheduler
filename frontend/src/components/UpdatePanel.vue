<template>
  <div class="info-update-section">
    <h3 class="section-title">
      <el-icon><Setting /></el-icon>
      <span>信息更新</span>
    </h3>
    <el-form :model="updateForm" label-width="84px" size="default">
      <el-form-item label="选择城市">
        <el-select
          v-model="updateForm.cityId"
          placeholder="请选择城市"
          style="width: 80px"
        >
          <el-option
            v-for="city in cities"
            :key="city.id"
            :label="city.name"
            :value="city.id"
          />
        </el-select>
      </el-form-item>

      <el-form-item class="update-action-form-item">
        <div class="update-action-list">
          <div class="update-action-row">
            <el-button
              type="primary"
              :loading="cinemaLoading"
              :disabled="!updateForm.cityId"
              class="update-action-button"
              @click="handleUpdateCinema"
            >
              更新影院信息
            </el-button>
            <div class="update-action-meta update-action-meta--time">
              <span v-if="cinemaUpdateMeta.lastUpdatedAt">
                <el-tooltip
                  :content="`更新用时 ${formatDurationMs(cinemaUpdateMeta.durationMs)}`"
                  placement="top"
                >
                  <span class="update-meta-trigger">
                    {{ formatTimestamp(cinemaUpdateMeta.lastUpdatedAt) }}
                  </span>
                </el-tooltip>
              </span>
              <span v-else>暂无更新记录</span>
            </div>
            <div class="update-action-meta update-action-meta--stats">
              {{ getCinemaUpdateSummary() }}
            </div>
          </div>

          <div class="update-action-row">
            <el-button
              type="primary"
              :loading="movieLoading"
              :disabled="!updateForm.cityId"
              class="update-action-button"
              @click="handleUpdateMovie"
            >
              更新电影信息
            </el-button>
            <div class="update-action-meta update-action-meta--time">
              <span v-if="movieLastUpdatedAt">
                <el-tooltip
                  v-if="movieUpdateMeta.durationMs"
                  :content="`更新用时 ${formatDurationMs(movieUpdateMeta.durationMs)}`"
                  placement="top"
                >
                  <span class="update-meta-trigger">
                    {{ formatTimestamp(movieLastUpdatedAt) }}
                  </span>
                </el-tooltip>
                <span v-else>{{ formatTimestamp(movieLastUpdatedAt) }}</span>
              </span>
              <span v-else>暂无更新记录</span>
            </div>
            <div class="update-action-meta update-action-meta--stats">
              {{ getMovieUpdateSummary() }}
            </div>
          </div>

          <div class="update-action-row">
            <el-button
              type="primary"
              :loading="showsLoading"
              :disabled="!updateForm.cityId"
              class="update-action-button"
              @click="handleUpdateShows"
            >
              更新场次信息
            </el-button>
            <div class="update-action-meta update-action-meta--time">
              <span v-if="showsLastUpdatedAt">
                <el-tooltip
                  v-if="showsUpdateMeta.durationMs"
                  :content="`更新用时 ${formatDurationMs(showsUpdateMeta.durationMs)}`"
                  placement="top"
                >
                  <span class="update-meta-trigger">
                    {{ formatTimestamp(showsLastUpdatedAt) }}
                  </span>
                </el-tooltip>
                <span v-else>{{ formatTimestamp(showsLastUpdatedAt) }}</span>
              </span>
              <span v-else>暂无更新记录</span>
            </div>
            <div class="update-action-meta update-action-meta--stats">
              {{ getShowsUpdateSummary() }}
            </div>
          </div>
        </div>
      </el-form-item>
    </el-form>

    <div v-if="cinemaUpdateProgress" class="update-results">
      <el-divider style="margin: 12px 0" />
      <div class="fetch-progress">
        <div class="progress-content">
          <div class="progress-label">影院更新进度</div>
          <div class="progress-text">{{ cinemaUpdateProgress }}</div>
        </div>
      </div>
    </div>

    <div v-if="movieUpdateProgress" class="update-results">
      <el-divider style="margin: 12px 0" />
      <div class="fetch-progress">
        <div class="progress-content">
          <div class="progress-label">电影更新进度</div>
          <div class="progress-text">{{ movieUpdateProgress }}</div>
        </div>
      </div>
    </div>

    <div v-if="showsUpdateProgress" class="update-results">
      <el-divider style="margin: 12px 0" />
      <div class="fetch-progress">
        <div class="progress-content">
          <div class="progress-label">场次更新进度</div>
          <div class="progress-text">{{ showsUpdateProgress }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { streamCinemaUpdate, streamMovieUpdate, streamShowUpdate } from '@/api'
import { readSseStream } from '@/api/sseStream'
import { useScheduleStore } from '@/stores/scheduleStore'
import { Setting } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { computed, onMounted, ref } from 'vue'

const props = defineProps({
  cities: {
    type: Array,
    default: () => [],
  },
  updateForm: {
    type: Object,
    required: true,
  },
})

const store = useScheduleStore()

const cinemaLoading = ref(false)
const cinemaUpdateProgress = ref('')
const movieLoading = ref(false)
const movieUpdateProgress = ref('')
const showsLoading = ref(false)
const showsUpdateProgress = ref('')

const cinemaResult = computed(() => store.cinemaUpdateResult)
const cinemaUpdateMeta = computed(() => store.cinemaUpdateMeta)
const movieResult = computed(() => store.movieUpdateResult)
const movieUpdateMeta = computed(() => store.movieUpdateMeta)
const movieLastUpdatedAt = computed(() => store.movieLastUpdatedAt)
const showsUpdateMeta = computed(() => store.showsUpdateMeta)
const showsUpdateResult = computed(() => store.showsUpdateResult)
const showsLastUpdatedAt = computed(
  () => showsUpdateMeta.value.lastUpdatedAt || store.showsLastFetchedAt,
)

onMounted(() => {
  // 拉一次后端定时任务的最新时间戳, 让首次进入页面就能显示
  void store.refreshMovieStatus()
})

const formatTimestamp = (raw) => {
  if (raw == null) return '暂无'
  const date = new Date(raw)
  if (Number.isNaN(date.getTime())) return String(raw)
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  const hours = String(date.getHours()).padStart(2, '0')
  const minutes = String(date.getMinutes()).padStart(2, '0')
  const seconds = String(date.getSeconds()).padStart(2, '0')
  return `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`
}

const formatDurationMs = (durationMs) => {
  if (typeof durationMs !== 'number' || Number.isNaN(durationMs) || durationMs < 0) return '暂无'
  if (durationMs < 1000) return `${durationMs} 毫秒`
  const totalSeconds = Math.round(durationMs / 1000)
  const minutes = Math.floor(totalSeconds / 60)
  const seconds = totalSeconds % 60
  return minutes === 0 ? `${seconds} 秒` : `${minutes} 分 ${seconds} 秒`
}

const getCinemaUpdateSummary = () => {
  if (!cinemaResult.value) return '暂无结果'
  return `成功 ${cinemaResult.value.success_count} / 失败 ${cinemaResult.value.failure_count}`
}

const getMovieUpdateSummary = () => {
  if (!movieResult.value) return '暂无结果'
  return `新增 ${movieResult.value.added} / 更新 ${movieResult.value.updated} / 删除 ${movieResult.value.removed}`
}

const getShowsUpdateSummary = () => {
  if (!showsUpdateResult.value) return '暂无结果'
  return `新增 ${showsUpdateResult.value.added} 场次 / 删除 ${showsUpdateResult.value.removed} 场次`
}

const handleUpdateCinema = async () => {
  cinemaLoading.value = true
  store.recordCinemaUpdate(null, null)
  cinemaUpdateProgress.value = ''
  const startedAt = Date.now()
  try {
    const response = await streamCinemaUpdate(props.updateForm.cityId)
    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`)

    await readSseStream(response, (data) => {
      if (data.type === 'progress') {
        cinemaUpdateProgress.value = data.message || '正在更新影院信息'
      } else if (data.type === 'complete') {
        store.recordCinemaUpdate(data.data, Date.now() - startedAt)
        cinemaUpdateProgress.value = '影院信息更新完成'
        ElMessage.success('影院信息更新成功')
      } else if (data.type === 'error') {
        cinemaUpdateProgress.value = ''
        ElMessage.error('更新失败: ' + data.error)
      }
    })
  } catch (error) {
    ElMessage.error('更新失败: ' + error.message)
  } finally {
    if (cinemaResult.value) {
      window.setTimeout(() => { cinemaUpdateProgress.value = '' }, 1200)
    } else {
      cinemaUpdateProgress.value = ''
    }
    cinemaLoading.value = false
  }
}

const handleUpdateMovie = async () => {
  movieLoading.value = true
  movieUpdateProgress.value = ''
  const startedAt = Date.now()
  let succeeded = false
  try {
    const response = await streamMovieUpdate(props.updateForm.cityId)
    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`)

    await readSseStream(response, (data) => {
      if (data.type === 'progress') {
        movieUpdateProgress.value = data.message || '正在更新电影信息'
      } else if (data.type === 'complete') {
        const { added, updated, removed, last_updated_at } = data.data || {}
        store.recordMovieUpdate({ added, updated, removed }, Date.now() - startedAt, last_updated_at)
        movieUpdateProgress.value = '电影信息更新完成'
        succeeded = true
        ElMessage.success('电影信息更新成功')
      } else if (data.type === 'error') {
        movieUpdateProgress.value = ''
        ElMessage.error('更新失败: ' + data.error)
      }
    })
  } catch (error) {
    ElMessage.error('更新失败: ' + error.message)
  } finally {
    if (succeeded) {
      window.setTimeout(() => { movieUpdateProgress.value = '' }, 1200)
    } else {
      movieUpdateProgress.value = ''
    }
    movieLoading.value = false
  }
}

const handleUpdateShows = async () => {
  if (!props.updateForm.cityId) return
  showsLoading.value = true
  showsUpdateProgress.value = ''
  const startedAt = Date.now()
  let succeeded = false
  try {
    const response = await streamShowUpdate(props.updateForm.cityId)
    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`)

    await readSseStream(response, (data) => {
      if (data.type === 'progress') {
        showsUpdateProgress.value = data.message || '正在更新场次信息'
      } else if (data.type === 'complete') {
        const { added, removed, last_fetched_at } = data.data || {}
        store.recordShowUpdate({ added, removed }, Date.now() - startedAt, last_fetched_at)
        showsUpdateProgress.value = '场次信息更新完成'
        succeeded = true
        ElMessage.success('场次信息更新成功')
      } else if (data.type === 'error') {
        showsUpdateProgress.value = ''
        ElMessage.error('更新失败: ' + data.error)
      }
    })

    if (succeeded) {
      void store.refreshShowsFromBackend()
    }
  } catch (error) {
    ElMessage.error('更新失败: ' + error.message)
  } finally {
    if (succeeded) {
      window.setTimeout(() => { showsUpdateProgress.value = '' }, 1200)
    } else {
      showsUpdateProgress.value = ''
    }
    showsLoading.value = false
  }
}
</script>

<style scoped>
.info-update-section {
  min-width: 0;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
}

.info-update-section .el-form {
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
  flex-wrap: wrap;
}

.info-update-section :deep(.el-form-item) {
  width: 100%;
  justify-content: flex-start;
}

.info-update-section :deep(.el-form-item__content) {
  width: 100%;
  justify-content: flex-start;
}

.info-update-section :deep(.el-form-item__label) {
  white-space: nowrap;
  justify-content: flex-start;
  text-align: left;
  padding-right: 12px;
}

.info-update-section :deep(.update-action-form-item .el-form-item__label) {
  display: none;
}

.info-update-section :deep(.update-action-form-item .el-form-item__content) {
  margin-left: 0 !important;
}

.update-action-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  align-items: flex-start;
  width: max-content;
  max-width: 100%;
}

.update-action-row {
  display: flex;
  align-items: center;
  justify-content: flex-start;
  gap: 8px;
  width: auto;
  max-width: 100%;
  flex-wrap: wrap;
}

.update-action-button {
  width: 120px;
}

.update-action-meta {
  min-width: 0;
  color: #64748b;
  font-size: 12px;
  line-height: 1.5;
  white-space: nowrap;
}

.update-action-meta--time {
  width: auto;
}

.update-action-meta--stats {
  color: #409eff;
}

.update-meta-trigger {
  cursor: default;
  border-bottom: 1px dashed rgba(100, 116, 139, 0.45);
}

.update-results {
  margin-top: 12px;
  width: 100%;
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

.progress-text {
  margin-top: 8px;
  font-size: 13px;
  color: #409eff;
  line-height: 1.5;
}
</style>
