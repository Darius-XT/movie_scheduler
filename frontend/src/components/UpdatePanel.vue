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
        <el-checkbox v-model="updateForm.forceUpdate" style="margin-left: 28px">强制更新</el-checkbox>
      </el-form-item>

      <el-form-item class="update-action-form-item">
        <div class="update-action-list">
          <div class="update-action-row">
            <div class="update-action-meta update-action-meta--left">
              <span v-if="cinemaUpdateMeta.lastUpdatedAt">
                <el-tooltip
                  :content="`更新用时 ${formatDurationMs(cinemaUpdateMeta.durationMs)}`"
                  placement="top"
                >
                  <span class="update-meta-trigger">
                    {{ formatUpdateTimestamp(cinemaUpdateMeta.lastUpdatedAt) }}
                  </span>
                </el-tooltip>
              </span>
              <span v-else>暂无更新记录</span>
            </div>
            <el-button
              type="primary"
              :loading="cinemaLoading"
              :disabled="!updateForm.cityId"
              @click="handleUpdateCinema"
              style="width: 120px"
            >
              更新影院信息
            </el-button>
            <div class="update-action-meta update-action-meta--right">
              {{ getCinemaUpdateSummary() }}
            </div>
          </div>
          <div class="update-action-row">
            <div class="update-action-meta update-action-meta--left">
              <span v-if="movieUpdateMeta.lastUpdatedAt">
                <el-tooltip
                  :content="`更新用时 ${formatDurationMs(movieUpdateMeta.durationMs)}`"
                  placement="top"
                >
                  <span class="update-meta-trigger">
                    {{ formatUpdateTimestamp(movieUpdateMeta.lastUpdatedAt) }}
                  </span>
                </el-tooltip>
              </span>
              <span v-else>暂无更新记录</span>
            </div>
            <el-button
              type="success"
              :loading="movieLoading"
              :disabled="!updateForm.cityId"
              @click="handleUpdateMovie"
              style="width: 120px"
            >
              更新电影信息
            </el-button>
            <div class="update-action-meta update-action-meta--right">
              {{ getMovieUpdateSummary() }}
            </div>
          </div>
        </div>
      </el-form-item>
    </el-form>

    <!-- 更新结果进度 -->
    <div v-if="cinemaUpdateProgress || movieUpdateProgress" class="update-results">
      <el-divider style="margin: 12px 0" />

      <div v-if="cinemaUpdateProgress" class="fetch-progress">
        <div class="progress-content">
          <div class="progress-label">影院更新进度</div>
          <div class="progress-text">{{ cinemaUpdateProgress }}</div>
        </div>
      </div>

      <div v-if="movieUpdateProgress" class="fetch-progress">
        <div class="progress-content">
          <div class="progress-label">电影更新进度</div>
          <div class="progress-text">{{ movieUpdateProgress }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { streamCinemaUpdate, streamMovieUpdate } from '@/api'
import { Setting } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { ref } from 'vue'

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

const emit = defineEmits(['update:lastAddedMovieIds', 'update:lastUpdatedMovieIds'])

const cinemaLoading = ref(false)
const movieLoading = ref(false)
const cinemaResult = ref(null)
const movieResult = ref(null)
const cinemaUpdateProgress = ref('')
const movieUpdateProgress = ref('')
const cinemaUpdateMeta = ref({ lastUpdatedAt: null, durationMs: null })
const movieUpdateMeta = ref({ lastUpdatedAt: null, durationMs: null })

const formatUpdateTimestamp = (timestamp) => {
  if (!timestamp) return '暂无'
  const date = new Date(timestamp)
  if (Number.isNaN(date.getTime())) return '暂无'
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
  return [
    `抓取 ${movieResult.value.base_info?.input_stats?.scraped_total || 0}`,
    `去重后 ${movieResult.value.base_info?.input_stats?.deduplicated_total || 0}`,
    `新增 ${movieResult.value.base_info?.result_stats?.added || 0}`,
    `更新 ${movieResult.value.base_info?.result_stats?.updated || 0}`,
    `删除 ${movieResult.value.base_info?.result_stats?.removed || 0}`,
  ].join(' / ')
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

const handleUpdateCinema = async () => {
  cinemaLoading.value = true
  cinemaResult.value = null
  cinemaUpdateProgress.value = ''
  const startedAt = Date.now()
  try {
    const response = await streamCinemaUpdate(props.updateForm.cityId, props.updateForm.forceUpdate)
    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`)
    if (!response.body) throw new Error('未收到更新响应流')

    await readSseStream(response, (data) => {
      if (data.type === 'progress') {
        cinemaUpdateProgress.value = data.message || '正在更新影院信息'
      } else if (data.type === 'complete') {
        cinemaResult.value = data.data
        cinemaUpdateProgress.value = '影院信息更新完成'
        cinemaUpdateMeta.value = { lastUpdatedAt: Date.now(), durationMs: Date.now() - startedAt }
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
  movieResult.value = null
  movieUpdateProgress.value = ''
  const startedAt = Date.now()
  try {
    const response = await streamMovieUpdate(props.updateForm.cityId, props.updateForm.forceUpdate)
    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`)
    if (!response.body) throw new Error('未收到更新响应流')

    await readSseStream(response, (data) => {
      if (data.type === 'progress') {
        movieUpdateProgress.value = data.message || '正在更新电影信息'
      } else if (data.type === 'complete') {
        movieResult.value = data.data
        movieUpdateProgress.value = '电影信息更新完成'
        movieUpdateMeta.value = { lastUpdatedAt: Date.now(), durationMs: Date.now() - startedAt }
        const addedIds = new Set(data.data.base_info?.result_stats?.added_movie_ids || [])
        const updatedIds = new Set(data.data.base_info?.result_stats?.updated_movie_ids || [])
        emit('update:lastAddedMovieIds', addedIds)
        emit('update:lastUpdatedMovieIds', updatedIds)
        ElMessage.success('电影信息更新成功')
      } else if (data.type === 'error') {
        movieUpdateProgress.value = ''
        ElMessage.error('更新失败: ' + data.error)
      }
    })
  } catch (error) {
    ElMessage.error('更新失败: ' + error.message)
  } finally {
    if (movieResult.value) {
      window.setTimeout(() => { movieUpdateProgress.value = '' }, 1200)
    } else {
      movieUpdateProgress.value = ''
    }
    movieLoading.value = false
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
  width: 100%;
}

.update-action-row {
  display: grid;
  grid-template-columns: max-content auto minmax(0, 1fr);
  align-items: center;
  gap: 10px;
  width: 100%;
}

.update-action-meta {
  min-width: 0;
  color: #64748b;
  font-size: 12px;
  line-height: 1.5;
  white-space: nowrap;
}

.update-action-meta--left {
  width: 110px;
  flex: 0 0 110px;
  text-align: left;
}

.update-action-meta--right {
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
