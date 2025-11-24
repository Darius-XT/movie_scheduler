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
                新增 {{ movieResult.base_info?.added || 0 }} /
                删除 {{ movieResult.base_info?.removed || 0 }} /
                总数 {{ movieResult.base_info?.total || 0 }}
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
            <el-form-item label="年份阈值">
              <div class="threshold-input-wrapper">
                <el-input-number
                  v-model="form.yearThreshold"
                  :min="1800"
                  :max="2100"
                  placeholder="留空则使用默认值"
                  style="width: 200px"
                />
                <el-tooltip
                  content="仅对中国大陆电影生效，上映年份小于阈值的电影会被选中"
                  placement="right"
                  :show-after="300"
                >
                  <el-icon class="info-icon"><QuestionFilled /></el-icon>
                </el-tooltip>
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
            <div v-if="fetchProgress.visible" class="fetch-progress">
              <el-divider style="margin: 12px 0" />
              <div class="progress-content">
                <div class="progress-text">{{ fetchProgress.text }}</div>
              </div>
            </div>
          </el-form>
        </div>
      </div>

      <el-divider />

      <div v-if="selectedMovies.length > 0" class="movies-section">
        <div class="section-header">
          <h3>已筛选电影（{{ selectedMovies.length }} 部）</h3>
        </div>

        <div class="movie-list">
          <el-card
            v-for="(movie, index) in selectedMovies"
            :key="movie.id"
            class="movie-card"
          >
            <div class="movie-header">
              <div class="movie-basic-info">
                <div class="movie-title-row">
                  <span class="movie-index">{{ index + 1 }}.</span>
                  <span class="movie-title">{{ movie.title }}</span>
                  <el-tag v-if="movie.score" type="warning" size="small" class="movie-score">
                    {{ movie.score }}
                  </el-tag>
                </div>
                <div class="movie-meta">
                  <span v-if="movie.release_year" class="meta-item">{{ movie.release_year }}</span>
                  <span v-if="movie.duration" class="meta-item">{{ movie.duration }}</span>
                  <span v-if="movie.country || movie.language" class="meta-item">
                    {{ [movie.country, movie.language].filter(Boolean).join(' - ') }}
                  </span>
                  <span v-if="movie.director" class="meta-item">导演: {{ movie.director }}</span>
                  <span v-if="movie.actors" class="meta-item">主演: {{ movie.actors }}</span>
                  <span v-if="movie.genres" class="meta-item">{{ movie.genres }}</span>
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
                  v-if="!movieShowsMap.has(movie.id)"
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
              <div v-if="movieProgress.has(movie.id)" class="single-movie-progress">
                <el-divider style="margin: 12px 0" />
                <div class="progress-content">
                  <div class="progress-text">{{ movieProgress.get(movie.id) }}</div>
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
              <div v-if="expandedShows.has(movie.id) && movieShowsMap.has(movie.id)" class="movie-shows">
                <el-divider style="margin: 12px 0" />
                <div class="shows-summary">
                  <el-tag type="info" size="small">
                    {{ movieShowsMap.get(movie.id).cinemas?.length || 0 }} 个影院
                  </el-tag>
                  <el-tag type="success" size="small" style="margin-left: 8px">
                    {{ getTotalShows(movieShowsMap.get(movie.id)) }} 个场次
                  </el-tag>
                </div>
                <div
                  v-for="cinema in movieShowsMap.get(movie.id).cinemas"
                  :key="cinema.cinema_id"
                  class="cinema-item"
                >
                  <h4 class="cinema-name">{{ cinema.cinema_name }}</h4>
                  <el-table :data="cinema.shows" size="small" style="width: 100%">
                    <el-table-column prop="date" label="日期" width="120" />
                    <el-table-column prop="time" label="时间" width="100" />
                    <el-table-column prop="price" label="价格" width="100">
                      <template #default="scope">
                        ¥{{ scope.row.price }}
                      </template>
                    </el-table-column>
                  </el-table>
                </div>
              </div>
            </el-collapse-transition>
          </el-card>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Setting, QuestionFilled, Filter } from '@element-plus/icons-vue'
import { selectMovies, getCities, updateCinema, updateMovie } from '@/api'

// LocalStorage 键名
const STORAGE_KEY = 'movie_selector_data'

// 信息更新相关状态
const cities = ref([])
const updateForm = ref({
  cityId: null
})
const cinemaLoading = ref(false)
const movieLoading = ref(false)
const cinemaResult = ref(null)
const movieResult = ref(null)

// 电影筛选相关状态
const form = ref({
  yearThreshold: 2020
})

const selectLoading = ref(false)
const fetchLoading = ref(false)
const selectedMovies = ref([])
const fetchingMovieIds = ref(new Set()) // 跟踪正在获取场次的电影ID
const movieShowsMap = ref(new Map()) // 存储每部电影的场次信息 Map<movieId, showsData>
const expandedDescriptions = ref(new Set()) // 展开简介的电影ID集合
const expandedShows = ref(new Set()) // 展开场次的电影ID集合

// 单个电影获取进度显示 Map<movieId, progressText>
const movieProgress = ref(new Map())

// 批量获取进度显示
const fetchProgress = ref({
  visible: false,
  text: ''
})

// 从 localStorage 恢复数据
const loadFromStorage = () => {
  try {
    const savedData = localStorage.getItem(STORAGE_KEY)
    if (savedData) {
      const data = JSON.parse(savedData)
      if (data.yearThreshold) {
        form.value.yearThreshold = data.yearThreshold
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
    }
  } catch (error) {
    console.error('恢复数据失败:', error)
  }
}

// 保存数据到 localStorage
const saveToStorage = () => {
  try {
    const data = {
      yearThreshold: form.value.yearThreshold,
      selectedMovies: selectedMovies.value,
      // 将 Map 转换为对象以便 JSON 序列化
      movieShowsMap: Object.fromEntries(movieShowsMap.value.entries()),
      expandedDescriptions: Array.from(expandedDescriptions.value),
      expandedShows: Array.from(expandedShows.value)
    }
    localStorage.setItem(STORAGE_KEY, JSON.stringify(data))
  } catch (error) {
    console.error('保存数据失败:', error)
  }
}

// 组件挂载时恢复数据并加载城市列表
onMounted(async () => {
  loadFromStorage()

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

// 监听数据变化并保存
watch([selectedMovies, movieShowsMap, expandedDescriptions, expandedShows, () => form.value.yearThreshold], () => {
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
  try {
    const response = await updateMovie(updateForm.value.cityId, false)
    if (response.data.success) {
      movieResult.value = response.data.data
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
  expandedDescriptions.value.clear()
  expandedShows.value.clear()
  try {
    const response = await selectMovies(form.value.yearThreshold)
    if (response.data.success) {
      selectedMovies.value = response.data.data.movies
      ElMessage.success(`成功筛选出 ${response.data.data.count} 部电影`)
    } else {
      ElMessage.error('筛选失败: ' + response.data.error)
    }
  } catch (error) {
    ElMessage.error('筛选失败: ' + error.message)
  } finally {
    selectLoading.value = false
  }
}

const handleFetchShows = async () => {
  // 过滤出需要获取场次的电影（未上映的和已获取过的都跳过）
  const moviesToFetch = selectedMovies.value.filter(
    m => m.id != null && m.is_showing !== false && !movieShowsMap.value.has(m.id)
  )

  if (moviesToFetch.length === 0) {
    ElMessage.warning('没有需要获取场次的电影')
    return
  }

  fetchLoading.value = true
  fetchProgress.value.visible = true
  fetchProgress.value.text = `开始批量获取 ${moviesToFetch.length} 部电影的场次...`

  const movieIds = moviesToFetch.map(m => m.id).join(',')
  const url = `/api/shows/fetch-stream?movie_ids=${movieIds}&use_async=true`

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
            fetchProgress.value.text = `电影《${movie?.title}》找到 ${data.dates.length} 个排片日期`
          } else if (data.type === 'processing_date') {
            const movie = moviesToFetch.find(m => m.id === data.movie_id)
            fetchProgress.value.text = `电影《${movie?.title}》处理日期 ${data.date_idx}/${data.total_dates}`
          } else if (data.type === 'processing_cinema') {
            const movie = moviesToFetch.find(m => m.id === data.movie_id)
            fetchProgress.value.text = `电影《${movie?.title}》日期 ${data.date} - 影院 ${data.cinema_idx}/${data.total_cinemas}`
          } else if (data.type === 'complete') {
            // 更新场次数据
            const shows = data.data
            shows.forEach(showItem => {
              movieShowsMap.value.set(showItem.movie_id, showItem)
            })

            const successCount = shows.filter(s => s.cinemas && s.cinemas.length > 0).length
            const noShowsCount = shows.length - successCount

            if (successCount > 0 && noShowsCount === 0) {
              ElMessage.success(`批量获取完成：成功获取 ${successCount} 部电影的场次信息`)
            } else if (successCount > 0 && noShowsCount > 0) {
              ElMessage.warning(`批量获取完成：${successCount} 部有场次，${noShowsCount} 部暂无场次`)
            } else {
              ElMessage.warning('批量获取完成：所有电影暂无场次信息')
            }

            fetchProgress.value.text = '批量获取完成'
            setTimeout(() => {
              fetchProgress.value.visible = false
            }, 2000)
          } else if (data.type === 'error') {
            ElMessage.error('批量获取失败: ' + data.error)
            fetchProgress.value.visible = false
          }
        }
      }
    }
  } catch (error) {
    console.error('SSE 连接错误:', error)
    ElMessage.error('批量获取失败: ' + error.message)
    fetchProgress.value.visible = false
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

  const url = `/api/shows/fetch-stream?movie_ids=${movie.id}&use_async=true`

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
            movieProgress.value.set(movie.id, `找到 ${data.dates.length} 个排片日期`)
          } else if (data.type === 'processing_date') {
            movieProgress.value.set(movie.id, `处理日期 ${data.date_idx}/${data.total_dates}: ${data.date}`)
          } else if (data.type === 'processing_cinema') {
            movieProgress.value.set(movie.id, `日期 ${data.date} - 影院 ${data.cinema_idx}/${data.total_cinemas}`)
          } else if (data.type === 'complete') {
            const shows = data.data
            if (shows.length > 0) {
              const showItem = shows[0]
              movieShowsMap.value.set(movie.id, showItem)
              expandedShows.value.add(movie.id)

              const totalShows = getTotalShows(showItem)
              ElMessage.success(`成功获取《${movie.title}》的场次信息（共 ${totalShows} 个场次）`)
            } else {
              ElMessage.warning(`电影《${movie.title}》暂无场次信息`)
            }

            // 2秒后隐藏进度
            setTimeout(() => {
              movieProgress.value.delete(movie.id)
            }, 2000)
          } else if (data.type === 'error') {
            ElMessage.error('获取失败: ' + data.error)
            movieProgress.value.delete(movie.id)
          }
        }
      }
    }
  } catch (error) {
    console.error('单个电影 SSE 连接错误:', error)
    ElMessage.error('获取失败: ' + error.message)
    movieProgress.value.delete(movie.id)
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
  align-items: center;
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

.info-icon {
  font-size: 18px;
  color: #909399;
  cursor: help;
}

.info-icon:hover {
  color: #409eff;
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

.progress-text {
  font-size: 13px;
  color: #409eff;
  line-height: 1.5;
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
  justify-content: flex-start;
  align-items: center;
  margin-bottom: 15px;
}

.section-header h3 {
  margin: 0;
  color: #333;
}

.movie-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
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
  font-size: 14px;
  color: #606266;
}

.meta-item {
  position: relative;
}

.meta-item:not(:last-child)::after {
  content: '|';
  position: absolute;
  right: -8px;
  color: #dcdfe6;
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
  margin-bottom: 12px;
}

.cinema-item {
  margin-bottom: 16px;
  padding: 12px;
  background-color: #f9fafc;
  border-radius: 4px;
  border: 1px solid #e4e7ed;
}

.cinema-item:last-child {
  margin-bottom: 0;
}

.cinema-name {
  margin: 0 0 10px 0;
  color: #409eff;
  font-size: 15px;
  font-weight: 500;
}
</style>
