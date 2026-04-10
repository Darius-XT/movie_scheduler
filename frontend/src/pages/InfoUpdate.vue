<template>
  <div class="info-update-page">
    <el-card class="page-card">
      <template #header>
        <div class="card-header">
          <span>信息更新</span>
        </div>
      </template>

      <el-form :model="form" label-width="120px">
        <el-form-item label="选择城市">
          <el-select
            v-model="form.cityId"
            placeholder="请选择城市"
            style="width: 240px"
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
          <el-space>
            <el-button
              type="primary"
              :loading="cinemaLoading"
              :disabled="!form.cityId"
              @click="handleUpdateCinema"
            >
              更新影院信息
            </el-button>
            <el-button
              type="success"
              :loading="movieLoading"
              :disabled="!form.cityId"
              @click="handleUpdateMovie"
            >
              更新电影信息
            </el-button>
          </el-space>
        </el-form-item>
      </el-form>

      <el-divider />

      <div v-if="cinemaUpdateProgress || movieUpdateProgress" class="result-section">
        <h3>更新进度</h3>
        <div v-if="cinemaUpdateProgress" class="progress-box">{{ cinemaUpdateProgress }}</div>
        <div v-if="movieUpdateProgress" class="progress-box">{{ movieUpdateProgress }}</div>
      </div>

      <div v-if="cinemaResult" class="result-section">
        <h3>影院更新结果</h3>
        <el-descriptions :column="2" border>
          <el-descriptions-item label="成功数量">
            {{ cinemaResult.success_count }}
          </el-descriptions-item>
          <el-descriptions-item label="失败数量">
            {{ cinemaResult.failure_count }}
          </el-descriptions-item>
        </el-descriptions>
      </div>

      <div v-if="movieResult" class="result-section">
        <h3>电影更新结果</h3>

        <h4>输入统计</h4>
        <el-descriptions :column="2" border>
          <el-descriptions-item label="抓取总数">
            {{ movieResult.base_info?.input_stats?.scraped_total || 0 }}
          </el-descriptions-item>
          <el-descriptions-item label="正在热映">
            {{ movieResult.base_info?.input_stats?.showing || 0 }}
          </el-descriptions-item>
          <el-descriptions-item label="即将上映">
            {{ movieResult.base_info?.input_stats?.upcoming || 0 }}
          </el-descriptions-item>
          <el-descriptions-item label="重复数量">
            {{ movieResult.base_info?.input_stats?.duplicate || 0 }}
          </el-descriptions-item>
          <el-descriptions-item label="去重后总数">
            {{ movieResult.base_info?.input_stats?.deduplicated_total || 0 }}
          </el-descriptions-item>
        </el-descriptions>

        <h4>更新结果统计</h4>
        <el-descriptions :column="2" border>
          <el-descriptions-item label="原有数量">
            {{ movieResult.base_info?.result_stats?.existing || 0 }}
          </el-descriptions-item>
          <el-descriptions-item label="新增数量">
            {{ movieResult.base_info?.result_stats?.added || 0 }}
          </el-descriptions-item>
          <el-descriptions-item label="更新数量">
            {{ movieResult.base_info?.result_stats?.updated || 0 }}
          </el-descriptions-item>
          <el-descriptions-item label="删除数量">
            {{ movieResult.base_info?.result_stats?.removed || 0 }}
          </el-descriptions-item>
          <el-descriptions-item label="当前总数">
            {{ movieResult.base_info?.result_stats?.total || 0 }}
          </el-descriptions-item>
          <el-descriptions-item label="额外详情更新数">
            {{ movieResult.extra_info?.updated_count || 0 }}
          </el-descriptions-item>
        </el-descriptions>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getCities } from '@/api'

const cities = ref([])
const form = ref({
  cityId: null,
})

const cinemaLoading = ref(false)
const movieLoading = ref(false)
const cinemaResult = ref(null)
const movieResult = ref(null)
const cinemaUpdateProgress = ref('')
const movieUpdateProgress = ref('')

onMounted(async () => {
  try {
    const response = await getCities()
    cities.value = response.data.cities
    const shanghaiCity = cities.value.find((city) => city.id === 10)
    if (shanghaiCity) {
      form.value.cityId = shanghaiCity.id
    } else if (cities.value.length > 0) {
      form.value.cityId = cities.value[0].id
    }
  } catch (error) {
    ElMessage.error(`获取城市列表失败: ${error.message}`)
  }
})

const handleUpdateCinema = async () => {
  cinemaLoading.value = true
  cinemaResult.value = null
  cinemaUpdateProgress.value = ''
  try {
    const response = await fetch(`/api/v1/update/cinema-stream?city_id=${form.value.cityId}`, {
      headers: { Accept: 'text/event-stream' },
    })
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }
    if (!response.body) {
      throw new Error('未收到更新响应流')
    }

    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''

      for (const line of lines) {
        if (!line.startsWith('data: ')) continue
        const data = JSON.parse(line.substring(6))
        if (data.type === 'progress') {
          cinemaUpdateProgress.value = data.message || '正在更新影院信息'
        } else if (data.type === 'complete') {
          cinemaResult.value = data.data
          cinemaUpdateProgress.value = '影院信息更新完成'
          ElMessage.success('影院信息更新成功')
        } else if (data.type === 'error') {
          cinemaUpdateProgress.value = ''
          ElMessage.error(`更新失败: ${data.error}`)
        }
      }
    }
  } catch (error) {
    ElMessage.error(`更新失败: ${error.message}`)
  } finally {
    if (cinemaResult.value) {
      window.setTimeout(() => {
        cinemaUpdateProgress.value = ''
      }, 1200)
    } else {
      cinemaUpdateProgress.value = ''
    }
    cinemaLoading.value = false
  }
}

const handleUpdateMovie = async () => {
  movieLoading.value = true
  movieResult.value = null
  movieUpdateProgress.value = ''
  try {
    const response = await fetch(`/api/v1/update/movie-stream?city_id=${form.value.cityId}&force_update_all=false`, {
      headers: { Accept: 'text/event-stream' },
    })
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }
    if (!response.body) {
      throw new Error('未收到更新响应流')
    }

    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''

      for (const line of lines) {
        if (!line.startsWith('data: ')) continue
        const data = JSON.parse(line.substring(6))
        if (data.type === 'progress') {
          movieUpdateProgress.value = data.message || '正在更新电影信息'
        } else if (data.type === 'complete') {
          movieResult.value = data.data
          movieUpdateProgress.value = '电影信息更新完成'
          ElMessage.success('电影信息更新成功')
        } else if (data.type === 'error') {
          movieUpdateProgress.value = ''
          ElMessage.error(`更新失败: ${data.error}`)
        }
      }
    }
  } catch (error) {
    ElMessage.error(`更新失败: ${error.message}`)
  } finally {
    if (movieResult.value) {
      window.setTimeout(() => {
        movieUpdateProgress.value = ''
      }, 1200)
    } else {
      movieUpdateProgress.value = ''
    }
    movieLoading.value = false
  }
}
</script>

<style scoped>
.info-update-page {
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

.result-section {
  margin-top: 20px;
}

.result-section h3 {
  margin-bottom: 10px;
  color: #333;
}

.result-section h4 {
  margin: 16px 0 10px;
  color: #606266;
}

.progress-box {
  margin-top: 10px;
  padding: 12px 14px;
  border-left: 3px solid #409eff;
  border-radius: 8px;
  background: #f0f9ff;
  color: #1d4ed8;
  line-height: 1.6;
}
</style>
