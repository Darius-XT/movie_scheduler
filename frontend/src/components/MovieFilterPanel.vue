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
        <el-button
          type="primary"
          :loading="selectLoading"
          @click="handleSelectMovies"
          style="width: 130px"
        >
          筛选喜欢的电影
        </el-button>
      </el-form-item>
    </el-form>
  </div>
</template>

<script setup>
import { selectMovies } from '@/api'
import { Filter } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { ref } from 'vue'
import { useScheduleStore } from '@/stores/scheduleStore'

const emit = defineEmits(['movies-selected'])

const store = useScheduleStore()

const form = ref({ selectionMode: 'showing' })
const selectLoading = ref(false)

const selectionModeOptions = [
  { label: '正在上映', value: 'showing' },
  { label: '即将上映', value: 'upcoming' },
  { label: '全部', value: 'all' },
]

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
</style>
