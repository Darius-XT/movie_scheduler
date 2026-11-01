<template>
  <div class="backup-toolbar">
    <el-button @click="dialogVisible = true">数据导入 / 导出</el-button>
  </div>

  <el-dialog
    v-model="dialogVisible"
    title="后端数据备份"
    width="min(560px, 94vw)"
    :close-on-click-modal="false"
    :close-on-press-escape="!busy"
    :show-close="!busy"
  >
    <p class="backup-description">仅包含后端保存的电影、影院、场次和行程，不包含浏览器缓存、Cookie 或环境配置。</p>
    <el-button type="primary" :loading="exporting" :disabled="busy && !exporting" @click="handleExport">
      导出 JSON 备份
    </el-button>

    <el-divider />

    <el-alert
      title="导入将全量覆盖四张业务表，不会与现有数据合并。"
      description="建议先导出当前数据。请等待信息更新和行程保存完成，并暂停其他设备的操作后再导入。"
      type="warning"
      show-icon
      :closable="false"
    />
    <div class="backup-file-picker">
      <input ref="fileInput" type="file" accept=".json,application/json" hidden @change="handleFileChange" />
      <el-button :loading="reading" :disabled="busy" @click="fileInput?.click()">选择备份文件</el-button>
      <span class="backup-filename">{{ fileName || '尚未选择文件' }}</span>
    </div>

    <template v-if="selectedBackup">
      <p>导出时间：{{ new Date(selectedBackup.data.exported_at).toLocaleString() }}</p>
      <el-descriptions :column="2" border size="small">
        <el-descriptions-item v-for="table in backupTables" :key="table.key" :label="table.label">
          {{ selectedBackup.data[table.key].length }} 条
        </el-descriptions-item>
      </el-descriptions>
    </template>

    <el-alert v-if="errorMessage" class="backup-error" :title="errorMessage" type="error" :closable="false" show-icon />

    <template #footer>
      <el-button :disabled="busy" @click="dialogVisible = false">关闭</el-button>
      <el-button type="danger" :loading="importing" :disabled="!selectedBackup || busy" @click="handleImport">
        导入并覆盖
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { computed, ref, shallowRef } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { exportBackendData, importBackendData } from '@/api'
import { backupTables, parseBackupFile } from '@/utils/backupFile'
import { useMovieSelectionStore } from '@/stores/movieSelectionStore'

const movieSelectionStore = useMovieSelectionStore()
const dialogVisible = ref(false)
const exporting = ref(false)
const importing = ref(false)
const reading = ref(false)
const busy = computed(() => exporting.value || importing.value || reading.value)
const fileInput = ref(null)
const fileName = ref('')
const selectedBackup = shallowRef(null)
const errorMessage = ref('')

const handleExport = async () => {
  exporting.value = true
  errorMessage.value = ''
  try {
    const response = await exportBackendData()
    const blob = new Blob([JSON.stringify(response.data, null, 2)], { type: 'application/json;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    const filename = response.headers['content-disposition']?.match(/filename="([^"]+)"/)?.[1]
    link.href = url
    link.download = filename || 'movie-scheduler-backup.json'
    document.body.appendChild(link)
    try {
      link.click()
    } finally {
      link.remove()
      window.setTimeout(() => URL.revokeObjectURL(url), 1000)
    }
    ElMessage.success('备份文件已生成')
  } catch (error) {
    errorMessage.value = error?.response?.data?.error || error.message || '导出失败，请重试'
  } finally {
    exporting.value = false
  }
}

const handleFileChange = async (event) => {
  const file = event.target.files?.[0]
  if (!file) return
  reading.value = true
  selectedBackup.value = null
  fileName.value = file.name
  errorMessage.value = ''
  try {
    selectedBackup.value = parseBackupFile(await file.text())
  } catch (error) {
    errorMessage.value = error.message
  } finally {
    reading.value = false
    event.target.value = ''
  }
}

const handleImport = async () => {
  if (!selectedBackup.value || busy.value) return
  importing.value = true
  errorMessage.value = ''
  const summary = backupTables.map(({ key, label }) => `${label} ${selectedBackup.value.data[key].length} 条`).join('、')
  try {
    await ElMessageBox.confirm(
      `将用文件中的${summary}覆盖当前后端数据。空表也会清空现有数据，此操作不可撤销。是否继续？`,
      '确认覆盖全部后端数据',
      { type: 'warning', confirmButtonText: '确认覆盖', cancelButtonText: '取消' },
    )
  } catch {
    importing.value = false
    return
  }
  try {
    const response = await importBackendData(selectedBackup.value)
    movieSelectionStore.setSelectedMovies([])
    const saved = backupTables.map(({ key, label }) => `${label} ${response.data.data[key]} 条`).join('、')
    await ElMessageBox.alert(`已恢复${saved}。重新加载页面以读取导入后的数据。`, '导入成功', {
      confirmButtonText: '重新加载页面', showClose: false, closeOnClickModal: false, closeOnPressEscape: false,
    })
    window.location.reload()
  } catch (error) {
    errorMessage.value = error?.response?.data?.error || '未能确认导入结果，请刷新页面核对数据后再重试'
    importing.value = false
  }
}
</script>

<style scoped>
.backup-toolbar {
  display: flex;
  justify-content: flex-end;
  margin-bottom: 16px;
}

.backup-description {
  margin-top: 0;
  line-height: 1.7;
  color: var(--el-text-color-regular);
}

.backup-file-picker {
  display: flex;
  align-items: center;
  gap: 12px;
  margin: 20px 0;
}

.backup-filename {
  overflow-wrap: anywhere;
  color: var(--el-text-color-secondary);
}

.backup-error {
  margin-top: 16px;
}
</style>
