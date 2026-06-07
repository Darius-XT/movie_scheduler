<template>
  <el-card class="planning-card">
    <template #header>
      <div class="planning-header">
        <div class="planning-header-main">
          <span>我的排片</span>
          <span class="planning-header-summary">
            共 {{ scheduleDateColumns.length }} 天，{{ store.scheduleItems.length }} 场已定行程
          </span>
        </div>
        <div class="planning-header-actions">
          <el-button
            text
            size="small"
            @click="openManualAddDialog"
          >
            手动添加
          </el-button>
          <el-button
            text
            size="small"
            :disabled="store.scheduleItems.length === 0"
            @click="handleRemovePastSchedules"
          >
            移除旧行程
          </el-button>
          <el-tag type="success" size="small">{{ store.scheduleItems.length }} 个已定行程</el-tag>
        </div>
      </div>
    </template>
    <div v-if="scheduleDateColumns.length > 0" class="schedule-board">
      <div class="schedule-board-scroll">
        <div
          v-for="column in scheduleDateColumns"
          :key="column.date"
          class="schedule-column"
        >
          <div class="schedule-column-header">{{ formatDateWithRelativeWeek(column.date) }}</div>
          <div class="schedule-column-body">
            <div
              v-for="item in column.items"
              :key="item.key"
              class="schedule-item"
            >
              <div class="schedule-item-time">{{ formatScheduleItemTimeRange(item) }}</div>
              <div class="schedule-item-title">{{ item.movieTitle }}</div>
              <div class="schedule-item-meta">{{ item.cinemaName }}</div>
              <div class="schedule-item-price">{{ formatShowPrice(item.price) }}</div>
              <div class="schedule-item-actions">
                <el-tag
                  :type="item.purchased ? 'success' : 'info'"
                  effect="plain"
                  class="schedule-ticket-tag"
                  @click="store.toggleSchedulePurchased(item.key)"
                >
                  <el-icon><Check /></el-icon>
                  <span>{{ item.purchased ? '已购票' : '待购票' }}</span>
                </el-tag>
                <el-button size="small" type="danger" plain @click="store.removeFromSchedule(item.key)">移除</el-button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
    <el-empty v-else description="还没有安排好的行程" />

    <el-dialog
      v-model="manualAddDialogVisible"
      title="手动添加行程"
      width="480px"
      align-center
      append-to-body
      @closed="resetManualForm"
    >
      <el-form
        ref="manualFormRef"
        :model="manualForm"
        :rules="manualFormRules"
        label-width="72px"
        @submit.prevent="handleManualAddSubmit"
      >
        <el-form-item label="电影名" prop="movieTitle">
          <el-input
            v-model="manualForm.movieTitle"
            maxlength="100"
            placeholder="电影标题"
            clearable
          />
        </el-form-item>
        <el-form-item label="日期" prop="date">
          <el-date-picker
            v-model="manualForm.date"
            type="date"
            value-format="YYYY-MM-DD"
            placeholder="选择日期"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="时间" prop="time">
          <el-time-picker
            v-model="manualForm.time"
            format="HH:mm"
            value-format="HH:mm"
            placeholder="选择开场时间"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="影院" prop="cinemaName">
          <el-input
            v-model="manualForm.cinemaName"
            maxlength="100"
            placeholder="影院名(留空显示为'其他')"
            clearable
          />
        </el-form-item>
        <el-form-item label="价格" prop="price">
          <el-input
            v-model="manualForm.price"
            maxlength="20"
            placeholder="价格(可选)"
            clearable
          />
        </el-form-item>
        <el-form-item label="片长" prop="durationMinutes">
          <el-input-number
            v-model="manualForm.durationMinutes"
            :min="1"
            :max="600"
            :step="5"
            controls-position="right"
            placeholder="分钟(可选)"
            style="width: 100%"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="manualAddDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleManualAddSubmit">添加</el-button>
      </template>
    </el-dialog>
  </el-card>
</template>

<script setup>
import { Check } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { computed, reactive, ref } from 'vue'
import { useScheduleStore } from '@/stores/scheduleStore'
import { formatDateWithRelativeWeek } from '@/utils/dateLabels'
import { formatShowTimeRange, parseShowTimeToMinutes, UNKNOWN_SHOW_DURATION_MINUTES } from '@/utils/showTime'

const store = useScheduleStore()

const formatShowPrice = (price) => {
  const normalized = String(price ?? '').trim()
  if (!normalized || normalized === '0' || normalized === '0.0' || normalized === '0.00') return '暂无价格'
  return `￥${normalized}`
}

const formatScheduleItemTimeRange = (item) => formatShowTimeRange(item.time, item.durationMinutes)

const scheduleDateColumns = computed(() => {
  const groups = new Map()
  store.scheduleItems.forEach((item) => {
    if (!groups.has(item.date)) groups.set(item.date, [])
    groups.get(item.date).push(item)
  })
  return Array.from(groups.entries())
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([date, items]) => ({
      date,
      items: [...items].sort((a, b) => String(a.time || '').localeCompare(String(b.time || ''))),
    }))
})

const handleRemovePastSchedules = () => {
  const removedCount = store.removePastSchedules()
  if (removedCount > 0) {
    ElMessage.success(`已移除 ${removedCount} 条旧行程`)
  } else {
    ElMessage.info('没有可移除的旧行程')
  }
}

// ===== 手动添加行程 =====
const manualAddDialogVisible = ref(false)
const manualFormRef = ref(null)

const createEmptyManualForm = () => ({
  movieTitle: '',
  date: '',
  time: '',
  cinemaName: '',
  price: '',
  durationMinutes: null,
})

const manualForm = reactive(createEmptyManualForm())

const manualFormRules = {
  movieTitle: [
    {
      required: true,
      validator: (_rule, value, callback) => {
        if (!String(value ?? '').trim()) callback(new Error('请输入电影名'))
        else callback()
      },
      trigger: 'blur',
    },
  ],
  date: [{ required: true, message: '请选择日期', trigger: 'change' }],
  time: [{ required: true, message: '请选择开场时间', trigger: 'change' }],
}

const resetManualForm = () => {
  Object.assign(manualForm, createEmptyManualForm())
  manualFormRef.value?.clearValidate()
}

const openManualAddDialog = () => {
  resetManualForm()
  manualAddDialogVisible.value = true
}

const resolveScheduleItemDuration = (item) => {
  if (typeof item?.durationMinutes === 'number' && item.durationMinutes > 0) {
    return item.durationMinutes
  }
  return UNKNOWN_SHOW_DURATION_MINUTES
}

const findManualScheduleConflict = (date, time, durationMinutes) => {
  const targetStart = parseShowTimeToMinutes(time)
  if (targetStart == null) return null
  const targetDuration = typeof durationMinutes === 'number' && durationMinutes > 0
    ? durationMinutes
    : UNKNOWN_SHOW_DURATION_MINUTES
  const targetEnd = targetStart + targetDuration
  return store.scheduleItems.find((item) => {
    if (item.date !== date) return false
    const itemStart = parseShowTimeToMinutes(item.time)
    if (itemStart == null) return item.time === time
    const itemEnd = itemStart + resolveScheduleItemDuration(item)
    return targetStart < itemEnd && itemStart < targetEnd
  }) || null
}

const buildManualScheduleKey = () => {
  const cryptoApi = typeof window !== 'undefined' ? window.crypto : null
  if (cryptoApi?.randomUUID) return `manual-${cryptoApi.randomUUID()}`
  const random = Math.random().toString(36).slice(2, 10)
  return `manual-${performance.now().toString(36)}-${random}`
}

const handleManualAddSubmit = async () => {
  if (!manualFormRef.value) return
  try {
    await manualFormRef.value.validate()
  } catch {
    return
  }
  const movieTitle = manualForm.movieTitle.trim()
  if (!movieTitle) return
  const cinemaName = manualForm.cinemaName.trim() || '其他'
  const price = manualForm.price.trim()
  const durationMinutes = typeof manualForm.durationMinutes === 'number' && manualForm.durationMinutes > 0
    ? manualForm.durationMinutes
    : null

  const conflict = findManualScheduleConflict(manualForm.date, manualForm.time, durationMinutes)
  if (conflict) {
    ElMessage.warning(
      `时间冲突:${manualForm.date} ${manualForm.time} 与《${conflict.movieTitle}》(${conflict.time}) 冲突`
    )
    return
  }

  const newKey = buildManualScheduleKey()
  store.addToSchedule({
    key: newKey,
    movieId: 0,
    movieTitle,
    date: manualForm.date,
    time: manualForm.time,
    cinemaId: 0,
    cinemaName,
    price,
    durationMinutes,
  })

  // 手动行程在前端没有任何其他 source of truth(WishPool 不会重建它),
  // 必须等后端写入成功才能关闭对话框;失败则本地回滚,避免页面刷新后悄无声息丢失。
  await store.persistScheduleToBackend()
  if (store.scheduleSyncError) {
    store.removeFromSchedule(newKey)
    ElMessage.error(`添加行程失败:${store.scheduleSyncError}`)
    return
  }

  ElMessage.success(`已添加《${movieTitle}》到行程`)
  manualAddDialogVisible.value = false
}
</script>

<style scoped>
.planning-card {
  margin-top: 16px;
}

.planning-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.planning-header-main {
  display: flex;
  align-items: baseline;
  gap: 10px;
  min-width: 0;
}

.planning-header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.planning-header-summary {
  color: #64748b;
  font-size: 13px;
  font-weight: 500;
  white-space: nowrap;
}

.schedule-board {
  overflow-x: auto;
}

.schedule-board-scroll {
  display: flex;
  gap: 16px;
  min-width: max-content;
  padding-bottom: 4px;
}

.schedule-column {
  width: 265px;
  flex: 0 0 265px;
  border-radius: 10px;
  border: 1px solid #dbe4f0;
  background-color: #f8fbff;
}

.schedule-column-header {
  padding: 12px 14px;
  border-bottom: 1px solid #dbe4f0;
  color: #1e3a8a;
  font-size: 14px;
  font-weight: 700;
  background-color: #edf4ff;
}

.schedule-column-body {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 12px;
}

.schedule-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 14px;
  border-radius: 8px;
  background-color: #ffffff;
  border: 1px solid #e2e8f0;
}

.schedule-item-time {
  color: #1d4ed8;
  font-size: 13px;
  font-weight: 700;
}

.schedule-item-title {
  color: #0f172a;
  font-size: 14px;
  font-weight: 600;
}

.schedule-item-meta,
.schedule-item-price {
  color: #64748b;
  font-size: 13px;
}

.schedule-ticket-tag {
  width: fit-content;
  cursor: pointer;
}

.schedule-ticket-tag :deep(.el-tag__content) {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.schedule-item-actions {
  display: inline-grid;
  grid-auto-flow: column;
  grid-auto-columns: max-content;
  align-items: center;
  gap: 8px;
  justify-content: start;
}

.schedule-item-actions > * {
  margin: 0 !important;
}

@media (max-width: 960px) {
  .planning-header {
    align-items: flex-start;
    flex-direction: column;
  }

  .planning-header-main {
    width: 100%;
    flex-wrap: wrap;
  }

  .planning-header-actions {
    width: 100%;
    justify-content: flex-start;
    flex-wrap: wrap;
  }

  .planning-header-summary {
    white-space: normal;
  }
}

@media (max-width: 640px) {
  .schedule-item-actions {
    width: 100%;
  }

  .schedule-column {
    width: 220px;
    flex-basis: 220px;
  }
}
</style>
