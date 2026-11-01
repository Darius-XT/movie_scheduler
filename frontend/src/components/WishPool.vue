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
        <div class="planning-header-actions">
          <div v-if="activeViewingFilter === 'cinema' && store.wishMovies.length > 0" class="planning-header-secondary-actions">
            <el-button text size="small" @click="expandAllWishGroups">全部展开</el-button>
            <el-button text size="small" @click="collapseAllWishGroups">全部收起</el-button>
          </div>
          <ManualMovieDialog />
        </div>
      </div>
      <el-tabs
        v-if="store.wishMovies.length > 0"
        v-model="activeViewingFilter"
        class="planning-header-tabs"
      >
        <el-tab-pane
          v-for="filter in viewingFilterOptions"
          :key="filter.value"
          :name="filter.value"
          :label="`${filter.label} (${filter.count})`"
        />
      </el-tabs>
      <el-tabs v-if="activeViewingFilter === 'home'" v-model="activeChannelFilter">
        <el-tab-pane
          v-for="channel in channelFilterOptions"
          :key="channel.value"
          :name="channel.value"
          :label="`${channel.label} (${channel.count})`"
        />
      </el-tabs>
      <div v-if="activeViewingFilter === 'cinema' && store.wishMovies.length > 0" class="wish-global-filter">
        <div class="wish-global-filter-field">
          <span class="wish-global-filter-label">影院</span>
          <el-select
            :model-value="globalWishFilter.cinemaId"
            class="wish-global-filter-select wish-global-filter-select--cinema"
            filterable
            clearable
            size="small"
            placeholder="全部影院"
            :disabled="globalCinemaOptions.length === 0"
            @update:model-value="handleGlobalCinemaChange"
          >
            <el-option
              v-for="cinemaOption in globalCinemaOptions"
              :key="cinemaOption.value"
              :label="cinemaOption.label"
              :value="cinemaOption.value"
            />
          </el-select>
        </div>
        <div class="wish-global-filter-field">
          <span class="wish-global-filter-label">日期</span>
          <el-select
            :model-value="globalWishFilter.date"
            class="wish-global-filter-select wish-global-filter-select--date"
            clearable
            size="small"
            :placeholder="globalDatePlaceholder"
            :disabled="globalDateOptions.length === 0"
            @update:model-value="handleGlobalDateChange"
          >
            <el-option
              v-for="dateOption in globalDateOptions"
              :key="dateOption.value"
              :label="dateOption.label"
              :value="dateOption.value"
            />
          </el-select>
        </div>
        <el-checkbox v-model="currentWeekOnly">仅看本周</el-checkbox>
        <div class="wish-global-filter-field wish-weekend-filter-field">
          <el-checkbox
            :model-value="globalWishFilter.weekendOnly"
            class="wish-weekend-checkbox"
            @update:model-value="handleGlobalWeekendOnlyChange"
          >
            只看周末
          </el-checkbox>
        </div>
        <div class="wish-global-filter-field wish-weekend-filter-field">
          <el-checkbox
            :model-value="globalWishFilter.joinableOnly"
            class="wish-weekend-checkbox"
            @update:model-value="handleGlobalJoinableOnlyChange"
          >
            可加入行程
          </el-checkbox>
        </div>
      </div>
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
            <MovieShowUpdateButton
              v-if="activeViewingFilter === 'cinema' && group.movieId > 0"
              :movie-id="group.movieId"
              :city-id="cityId"
            />
            <MovieViewingLocationButtons :movie="group.movie" />
            <MovieChannelSelect v-if="activeViewingFilter === 'home'" :movie="group.movie" />
            <el-button text size="small" @click="handleRemoveWishMovie(group.movie)">
              移出想看
            </el-button>
            <el-button v-if="activeViewingFilter === 'cinema'" text size="small" @click="toggleWishGroup(group.movieId)">
              {{ isWishGroupCollapsed(group.movieId) ? '展开' : '收起' }}
            </el-button>
          </div>
        </div>
        <div v-if="activeViewingFilter === 'cinema' && !isWishGroupCollapsed(group.movieId)" class="wish-pool-group-body">
          <div class="wish-pool-group-filter">
            <el-select
              :model-value="getWishGroupFilter(group.movieId).cinemaId"
              class="wish-pool-group-filter-input"
              size="small"
              filterable
              clearable
              placeholder="全部影院"
              @update:model-value="(value) => updateWishGroupFilter(group.movieId, { cinemaId: normalizeFilterValue(value), cinema: '' })"
            >
              <el-option
                v-for="cinemaOption in getWishGroupCinemaOptions(group)"
                :key="cinemaOption.value"
                :label="cinemaOption.label"
                :value="cinemaOption.value"
              />
            </el-select>
            <el-select
              :model-value="getWishGroupFilter(group.movieId).date"
              class="wish-pool-group-filter-select"
              size="small"
              clearable
              :placeholder="globalDatePlaceholder"
              @update:model-value="(value) => updateWishGroupFilter(group.movieId, { date: value ?? '' })"
            >
              <el-option
                v-for="dateOption in getWishGroupDateOptions(group)"
                :key="dateOption.value"
                :label="dateOption.label"
                :value="dateOption.value"
              />
            </el-select>
            <el-checkbox
              :model-value="getWishGroupFilter(group.movieId).weekendOnly"
              class="wish-weekend-checkbox"
              @update:model-value="(value) => updateWishGroupFilter(group.movieId, { weekendOnly: Boolean(value) })"
            >
              只看周末
            </el-checkbox>
            <el-checkbox
              :model-value="getWishGroupFilter(group.movieId).joinableOnly"
              class="wish-weekend-checkbox"
              @update:model-value="(value) => updateWishGroupFilter(group.movieId, { joinableOnly: Boolean(value) })"
            >
              可加入行程
            </el-checkbox>
            <span class="wish-pool-group-filter-summary">
              {{ getFilteredWishItems(group).length }} / {{ group.items.length }}
            </span>
          </div>
          <template v-if="!group.hasShows">
            <div class="wish-pool-group-empty">
              {{ group.movieId < 0 ? '手动添加的电影，暂不支持自动获取场次' : group.isLoading ? '正在抓取场次...' : '暂无场次,等待下一次自动抓取' }}
            </div>
          </template>
          <template v-else>
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
import { computed, ref, watch } from 'vue'
import ManualMovieDialog from '@/components/ManualMovieDialog.vue'
import MovieChannelSelect from '@/components/MovieChannelSelect.vue'
import MovieViewingLocationButtons from '@/components/MovieViewingLocationButtons.vue'
import MovieShowUpdateButton from '@/components/MovieShowUpdateButton.vue'
import { MOVIE_CHANNELS, getMovieViewingGroup, getMovieYear, matchesMovieChannel } from '@/utils/wishFilters'
import { useScheduleStore } from '@/stores/scheduleStore'
import {
  formatDateAsWeekdayWithMonthDay,
  formatDateWithRelativeWeek,
  getWeekOffsetFromToday,
  isWeekendDate,
} from '@/utils/dateLabels'
import { formatShowTimeRange, parseShowTimeToMinutes, UNKNOWN_SHOW_DURATION_MINUTES } from '@/utils/showTime'

const store = useScheduleStore()
defineProps({ cityId: { type: Number, default: null } })

const WISH_GROUP_DEFAULT_COLLAPSED = true
const SHOWS_PAGE_SIZE = 8

const VIEWING_FILTER_DEFINITIONS = [
  { value: 'home', label: '家里看' },
  { value: 'cinema', label: '影院看' },
  { value: 'unclassified', label: '未分类' },
]

const EMPTY_WISH_GROUP_FILTER = Object.freeze({
  cinemaId: '',
  cinema: '',
  date: '',
  weekendOnly: false,
  joinableOnly: false,
})

const wishGroupCollapseOverrides = ref(new Map())
const wishGroupFilters = ref(new Map())
const wishGroupPages = ref(new Map())
const activeViewingFilter = ref('unclassified')
const activeChannelFilter = ref('all')
const currentWeekOnly = ref(false)
const viewingFilterOptions = computed(() => VIEWING_FILTER_DEFINITIONS.map((filter) => ({
  ...filter,
  count: store.wishMovies.filter((movie) => getMovieViewingGroup(movie) === filter.value).length,
})))
const cinemaMovies = computed(() => store.wishMovies.filter((movie) => getMovieViewingGroup(movie) === 'cinema'))
const homeMovies = computed(() => store.wishMovies.filter((movie) => getMovieViewingGroup(movie) === 'home'))
const channelFilterOptions = computed(() => [
  { value: 'all', label: '全部' }, ...MOVIE_CHANNELS, { value: 'none', label: '暂无' },
].map((channel) => ({
  ...channel, count: homeMovies.value.filter((movie) => matchesMovieChannel(movie, channel.value)).length,
})))
const visibleMovies = computed(() => store.wishMovies.filter((movie) =>
  getMovieViewingGroup(movie) === activeViewingFilter.value
  && (activeViewingFilter.value !== 'home' || matchesMovieChannel(movie, activeChannelFilter.value))
))
const globalWishFilter = ref({
  cinemaId: '',
  date: '',
  weekendOnly: false,
  joinableOnly: false,
})

const normalizeFilterValue = (value) => {
  if (value == null) return ''
  return String(value).trim()
}

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

const matchesActiveWeekFilter = (item) => {
  return !currentWeekOnly.value || getWeekOffsetFromToday(item.date) === 0
}

const formatWishDateFilterLabel = (date) => {
  if (!currentWeekOnly.value) return formatDateWithRelativeWeek(date)
  return formatDateAsWeekdayWithMonthDay(date)
}

const buildCinemaOptions = (items) => {
  const cinemaMap = new Map()
  items.forEach((item) => {
    const cinemaId = normalizeFilterValue(item.cinemaId)
    if (!cinemaId || cinemaMap.has(cinemaId)) return
    cinemaMap.set(cinemaId, {
      value: cinemaId,
      label: String(item.cinemaName || '').trim() || `影院 ${cinemaId}`,
    })
  })
  return Array.from(cinemaMap.values()).sort((a, b) => a.label.localeCompare(b.label, 'zh'))
}

const buildDateOptions = (items, { weekendOnly = false } = {}) => {
  const sourceItems = weekendOnly ? items.filter((item) => isWeekendDate(item.date)) : items
  const uniqueDates = Array.from(new Set(sourceItems.map((item) => item.date).filter(Boolean))).sort()
  return uniqueDates.map((date) => ({ value: date, label: formatWishDateFilterLabel(date) }))
}

const activeWeekShowEntries = computed(() => {
  return cinemaMovies.value.flatMap((movie) => buildShowEntries(movie)).filter(matchesActiveWeekFilter)
})

const globalCinemaOptions = computed(() => buildCinemaOptions(activeWeekShowEntries.value))

const globalDateOptions = computed(() =>
  buildDateOptions(activeWeekShowEntries.value, { weekendOnly: globalWishFilter.value.weekendOnly })
)

const globalDatePlaceholder = computed(() => {
  return currentWeekOnly.value ? '本周日期' : '全部日期'
})

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
  const parsed = parseMovieDurationMinutes(movie?.duration)
  if (parsed != null) return parsed
  // 手动添加的行程没有对应 wishMovie,可能没填片长,这里用默认值做冲突检测的回退,
  // 与 planningStore.removePastSchedules 走的 UNKNOWN_SHOW_DURATION_MINUTES 保持一致。
  if (showEntry?.movieId === 0) return UNKNOWN_SHOW_DURATION_MINUTES
  return null
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

const isShowEntryJoinable = (showEntry) => {
  return !store.isInSchedule(showEntry.key) && !getScheduleConflict(showEntry)
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

const isMovieShowsLoading = (movieId) => {
  const isPolling = store.isMovieShowsPolling
  return typeof isPolling === 'function' ? isPolling(movieId) : false
}

const groupedWishMovies = computed(() => {
  return visibleMovies.value.map((movie) => {
    const allEntries = activeViewingFilter.value === 'cinema' ? buildShowEntries(movie) : []
    const filteredByWeek = allEntries.filter(matchesActiveWeekFilter)
    return {
      movieId: movie.id,
      movieTitle: movie.title,
      movie,
      isLoading: isMovieShowsLoading(movie.id),
      hasShows: allEntries.length > 0,
      items: filteredByWeek.sort((a, b) => {
        const aKey = `${a.date} ${a.time}`
        const bKey = `${b.date} ${b.time}`
        return aKey.localeCompare(bKey)
      }),
    }
  }).filter((group) => {
    if (activeViewingFilter.value !== 'cinema' || !currentWeekOnly.value) return true
    return group.items.length > 0
  })
})

const normalizeWishGroupFilter = (filter = EMPTY_WISH_GROUP_FILTER) => {
  const date = normalizeFilterValue(filter.date)
  const weekendOnly = Boolean(filter.weekendOnly)
  return {
    cinemaId: normalizeFilterValue(filter.cinemaId),
    cinema: String(filter.cinema || ''),
    date: weekendOnly && !isWeekendDate(date) ? '' : date,
    weekendOnly,
    joinableOnly: Boolean(filter.joinableOnly),
  }
}

const isWishGroupFilterEmpty = (filter) => {
  return !filter.cinemaId
    && !filter.cinema
    && !filter.date
    && !filter.weekendOnly
    && !filter.joinableOnly
}

const getCinemaLabelById = (cinemaId) => {
  const normalizedCinemaId = normalizeFilterValue(cinemaId)
  const option = globalCinemaOptions.value.find((item) => item.value === normalizedCinemaId)
  return option?.label || normalizedCinemaId
}

const applyGlobalFilterPatchToGroups = (patch) => {
  const next = new Map(wishGroupFilters.value)
  store.wishMovies.forEach((movie) => {
    const current = normalizeWishGroupFilter(next.get(movie.id))
    const nextFilter = normalizeWishGroupFilter({ ...current, ...patch })
    if (isWishGroupFilterEmpty(nextFilter)) {
      next.delete(movie.id)
    } else {
      next.set(movie.id, nextFilter)
    }
  })
  wishGroupFilters.value = next
  wishGroupPages.value = new Map()
}

const handleGlobalCinemaChange = (value) => {
  const cinemaId = normalizeFilterValue(value)
  globalWishFilter.value = { ...globalWishFilter.value, cinemaId }
  applyGlobalFilterPatchToGroups({ cinemaId, cinema: '' })
}

const handleGlobalDateChange = (value) => {
  const date = normalizeFilterValue(value)
  globalWishFilter.value = { ...globalWishFilter.value, date }
  applyGlobalFilterPatchToGroups({ date })
}

const handleGlobalWeekendOnlyChange = (value) => {
  const weekendOnly = Boolean(value)
  const nextGlobalFilter = normalizeWishGroupFilter({ ...globalWishFilter.value, weekendOnly })
  globalWishFilter.value = {
    cinemaId: nextGlobalFilter.cinemaId,
    date: nextGlobalFilter.date,
    weekendOnly: nextGlobalFilter.weekendOnly,
    joinableOnly: nextGlobalFilter.joinableOnly,
  }
  applyGlobalFilterPatchToGroups({ weekendOnly })
}

const handleGlobalJoinableOnlyChange = (value) => {
  const joinableOnly = Boolean(value)
  globalWishFilter.value = { ...globalWishFilter.value, joinableOnly }
  applyGlobalFilterPatchToGroups({ joinableOnly })
}

const hasActiveJoinableOnlyFilter = computed(() => {
  if (globalWishFilter.value.joinableOnly) return true
  return Array.from(wishGroupFilters.value.values()).some((filter) => Boolean(filter?.joinableOnly))
})

const pruneInvalidGlobalWishFilter = () => {
  const current = {
    cinemaId: normalizeFilterValue(globalWishFilter.value.cinemaId),
    date: normalizeFilterValue(globalWishFilter.value.date),
    weekendOnly: Boolean(globalWishFilter.value.weekendOnly),
    joinableOnly: Boolean(globalWishFilter.value.joinableOnly),
  }
  const validCinemaIds = new Set(globalCinemaOptions.value.map((option) => option.value))
  const validDates = new Set(globalDateOptions.value.map((option) => option.value))
  const nextCinemaId = current.cinemaId && !validCinemaIds.has(current.cinemaId) ? '' : current.cinemaId
  const nextDate = current.date && !validDates.has(current.date) ? '' : current.date

  if (nextCinemaId === current.cinemaId && nextDate === current.date) return

  globalWishFilter.value = {
    cinemaId: nextCinemaId,
    date: nextDate,
    weekendOnly: current.weekendOnly,
    joinableOnly: current.joinableOnly,
  }
  const patch = {}
  if (nextCinemaId !== current.cinemaId) {
    patch.cinemaId = nextCinemaId
    patch.cinema = ''
  }
  if (nextDate !== current.date) patch.date = nextDate
  applyGlobalFilterPatchToGroups(patch)
}

watch(currentWeekOnly, () => {
  wishGroupPages.value = new Map()
  pruneInvalidGlobalWishFilter()
})

watch(viewingFilterOptions, (options) => {
  if (!options.some((option) => option.value === activeViewingFilter.value)) activeViewingFilter.value = 'cinema'
})

watch([globalCinemaOptions, globalDateOptions], () => {
  pruneInvalidGlobalWishFilter()
})

watch(
  () => store.scheduleItems.map((item) => `${item.key}:${item.date}:${item.time}:${item.durationMinutes}`).join('|'),
  () => {
    if (hasActiveJoinableOnlyFilter.value) {
      wishGroupPages.value = new Map()
    }
  }
)

const getWishGroupMovieScoreMeta = (movie) => {
  const score = String(movie?.score || '').trim()
  if (!score) return '未获取评分'
  if (score === '无豆瓣评分') return score
  return `评分 ${score}`
}

const getWishGroupMovieMeta = (movie) => {
  if (!movie) return ''
  const metaParts = [
    getMovieYear(movie),
    String(movie.director || '').trim(),
    String(movie.country || '').trim(),
    getWishGroupMovieScoreMeta(movie),
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
  const filter = wishGroupFilters.value.get(movieId)
  return filter ? normalizeWishGroupFilter(filter) : EMPTY_WISH_GROUP_FILTER
}

const updateWishGroupFilter = (movieId, patch) => {
  const current = getWishGroupFilter(movieId)
  const nextFilter = normalizeWishGroupFilter({ ...current, ...patch })
  const next = new Map(wishGroupFilters.value)
  if (isWishGroupFilterEmpty(nextFilter)) {
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

const getWishGroupCinemaOptions = (group) => {
  const options = buildCinemaOptions(group?.items || [])
  const filter = getWishGroupFilter(group.movieId)
  if (!filter.cinemaId || options.some((option) => option.value === filter.cinemaId)) return options
  return [
    { value: filter.cinemaId, label: getCinemaLabelById(filter.cinemaId) },
    ...options,
  ]
}

const getWishGroupDateOptions = (group) => {
  if (!group?.items) return []
  const filter = getWishGroupFilter(group.movieId)
  const options = buildDateOptions(group.items, { weekendOnly: filter.weekendOnly })
  if (!filter.date || options.some((option) => option.value === filter.date)) return options
  return [
    { value: filter.date, label: formatWishDateFilterLabel(filter.date) },
    ...options,
  ]
}

const getFilteredWishItems = (group) => {
  const filter = getWishGroupFilter(group.movieId)
  const targetCinemaId = normalizeFilterValue(filter.cinemaId)
  const cinemaKeyword = String(filter.cinema || '').trim().toLowerCase()
  const targetDate = String(filter.date || '').trim()
  if (
    !targetCinemaId
    && !cinemaKeyword
    && !targetDate
    && !filter.weekendOnly
    && !filter.joinableOnly
  ) {
    return group.items
  }
  return group.items.filter((item) => {
    if (filter.weekendOnly && !isWeekendDate(item.date)) return false
    if (filter.joinableOnly && !isShowEntryJoinable(item)) return false
    if (targetDate && item.date !== targetDate) return false
    if (targetCinemaId && normalizeFilterValue(item.cinemaId) !== targetCinemaId) return false
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
  justify-content: flex-start;
  gap: 12px;
  flex-wrap: wrap;
}

.planning-header-main {
  display: flex;
  align-items: baseline;
  gap: 10px;
  min-width: 0;
  flex-wrap: wrap;
}

.planning-header-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 12px;
  flex: 1;
  min-width: 0;
  flex-wrap: wrap;
}

.planning-header-secondary-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
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

.wish-global-filter {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px 14px;
  margin-top: 12px;
  padding: 10px 12px;
  border: 1px solid #dbe4f0;
  border-radius: 8px;
  background-color: #f8fafc;
}

.wish-global-filter-field {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.wish-global-filter-label {
  color: #475569;
  font-size: 12px;
  font-weight: 700;
  white-space: nowrap;
}

.wish-global-filter-select--cinema {
  width: 260px;
}

.wish-global-filter-select--date {
  width: 180px;
}

.wish-weekend-filter-field {
  min-height: 24px;
}

.wish-weekend-checkbox {
  height: 24px;
  margin-right: 0;
}

.wish-weekend-checkbox :deep(.el-checkbox__label) {
  color: #475569;
  font-size: 12px;
  font-weight: 700;
  padding-left: 6px;
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
    justify-content: flex-end;
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

  .wish-global-filter {
    align-items: stretch;
  }

  .wish-global-filter-field {
    width: 100%;
  }

  .wish-global-filter-select {
    width: 100%;
  }
}
</style>
