<template>
  <div class="viewing-location-buttons">
    <el-tooltip v-if="movie.viewing_location" :content="switchLabel" placement="top">
      <el-button
        text
        size="small"
        :icon="Switch"
        :disabled="saving"
        :aria-label="switchLabel"
        @click="save(movie.viewing_location === 'home' ? 'cinema' : 'home')"
      />
    </el-tooltip>
    <template v-else>
      <el-button
        v-for="option in options"
        :key="option.value"
        class="movie-label-button"
        size="small"
        :type="option.type"
        :plain="movie.viewing_location !== option.value"
        :disabled="saving"
        :aria-pressed="movie.viewing_location === option.value"
        @click="save(option.value)"
      >{{ option.label }}</el-button>
    </template>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { Switch } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { useMovieSelectionStore } from '@/stores/movieSelectionStore'

const props = defineProps({ movie: { type: Object, required: true } })
const store = useMovieSelectionStore()
const saving = ref(false)
const switchLabel = computed(() => props.movie.viewing_location === 'home' ? '切换到影院看' : '切换到家里看')
const options = [
  { value: 'home', label: '家里看', type: 'success' },
  { value: 'cinema', label: '影院看', type: 'warning' },
]

const save = async (location) => {
  if (saving.value) return
  saving.value = true
  try {
    await store.updateMovieViewingLocation(props.movie.id, location)
  } catch (error) {
    ElMessage.error(error?.response?.data?.error || '保存分类失败，请重试')
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.viewing-location-buttons {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.viewing-location-buttons .el-button {
  margin-left: 0;
}

.movie-label-button.is-plain,
.movie-label-button.is-plain:hover,
.movie-label-button.is-plain:focus {
  color: var(--el-button-text-color);
  background-color: transparent;
  border-color: var(--el-button-text-color);
}
</style>
