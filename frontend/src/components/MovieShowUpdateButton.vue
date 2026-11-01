<template>
  <div class="movie-show-update">
  <el-tooltip v-if="!loading" :content="progress || '更新这部电影在所选城市的场次'">
    <el-button
      text
      size="small"
      :loading="loading"
      :disabled="!cityId || store.isMovieShowsPolling(movieId)"
      @click="updateShows"
    >
      {{ loading ? '更新中' : '更新场次' }}
    </el-button>
  </el-tooltip>
    <TaskProgress v-if="loading || progressEvent.type === 'error'" :event="{ ...progressEvent, message: progress }" />
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { streamShowUpdate } from '@/api'
import { readSseStream } from '@/api/sseStream'
import { useShowCacheStore } from '@/stores/showCacheStore'
import TaskProgress from '@/components/TaskProgress.vue'

const props = defineProps({
  movieId: { type: Number, required: true },
  cityId: { type: Number, default: null },
})
const store = useShowCacheStore()
const loading = ref(false)
const progress = ref('')
const progressEvent = ref({})

const updateShows = async () => {
  if (loading.value || !props.cityId) return
  const movieId = props.movieId
  loading.value = true
  progress.value = '正在抓取场次'
  progressEvent.value = {}
  try {
    const response = await streamShowUpdate(props.cityId, movieId)
    if (!response.ok) throw new Error(`场次更新请求失败（${response.status}）`)
    let result = null
    await readSseStream(response, (event) => {
      progressEvent.value = event
      if (event.type === 'progress') progress.value = event.message || '正在抓取场次'
      if (event.type === 'error') throw new Error(event.error || '场次更新失败')
      if (event.type === 'complete') result = event.data || {}
    })
    if (!result) throw new Error('更新连接已中断，请稍后重试')
    await store.refreshMovieFromBackend(movieId)
    if (result.failed_movies > 0) ElMessage.warning('抓取不完整，已保留原有场次')
    else ElMessage.success('该电影场次已更新')
  } catch (error) {
    progressEvent.value = { type: 'error' }
    progress.value = error.message || '场次更新失败'
    ElMessage.error(error.message || '场次更新失败')
  } finally {
    loading.value = false
    if (progressEvent.value.type !== 'error') progress.value = ''
  }
}
</script>

<style scoped>
.movie-show-update { max-width: 300px; }
.movie-show-update :deep(.task-progress) { width: 180px; }
</style>
