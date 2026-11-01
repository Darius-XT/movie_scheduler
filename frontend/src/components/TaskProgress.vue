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
    <small v-else-if="!finished">当前阶段{{ determinate ? `：${event.current}/${event.total}` : '：正在获取数据' }}</small>
  </div>
</template>

<script setup>
import { computed } from 'vue'
const props = defineProps({
  event: { type: Object, default: () => ({}) },
})
const finished = computed(() => ['complete', 'error'].includes(props.event.type))
const determinate = computed(() => Number.isFinite(props.event.current) && props.event.total > 0)
const percentage = computed(() => props.event.type === 'complete' ? 100
  : determinate.value ? Math.min(100, Math.max(0, Math.round(props.event.current / props.event.total * 100)))
    : props.event.type === 'error' ? 0 : 40)
</script>

<style scoped>
.task-progress { width: 100%; min-width: 180px; font-size: var(--el-font-size-extra-small, 12px); font-weight: normal; }
small { display: block; margin-top: 4px; font-size: inherit; line-height: 1.4; color: var(--el-text-color-secondary); overflow-wrap: anywhere; }
</style>
