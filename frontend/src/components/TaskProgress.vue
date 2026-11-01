<template>
  <div class="task-progress" role="status" aria-live="polite">
    <el-progress
      :percentage="percentage"
      :indeterminate="!determinate && !finished"
      :show-text="false"
      :status="event.type === 'error' ? 'exception' : event.type === 'complete' ? 'success' : undefined"
      :stroke-width="8"
    />
    <small v-if="finished">{{ event.message }}</small>
    <small v-else>{{ stageCaption }}</small>
  </div>
</template>

<script setup>
import { computed } from 'vue'
const props = defineProps({
  event: { type: Object, default: () => ({}) },
})
const finished = computed(() => ['complete', 'error'].includes(props.event.type))
const determinate = computed(() => Number.isFinite(props.event.current) && props.event.total > 0)
const stageCaption = computed(() => {
  const { stage, message = '', current, total } = props.event
  const stageNames = {
    fetching_movie_details: '更新详细信息',
    base_info_completed: '电影列表更新完成',
    finalizing_movie_update: '汇总电影更新结果',
    fetching_shows: '准备抓取场次',
    fetching_show_dates: '获取放映日期',
    fetching_show_cinemas: '获取影院列表',
    fetching_cinema_shows: '抓取影院场次',
    persisting_shows: '保存场次信息',
    empty_wishlist: '没有需要更新的电影',
  }
  let stageName = stageNames[stage] || '准备更新'
  if (stage === 'fetching_movie_list') {
    const listName = message.includes('即将上映') ? '即将上映列表'
      : message.includes('正在热映') ? '正在热映列表' : '电影列表'
    stageName = `抓取${listName}`
  }
  return `${stageName}${determinate.value ? `：${current}/${total}` : ''}`
})
const percentage = computed(() => props.event.type === 'complete' ? 100
  : determinate.value ? Math.min(100, Math.max(0, Math.round(props.event.current / props.event.total * 100)))
    : props.event.type === 'error' ? 0 : 40)
</script>

<style scoped>
.task-progress { width: 100%; min-width: 180px; font-size: var(--el-font-size-extra-small, 12px); font-weight: normal; }
small { display: block; margin-top: 4px; font-size: inherit; line-height: 1.4; color: var(--el-text-color-secondary); overflow-wrap: anywhere; }
</style>
