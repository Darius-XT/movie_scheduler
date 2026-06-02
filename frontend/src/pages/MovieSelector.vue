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
          <MovieCard
            v-for="(movie, index) in filteredSelectedMovies"
            :key="movie.id"
            :movie="movie"
            :index="index"
            mode="select"
            :is-douban-fetching="doubanFetchingIds.has(movie.id)"
            :is-wish-toggling="wishTogglingIds.has(movie.id)"
            @fetch-douban="handleFetchDouban"
            @toggle-wish-movie="handleToggleWishMovie"
          />
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { fetchMovieDouban, getCities } from '@/api'
import { ElMessage } from 'element-plus'
import { computed, onMounted, ref, watch } from 'vue'
import { useScheduleStore } from '@/stores/scheduleStore'
import MovieCard from '@/components/MovieCard.vue'
import MovieFilterPanel from '@/components/MovieFilterPanel.vue'
import ScheduleBoard from '@/components/ScheduleBoard.vue'
import UpdatePanel from '@/components/UpdatePanel.vue'
import WishPool from '@/components/WishPool.vue'

const store = useScheduleStore()

// ===== 城市 / 更新表单 =====
const cities = ref([])
const updateForm = ref({ cityId: null })

// ===== 电影列表状态 =====
const movieSearchKeyword = ref('')
const movieSortOrder = ref('newest')
const doubanFetchingIds = ref(new Set())
const wishTogglingIds = ref(new Set())

// ===== 初始化 =====
onMounted(async () => {
  const cityTask = loadCities()
  await Promise.allSettled([
    cityTask,
    store.initializeScheduleSync(),
    store.initializeWishSync(),
  ])
  void store.refreshShowsFromBackend()
})

const loadCities = async () => {
  try {
    const response = await getCities()
    cities.value = response.data.data.cities
    const shanghaiCity = cities.value.find((city) => city.id === 10)
    if (shanghaiCity) updateForm.value.cityId = shanghaiCity.id
    else if (cities.value.length > 0) updateForm.value.cityId = cities.value[0].id
  } catch (error) {
    console.error('获取城市列表失败:', error)
  }
}

watch(
  () => store.scheduleSyncError,
  (message) => {
    if (message) ElMessage.warning(message)
  }
)

watch(
  () => store.wishSyncError,
  (message) => {
    if (message) ElMessage.warning(message)
  }
)

watch(
  () => store.showsSyncError,
  (message) => {
    if (message) ElMessage.warning(message)
  }
)

// ===== 事件处理：来自 MovieFilterPanel =====
const handleMoviesSelected = () => {
  // no-op now; 场次抓取已移到想看列表
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

// ===== 想看交互(电影维度) =====
const handleToggleWishMovie = async (movie) => {
  if (!movie?.id) return
  wishTogglingIds.value = new Set([...wishTogglingIds.value, movie.id])
  try {
    if (store.isInWishMovies(movie.id)) {
      await store.removeFromWishMovies(movie.id)
      store.removeMovieShows(movie.id)
      ElMessage.info(`已将《${movie.title}》移出想看`)
    } else {
      await store.addToWishMovies(movie)
      store.removeMovieShows(movie.id)
      void store.pollMovieShowsUntilUpdated(movie.id)
      ElMessage.success(`已将《${movie.title}》加入想看`)
    }
  } catch {
    // store 已 rollback,并设置过 wishSyncError(由 watch 弹出 warning)
  } finally {
    const next = new Set(wishTogglingIds.value)
    next.delete(movie.id)
    wishTogglingIds.value = next
  }
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
