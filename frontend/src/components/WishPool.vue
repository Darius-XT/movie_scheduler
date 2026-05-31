<template>
  <el-card
    class="planning-card wish-planning-card"
    :body-style="groupedWishMovies.length === 0 ? { display: 'none' } : undefined"
  >
    <template #header>
      <div class="planning-header">
        <div class="planning-header-main">
          <span>想看</span>
        </div>
        <div v-if="store.wishMovies.length > 0" class="planning-header-actions">
          <el-button
            type="primary"
            size="small"
            :loading="batchFetching"
            @click="handleBatchFetch"
          >
            一键抓取&更新场次
          </el-button>
          <el-button text size="small" @click="expandAllWishGroups">全部展开</el-button>
          <el-button text size="small" @click="collapseAllWishGroups">全部收起</el-button>
        </div>
      </div>
      <el-progress
        v-if="batchFetching || (batchTotal > 0 && batchDone < batchTotal)"
        class="planning-header-progress"
        :percentage="batchPercentage"
        :format="() => `${batchDone}/${batchTotal} 部完成`"
      />
      <el-tabs
        v-if="store.wishMovies.length > 0"
        v-model="activeWeekFilter"
        class="planning-header-tabs"
      >
        <el-tab-pane
          v-for="filter in weekFilterOptions"
          :key="filter.value"
          :name="filter.value"
          :label="`${filter.label} (${filter.count})`"
        />
      </el-tabs>
    </template>
    <div v-if="groupedWishMovies.length > 0" class="wish-pool-list">
      <div
        v-for="group in groupedWishMovies"
        :key="group.movieId"
        class="wish-pool-group"
      >
        <div class="wish-pool-group-header">
          <div class="wish-pool-group-title">
            <span>{{ group.movieTitle }}</span>
            <span v-if="getWishGroupMovieMeta(group.movie)" class="wish-pool-group-meta">
              {{ getWishGroupMovieMeta(group.movie) }}
            </span>
          </div>
          <div class="wish-pool-group-actions">
            <el-button
              size="small"
              :type="group.hasShows ? 'success' : 'primary'"
              :loading="fetchingMovieIds.has(group.movieId)"
              @click="handleFetchOne(group.movie)"
            >
              {{ group.hasShows ? '更新场次' : '抓取场次' }}
            </el-button>
            <el-button text size="small" @click="handleRemoveWishMovie(group.movie)">
              移出想看
            </el-button>
            <el-button text size="small" @click="toggleWishGroup(group.movieId)">
              {{ isWishGroupCollapsed(group.movieId) ? '展开' : '收起' }}
            </el-button>
          </div>
        </div>
        <div v-if="!isWishGroupCollapsed(group.movieId)" class="wish-pool-group-body">
          <div v-if="movieProgress.get(group.movieId)" class="wish-pool-group-progress">
            {{ movieProgress.get(group.movieId) }}
          </div>
          <template v-if="!group.hasShows">
            <div class="wish-pool-group-empty">
              暂无场次,点击「抓取场次」获取
            </div>
          </template>
          <template v-else>
            <div v-if="group.items.length > 1" class="wish-pool-group-filter">
              <el-input
                :model-value="getWishGroupFilter(group.movieId).cinema"
                class="wish-pool-group-filter-input"
                size="small"
                clearable
                placeholder="搜索影院名"
                @update:model-value="(value) => updateWishGroupFilter(group.movieId, { cinema: value })"
              />
              <el-select
                :model-value="getWishGroupFilter(group.movieId).date"
                class="wish-pool-group-filter-select"
                size="small"
                clearable
                placeholder="全部日期"
                @update:model-value="(value) => updateWishGroupFilter(group.movieId, { date: value ?? '' })"
              >
                <el-option
                  v-for="dateOption in getWishGroupDateOptions(group)"
                  :key="dateOption.value"
                  :label="dateOption.label"
                  :value="dateOption.value"
                />
              </el-select>
              <span
                v-if="getFilteredWishItems(group).length !== group.items.length"
                class="wish-pool-group-filter-summary"
              >
                {{ getFilteredWishItems(group).length }} / {{ group.items.length }}
              </span>
            </div>
            <div
              v-if="getFilteredWishItems(group).length === 0"
              class="wish-pool-group-empty"
            >
              没有符合筛选条件的场次
            </div>
            <template v-else>
              <div class="wish-pool-group-list">
                <div
                  v-for="item in getPagedWishItems(group)"
                  :key="item.key"
                  class="wish-pool-item"
                >
                  <div class="wish-pool-main">
                    <div class="wish-pool-meta">
                      <span>{{ formatDateWithRelativeWeek(item.date) }}</span>
                      <span>{{ formatWishItemTimeRange(item) }}</span>
                      <span>{{ item.cinemaName }}</span>
                      <span>{{ formatShowPrice(item.price) }}</span>
                    </div>
                  </div>
                  <div class="wish-pool-actions">
                    <el-button
                      size="small"
                      type="success"
                      :plain="store.isInSchedule(item.key)"
                      :disabled="store.isInSchedule(item.key)"
                      @click="handleAddToSchedule(item)"
                    >
                      {{ store.isInSchedule(item.key) ? '已加入行程' : '加入行程' }}
                    </el-button>
                  </div>
                </div>
              </div>
              <el-pagination
                v-if="getFilteredWishItems(group).length > SHOWS_PAGE_SIZE"
                class="wish-pool-group-pagination"
                small
                background
                layout="prev, pager, next, total"
                :page-size="SHOWS_PAGE_SIZE"
                :total="getFilteredWishItems(group).length"
                :current-page="getWishGroupPage(group.movieId)"
                @current-change="(page) => setWishGroupPage(group.movieId, page)"
              />
            </template>
          </template>
        </div>
      </div>
    </div>
  </el-card>
</template>

<script setup>
import { ElMessage, ElMessageBox } from 'element-plus'
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useShowFetching } from '@/composables/useShowFetching'
import { useScheduleStore } from '@/stores/scheduleStore'
import { formatDateWithRelativeWeek, getWeekOffsetFromToday } from '@/utils/dateLabels'
import { formatShowTimeRange, parseShowTimeToMinutes } from '@/utils/showTime'

const props = defineProps({
  updateForm: {
    type: Object,
    required: true,
  },
})

const store = useScheduleStore()

const {
  fetchingMovieIds,
  movieProgress,
  handleFetchSingleShow,
  handleBatchFetchShows,
  batchFetching,
  batchTotal,
  batchDone,
  scheduleMidnightCleanup,
  stopMidnightCleanup,
} = useShowFetching(store, props.updateForm)

const WISH_GROUP_DEFAULT_COLLAPSED = true
const SHOWS_PAGE_SIZE = 8

const WEEK_FILTER_DEFINITIONS = [
  { value: 'all', label: '全部', offset: null },
  { value: 'current', label: '本周', offset: 0 },
  { value: 'next', label: '下周', offset: 1 },
]

const EMPTY_WISH_GROUP_FILTER = Object.freeze({ cinema: '', date: '' })

const wishGroupCollapseOverrides = ref(new Map())
const wishGroupFilters = ref(new Map())
const wishGroupPages = ref(new Map())
const activeWeekFilter = ref('all')

onMounted(() => {
  scheduleMidnightCleanup()
})

onBeforeUnmount(() => {
  stopMidnightCleanup()
})

const batchPercentage = computed(() => {
  if (!batchTotal.value) return 0
  return Math.round((batchDone.value / batchTotal.value) * 100)
})

const parseMovieDurationMinutes = (durationText) => {
  const normalized = String(durationText ?? '').trim()
  const match = normalized.match(/(\d+)/)
  return match ? Number(match[1]) : null
}

const buildShowEntries = (movie) => {
  const showsData = store.getMovieShowsData(movie.id)
  if (!showsData?.cinemas) return []
  const durationMinutes = parseMovieDurationMinutes(movie?.duration)
  return showsData.cinemas.flatMap((cinema) =>
    (cinema.shows || []).map((show) => ({
      key: `${movie.id}-${cinema.cinema_id}-${show.date}-${show.time}`,
      movieId: movie.id,
      movieTitle: movie.title,
      date: show.date,
      time: show.time,
      cinemaId: cinema.cinema_id,
      cinemaName: cinema.cinema_name,
      price: show.price,
      durationMinutes,
    }))
  )
}

const getItemWeekFilterValue = (item) => {
  const offset = getWeekOffsetFromToday(item.date)
  const definition = WEEK_FILTER_DEFINITIONS.find((entry) => entry.offset === offset)
  return definition ? definition.value : null
}

const matchesActiveWeekFilter = (item) => {
  if (activeWeekFilter.value === 'all') return true
  return getItemWeekFilterValue(item) === activeWeekFilter.value
}

const formatShowPrice = (price) => {
  const normalized = String(price ?? '').trim()
  if (!normalized || normalized === '0' || normalized === '0.0' || normalized === '0.00') return '暂无价格'
  return `￥${normalized}`
}

const getShowEntryDurationMinutes = (showEntry) => {
  if (typeof showEntry?.durationMinutes === 'number' && !Number.isNaN(showEntry.durationMinutes)) {
    return showEntry.durationMinutes
  }
  const movie = store.wishMovies.find((item) => item.id === showEntry?.movieId)
  return parseMovieDurationMinutes(movie?.duration)
}

const formatWishItemTimeRange = (item) => formatShowTimeRange(item.time, getShowEntryDurationMinutes(item))

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

const groupedWishMovies = computed(() => {
  return store.wishMovies.map((movie) => {
    const allEntries = buildShowEntries(movie)
    const filteredByWeek = allEntries.filter(matchesActiveWeekFilter)
    return {
      movieId: movie.id,
      movieTitle: movie.title,
      movie,
      hasShows: allEntries.length > 0,
      items: filteredByWeek.sort((a, b) => {
        const aKey = `${a.date} ${a.time}`
        const bKey = `${b.date} ${b.time}`
        return aKey.localeCompare(bKey)
      }),
    }
  }).filter((group) => {
    // 当 week filter 不是 'all' 时,只显示有匹配周场次的电影;或者无场次的电影也保留(让用户能抓取)
    if (activeWeekFilter.value === 'all') return true
    return group.items.length > 0 || !group.hasShows
  })
})

const weekFilterOptions = computed(() => {
  const movieIdsByFilter = new Map(
    WEEK_FILTER_DEFINITIONS.map((definition) => [definition.value, new Set()])
  )
  store.wishMovies.forEach((movie) => {
    movieIdsByFilter.get('all').add(movie.id)
    const entries = buildShowEntries(movie)
    entries.forEach((item) => {
      const value = getItemWeekFilterValue(item)
      if (value && movieIdsByFilter.has(value)) {
        movieIdsByFilter.get(value).add(movie.id)
      }
    })
  })
  return WEEK_FILTER_DEFINITIONS.map((definition) => ({
    value: definition.value,
    label: definition.label,
    count: movieIdsByFilter.get(definition.value).size,
  }))
})

watch(activeWeekFilter, () => {
  wishGroupPages.value = new Map()
})

const getMovieYear = (movie) => {
  const releaseDate = String(movie?.release_date || '').trim()
  const match = releaseDate.match(/^(\d{4})/)
  return match ? match[1] : ''
}

const getWishGroupMovieMeta = (movie) => {
  if (!movie) return ''
  const metaParts = [
    getMovieYear(movie),
    String(movie.director || '').trim(),
    String(movie.country || '').trim(),
  ].filter(Boolean)
  return metaParts.join(' · ')
}

const isWishGroupCollapsed = (movieId) => {
  if (wishGroupCollapseOverrides.value.has(movieId)) {
    return wishGroupCollapseOverrides.value.get(movieId)
  }
  return WISH_GROUP_DEFAULT_COLLAPSED
}

const toggleWishGroup = (movieId) => {
  const next = new Map(wishGroupCollapseOverrides.value)
  next.set(movieId, !isWishGroupCollapsed(movieId))
  wishGroupCollapseOverrides.value = next
}

const getWishGroupFilter = (movieId) => {
  return wishGroupFilters.value.get(movieId) || EMPTY_WISH_GROUP_FILTER
}

const updateWishGroupFilter = (movieId, patch) => {
  const current = getWishGroupFilter(movieId)
  const nextFilter = { ...current, ...patch }
  const next = new Map(wishGroupFilters.value)
  if (!nextFilter.cinema && !nextFilter.date) {
    next.delete(movieId)
  } else {
    next.set(movieId, nextFilter)
  }
  wishGroupFilters.value = next
  if (wishGroupPages.value.has(movieId)) {
    const nextPages = new Map(wishGroupPages.value)
    nextPages.delete(movieId)
    wishGroupPages.value = nextPages
  }
}

const getWishGroupDateOptions = (group) => {
  if (!group?.items) return []
  const uniqueDates = Array.from(new Set(group.items.map((item) => item.date).filter(Boolean))).sort()
  return uniqueDates.map((date) => ({ value: date, label: formatDateWithRelativeWeek(date) }))
}

const getFilteredWishItems = (group) => {
  const filter = getWishGroupFilter(group.movieId)
  const cinemaKeyword = String(filter.cinema || '').trim().toLowerCase()
  const targetDate = String(filter.date || '').trim()
  if (!cinemaKeyword && !targetDate) return group.items
  return group.items.filter((item) => {
    if (targetDate && item.date !== targetDate) return false
    if (cinemaKeyword && !String(item.cinemaName || '').toLowerCase().includes(cinemaKeyword)) return false
    return true
  })
}

const getWishGroupPage = (movieId) => wishGroupPages.value.get(movieId) || 1

const setWishGroupPage = (movieId, page) => {
  const next = new Map(wishGroupPages.value)
  next.set(movieId, page)
  wishGroupPages.value = next
}

const getPagedWishItems = (group) => {
  const filtered = getFilteredWishItems(group)
  const page = getWishGroupPage(group.movieId)
  const start = (page - 1) * SHOWS_PAGE_SIZE
  return filtered.slice(start, start + SHOWS_PAGE_SIZE)
}

const expandAllWishGroups = () => {
  const next = new Map()
  groupedWishMovies.value.forEach((group) => {
    next.set(group.movieId, false)
  })
  wishGroupCollapseOverrides.value = next
}

const collapseAllWishGroups = () => {
  const next = new Map()
  groupedWishMovies.value.forEach((group) => {
    next.set(group.movieId, true)
  })
  wishGroupCollapseOverrides.value = next
}

const handleFetchOne = async (movie) => {
  if (!movie?.id) return
  await handleFetchSingleShow(movie)
  // 抓取完成后自动展开该电影场次
  const next = new Map(wishGroupCollapseOverrides.value)
  next.set(movie.id, false)
  wishGroupCollapseOverrides.value = next
}

const handleBatchFetch = async () => {
  if (batchFetching.value) return
  if (store.wishMovies.length === 0) {
    ElMessage.warning('想看列表为空')
    return
  }
  await handleBatchFetchShows(store.wishMovies)
}

const handleRemoveWishMovie = async (movie) => {
  if (!movie?.id) return
  if (store.hasScheduleForMovie(movie.id)) {
    ElMessage.warning(`《${movie.title}》还有场次在行程中,请先从行程移除`)
    return
  }
  try {
    await ElMessageBox.confirm(
      `确认将《${movie.title}》从想看中移除?`,
      '移出想看',
      {
        type: 'warning',
        confirmButtonText: '移除',
        cancelButtonText: '取消',
      }
    )
  } catch {
    return
  }
  try {
    await store.removeFromWishMovies(movie.id)
    store.removeMovieShowsData(movie.id)
    // 清理本组件内的 UI 状态
    ;[wishGroupCollapseOverrides, wishGroupFilters, wishGroupPages].forEach((mapRef) => {
      if (mapRef.value.has(movie.id)) {
        const next = new Map(mapRef.value)
        next.delete(movie.id)
        mapRef.value = next
      }
    })
    ElMessage.info(`已将《${movie.title}》移出想看`)
  } catch {
    // wishSyncError watcher 会提示
  }
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
  align-items: center;
  gap: 10px;
  min-width: 0;
  flex-wrap: wrap;
}

.planning-header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.planning-header-progress {
  margin-top: 8px;
}

.planning-header-tabs {
  margin-top: 8px;
}

.planning-header-tabs :deep(.el-tabs__header) {
  margin: 0;
}

.planning-header-tabs :deep(.el-tabs__nav-wrap::after) {
  height: 1px;
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
  align-items: center;
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

.wish-pool-group-body {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.wish-pool-group-progress {
  padding: 6px 10px;
  background-color: #f0f9ff;
  border-left: 3px solid #409eff;
  color: #1d4ed8;
  font-size: 12px;
  border-radius: 4px;
}

.wish-pool-group-filter {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.wish-pool-group-filter-input {
  width: 180px;
}

.wish-pool-group-filter-select {
  width: 200px;
}

.wish-pool-group-filter-summary {
  color: #64748b;
  font-size: 12px;
}

.wish-pool-group-empty {
  color: #94a3b8;
  font-size: 13px;
  padding: 8px 0;
}

.wish-pool-group-pagination {
  justify-content: flex-end;
  margin-top: 8px;
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

  .wish-pool-group-filter-input,
  .wish-pool-group-filter-select {
    width: 100%;
  }
}
</style>
