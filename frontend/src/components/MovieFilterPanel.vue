<template>
  <div class="movie-selector-section">
    <h3 class="section-title">
      <el-icon><Filter /></el-icon>
      <span>电影筛选</span>
    </h3>
    <el-form :model="form" class="filter-form" label-width="72px" size="default">
      <el-form-item label="城市">
        <el-select
          v-model="updateForm.cityId"
          placeholder="请选择城市"
          style="width: 100%"
        >
          <el-option
            v-for="city in cities"
            :key="city.id"
            :label="city.name"
            :value="city.id"
          />
        </el-select>
      </el-form-item>

      <el-form-item label="上映状态">
        <div class="threshold-input-wrapper">
          <el-select
            v-model="form.selectionMode"
            placeholder="请选择上映状态"
            :loading="selectLoading"
            style="width: 100%"
            @change="handleSelectionModeChange"
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
    </el-form>
  </div>
</template>

<script setup>
import { selectMovies } from '@/api'
import { Filter } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { onMounted, onUnmounted, ref, toRefs, watch } from 'vue'
import { useScheduleStore } from '@/stores/scheduleStore'

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

const { cities, updateForm } = toRefs(props)

const store = useScheduleStore()
const MOVIE_STATUS_POLL_INTERVAL_MS = 60_000

const form = ref({ selectionMode: 'showing' })
const selectLoading = ref(false)
const hasLoadedSelection = ref(false)
const selectionRequestId = ref(0)
let movieStatusPollingId = null

const selectionModeOptions = [
  { label: '正在上映', value: 'showing' },
  { label: '即将上映', value: 'upcoming' },
  { label: '全部', value: 'all' },
]

const runSelection = async (mode) => {
  const requestId = selectionRequestId.value + 1
  selectionRequestId.value = requestId
  selectLoading.value = true
  try {
    const response = await selectMovies(mode)
    if (requestId !== selectionRequestId.value) return

    if (response.data.success) {
      const movies = response.data.data.movies
      store.setSelectedMovies(movies)
      hasLoadedSelection.value = true
    } else {
      ElMessage.error('筛选失败: ' + response.data.error)
    }
  } catch (error) {
    if (requestId === selectionRequestId.value) ElMessage.error('筛选失败: ' + error.message)
  } finally {
    if (requestId === selectionRequestId.value) selectLoading.value = false
  }
}

const handleSelectionModeChange = async (mode) => {
  await runSelection(mode)
}

onMounted(async () => {
  await store.refreshMovieStatus()
  await runSelection(form.value.selectionMode)
  movieStatusPollingId = window.setInterval(() => {
    void store.refreshMovieStatus()
  }, MOVIE_STATUS_POLL_INTERVAL_MS)
})

onUnmounted(() => {
  if (movieStatusPollingId != null) {
    window.clearInterval(movieStatusPollingId)
    movieStatusPollingId = null
  }
})

// 手动或定时更新电影完成后 lastUpdatedAt 会变化,自动按当前上映状态刷新列表。
watch(
  () => store.movieLastUpdatedAt,
  (next, prev) => {
    if (!prev || !next || next === prev) return
    if (!hasLoadedSelection.value) return
    void runSelection(form.value.selectionMode)
  }
)
</script>

<style scoped>
.movie-selector-section {
  min-width: 0;
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  padding: 14px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background-color: #ffffff;
}

.filter-form {
  width: 100%;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
}

.section-title {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0 0 18px 0;
  font-size: 16px;
  font-weight: 700;
  color: #1f2937;
  width: 100%;
  justify-content: flex-start;
}

.threshold-input-wrapper {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
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

@media (max-width: 960px) {
  .movie-selector-section {
    height: auto;
  }
}
</style>
