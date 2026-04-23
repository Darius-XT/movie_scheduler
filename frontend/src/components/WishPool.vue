<template>
  <el-card
    class="planning-card wish-planning-card"
    :body-style="groupedWishPool.length === 0 ? { display: 'none' } : undefined"
  >
    <template #header>
      <div class="planning-header">
        <div class="planning-header-main">
          <span>想看</span>
          <span class="planning-header-summary">{{ store.wishPool.length }} 个想看场次</span>
        </div>
        <div v-if="groupedWishPool.length > 0" class="planning-header-actions">
          <el-button text size="small" @click="expandAllWishGroups">全部展开</el-button>
          <el-button text size="small" @click="collapseAllWishGroups">全部收起</el-button>
        </div>
      </div>
    </template>
    <div v-if="groupedWishPool.length > 0" class="wish-pool-list">
      <div
        v-for="group in groupedWishPool"
        :key="group.movieId"
        class="wish-pool-group"
      >
        <div class="wish-pool-group-header">
          <div class="wish-pool-group-title">
            <span>{{ group.movieTitle }}</span>
            <span v-if="getWishGroupMovieMeta(group.movieId)" class="wish-pool-group-meta">
              {{ getWishGroupMovieMeta(group.movieId) }}
            </span>
          </div>
          <div class="wish-pool-group-actions">
            <el-button text size="small" @click="store.removeWishMovieGroup(group.movieId)">
              全部移除
            </el-button>
            <el-button text size="small" @click="toggleWishGroup(group.movieId)">
              {{ isWishGroupCollapsed(group.movieId) ? '展开' : '收起' }}
            </el-button>
          </div>
        </div>
        <div v-if="!isWishGroupCollapsed(group.movieId)" class="wish-pool-group-list">
          <div
            v-for="item in group.items"
            :key="item.key"
            class="wish-pool-item"
          >
            <div class="wish-pool-main">
              <div class="wish-pool-meta">
                <span>{{ formatDateWithRelativeWeek(item.date) }}</span>
                <span>{{ item.time }}</span>
                <span>{{ item.cinemaName }}</span>
                <span>{{ formatShowPrice(item.price) }}</span>
              </div>
            </div>
            <div class="wish-pool-actions">
              <el-button size="small" type="success" @click="handleAddToSchedule(item)">加入行程</el-button>
              <el-button size="small" @click="store.removeFromWishPool(item.key)">移除</el-button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </el-card>
</template>

<script setup>
import { ElMessage } from 'element-plus'
import { computed, ref } from 'vue'
import { useScheduleStore } from '@/stores/scheduleStore'

const store = useScheduleStore()

const collapsedWishMovieIds = ref(new Set())

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

const parseMovieDurationMinutes = (durationText) => {
  const normalized = String(durationText ?? '').trim()
  const match = normalized.match(/(\d+)/)
  return match ? Number(match[1]) : null
}

const parseShowTimeToMinutes = (timeText) => {
  const normalized = String(timeText ?? '').trim()
  const match = normalized.match(/^(\d{1,2}):(\d{2})$/)
  if (!match) return null
  const hours = Number(match[1])
  const minutes = Number(match[2])
  if (Number.isNaN(hours) || Number.isNaN(minutes)) return null
  return hours * 60 + minutes
}

const getShowEntryDurationMinutes = (showEntry) => {
  if (typeof showEntry?.durationMinutes === 'number' && !Number.isNaN(showEntry.durationMinutes)) {
    return showEntry.durationMinutes
  }
  const movie = store.selectedMovies.find((item) => item.id === showEntry?.movieId)
  return parseMovieDurationMinutes(movie?.duration)
}

const getScheduleConflict = (showEntry) => {
  const targetStart = parseShowTimeToMinutes(showEntry.time)
  const targetDuration = getShowEntryDurationMinutes(showEntry)

  return store.scheduleItems.find((item) => {
    if (item.date !== showEntry.date) return false
    const itemStart = parseShowTimeToMinutes(item.time)
    const itemDuration = getShowEntryDurationMinutes(item)
    if (targetStart == null || itemStart == null || targetDuration == null || itemDuration == null) {
      return item.time === showEntry.time
    }
    const targetEnd = targetStart + targetDuration
    const itemEnd = itemStart + itemDuration
    return targetStart < itemEnd && itemStart < targetEnd
  }) || null
}

const handleAddToSchedule = (showEntry) => {
  if (store.isInSchedule(showEntry.key)) return
  const conflictItem = getScheduleConflict(showEntry)
  if (conflictItem) {
    ElMessage.warning(
      `加入行程失败：${showEntry.date} ${showEntry.time} 与《${conflictItem.movieTitle}》冲突`
    )
    return
  }
  store.addToSchedule(showEntry)
  ElMessage.success(`已将《${showEntry.movieTitle}》加入行程`)
}

const groupedWishPool = computed(() => {
  const groups = new Map()
  store.wishPool.forEach((item) => {
    if (!groups.has(item.movieId)) {
      groups.set(item.movieId, { movieId: item.movieId, movieTitle: item.movieTitle, items: [] })
    }
    groups.get(item.movieId).items.push(item)
  })
  return Array.from(groups.values())
    .sort((a, b) => String(a.movieTitle || '').localeCompare(String(b.movieTitle || '')))
    .map((group) => ({
      ...group,
      items: [...group.items].sort((a, b) => {
        const aKey = `${a.date} ${a.time}`
        const bKey = `${b.date} ${b.time}`
        return aKey.localeCompare(bKey)
      }),
    }))
})

const getMovieYear = (movie) => {
  const releaseDate = String(movie?.release_date || '').trim()
  const match = releaseDate.match(/^(\d{4})/)
  return match ? match[1] : ''
}

const getWishGroupMovieMeta = (movieId) => {
  const movie = store.selectedMovies.find((item) => item.id === movieId)
  if (!movie) return ''
  const metaParts = [
    getMovieYear(movie),
    String(movie.director || '').trim(),
    String(movie.country || '').trim(),
  ].filter(Boolean)
  return metaParts.join(' · ')
}

const isWishGroupCollapsed = (movieId) => collapsedWishMovieIds.value.has(movieId)

const toggleWishGroup = (movieId) => {
  const next = new Set(collapsedWishMovieIds.value)
  if (next.has(movieId)) next.delete(movieId)
  else next.add(movieId)
  collapsedWishMovieIds.value = next
}

const expandAllWishGroups = () => {
  collapsedWishMovieIds.value = new Set()
}

const collapseAllWishGroups = () => {
  collapsedWishMovieIds.value = new Set(groupedWishPool.value.map((group) => group.movieId))
}
</script>

<style scoped>
.planning-card {
  margin-top: 16px;
}

.wish-planning-card {
  margin-bottom: 10px;
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

.wish-pool-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.wish-pool-group {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.wish-pool-group-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.wish-pool-group-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.wish-pool-group-title {
  display: flex;
  align-items: baseline;
  flex-wrap: wrap;
  gap: 8px;
  color: #0f172a;
  font-size: 15px;
  font-weight: 700;
}

.wish-pool-group-meta {
  color: #64748b;
  font-size: 13px;
  font-weight: 500;
}

.wish-pool-group-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.wish-pool-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 12px;
  border-radius: 8px;
  background-color: #f8fafc;
  border: 1px solid #e2e8f0;
}

.wish-pool-main {
  min-width: 0;
}

.wish-pool-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 12px;
  color: #64748b;
  font-size: 13px;
}

.wish-pool-actions {
  display: flex;
  gap: 8px;
  flex-shrink: 0;
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
  .wish-pool-group-header,
  .wish-pool-item,
  .wish-pool-actions {
    flex-direction: column;
    align-items: flex-start;
  }

  .wish-pool-group-actions {
    width: 100%;
    justify-content: flex-start;
    flex-wrap: wrap;
  }
}
</style>
