<template>
  <div class="movie-scheduler-page">
    <el-card class="page-card">
      <template #header>
        <div class="card-header">
          <span>电影场次查询系统</span>
        </div>
      </template>

      <!-- 顶部左右布局：信息更新 + 电影筛选 -->
      <div class="top-section">
        <UpdatePanel
          :cities="cities"
          :update-form="updateForm"
          @update:lastAddedMovieIds="lastAddedMovieIds = $event"
          @update:lastUpdatedMovieIds="lastUpdatedMovieIds = $event"
        />
        <MovieFilterPanel
          :update-form="updateForm"
          @movies-selected="handleMoviesSelected"
        />
      </div>

      <el-divider />

      <div v-if="store.selectedMovies.length > 0" class="movies-section">
        <!-- 行程看板 -->
        <ScheduleBoard />

        <!-- 想看池 -->
        <WishPool />

        <!-- 电影列表 -->
        <div class="section-header">
          <h3>已筛选电影（{{ filteredSelectedMovies.length }} / {{ store.selectedMovies.length }} 部）</h3>
          <div class="section-header-controls">
            <el-radio-group v-model="movieSortOrder" size="small">
              <el-radio-button label="newest">最新</el-radio-button>
              <el-radio-button label="name">名称</el-radio-button>
            </el-radio-group>
            <el-input
              v-model="movieSearchKeyword"
              class="movie-search-input"
              clearable
              placeholder="搜索电影名、导演、主演、类型、国家、语言"
            />
          </div>
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

            <MovieCard
              v-for="(movie, index) in section.movies"
              :key="movie.id"
              :movie="movie"
              :index="section.startIndex + index"
              :is-fetching="fetchingMovieIds.has(movie.id)"
              :is-douban-fetching="doubanFetchingIds.has(movie.id)"
              :movie-progress-text="movieProgress.get(movie.id) || ''"
              :movie-fetch-date-entries="getMovieDateProgressEntries(movie.id)"
              :shows-data="getMovieShowsData(movie.id)"
              :has-valid-shows="hasValidMovieShows(movie.id)"
              @fetch-single-show="handleFetchSingleShow"
              @fetch-douban="handleFetchDouban"
              @toggle-wish-pool-entry="handleToggleWishPoolEntry"
              @add-all-to-wish-pool="handleAddAllToWishPool"
            />
          </section>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { fetchMovieDouban, getCities } from '@/api'
import { ElMessage } from 'element-plus'
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useShowFetching } from '@/composables/useShowFetching'
import { useScheduleStore } from '@/stores/scheduleStore'
import MovieCard from '@/components/MovieCard.vue'
import MovieFilterPanel from '@/components/MovieFilterPanel.vue'
import ScheduleBoard from '@/components/ScheduleBoard.vue'
import UpdatePanel from '@/components/UpdatePanel.vue'
import WishPool from '@/components/WishPool.vue'

const store = useScheduleStore()

// ===== 城市 / 更新表单 =====
const cities = ref([])
const updateForm = ref({ cityId: null, forceUpdate: false })

// ===== 电影筛选更新标记 =====
const lastAddedMovieIds = ref(new Set())
const lastUpdatedMovieIds = ref(new Set())

// ===== 场次缓存跨天失效定时器 =====
// 场次按自然日缓存：同一天内保留，跨过 0 点自动失效（由 store 负责判断）。
const {
  fetchingMovieIds,
  movieProgress,
  getMovieDateProgressEntries,
  clearAllMovieFetchProgress,
  handleFetchSingleShow,
  scheduleMidnightCleanup,
  stopMidnightCleanup,
} = useShowFetching(store, updateForm)

// ===== 电影列表状态 =====
const movieSearchKeyword = ref('')
const movieSortOrder = ref('newest')
const doubanFetchingIds = ref(new Set())

// ===== 初始化 =====
onMounted(async () => {
  store.pruneStaleMovieShows()
  await store.initializePlanningSync()
  scheduleMidnightCleanup()
  try {
    const response = await getCities()
    cities.value = response.data.data.cities
    const shanghaiCity = cities.value.find((city) => city.id === 10)
    if (shanghaiCity) updateForm.value.cityId = shanghaiCity.id
    else if (cities.value.length > 0) updateForm.value.cityId = cities.value[0].id
  } catch (error) {
    console.error('获取城市列表失败:', error)
  }
})

onBeforeUnmount(() => {
  stopMidnightCleanup()
})

watch(
  () => store.planningSyncError,
  (message) => {
    if (message) ElMessage.warning(message)
  }
)

const hasValidMovieShows = (movieId) => store.hasMovieShowsData(movieId)

const getMovieShowsData = (movieId) => store.getMovieShowsData(movieId)

// ===== 事件处理：来自 MovieFilterPanel =====
const handleMoviesSelected = () => {
  clearAllMovieFetchProgress()
}

// ===== 豆瓣信息获取 =====
const handleFetchDouban = async (movie) => {
  if (!movie.id) return
  doubanFetchingIds.value = new Set([...doubanFetchingIds.value, movie.id])
  try {
    const res = await fetchMovieDouban(movie.id)
    const { score, douban_url } = res.data.data
    store.updateMovieScore(movie.id, score, douban_url)
    if (douban_url) {
      ElMessage.success(`《${movie.title}》豆瓣评分：${score}`)
    } else {
      ElMessage.warning(`《${movie.title}》未找到豆瓣匹配条目`)
    }
  } catch (error) {
    const msg = error?.response?.data?.detail || error?.message || '未知错误'
    ElMessage.error(`获取豆瓣信息失败：${msg}`)
  } finally {
    const next = new Set(doubanFetchingIds.value)
    next.delete(movie.id)
    doubanFetchingIds.value = next
  }
}

// ===== 想看池交互 =====
const parseMovieDurationMinutes = (durationText) => {
  const normalized = String(durationText ?? '').trim()
  const match = normalized.match(/(\d+)/)
  return match ? Number(match[1]) : null
}

const createShowEntry = (movie, cinema, show) => ({
  key: `${movie.id}-${cinema.cinema_id}-${show.date}-${show.time}`,
  movieId: movie.id,
  movieTitle: movie.title,
  date: show.date,
  time: show.time,
  cinemaId: cinema.cinema_id,
  cinemaName: cinema.cinema_name,
  price: show.price,
  durationMinutes: parseMovieDurationMinutes(movie?.duration),
})

const handleToggleWishPoolEntry = (entry) => {
  if (store.isInSchedule(entry.key)) return
  if (store.isInWishPool(entry.key)) {
    store.removeFromWishPool(entry.key)
    return
  }
  store.addToWishPool(entry)
  ElMessage.success(`已将《${entry.movieTitle}》加入想看`)
}

const handleAddAllToWishPool = (movie, providedEntries) => {
  let entries = providedEntries
  if (!entries) {
    const showsData = getMovieShowsData(movie.id)
    if (!showsData?.cinemas) return
    entries = showsData.cinemas.flatMap((cinema) =>
      (cinema.shows || [])
        .map((show) => createShowEntry(movie, cinema, show))
        .filter((entry) => !store.isInSchedule(entry.key))
    )
  }

  if (entries.length === 0) {
    ElMessage.warning(`《${movie.title}》的场次已全部加入想看或行程`)
    return
  }

  const added = store.addManyToWishPool(entries)
  ElMessage.success(`已将《${movie.title}》的 ${added} 个场次加入想看`)
}

// ===== 计算属性 =====
const filteredSelectedMovies = computed(() => {
  const keyword = String(movieSearchKeyword.value || '').trim().toLowerCase()
  const movies = keyword
    ? store.selectedMovies.filter((movie) => {
        const haystacks = [movie.title, movie.director, movie.actors, movie.genres, movie.country, movie.language]
          .map((item) => String(item || '').toLowerCase())
          .filter(Boolean)
        return haystacks.some((text) => text.includes(keyword))
      })
    : [...store.selectedMovies]

  if (movieSortOrder.value === 'name') {
    movies.sort((a, b) => String(a.title || '').localeCompare(String(b.title || ''), 'zh'))
  } else {
    movies.sort((a, b) => {
      const av = a.first_showing_at || ''
      const bv = b.first_showing_at || ''
      if (!av && !bv) return 0
      if (!av) return 1
      if (!bv) return -1
      return bv.localeCompare(av)
    })
  }

  return movies
})

const movieDisplaySections = computed(() => {
  const addedMovies = []
  const existingMovies = []

  filteredSelectedMovies.value.forEach((movie) => {
    if (lastAddedMovieIds.value.has(movie.id)) {
      addedMovies.push(movie)
    } else {
      existingMovies.push(movie)
    }
  })

  const sections = []
  let offset = 0

  if (addedMovies.length > 0) {
    sections.push({ key: 'added', title: '新增电影', movies: addedMovies, startIndex: offset })
    offset += addedMovies.length
  }

  sections.push({ key: 'existing', title: '在库电影', movies: existingMovies, startIndex: offset })

  return sections.filter((section) => section.movies.length > 0)
})
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

.top-section {
  display: grid;
  grid-template-columns: minmax(0, 1.2fr) minmax(0, 0.8fr);
  gap: 40px;
  margin-bottom: 20px;
  align-items: start;
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

.section-header-controls {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
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

@media (max-width: 960px) {
  .top-section {
    grid-template-columns: 1fr;
    gap: 24px;
  }

  .section-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .movie-search-input {
    width: 100%;
  }
}

@media (max-width: 640px) {
  .movie-scheduler-page {
    padding: 0 12px;
  }
}
</style>
