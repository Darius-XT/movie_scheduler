<template>
  <el-button type="primary" plain size="small" @click="visible = true">手动添加</el-button>
  <el-dialog
    v-model="visible"
    title="手动添加想看电影"
    width="min(440px, 92vw)"
    append-to-body
    :close-on-click-modal="false"
    :before-close="handleClose"
    @closed="title = ''"
  >
    <el-form @submit.prevent="submit">
      <el-form-item label="电影名称" required>
        <el-input v-model="title" maxlength="200" show-word-limit placeholder="输入电影名称" :disabled="saving" />
      </el-form-item>
      <p class="manual-movie-hint">无需搜索即可保存。手动添加的电影暂不支持自动获取场次。</p>
    </el-form>
    <template #footer>
      <el-button :disabled="saving" @click="visible = false">取消</el-button>
      <el-button type="primary" :loading="saving" :disabled="!title.trim()" @click="submit">加入想看</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { useMovieSelectionStore } from '@/stores/movieSelectionStore'

const store = useMovieSelectionStore()
const visible = ref(false)
const title = ref('')
const saving = ref(false)

const handleClose = (done) => {
  if (!saving.value) done()
}

const submit = async () => {
  if (saving.value || !title.value.trim()) return
  saving.value = true
  try {
    const movie = await store.addManualMovie(title.value.trim())
    visible.value = false
    ElMessage.success(`已将《${movie.title}》加入想看`)
  } catch (error) {
    ElMessage.error(error?.response?.data?.error || '手动添加失败，请重试')
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.manual-movie-hint {
  color: var(--el-text-color-secondary);
  font-size: 13px;
}
</style>
