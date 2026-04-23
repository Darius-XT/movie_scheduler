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
              <div class="schedule-item-time">{{ item.time }}</div>
              <div class="schedule-item-title">{{ item.movieTitle }}</div>
              <div class="schedule-item-meta">{{ item.cinemaName }}</div>
              <div class="schedule-item-price">{{ formatShowPrice(item.price) }}</div>
              <div class="schedule-item-actions">
                <el-button size="small" @click="store.moveFromScheduleToWishPool(item.key)">放回想看</el-button>
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
  </el-card>
</template>

<script setup>
import { Check } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { computed } from 'vue'
import { useScheduleStore } from '@/stores/scheduleStore'

const store = useScheduleStore()

const WEEKDAY_LABELS = ['周日', '周一', '周二', '周三', '周四', '周五', '周六']

const getWeekStart = (date) => {
  const normalized = new Date(date)
  normalized.setHours(0, 0, 0, 0)
  const weekday = normalized.getDay()
  const offset = weekday === 0 ? -6 : 1 - weekday
  normalized.setDate(normalized.getDate() + offset)
  return normalized
}

const formatDateWithRelativeWeek = (dateText) => {
  if (!dateText) return ''
  const targetDate = new Date(`${dateText}T00:00:00`)
  if (Number.isNaN(targetDate.getTime())) return dateText
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  const currentWeekStart = getWeekStart(today)
  const targetWeekStart = getWeekStart(targetDate)
  const diffWeeks = Math.floor(
    (targetWeekStart.getTime() - currentWeekStart.getTime()) / (7 * 24 * 60 * 60 * 1000)
  )
  let suffix = ''
  if (diffWeeks <= 0) suffix = `本${WEEKDAY_LABELS[targetDate.getDay()]}`
  else if (diffWeeks === 1) suffix = `下${WEEKDAY_LABELS[targetDate.getDay()]}`
  else if (diffWeeks === 2) suffix = `下下${WEEKDAY_LABELS[targetDate.getDay()]}`
  else suffix = '三周后'
  return `${dateText}（${suffix}）`
}

const formatShowPrice = (price) => {
  const normalized = String(price ?? '').trim()
  if (!normalized || normalized === '0' || normalized === '0.0' || normalized === '0.00') return '暂无价格'
  return `￥${normalized}`
}

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
