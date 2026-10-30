<template>
  <el-select
    :model-value="movie.channels?.[0] || ''"
    clearable
    size="small"
    placeholder="暂无"
    aria-label="观看渠道"
    style="width: 120px"
    :disabled="saving"
    :loading="saving"
    @update:model-value="save"
  >
    <el-option v-for="channel in MOVIE_CHANNELS" :key="channel.value" :label="channel.label" :value="channel.value" />
  </el-select>
</template>

<script setup>
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { useMovieSelectionStore } from '@/stores/movieSelectionStore'
import { MOVIE_CHANNELS } from '@/utils/wishFilters'

const props = defineProps({ movie: { type: Object, required: true } })
const store = useMovieSelectionStore()
const saving = ref(false)

const save = async (channel) => {
  if (saving.value) return
  saving.value = true
  try {
    await store.updateMovieChannels(props.movie.id, channel ? [channel] : [])
  } catch (error) {
    ElMessage.error(error?.response?.data?.error || '保存渠道失败，请重试')
  } finally {
    saving.value = false
  }
}
</script>
