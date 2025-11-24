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
        <el-descriptions :column="2" border>
          <el-descriptions-item label="新增电影">
            {{ movieResult.base_info?.added || 0 }}
          </el-descriptions-item>
          <el-descriptions-item label="删除电影">
            {{ movieResult.base_info?.removed || 0 }}
          </el-descriptions-item>
          <el-descriptions-item label="电影总数">
            {{ movieResult.base_info?.total || 0 }}
          </el-descriptions-item>
          <el-descriptions-item label="更新详情数">
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
import { getCities, updateCinema, updateMovie } from '@/api'

const cities = ref([])
const form = ref({
  cityId: null
})

const cinemaLoading = ref(false)
const movieLoading = ref(false)
const cinemaResult = ref(null)
const movieResult = ref(null)

onMounted(async () => {
  try {
    const response = await getCities()
    cities.value = response.data.cities
    // 默认选中上海（城市 ID 为 10）
    const shanghaiCity = cities.value.find(city => city.id === 10)
    if (shanghaiCity) {
      form.value.cityId = shanghaiCity.id
    } else if (cities.value.length > 0) {
      form.value.cityId = cities.value[0].id
    }
  } catch (error) {
    ElMessage.error('获取城市列表失败: ' + error.message)
  }
})

const handleUpdateCinema = async () => {
  cinemaLoading.value = true
  cinemaResult.value = null
  try {
    const response = await updateCinema(form.value.cityId)
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
    const response = await updateMovie(form.value.cityId, false)
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
</style>
