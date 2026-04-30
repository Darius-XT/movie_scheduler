<template>
  <el-card class="movie-card">
    <div class="movie-header">
      <div class="movie-basic-info">
        <div class="movie-title-row">
          <span class="movie-index">{{ index + 1 }}.</span>
          <span class="movie-title">{{ movie.title }}</span>
          <template v-if="movie.douban_url">
            <el-tag type="warning" size="small" class="movie-score">
              <a
                :href="movie.douban_url"
                target="_blank"
                rel="noopener noreferrer"
                class="douban-link"
              >{{ movie.score }}</a>
            </el-tag>
          </template>
          <template v-else-if="movie.score === '无豆瓣评分'">
            <el-tag type="info" size="small" class="movie-score">无豆瓣评分</el-tag>
          </template>
          <template v-else>
            <el-tag type="info" size="small" class="movie-score" style="opacity: 0.5">未获取评分</el-tag>
          </template>
        </div>
        <div class="movie-meta">
          <span v-if="movie.release_date" class="meta-item meta-item--primary">
            {{ movie.release_date }}
          </span>
          <span v-if="movie.director" class="meta-item meta-item--primary">
            导演 {{ movie.director }}
          </span>
          <span v-if="movieRegion" class="meta-item meta-item--primary">
            {{ movieRegion }}
          </span>
        </div>
        <div v-if="movie.duration || movie.language || movie.actors || movie.genres" class="movie-secondary-meta">
          <span v-if="movie.duration" class="secondary-meta-item">{{ movie.duration }}</span>
          <span v-if="movie.language" class="secondary-meta-item">{{ movie.language }}</span>
          <span v-if="movie.actors" class="secondary-meta-item">主演: {{ movie.actors }}</span>
          <span v-if="movie.genres" class="secondary-meta-item">类型: {{ movie.genres }}</span>
        </div>
      </div>
      <div class="movie-actions">
        <el-button size="small" @click="toggleDescription">
          {{ descriptionExpanded ? '收起' : '展开' }}简介
        </el-button>
        <el-button
          v-if="!hasValidShows"
          :type="movie.is_showing === false ? 'info' : 'primary'"
          size="small"
          :loading="isFetching"
          :disabled="movie.is_showing === false"
          @click="$emit('fetch-single-show', movie)"
        >
          {{ movie.is_showing === false ? '暂未上映' : '获取场次信息' }}
        </el-button>
        <el-button
          v-else
          type="success"
          size="small"
          @click="toggleShows"
        >
          {{ showsExpanded ? '收起' : '展开' }}场次信息
        </el-button>
        <el-button
          size="small"
          :loading="isDoubanFetching"
          @click="$emit('fetch-douban', movie)"
        >
          {{ (movie.douban_url || movie.score === '无豆瓣评分') ? '更新豆瓣' : '获取豆瓣' }}
        </el-button>
      </div>
    </div>

    <!-- 单个电影获取进度 -->
    <el-collapse-transition>
      <div
        v-if="movieProgressText"
        class="single-movie-progress"
        role="status"
        aria-live="polite"
        aria-atomic="true"
      >
        <el-divider style="margin: 12px 0" />
        <div class="progress-content">
          <div class="progress-label">当前电影进度</div>
          <div class="progress-text">{{ movieProgressText }}</div>
        </div>
      </div>
    </el-collapse-transition>

    <!-- 日期抓取进度 -->
    <el-collapse-transition>
      <div v-if="movieFetchDateEntries.length > 0" class="single-movie-progress">
        <el-divider style="margin: 12px 0" />
        <div
          class="date-progress-list"
          role="status"
          aria-live="polite"
          :aria-label="`${movie.title} 抓取进度`"
        >
          <div class="progress-section-title">抓取进度</div>
          <div
            v-for="item in movieFetchDateEntries"
            :key="`${movie.id}-${item.date}`"
            class="date-progress-item"
            :class="{ 'date-progress-item--active': item.active }"
          >
            <div class="date-progress-main">
              <span class="date-progress-date">{{ formatDateWithRelativeWeek(item.date) }}</span>
              <span class="date-progress-meta">
                <span class="date-progress-status">{{ getDateProgressStatusLabel(item) }}</span>
                <span class="date-progress-count">({{ item.done }}/{{ item.total || '?' }})</span>
              </span>
            </div>
            <el-progress
              :percentage="getDateProgressPercent(item)"
              :stroke-width="8"
              :show-text="false"
              :status="item.total > 0 && item.done >= item.total ? 'success' : undefined"
            />
          </div>
        </div>
      </div>
    </el-collapse-transition>

    <!-- 简介 -->
    <el-collapse-transition>
      <div v-if="descriptionExpanded" class="movie-description">
        <el-divider style="margin: 12px 0" />
        <div class="description-content">
          {{ movie.description || '暂无简介' }}
        </div>
      </div>
    </el-collapse-transition>

    <!-- 场次列表 -->
    <el-collapse-transition>
      <div v-if="showsExpanded && hasValidShows" class="movie-shows">
        <el-divider style="margin: 12px 0" />
        <div class="shows-summary">
          <el-tag type="info" size="small">
            {{ showsData?.cinemas?.length || 0 }} 个影院
          </el-tag>
          <el-tag type="success" size="small">
            {{ filteredShowCount }} / {{ getTotalShows(showsData) }} 个场次
          </el-tag>
          <el-button
            size="small"
            plain
            :disabled="availableEntries.length === 0"
            @click="$emit('add-all-to-wish-pool', movie, availableEntries)"
          >
            全部想看
          </el-button>
          <el-radio-group
            class="show-view-mode"
            size="small"
            v-model="showViewMode"
          >
            <el-radio-button label="time">按日期</el-radio-button>
            <el-radio-button label="cinema">按影院</el-radio-button>
          </el-radio-group>
        </div>
        <div class="shows-filter-bar">
          <el-input
            v-model="cinemaKeyword"
            class="shows-filter-input"
            size="small"
            clearable
            placeholder="搜索影院名"
          />
          <el-select
            v-model="selectedShowDate"
            class="shows-filter-select"
            size="small"
            clearable
            placeholder="全部日期"
          >
            <el-option
              v-for="option in availableDateOptions"
              :key="option.value"
              :label="option.label"
              :value="option.value"
            />
          </el-select>
        </div>
        <div v-if="displayGroups.length === 0" class="shows-empty">
          没有匹配的场次
        </div>
        <template v-else>
          <div class="time-group-list">
            <div
              v-for="(entry, entryIndex) in getPagedEntries()"
              :key="`${entry.cinemaId}-${entry.date}-${entry.time}-${entryIndex}`"
              class="time-group-row"
            >
              <div class="time-group-main">
                <span
                  class="time-group-primary"
                  :class="{ 'time-group-primary--cinema': showViewMode === 'cinema' }"
                >
                  {{ entry.primaryText }}
                </span>
                <span class="time-group-secondary">{{ entry.secondaryText }}</span>
              </div>
              <div class="time-group-actions">
                <span class="time-group-price">{{ formatShowPrice(entry.price) }}</span>
                <el-button
                  size="small"
                  type="primary"
                  plain
                  :disabled="isEntryUnavailable(entry)"
                  @click="$emit('toggle-wish-pool-entry', entry)"
                >
                  {{ getShowActionLabel(entry) }}
                </el-button>
              </div>
            </div>
          </div>
          <el-pagination
            v-if="allEntries.length > SHOWS_PAGE_SIZE"
            class="time-group-pagination"
            small
            background
            layout="prev, pager, next, total"
            :page-size="SHOWS_PAGE_SIZE"
            :total="allEntries.length"
            :current-page="currentPage"
            @current-change="(page) => (currentPage = page)"
          />
        </template>
        <div class="shows-collapse-footer">
          <el-button text type="primary" @click="toggleShows">
            <el-icon><ArrowUp /></el-icon>
            收起场次信息
          </el-button>
        </div>
      </div>
    </el-collapse-transition>
  </el-card>
</template>

<script setup>
import { ArrowUp } from '@element-plus/icons-vue'
import { computed, ref, watch } from 'vue'
import { useScheduleStore } from '@/stores/scheduleStore'
import { formatDateWithRelativeWeek } from '@/utils/dateLabels'

const props = defineProps({
  movie: {
    type: Object,
    required: true,
  },
  index: {
    type: Number,
    default: 0,
  },
  isFetching: {
    type: Boolean,
    default: false,
  },
  isDoubanFetching: {
    type: Boolean,
    default: false,
  },
  movieProgressText: {
    type: String,
    default: '',
  },
  movieFetchDateEntries: {
    type: Array,
    default: () => [],
  },
  showsData: {
    type: Object,
    default: null,
  },
  hasValidShows: {
    type: Boolean,
    default: false,
  },
})

defineEmits([
  'fetch-single-show',
  'fetch-douban',
  'toggle-wish-pool-entry',
  'add-all-to-wish-pool',
])

const store = useScheduleStore()

const descriptionExpanded = ref(false)
const showsExpanded = ref(false)
const showViewMode = ref('time')
const cinemaKeyword = ref('')
const selectedShowDate = ref('')

const movieRegion = computed(() => String(props.movie?.country || '').trim())

const toggleDescription = () => {
  descriptionExpanded.value = !descriptionExpanded.value
}

const toggleShows = () => {
  showsExpanded.value = !showsExpanded.value
}

// Expose toggleShows so parent can auto-expand after fetch
defineExpose({ toggleShows, showsExpanded })

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

const getTotalShows = (movieShowData) => {
  if (!movieShowData || !movieShowData.cinemas) return 0
  return movieShowData.cinemas.reduce((total, cinema) => total + (cinema.shows?.length || 0), 0)
}

const getDateProgressPercent = (item) => {
  if (!item.total) return 0
  return Math.min(100, Math.round((item.done / item.total) * 100))
}

const getDateProgressStatusLabel = (item) => {
  if (item.total > 0 && item.done >= item.total) return '已完成'
  if (item.active) return '进行中'
  return '等待中'
}

const isEntryUnavailable = (entry) => store.isInSchedule(entry.key)

const getShowActionLabel = (entry) => {
  if (store.isInSchedule(entry.key)) return '已在行程'
  if (store.isInWishPool(entry.key)) return '移出想看'
  return '想看'
}

const createShowEntry = (cinema, show) => ({
  key: `${props.movie.id}-${cinema.cinema_id}-${show.date}-${show.time}`,
  movieId: props.movie.id,
  movieTitle: props.movie.title,
  date: show.date,
  time: show.time,
  cinemaId: cinema.cinema_id,
  cinemaName: cinema.cinema_name,
  price: show.price,
  durationMinutes: parseMovieDurationMinutes(props.movie?.duration),
})

const availableDateOptions = computed(() => {
  if (!props.showsData?.cinemas) return []
  const dateSet = new Set()
  props.showsData.cinemas.forEach((cinema) => {
    ;(cinema.shows || []).forEach((show) => {
      if (show.date) dateSet.add(show.date)
    })
  })
  return Array.from(dateSet)
    .sort((a, b) => String(a).localeCompare(String(b)))
    .map((date) => ({ value: date, label: formatDateWithRelativeWeek(date) }))
})

const matchesCinemaKeyword = (cinemaName) => {
  const keyword = cinemaKeyword.value.trim().toLowerCase()
  if (!keyword) return true
  return String(cinemaName || '').toLowerCase().includes(keyword)
}

const matchesSelectedDate = (date) => {
  if (!selectedShowDate.value) return true
  return date === selectedShowDate.value
}

const filteredCinemaShows = computed(() => {
  if (!props.showsData?.cinemas) return []
  return props.showsData.cinemas
    .filter((cinema) => matchesCinemaKeyword(cinema.cinema_name))
    .map((cinema) => ({
      ...cinema,
      shows: (cinema.shows || []).filter((show) => matchesSelectedDate(show.date)),
    }))
    .filter((cinema) => cinema.shows.length > 0)
})

const filteredShowCount = computed(() =>
  filteredCinemaShows.value.reduce((total, cinema) => total + cinema.shows.length, 0),
)

const availableEntries = computed(() => {
  return filteredCinemaShows.value.flatMap((cinema) =>
    cinema.shows
      .map((show) => createShowEntry(cinema, show))
      .filter((entry) => !isEntryUnavailable(entry))
  )
})

const displayGroups = computed(() => {
  const cinemas = filteredCinemaShows.value
  if (cinemas.length === 0) return []
  const mode = showViewMode.value
  const groups = new Map()

  cinemas.forEach((cinema) => {
    cinema.shows.forEach((show) => {
      const date = show.date || '未标注日期'
      const groupKey = mode === 'cinema' ? `${cinema.cinema_id}` : date

      if (!groups.has(groupKey)) {
        groups.set(groupKey, {
          groupKey,
          groupTitle:
            mode === 'cinema' ? cinema.cinema_name : formatDateWithRelativeWeek(date),
          sortKey: mode === 'cinema' ? cinema.cinema_name : date,
          entries: [],
        })
      }

      groups.get(groupKey).entries.push(createShowEntry(cinema, show))
    })
  })

  return Array.from(groups.values())
    .sort((a, b) => String(a.sortKey).localeCompare(String(b.sortKey)))
    .map((group) => ({
      ...group,
      entries: [...group.entries]
        .sort((a, b) => {
          if (mode === 'cinema') {
            const dateCompare = String(a.date || '').localeCompare(String(b.date || ''))
            if (dateCompare !== 0) return dateCompare
          }
          if (mode === 'time') {
            const cinemaCompare = String(a.cinemaName || '').localeCompare(String(b.cinemaName || ''))
            if (cinemaCompare !== 0) return cinemaCompare
          }
          return String(a.time || '').localeCompare(String(b.time || ''))
        })
        .map((entry) => ({
          ...entry,
          primaryText: mode === 'cinema' ? formatDateWithRelativeWeek(entry.date) : entry.cinemaName,
          secondaryText: entry.time,
        })),
    }))
})

// ===== 分页 =====
const SHOWS_PAGE_SIZE = 8
const currentPage = ref(1)

const allEntries = computed(() =>
  displayGroups.value.flatMap((group) => group.entries),
)

const getPagedEntries = () => {
  const start = (currentPage.value - 1) * SHOWS_PAGE_SIZE
  return allEntries.value.slice(start, start + SHOWS_PAGE_SIZE)
}

watch([showViewMode, cinemaKeyword, selectedShowDate], () => {
  currentPage.value = 1
})
</script>

<style scoped>
.movie-card {
  transition: box-shadow 0.3s;
}

.movie-card:hover {
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.15);
}

.movie-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 20px;
}

.movie-basic-info {
  flex: 1;
  min-width: 0;
}

.movie-title-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.movie-index {
  font-weight: bold;
  color: #909399;
  font-size: 16px;
  min-width: 30px;
}

.movie-title {
  font-size: 18px;
  font-weight: bold;
  color: #303133;
}

.movie-score {
  margin-left: auto;
}

.douban-link {
  color: inherit;
  text-decoration: none;
}

.douban-link:hover {
  text-decoration: underline;
}

.movie-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: center;
  margin-bottom: 10px;
}

.meta-item {
  display: inline-flex;
  align-items: center;
  min-height: 30px;
  padding: 0 12px;
  border-radius: 999px;
  background: linear-gradient(135deg, #e8f1ff 0%, #f6f9ff 100%);
  border: 1px solid #d7e6ff;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.8);
  color: #1f3b73;
  font-size: 13px;
  font-weight: 600;
}

.meta-item--primary {
  letter-spacing: 0.01em;
}

.movie-secondary-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 2px;
}

.secondary-meta-item {
  display: inline-flex;
  align-items: center;
  min-height: 24px;
  padding: 0 10px;
  border-radius: 999px;
  background-color: #f6f7fb;
  color: #6b7280;
  font-size: 12px;
  line-height: 1.4;
}

.movie-actions {
  display: flex;
  gap: 8px;
  flex-shrink: 0;
}

.movie-description {
  margin-top: 8px;
}

.description-content {
  padding: 12px;
  background-color: #f5f7fa;
  border-radius: 4px;
  line-height: 1.6;
  color: #606266;
  font-size: 14px;
}

.movie-shows {
  margin-top: 8px;
}

.shows-summary {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 12px;
}

.shows-filter-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 12px;
}

.shows-filter-input {
  flex: 1 1 200px;
  min-width: 160px;
  max-width: 320px;
}

.shows-filter-select {
  flex: 0 0 200px;
}

.shows-empty {
  padding: 24px 12px;
  background-color: #fafbff;
  border: 1px dashed #d7e6ff;
  border-radius: 6px;
  color: #94a3b8;
  font-size: 13px;
  text-align: center;
}

.show-view-mode {
  margin-left: auto;
}

.single-movie-progress {
  margin-top: 0;
}

.progress-content {
  padding: 8px 12px;
  background-color: #f0f9ff;
  border-radius: 4px;
  border-left: 3px solid #409eff;
}

.progress-label {
  margin-bottom: 4px;
  font-size: 12px;
  font-weight: 600;
  color: #1d4ed8;
}

.progress-text {
  margin-top: 8px;
  font-size: 13px;
  color: #409eff;
  line-height: 1.5;
}

.date-progress-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.progress-section-title {
  font-size: 13px;
  font-weight: 600;
  color: #303133;
}

.date-progress-item {
  padding: 10px 12px;
  background-color: #f8fbff;
  border: 1px solid #d9ecff;
  border-radius: 6px;
}

.date-progress-item--active {
  border-color: #409eff;
  box-shadow: 0 0 0 1px rgba(64, 158, 255, 0.15);
}

.date-progress-main {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
  font-size: 13px;
  color: #409eff;
}

.date-progress-meta {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.date-progress-date {
  font-weight: 500;
}

.date-progress-status {
  display: inline-flex;
  align-items: center;
  min-height: 24px;
  padding: 0 8px;
  border-radius: 999px;
  background-color: #eaf3ff;
  color: #1d4ed8;
  font-size: 12px;
  font-weight: 600;
}

.date-progress-count {
  color: #606266;
}

.time-group-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.time-group-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 12px;
  border-radius: 6px;
  background-color: #f5f7fb;
}

.time-group-main {
  display: flex;
  align-items: center;
  gap: 12px;
}

.time-group-primary {
  min-width: 56px;
  color: #0f172a;
  font-size: 13px;
  font-weight: 600;
}

.time-group-primary--cinema {
  min-width: 0;
}

.time-group-secondary {
  color: #475569;
  font-size: 13px;
}

.time-group-price {
  color: #111827;
  font-size: 13px;
  font-weight: 600;
}

.time-group-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.time-group-pagination {
  justify-content: flex-end;
  margin-top: 8px;
}

.shows-collapse-footer {
  display: flex;
  justify-content: center;
  margin-top: 16px;
  padding-top: 4px;
}

.shows-collapse-footer .el-button {
  gap: 6px;
}

@media (max-width: 960px) {
  .movie-header {
    flex-direction: column;
    gap: 12px;
  }

  .movie-actions {
    width: 100%;
    flex-wrap: wrap;
  }

  .show-view-mode {
    margin-left: 0;
    width: 100%;
  }
}

@media (max-width: 640px) {
  .movie-actions .el-button {
    flex: 1 1 140px;
  }

  .date-progress-main {
    flex-direction: column;
    align-items: flex-start;
    gap: 6px;
  }

  .movie-secondary-meta {
    gap: 6px;
  }

  .meta-item {
    min-height: 28px;
    padding: 0 10px;
  }

  .shows-summary {
    align-items: flex-start;
  }

  .shows-filter-bar {
    flex-direction: column;
    align-items: stretch;
  }

  .shows-filter-input,
  .shows-filter-select {
    width: 100%;
    max-width: none;
    flex: none;
  }

  .time-group-row {
    flex-direction: column;
    align-items: flex-start;
  }

  .time-group-main {
    flex-direction: column;
    align-items: flex-start;
    gap: 4px;
  }

  .time-group-actions {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
