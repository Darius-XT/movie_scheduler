<template>
  <div class="movie-scheduler-page">
    <el-card class="page-card">
      <template #header>
        <div class="card-header">
          <span>电影场次查询系统</span>
        </div>
      </template>

      <!-- 信息更新和电影筛选并排 -->
      <div class="top-section">
        <!-- 左侧：信息更新 -->
        <div class="info-update-section">
          <h3 class="section-title">
            <el-icon><Setting /></el-icon>
            <span>信息更新</span>
          </h3>
          <el-form :model="updateForm" label-width="100px" size="default">
            <el-form-item label="选择城市">
              <el-select
                v-model="updateForm.cityId"
                placeholder="请选择城市"
                style="width: 200px"
              >
                <el-option
                  v-for="city in cities"
                  :key="city.id"
                  :label="city.name"
                  :value="city.id"
                />
              </el-select>
            </el-form-item>

            <el-form-item>
              <el-space direction="vertical" :size="8">
                <el-button
                  type="primary"
                  :loading="cinemaLoading"
                  :disabled="!updateForm.cityId"
                  @click="handleUpdateCinema"
                  style="width: 200px"
                >
                  更新影院信息
                </el-button>
                <el-button
                  type="success"
                  :loading="movieLoading"
                  :disabled="!updateForm.cityId"
                  @click="handleUpdateMovie"
                  style="width: 200px"
                >
                  更新电影信息
                </el-button>
              </el-space>
            </el-form-item>
          </el-form>

          <!-- 更新结果 -->
          <div v-if="cinemaResult || movieResult" class="update-results">
            <el-divider style="margin: 12px 0" />

            <div v-if="cinemaResult" class="result-item">
              <div class="result-label">影院更新:</div>
              <div class="result-value">
                成功 {{ cinemaResult.success_count }} / 失败 {{ cinemaResult.failure_count }}
              </div>
            </div>

            <div v-if="movieResult" class="result-item">
              <div class="result-label">电影更新:</div>
              <div class="result-value">
                抓取 {{ movieResult.base_info?.input_stats?.scraped_total || 0 }} /
                去重后 {{ movieResult.base_info?.input_stats?.deduplicated_total || 0 }} /
                新增 {{ movieResult.base_info?.result_stats?.added || 0 }} /
                更新 {{ movieResult.base_info?.result_stats?.updated || 0 }} /
                删除 {{ movieResult.base_info?.result_stats?.removed || 0 }}
              </div>
            </div>
          </div>
        </div>

        <!-- 右侧：电影筛选 -->
        <div class="movie-selector-section">
          <h3 class="section-title">
            <el-icon><Filter /></el-icon>
            <span>电影筛选</span>
          </h3>
          <el-form :model="form" label-width="100px" size="default">
            <el-form-item label="上映状态">
              <div class="threshold-input-wrapper">
                <el-select
                  v-model="form.selectionMode"
                  placeholder="请选择上映状态"
                  style="width: 200px"
                >
                  <el-option
                    v-for="option in selectionModeOptions"
                    :key="option.value"
                    :label="option.label"
                    :value="option.value"
                  />
                </el-select>
              </div>
            </el-form-item>


            <el-form-item>
              <el-space direction="vertical" :size="8">
                <el-button
                  type="primary"
                  :loading="selectLoading"
                  @click="handleSelectMovies"
                  style="width: 200px"
                >
                  筛选喜欢的电影
                </el-button>
                <el-button
                  type="success"
                  :loading="fetchLoading"
                  :disabled="selectedMovies.length === 0"
                  @click="handleFetchShows"
                  style="width: 200px"
                >
                  批量获取所有场次
                </el-button>
              </el-space>
            </el-form-item>

            <!-- 批量获取进度显示 -->
            <div
              v-if="fetchProgress.visible"
              class="fetch-progress"
              role="status"
              aria-live="polite"
              aria-atomic="true"
            >
              <el-divider style="margin: 12px 0" />
              <div class="progress-content">
                <div class="progress-label">批量抓取进度</div>
                <div class="progress-summary">
                  已完成 {{ fetchProgress.completedMovies }} / {{ fetchProgress.totalMovies }} 部电影
                </div>
                <el-progress
                  :percentage="getBatchProgressPercent()"
                  :stroke-width="10"
                  :show-text="false"
                  :status="fetchProgress.completedMovies >= fetchProgress.totalMovies && fetchProgress.totalMovies > 0 ? 'success' : undefined"
                />
                <div class="progress-text">{{ fetchProgress.text }}</div>
              </div>
            </div>
          </el-form>
        </div>
      </div>

      <el-divider />

      <div v-if="selectedMovies.length > 0" class="movies-section">
        <el-card class="planning-card">
          <template #header>
            <div class="planning-header">
              <div class="planning-header-main">
                <span>我的排片</span>
                <span class="planning-header-summary">
                  共 {{ scheduleDateColumns.length }} 天，{{ scheduleItems.length }} 场已定行程
                </span>
              </div>
              <div class="planning-header-actions">
                <el-button
                  text
                  size="small"
                  :disabled="scheduleItems.length === 0"
                  @click="removePastSchedules"
                >
                  移除旧行程
                </el-button>
                <el-tag type="success" size="small">{{ scheduleItems.length }} 个已定行程</el-tag>
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
                      <el-button size="small" @click="moveFromScheduleToWishPool(item.key)">放回想看</el-button>
                      <el-tag
                        :type="item.purchased ? 'success' : 'info'"
                        effect="plain"
                        class="schedule-ticket-tag"
                        @click="toggleSchedulePurchased(item.key)"
                      >
                        <el-icon><Check /></el-icon>
                        <span>{{ item.purchased ? '已购票' : '待购票' }}</span>
                      </el-tag>
                      <el-button size="small" type="danger" plain @click="removeFromSchedule(item.key)">移除</el-button>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
          <el-empty v-else description="还没有安排好的行程" />
        </el-card>
        <el-card
          class="planning-card wish-planning-card"
          :body-style="groupedWishPool.length === 0 ? { display: 'none' } : undefined"
        >
          <template #header>
            <div class="planning-header">
              <div class="planning-header-main">
                <span>想看</span>
                <span class="planning-header-summary">{{ wishPool.length }} 个想看场次</span>
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
                  <el-button text size="small" @click="removeWishMovieGroup(group.movieId)">
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
                    <el-button size="small" type="success" @click="addToSchedule(item)">加入行程</el-button>
                    <el-button size="small" @click="removeFromWishPool(item.key)">移除</el-button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </el-card>

        <div class="section-header">
          <h3>已筛选电影（{{ filteredSelectedMovies.length }} / {{ selectedMovies.length }} 部）</h3>
          <el-input
            v-model="movieSearchKeyword"
            class="movie-search-input"
            clearable
            placeholder="搜索电影名、导演、主演、类型、国家、语言"
          />
        </div>

        <div class="movie-list">
          <section
            v-for="section in movieDisplaySections"
            :key="section.key"
            class="movie-category-section"
          >
            <div class="movie-category-header">
              <h4 class="movie-category-title">{{ section.title }}</h4>
              <el-tag size="small" type="info">{{ section.movies.length }} 部</el-tag>
            </div>

            <el-card
              v-for="(movie, index) in section.movies"
              :key="movie.id"
              class="movie-card"
            >
            <div class="movie-header">
              <div class="movie-basic-info">
                <div class="movie-title-row">
                  <span class="movie-index">{{ section.startIndex + index + 1 }}.</span>
                  <span class="movie-title">{{ movie.title }}</span>
                  <el-tag v-if="movie.score" type="warning" size="small" class="movie-score">
                    {{ movie.score }}
                  </el-tag>
                </div>
                <div class="movie-meta">
                  <span v-if="movie.release_date" class="meta-item meta-item--primary">
                    {{ movie.release_date }}
                  </span>
                  <span v-if="movie.director" class="meta-item meta-item--primary">
                    导演 {{ movie.director }}
                  </span>
                  <span v-if="getMovieRegion(movie)" class="meta-item meta-item--primary">
                    {{ getMovieRegion(movie) }}
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
                <el-button
                  size="small"
                  @click="toggleDescription(movie.id)"
                >
                  {{ expandedDescriptions.has(movie.id) ? '收起' : '展开' }}简介
                </el-button>
                <el-button
                  v-if="!hasValidMovieShows(movie.id)"
                  :type="movie.is_showing === false ? 'info' : 'primary'"
                  size="small"
                  :loading="fetchingMovieIds.has(movie.id)"
                  :disabled="movie.is_showing === false"
                  @click="handleFetchSingleShow(movie)"
                >
                  {{ movie.is_showing === false ? '暂未上映' : '获取场次信息' }}
                </el-button>
                <el-button
                  v-else
                  type="success"
                  size="small"
                  @click="toggleShows(movie.id)"
                >
                  {{ expandedShows.has(movie.id) ? '收起' : '展开' }}场次信息
                </el-button>
              </div>
            </div>

            <!-- 单个电影获取进度显示 -->
            <el-collapse-transition>
              <div
                v-if="movieProgress.has(movie.id)"
                class="single-movie-progress"
                role="status"
                aria-live="polite"
                aria-atomic="true"
              >
                <el-divider style="margin: 12px 0" />
                <div class="progress-content">
                  <div class="progress-label">当前电影进度</div>
                  <div class="progress-text">{{ movieProgress.get(movie.id) }}</div>
                </div>
              </div>
            </el-collapse-transition>

            <el-collapse-transition>
              <div v-if="movieFetchDetails.has(movie.id)" class="single-movie-progress">
                <el-divider style="margin: 12px 0" />
                <div
                  class="date-progress-list"
                  role="status"
                  aria-live="polite"
                  :aria-label="`${movie.title} 抓取进度`"
                >
                  <div class="progress-section-title">抓取进度</div>
                  <div
                    v-for="item in getMovieDateProgressEntries(movie.id)"
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

            <el-collapse-transition>
              <div v-if="expandedDescriptions.has(movie.id)" class="movie-description">
                <el-divider style="margin: 12px 0" />
                <div class="description-content">
                  {{ movie.description || '暂无简介' }}
                </div>
              </div>
            </el-collapse-transition>

            <el-collapse-transition>
              <div v-if="expandedShows.has(movie.id) && hasValidMovieShows(movie.id)" class="movie-shows">
                <el-divider style="margin: 12px 0" />
                <div class="shows-summary">
                  <el-tag type="info" size="small">
                    {{ getMovieShowsData(movie.id)?.cinemas?.length || 0 }} 个影院
                  </el-tag>
                  <el-tag type="success" size="small" style="margin-left: 8px">
                    {{ getTotalShows(getMovieShowsData(movie.id)) }} 个场次
                  </el-tag>
                  <el-button
                    size="small"
                    plain
                    :disabled="getAvailableMovieShowEntries(movie, getMovieShowsData(movie.id)).length === 0"
                    @click="addAllMovieShowsToWishPool(movie)"
                  >
                    全部想看
                  </el-button>
                  <el-radio-group
                    class="show-view-mode"
                    size="small"
                    :model-value="getMovieShowViewMode(movie.id)"
                    @update:model-value="setMovieShowViewMode(movie.id, $event)"
                  >
                    <el-radio-button label="time">按日期</el-radio-button>
                    <el-radio-button label="cinema">按影院</el-radio-button>
                  </el-radio-group>
                </div>
                <div
                  v-for="group in getMovieShowDisplayGroups(movie, getMovieShowsData(movie.id), getMovieShowViewMode(movie.id))"
                  :key="`${movie.id}-${getMovieShowViewMode(movie.id)}-${group.groupKey}`"
                  class="time-group-item"
                >
                  <div class="time-group-header">
                    <span class="time-group-title">{{ group.groupTitle }}</span>
                    <el-tag size="small" type="info">{{ group.entries.length }} 个场次</el-tag>
                  </div>
                  <div class="time-group-list">
                    <div
                      v-for="(entry, entryIndex) in group.entries"
                      :key="`${group.groupKey}-${entry.cinemaId}-${entry.time}-${entryIndex}`"
                      class="time-group-row"
                    >
                      <div class="time-group-main">
                        <span
                          class="time-group-primary"
                          :class="{ 'time-group-primary--cinema': getMovieShowViewMode(movie.id) === 'cinema' }"
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
                          :disabled="isShowUnavailable(entry)"
                          @click="toggleWishPoolEntry(entry)"
                        >
                          {{ getShowActionLabel(entry) }}
                        </el-button>
                      </div>
                    </div>
                  </div>
                </div>
                <div class="shows-collapse-footer">
                  <el-button text type="primary" @click="toggleShows(movie.id)">
                    <el-icon><ArrowUp /></el-icon>
                    收起场次信息
                  </el-button>
                </div>
              </div>
            </el-collapse-transition>
            </el-card>
          </section>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { computed, ref, onMounted, onBeforeUnmount, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Setting, Filter, ArrowUp, Check } from '@element-plus/icons-vue'
import { selectMovies, getCities, updateCinema, updateMovie } from '@/api'

// LocalStorage 键名
const STORAGE_KEY = 'movie_selector_data'
const SHOW_CACHE_TTL_MS = 60 * 60 * 1000
const CACHE_CLEANUP_INTERVAL_MS = 1000

// 信息更新相关状态
const cities = ref([])
const updateForm = ref({
  cityId: null
})
const cinemaLoading = ref(false)
const movieLoading = ref(false)
const cinemaResult = ref(null)
const movieResult = ref(null)
const lastAddedMovieIds = ref(new Set())
const lastUpdatedMovieIds = ref(new Set())

// 电影筛选相关状态
const form = ref({
  selectionMode: 'all'
})

const selectionModeOptions = [
  { label: '正在上映', value: 'showing' },
  { label: '即将上映', value: 'upcoming' },
  { label: '全部', value: 'all' }
]

const selectLoading = ref(false)
const fetchLoading = ref(false)
const selectedMovies = ref([])
const movieSearchKeyword = ref('')
const fetchingMovieIds = ref(new Set()) // 跟踪正在获取场次的电影ID
const movieShowsMap = ref(new Map()) // 存储每部电影的场次信息 Map<movieId, showsData>
const movieFetchDetails = ref(new Map()) // 抓取中的日期进度 Map<movieId, { dates: Record<string, {...}> }>
const expandedDescriptions = ref(new Set()) // 展开简介的电影ID集合
const expandedShows = ref(new Set()) // 展开场次的电影ID集合
const showViewModeMap = ref(new Map()) // 每部电影的场次展示方式 Map<movieId, 'cinema' | 'time'>
const wishPool = ref([]) // 想看的候选场次
const scheduleItems = ref([]) // 已确认的排片
const collapsedWishMovieIds = ref(new Set()) // 想看区域中被收起的电影分组

// 单个电影获取进度显示 Map<movieId, progressText>
const movieProgress = ref(new Map())
const currentTime = ref(Date.now())
let cacheCleanupTimer = null

// 批量获取进度显示
const fetchProgress = ref({
  visible: false,
  text: '',
  totalMovies: 0,
  completedMovies: 0
})

// 从 localStorage 恢复数据
const loadFromStorage = () => {
  try {
    const savedData = localStorage.getItem(STORAGE_KEY)
    if (savedData) {
      const data = JSON.parse(savedData)
      if (data.selectionMode) {
        form.value.selectionMode = data.selectionMode
      }
      if (data.selectedMovies) {
        selectedMovies.value = data.selectedMovies
      }
      if (data.movieShowsMap) {
        // 将对象转换回 Map
        movieShowsMap.value = new Map(Object.entries(data.movieShowsMap).map(([k, v]) => [Number(k), v]))
      }
      if (data.expandedDescriptions) {
        expandedDescriptions.value = new Set(data.expandedDescriptions)
      }
      if (data.expandedShows) {
        expandedShows.value = new Set(data.expandedShows)
      }
      if (data.collapsedWishMovieIds) {
        collapsedWishMovieIds.value = new Set(data.collapsedWishMovieIds)
      }
      if (data.wishPool) {
        wishPool.value = data.wishPool
      }
      if (data.scheduleItems) {
        scheduleItems.value = data.scheduleItems
      }
      pruneExpiredMovieShows()
    }
  } catch (error) {
    console.error('恢复数据失败:', error)
  }
}

// 保存数据到 localStorage
const saveToStorage = () => {
  try {
    const data = {
      selectionMode: form.value.selectionMode,
      selectedMovies: selectedMovies.value,
      // 将 Map 转换为对象以便 JSON 序列化
      movieShowsMap: Object.fromEntries(movieShowsMap.value.entries()),
      expandedDescriptions: Array.from(expandedDescriptions.value),
      expandedShows: Array.from(expandedShows.value),
      collapsedWishMovieIds: Array.from(collapsedWishMovieIds.value),
      wishPool: wishPool.value,
      scheduleItems: scheduleItems.value
    }
    localStorage.setItem(STORAGE_KEY, JSON.stringify(data))
  } catch (error) {
    console.error('保存数据失败:', error)
  }
}

// 组件挂载时恢复数据并加载城市列表
onMounted(async () => {
  loadFromStorage()
  startCacheCleanupTimer()

  // 加载城市列表
  try {
    const response = await getCities()
    cities.value = response.data.cities
    // 默认选中上海（城市 ID 为 10）
    const shanghaiCity = cities.value.find(city => city.id === 10)
    if (shanghaiCity) {
      updateForm.value.cityId = shanghaiCity.id
    } else if (cities.value.length > 0) {
      updateForm.value.cityId = cities.value[0].id
    }
  } catch (error) {
    console.error('获取城市列表失败:', error)
  }
})

onBeforeUnmount(() => {
  stopCacheCleanupTimer()
})

// 监听数据变化并保存
watch([selectedMovies, movieShowsMap, expandedDescriptions, expandedShows, collapsedWishMovieIds, wishPool, scheduleItems, () => form.value.selectionMode], () => {
  saveToStorage()
}, { deep: true })

// ===== 信息更新功能 =====
const handleUpdateCinema = async () => {
  cinemaLoading.value = true
  cinemaResult.value = null
  try {
    const response = await updateCinema(updateForm.value.cityId)
    if (response.data.success) {
      cinemaResult.value = response.data.data
      ElMessage.success('影院信息更新成功')
    } else {
      ElMessage.error('更新失败: ' + response.data.error)
    }
  } catch (error) {
    ElMessage.error('更新失败: ' + error.message)
  } finally {
    cinemaLoading.value = false
  }
}

const handleUpdateMovie = async () => {
  movieLoading.value = true
  movieResult.value = null
  lastAddedMovieIds.value = new Set()
  lastUpdatedMovieIds.value = new Set()
  try {
    const response = await updateMovie(updateForm.value.cityId, false)
    if (response.data.success) {
      movieResult.value = response.data.data
      lastAddedMovieIds.value = new Set(response.data.data.base_info?.result_stats?.added_movie_ids || [])
      lastUpdatedMovieIds.value = new Set(response.data.data.base_info?.result_stats?.updated_movie_ids || [])
      ElMessage.success('电影信息更新成功')
    } else {
      ElMessage.error('更新失败: ' + response.data.error)
    }
  } catch (error) {
    ElMessage.error('更新失败: ' + error.message)
  } finally {
    movieLoading.value = false
  }
}

// ===== 电影筛选功能 =====

const handleSelectMovies = async () => {
  selectLoading.value = true
  selectedMovies.value = []
  movieShowsMap.value.clear()
  movieFetchDetails.value.clear()
  movieProgress.value.clear()
  expandedDescriptions.value.clear()
  expandedShows.value.clear()
  showViewModeMap.value.clear()
  try {
    const response = await selectMovies(form.value.selectionMode)
    if (response.data.success) {
      selectedMovies.value = response.data.data.movies
      ElMessage.success(`成功筛选出 ${response.data.data.movies.length} 部电影`)
    } else {
      ElMessage.error('筛选失败: ' + response.data.error)
    }
  } catch (error) {
    ElMessage.error('筛选失败: ' + error.message)
  } finally {
    selectLoading.value = false
  }
}

const ensureMovieFetchDetails = (movieId) => {
  if (!movieFetchDetails.value.has(movieId)) {
    movieFetchDetails.value.set(movieId, { dates: {} })
  }
  return movieFetchDetails.value.get(movieId)
}

const initializeMovieDates = (movieId, dates) => {
  const details = ensureMovieFetchDetails(movieId)
  const nextDates = {}
  dates.forEach((date) => {
    const current = details.dates[date]
    nextDates[date] = {
      done: current?.done ?? 0,
      total: current?.total ?? 0,
      active: current?.active ?? false
    }
  })
  details.dates = nextDates
}

const updateMovieDateProgress = (movieId, targetDate, patch) => {
  const details = ensureMovieFetchDetails(movieId)
  const dates = { ...details.dates }

  Object.keys(dates).forEach((date) => {
    dates[date] = {
      ...dates[date],
      active: false
    }
  })

  const current = dates[targetDate] ?? { done: 0, total: 0, active: false }
  dates[targetDate] = {
    ...current,
    ...patch
  }

  details.dates = dates
}

const clearMovieFetchProgress = (movieIds) => {
  movieIds.forEach((movieId) => {
    movieFetchDetails.value.delete(movieId)
    movieProgress.value.delete(movieId)
  })
}

const getMovieDateProgressEntries = (movieId) => {
  const details = movieFetchDetails.value.get(movieId)
  if (!details) return []
  return Object.entries(details.dates)
    .sort(([leftDate], [rightDate]) => leftDate.localeCompare(rightDate))
    .map(([date, info]) => ({
      date,
      ...info
    }))
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

const isMovieShowCacheExpired = (cachedAt) => {
  if (!cachedAt) return true
  return currentTime.value - cachedAt >= SHOW_CACHE_TTL_MS
}

const removeMovieShowCache = (movieId) => {
  movieShowsMap.value.delete(movieId)
  expandedShows.value.delete(movieId)
  showViewModeMap.value.delete(movieId)
}

const pruneExpiredMovieShows = () => {
  const expiredMovieIds = []

  movieShowsMap.value.forEach((showData, movieId) => {
    if (isMovieShowCacheExpired(showData?.cachedAt)) {
      expiredMovieIds.push(movieId)
    }
  })

  expiredMovieIds.forEach((movieId) => {
    removeMovieShowCache(movieId)
  })
}

const refreshCurrentTime = () => {
  currentTime.value = Date.now()
  pruneExpiredMovieShows()
}

const startCacheCleanupTimer = () => {
  stopCacheCleanupTimer()
  cacheCleanupTimer = window.setInterval(() => {
    refreshCurrentTime()
  }, CACHE_CLEANUP_INTERVAL_MS)
}

const stopCacheCleanupTimer = () => {
  if (cacheCleanupTimer != null) {
    window.clearInterval(cacheCleanupTimer)
    cacheCleanupTimer = null
  }
}

const hasValidMovieShows = (movieId) => {
  const showData = movieShowsMap.value.get(movieId)
  return Boolean(showData && !isMovieShowCacheExpired(showData.cachedAt))
}

const getMovieShowsData = (movieId) => {
  if (!hasValidMovieShows(movieId)) return null
  return movieShowsMap.value.get(movieId)
}

const createCachedShowItem = (showItem) => ({
  ...showItem,
  cachedAt: Date.now()
})

const createShowEntry = (movie, cinema, show) => ({
  key: `${movie.id}-${cinema.cinema_id}-${show.date}-${show.time}`,
  movieId: movie.id,
  movieTitle: movie.title,
  date: show.date,
  time: show.time,
  cinemaId: cinema.cinema_id,
  cinemaName: cinema.cinema_name,
  price: show.price,
  durationMinutes: parseMovieDurationMinutes(movie?.duration)
})

const formatShowPrice = (price) => {
  const normalized = String(price ?? '').trim()
  if (!normalized || normalized === '0' || normalized === '0.0' || normalized === '0.00') {
    return '暂无价格'
  }

  return `￥${normalized}`
}

const parseMovieDurationMinutes = (durationText) => {
  const normalized = String(durationText ?? '').trim()
  const match = normalized.match(/(\d+)/)
  return match ? Number(match[1]) : null
}

const getShowEntryDurationMinutes = (showEntry) => {
  if (typeof showEntry?.durationMinutes === 'number' && !Number.isNaN(showEntry.durationMinutes)) {
    return showEntry.durationMinutes
  }

  const movie = selectedMovies.value.find((item) => item.id === showEntry?.movieId)
  return parseMovieDurationMinutes(movie?.duration)
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

const getMovieShowEntries = (movie, movieShowData) => {
  if (!movieShowData?.cinemas) return []

  return movieShowData.cinemas.flatMap((cinema) =>
    (cinema.shows || []).map((show) => createShowEntry(movie, cinema, show))
  )
}

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
  const diffWeeks = Math.floor((targetWeekStart.getTime() - currentWeekStart.getTime()) / (7 * 24 * 60 * 60 * 1000))

  let suffix = ''
  if (diffWeeks <= 0) {
    suffix = `本${WEEKDAY_LABELS[targetDate.getDay()]}`
  } else if (diffWeeks === 1) {
    suffix = `下${WEEKDAY_LABELS[targetDate.getDay()]}`
  } else if (diffWeeks === 2) {
    suffix = `下下${WEEKDAY_LABELS[targetDate.getDay()]}`
  } else {
    suffix = '三周后'
  }

  return `${dateText}（${suffix}）`
}

const isInWishPool = (showEntry) => {
  return wishPool.value.some((item) => item.key === showEntry.key)
}

const isInSchedule = (showEntry) => {
  return scheduleItems.value.some((item) => item.key === showEntry.key)
}

const isShowUnavailable = (showEntry) => {
  return isInSchedule(showEntry)
}

const getShowActionLabel = (showEntry) => {
  if (isInSchedule(showEntry)) return '已在行程'
  if (isInWishPool(showEntry)) return '移出想看'
  return '想看'
}

const addToWishPool = (showEntry) => {
  if (isInWishPool(showEntry)) return
  wishPool.value.push(showEntry)
  collapsedWishMovieIds.value.delete(showEntry.movieId)
  ElMessage.success(`已将《${showEntry.movieTitle}》加入想看`)
}

const toggleWishPoolEntry = (showEntry) => {
  if (isInSchedule(showEntry)) return

  if (isInWishPool(showEntry)) {
    removeFromWishPool(showEntry.key)
    return
  }

  addToWishPool(showEntry)
}

const removeFromWishPool = (showKey) => {
  const targetItem = wishPool.value.find((item) => item.key === showKey)
  wishPool.value = wishPool.value.filter((item) => item.key !== showKey)

  if (targetItem && !wishPool.value.some((item) => item.movieId === targetItem.movieId)) {
    collapsedWishMovieIds.value.delete(targetItem.movieId)
  }
}

const removeWishMovieGroup = (movieId) => {
  wishPool.value = wishPool.value.filter((item) => item.movieId !== movieId)
  collapsedWishMovieIds.value.delete(movieId)
}

const isWishGroupCollapsed = (movieId) => {
  return collapsedWishMovieIds.value.has(movieId)
}

const toggleWishGroup = (movieId) => {
  if (collapsedWishMovieIds.value.has(movieId)) {
    collapsedWishMovieIds.value.delete(movieId)
  } else {
    collapsedWishMovieIds.value.add(movieId)
  }
}

const expandAllWishGroups = () => {
  collapsedWishMovieIds.value.clear()
}

const collapseAllWishGroups = () => {
  collapsedWishMovieIds.value = new Set(groupedWishPool.value.map((group) => group.movieId))
}

const getAvailableMovieShowEntries = (movie, movieShowData) => {
  return getMovieShowEntries(movie, movieShowData).filter((entry) => !isShowUnavailable(entry))
}

const addAllMovieShowsToWishPool = (movie) => {
  const movieShowData = getMovieShowsData(movie.id)
  const entries = getAvailableMovieShowEntries(movie, movieShowData)

  if (entries.length === 0) {
    ElMessage.warning(`《${movie.title}》的场次已全部加入想看或行程`)
    return
  }

  wishPool.value.push(...entries)
  collapsedWishMovieIds.value.delete(movie.id)
  ElMessage.success(`已将《${movie.title}》的 ${entries.length} 个场次加入想看`)
}

const getScheduleConflict = (showEntry) => {
  const targetStart = parseShowTimeToMinutes(showEntry.time)
  const targetDuration = getShowEntryDurationMinutes(showEntry)

  return scheduleItems.value.find((item) => {
    if (item.date !== showEntry.date) return false

    const itemStart = parseShowTimeToMinutes(item.time)
    const itemDuration = getShowEntryDurationMinutes(item)

    if (
      targetStart == null ||
      itemStart == null ||
      targetDuration == null ||
      itemDuration == null
    ) {
      return item.time === showEntry.time
    }

    const targetEnd = targetStart + targetDuration
    const itemEnd = itemStart + itemDuration

    return targetStart < itemEnd && itemStart < targetEnd
  }) || null
}

const addToSchedule = (showEntry) => {
  if (isInSchedule(showEntry)) return

  const conflictItem = getScheduleConflict(showEntry)
  if (conflictItem) {
    ElMessage.warning(
      `加入行程失败：${showEntry.date} ${showEntry.time} 与《${conflictItem.movieTitle}》冲突`
    )
    return
  }

  scheduleItems.value.push({
    ...showEntry,
    purchased: false
  })
  removeFromWishPool(showEntry.key)
  ElMessage.success(`已将《${showEntry.movieTitle}》加入行程`)
}

const moveFromScheduleToWishPool = (showKey) => {
  const targetItem = scheduleItems.value.find((item) => item.key === showKey)
  scheduleItems.value = scheduleItems.value.filter((item) => item.key !== showKey)

  if (targetItem && !wishPool.value.some((item) => item.key === showKey)) {
    const { purchased, ...wishEntry } = targetItem
    wishPool.value.push(wishEntry)
  }
}

const removeFromSchedule = (showKey) => {
  scheduleItems.value = scheduleItems.value.filter((item) => item.key !== showKey)
}

const toggleSchedulePurchased = (showKey) => {
  scheduleItems.value = scheduleItems.value.map((item) => {
    if (item.key !== showKey) return item
    return {
      ...item,
      purchased: !item.purchased
    }
  })
}

const getTodayDateString = () => {
  const today = new Date()
  const year = today.getFullYear()
  const month = String(today.getMonth() + 1).padStart(2, '0')
  const day = String(today.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

const removePastSchedules = () => {
  const today = getTodayDateString()
  const originalCount = scheduleItems.value.length
  scheduleItems.value = scheduleItems.value.filter((item) => String(item.date || '') >= today)

  const removedCount = originalCount - scheduleItems.value.length
  if (removedCount > 0) {
    ElMessage.success(`已移除 ${removedCount} 条旧行程`)
  } else {
    ElMessage.info('没有可移除的旧行程')
  }
}

const groupedWishPool = computed(() => {
  const groups = new Map()

  wishPool.value.forEach((item) => {
    if (!groups.has(item.movieId)) {
      groups.set(item.movieId, {
        movieId: item.movieId,
        movieTitle: item.movieTitle,
        items: []
      })
    }

    groups.get(item.movieId).items.push(item)
  })

  return Array.from(groups.values())
    .sort((leftGroup, rightGroup) => String(leftGroup.movieTitle || '').localeCompare(String(rightGroup.movieTitle || '')))
    .map((group) => ({
      ...group,
      items: [...group.items].sort((leftItem, rightItem) => {
        const leftKey = `${leftItem.date} ${leftItem.time}`
        const rightKey = `${rightItem.date} ${rightItem.time}`
        return leftKey.localeCompare(rightKey)
      })
    }))
})

const filteredSelectedMovies = computed(() => {
  const keyword = String(movieSearchKeyword.value || '').trim().toLowerCase()
  if (!keyword) return selectedMovies.value

  return selectedMovies.value.filter((movie) => {
    const haystacks = [
      movie.title,
      movie.director,
      movie.actors,
      movie.genres,
      movie.country,
      movie.language
    ]
      .map((item) => String(item || '').toLowerCase())
      .filter(Boolean)

    return haystacks.some((text) => text.includes(keyword))
  })
})

const movieDisplaySections = computed(() => {
  const addedMovies = []
  const existingMovies = []

  filteredSelectedMovies.value.forEach((movie) => {
    if (lastAddedMovieIds.value.has(movie.id)) {
      addedMovies.push(movie)
      return
    }

    if (lastUpdatedMovieIds.value.has(movie.id) || !lastAddedMovieIds.value.size) {
      existingMovies.push(movie)
      return
    }

    existingMovies.push(movie)
  })

  const sections = []
  let offset = 0

  if (addedMovies.length > 0) {
    sections.push({
      key: 'added',
      title: '新增电影',
      movies: addedMovies,
      startIndex: offset
    })
    offset += addedMovies.length
  }

  sections.push({
    key: 'existing',
    title: '在库电影',
    movies: existingMovies,
    startIndex: offset
  })

  return sections.filter((section) => section.movies.length > 0)
})

const scheduleDateColumns = computed(() => {
  const groups = new Map()

  scheduleItems.value.forEach((item) => {
    if (!groups.has(item.date)) {
      groups.set(item.date, [])
    }
    groups.get(item.date).push(item)
  })

  return Array.from(groups.entries())
    .sort(([leftDate], [rightDate]) => leftDate.localeCompare(rightDate))
    .map(([date, items]) => ({
      date,
      items: [...items].sort((leftItem, rightItem) =>
        String(leftItem.time || '').localeCompare(String(rightItem.time || ''))
      )
    }))
})

const getMovieShowViewMode = (movieId) => {
  return showViewModeMap.value.get(movieId) || 'time'
}

const setMovieShowViewMode = (movieId, mode) => {
  if (!hasValidMovieShows(movieId)) {
    showViewModeMap.value.delete(movieId)
    return
  }

  if (mode !== 'cinema' && mode !== 'time') return
  showViewModeMap.value.set(movieId, mode)
}

const getBatchProgressPercent = () => {
  if (!fetchProgress.value.totalMovies) return 0
  return Math.min(
    100,
    Math.round((fetchProgress.value.completedMovies / fetchProgress.value.totalMovies) * 100)
  )
}

const COMPLETE_TRANSITION_MS = 1200

const waitForProgressTransition = async () => {
  await new Promise((resolve) => {
    window.setTimeout(resolve, COMPLETE_TRANSITION_MS)
  })
}

const handleFetchShows = async () => {
  // 过滤出需要获取场次的电影（未上映的和已获取过的都跳过）
  const moviesToFetch = selectedMovies.value.filter(
    m => m.id != null && m.is_showing !== false && !hasValidMovieShows(m.id)
  )

  if (moviesToFetch.length === 0) {
    ElMessage.warning('没有需要获取场次的电影')
    return
  }

  fetchLoading.value = true
  fetchProgress.value.visible = true
  fetchProgress.value.totalMovies = moviesToFetch.length
  fetchProgress.value.completedMovies = 0
  fetchProgress.value.text = `开始批量获取 ${moviesToFetch.length} 部电影的场次...`
  moviesToFetch.forEach((movie) => {
    movieFetchDetails.value.delete(movie.id)
  })

  const movieIds = moviesToFetch.map(m => m.id).join(',')
  const cityQuery = updateForm.value.cityId ? `&city_id=${updateForm.value.cityId}` : ''
  const url = `/api/v1/shows/fetch-stream?movie_ids=${movieIds}${cityQuery}`

  try {
    console.log('开始 SSE 连接:', url)
    const response = await fetch(url, {
      headers: {
        'Accept': 'text/event-stream',
      },
    })

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }

    const reader = response.body.getReader()
    const decoder = new TextDecoder()

    let buffer = ''
    while (true) {
      const { done, value } = await reader.read()
      if (done) {
        console.log('SSE 流结束')
        break
      }

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() // 保留最后一个不完整的行

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = JSON.parse(line.substring(6))
          console.log('收到进度更新:', data)

          // 处理不同类型的进度更新
          if (data.type === 'dates_found') {
            const movie = moviesToFetch.find(m => m.id === data.movie_id)
            initializeMovieDates(data.movie_id, data.dates)
            fetchProgress.value.text = `电影《${movie?.title}》找到 ${data.dates.length} 个排片日期`
          } else if (data.type === 'processing_date') {
            const movie = moviesToFetch.find(m => m.id === data.movie_id)
            updateMovieDateProgress(data.movie_id, data.date, {
              active: true
            })
            fetchProgress.value.text = `电影《${movie?.title}》处理日期 ${data.date_idx}/${data.total_dates}`
          } else if (data.type === 'processing_cinema') {
            const movie = moviesToFetch.find(m => m.id === data.movie_id)
            updateMovieDateProgress(data.movie_id, data.date, {
              done: data.cinema_idx,
              total: data.total_cinemas,
              active: true
            })
            fetchProgress.value.text = `电影《${movie?.title}》日期 ${data.date} - 影院 ${data.cinema_idx}/${data.total_cinemas}`
          } else if (data.type === 'movie_complete') {
            const movie = moviesToFetch.find(m => m.id === data.movie_id)
            fetchProgress.value.completedMovies = Math.min(
              fetchProgress.value.totalMovies,
              fetchProgress.value.completedMovies + 1
            )
            fetchProgress.value.text = data.has_shows
              ? `电影《${movie?.title}》场次抓取完成`
              : `电影《${movie?.title}》抓取完成，暂无场次`
          } else if (data.type === 'complete') {
            const shows = data.data
            const successCount = shows.filter(s => s.cinemas && s.cinemas.length > 0).length
            const noShowsCount = shows.length - successCount

            fetchProgress.value.completedMovies = fetchProgress.value.totalMovies
            fetchProgress.value.text = '批量获取完成'
            await waitForProgressTransition()
            fetchProgress.value.visible = false
            fetchProgress.value.totalMovies = 0
            fetchProgress.value.completedMovies = 0
            clearMovieFetchProgress(moviesToFetch.map(movie => movie.id))
            shows.forEach(showItem => {
              movieShowsMap.value.set(showItem.movie_id, createCachedShowItem(showItem))
            })

            if (successCount > 0 && noShowsCount === 0) {
              ElMessage.success(`批量获取完成：成功获取 ${successCount} 部电影的场次信息`)
            } else if (successCount > 0 && noShowsCount > 0) {
              ElMessage.warning(`批量获取完成：${successCount} 部有场次，${noShowsCount} 部暂无场次`)
            } else {
              ElMessage.warning('批量获取完成：所有电影暂无场次信息')
            }
          } else if (data.type === 'error') {
            ElMessage.error('批量获取失败: ' + data.error)
            fetchProgress.value.visible = false
            fetchProgress.value.totalMovies = 0
            fetchProgress.value.completedMovies = 0
            clearMovieFetchProgress(moviesToFetch.map(movie => movie.id))
          }
        }
      }
    }
  } catch (error) {
    console.error('SSE 连接错误:', error)
    ElMessage.error('批量获取失败: ' + error.message)
    fetchProgress.value.visible = false
    fetchProgress.value.totalMovies = 0
    fetchProgress.value.completedMovies = 0
    clearMovieFetchProgress(moviesToFetch.map(movie => movie.id))
  } finally {
    fetchLoading.value = false
  }
}

const handleFetchSingleShow = async (movie) => {
  if (!movie.id) {
    ElMessage.warning('电影ID无效')
    return
  }

  fetchingMovieIds.value.add(movie.id)
  movieProgress.value.set(movie.id, '开始获取场次信息...')
  movieFetchDetails.value.delete(movie.id)

  const cityQuery = updateForm.value.cityId ? `&city_id=${updateForm.value.cityId}` : ''
  const url = `/api/v1/shows/fetch-stream?movie_ids=${movie.id}${cityQuery}`

  try {
    console.log('开始单个电影 SSE 连接:', url)
    const response = await fetch(url, {
      headers: {
        'Accept': 'text/event-stream',
      },
    })

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }

    const reader = response.body.getReader()
    const decoder = new TextDecoder()

    let buffer = ''
    while (true) {
      const { done, value } = await reader.read()
      if (done) {
        console.log('单个电影 SSE 流结束')
        break
      }

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop()

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = JSON.parse(line.substring(6))
          console.log('收到单个电影进度更新:', data)

          // 处理不同类型的进度更新
          if (data.type === 'dates_found') {
            initializeMovieDates(movie.id, data.dates)
            movieProgress.value.set(movie.id, `找到 ${data.dates.length} 个排片日期`)
          } else if (data.type === 'processing_date') {
            updateMovieDateProgress(movie.id, data.date, {
              active: true
            })
            movieProgress.value.set(movie.id, `处理日期 ${data.date_idx}/${data.total_dates}: ${data.date}`)
          } else if (data.type === 'processing_cinema') {
            updateMovieDateProgress(movie.id, data.date, {
              done: data.cinema_idx,
              total: data.total_cinemas,
              active: true
            })
            movieProgress.value.set(movie.id, `日期 ${data.date} - 影院 ${data.cinema_idx}/${data.total_cinemas}`)
          } else if (data.type === 'complete') {
            const shows = data.data
            const showItem = shows[0]
            const totalShows = showItem ? getTotalShows(showItem) : 0

            movieProgress.value.set(movie.id, showItem ? `抓取完成，共 ${totalShows} 个场次` : '抓取完成，暂无场次')
            await waitForProgressTransition()
            clearMovieFetchProgress([movie.id])

            if (shows.length > 0) {
              movieShowsMap.value.set(movie.id, createCachedShowItem(showItem))
              expandedShows.value.add(movie.id)
              ElMessage.success(`成功获取《${movie.title}》的场次信息（共 ${totalShows} 个场次）`)
            } else {
              ElMessage.warning(`电影《${movie.title}》暂无场次信息`)
            }
          } else if (data.type === 'error') {
            ElMessage.error('获取失败: ' + data.error)
            clearMovieFetchProgress([movie.id])
          }
        }
      }
    }
  } catch (error) {
    console.error('单个电影 SSE 连接错误:', error)
    ElMessage.error('获取失败: ' + error.message)
    clearMovieFetchProgress([movie.id])
  } finally {
    fetchingMovieIds.value.delete(movie.id)
  }
}

const toggleDescription = (movieId) => {
  if (expandedDescriptions.value.has(movieId)) {
    expandedDescriptions.value.delete(movieId)
  } else {
    expandedDescriptions.value.add(movieId)
  }
}

const toggleShows = (movieId) => {
  if (expandedShows.value.has(movieId)) {
    expandedShows.value.delete(movieId)
  } else {
    expandedShows.value.add(movieId)
  }
}

const getTotalShows = (movieShowData) => {
  if (!movieShowData || !movieShowData.cinemas) return 0
  return movieShowData.cinemas.reduce((total, cinema) => total + (cinema.shows?.length || 0), 0)
}

const getMovieRegion = (movie) => {
  return String(movie?.country || '').trim()
}

const getMovieYear = (movie) => {
  const releaseDate = String(movie?.release_date || '').trim()
  const match = releaseDate.match(/^(\d{4})/)
  return match ? match[1] : ''
}

const getWishGroupMovieMeta = (movieId) => {
  const movie = selectedMovies.value.find((item) => item.id === movieId)
  if (!movie) return ''

  const metaParts = [
    getMovieYear(movie),
    String(movie.director || '').trim(),
    getMovieRegion(movie)
  ].filter(Boolean)

  return metaParts.join(' · ')
}

const getMovieShowDisplayGroups = (movie, movieShowData, mode = 'time') => {
  if (!movieShowData?.cinemas) return []

  const groups = new Map()

  movieShowData.cinemas.forEach((cinema) => {
    ;(cinema.shows || []).forEach((show) => {
      const date = show.date || '未标注日期'
      const groupKey = mode === 'cinema'
        ? `${cinema.cinema_id}`
        : date

      if (!groups.has(groupKey)) {
        groups.set(groupKey, {
          groupKey,
          groupTitle: mode === 'cinema'
            ? cinema.cinema_name
            : formatDateWithRelativeWeek(date),
          sortKey: mode === 'cinema'
            ? cinema.cinema_name
            : date,
          entries: []
        })
      }

      groups.get(groupKey).entries.push({
        key: `${movie.id}-${cinema.cinema_id}-${show.date}-${show.time}`,
        movieId: movie.id,
        movieTitle: movie.title,
        cinemaId: cinema.cinema_id,
        cinemaName: cinema.cinema_name,
        date,
        time: show.time || '未标注时间',
        price: show.price
      })
    })
  })

  return Array.from(groups.values())
    .sort((leftGroup, rightGroup) => String(leftGroup.sortKey).localeCompare(String(rightGroup.sortKey)))
    .map((group) => ({
      ...group,
      entries: [...group.entries]
        .sort((leftEntry, rightEntry) => {
          if (mode === 'cinema') {
            const dateCompare = String(leftEntry.date || '').localeCompare(String(rightEntry.date || ''))
            if (dateCompare !== 0) return dateCompare
          }

          if (mode === 'time') {
            const cinemaCompare = String(leftEntry.cinemaName || '').localeCompare(String(rightEntry.cinemaName || ''))
            if (cinemaCompare !== 0) return cinemaCompare
          }

          return String(leftEntry.time || '').localeCompare(String(rightEntry.time || ''))
        })
        .map((entry) => ({
          ...entry,
          primaryText: mode === 'cinema' ? formatDateWithRelativeWeek(entry.date) : entry.cinemaName,
          secondaryText: mode === 'cinema' ? entry.time : entry.time
        }))
    }))
}
</script>

<style scoped>
.movie-scheduler-page {
  max-width: 1200px;
  margin: 0 auto;
}

.page-card {
  margin-bottom: 20px;
}

.card-header {
  font-size: 18px;
  font-weight: bold;
}

/* 顶部左右布局 */
.top-section {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 60px;
  margin-bottom: 20px;
  align-items: start;
}

.info-update-section,
.movie-selector-section {
  min-width: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.info-update-section .el-form,
.movie-selector-section .el-form {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
}

.section-title {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0 0 16px 0;
  font-size: 16px;
  font-weight: 500;
  color: #333;
}

/* 年份阈值输入框包装 */
.threshold-input-wrapper {
  display: flex;
  align-items: center;
  gap: 8px;
}

.movie-selector-section :deep(.el-form-item) {
  width: 100%;
  justify-content: flex-start;
}

.movie-selector-section :deep(.el-form-item__content) {
  justify-content: flex-start;
}

.movie-selector-section :deep(.el-space) {
  align-items: flex-start;
}

/* 更新结果样式 */
.update-results {
  margin-top: 12px;
  width: 100%;
}

/* 批量获取进度显示 */
.fetch-progress {
  margin-top: 12px;
  width: 100%;
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

.progress-summary {
  margin-bottom: 8px;
  font-size: 13px;
  color: #475569;
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

.result-item {
  display: flex;
  align-items: center;
  margin-bottom: 8px;
  font-size: 13px;
}

.result-item:last-child {
  margin-bottom: 0;
}

.result-label {
  font-weight: 500;
  color: #606266;
  margin-right: 8px;
  min-width: 80px;
}

.result-value {
  color: #409eff;
}

.movies-section {
  margin-top: 20px;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  margin-bottom: 15px;
}

.section-header h3 {
  margin: 0;
  color: #333;
}

.movie-search-input {
  width: 305px;
  max-width: 100%;
}

.movie-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.movie-category-section {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.movie-category-section + .movie-category-section {
  margin-top: 8px;
}

.movie-category-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.movie-category-title {
  margin: 0;
  color: #173b7a;
  font-size: 20px;
  font-weight: 700;
}

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

.show-view-mode {
  margin-left: auto;
}

.time-group-item {
  margin-bottom: 16px;
  padding: 12px;
  background-color: #fbfcff;
  border-radius: 6px;
  border: 1px solid #e6ecf5;
}

.time-group-item:last-child {
  margin-bottom: 0;
}

.time-group-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 10px;
}

.time-group-title {
  font-size: 14px;
  font-weight: 600;
  color: #303133;
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

.shows-collapse-footer {
  display: flex;
  justify-content: center;
  margin-top: 16px;
  padding-top: 4px;
}

.shows-collapse-footer .el-button {
  gap: 6px;
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

.wish-pool-title {
  margin-bottom: 6px;
  color: #0f172a;
  font-size: 14px;
  font-weight: 600;
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
  .top-section {
    grid-template-columns: 1fr;
    gap: 24px;
  }

  .info-update-section,
  .movie-selector-section {
    align-items: stretch;
  }

  .info-update-section .el-form,
  .movie-selector-section .el-form {
    width: 100%;
    max-width: 100%;
  }

  .movie-header {
    flex-direction: column;
    gap: 12px;
  }

  .movie-actions {
    width: 100%;
    flex-wrap: wrap;
  }

  .section-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .movie-search-input {
    width: 100%;
  }

  .show-view-mode {
    margin-left: 0;
    width: 100%;
  }

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
  .movie-scheduler-page {
    padding: 0 12px;
  }

  .threshold-input-wrapper {
    width: 100%;
    flex-wrap: wrap;
    align-items: flex-start;
  }

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

  .time-group-header,
  .time-group-row {
    flex-direction: column;
    align-items: flex-start;
  }

  .time-group-main {
    flex-direction: column;
    align-items: flex-start;
    gap: 4px;
  }

  .wish-pool-group-header,
  .time-group-actions,
  .wish-pool-item,
  .wish-pool-actions {
    flex-direction: column;
    align-items: flex-start;
  }

  .schedule-item-actions {
    width: 100%;
  }

  .wish-pool-group-actions {
    width: 100%;
    justify-content: flex-start;
    flex-wrap: wrap;
  }

  .schedule-column {
    width: 220px;
    flex-basis: 220px;
  }
}
</style>
