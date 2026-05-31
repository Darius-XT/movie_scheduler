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
          size="small"
          :loading="isDoubanFetching"
          @click="$emit('fetch-douban', movie)"
        >
          {{ (movie.douban_url || movie.score === '无豆瓣评分') ? '更新豆瓣' : '获取豆瓣' }}
        </el-button>
        <el-button
          size="small"
          :type="isInWishMovies ? 'success' : 'primary'"
          :plain="isInWishMovies"
          :loading="isWishToggling"
          @click="$emit('toggle-wish-movie', movie)"
        >
          {{ isInWishMovies ? '已加入想看' : '加入想看' }}
        </el-button>
      </div>
    </div>

    <!-- 简介 -->
    <el-collapse-transition>
      <div v-if="descriptionExpanded" class="movie-description">
        <el-divider style="margin: 12px 0" />
        <div class="description-content">
          {{ movie.description || '暂无简介' }}
        </div>
      </div>
    </el-collapse-transition>
  </el-card>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useScheduleStore } from '@/stores/scheduleStore'

const props = defineProps({
  movie: {
    type: Object,
    required: true,
  },
  index: {
    type: Number,
    default: 0,
  },
  isDoubanFetching: {
    type: Boolean,
    default: false,
  },
  isWishToggling: {
    type: Boolean,
    default: false,
  },
})

defineEmits([
  'fetch-douban',
  'toggle-wish-movie',
])

const store = useScheduleStore()

const descriptionExpanded = ref(false)

const movieRegion = computed(() => String(props.movie?.country || '').trim())

const isInWishMovies = computed(() => store.isInWishMovies(props.movie?.id))

const toggleDescription = () => {
  descriptionExpanded.value = !descriptionExpanded.value
}
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

@media (max-width: 960px) {
  .movie-header {
    flex-direction: column;
    gap: 12px;
  }

  .movie-actions {
    width: 100%;
    flex-wrap: wrap;
  }
}

@media (max-width: 640px) {
  .movie-actions .el-button {
    flex: 1 1 140px;
  }

  .movie-secondary-meta {
    gap: 6px;
  }

  .meta-item {
    min-height: 28px;
    padding: 0 10px;
  }
}
</style>
