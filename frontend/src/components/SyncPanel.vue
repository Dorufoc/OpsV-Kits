<template>
  <div class="sync-panel">
    <div class="panel-header">
      <span class="panel-title">同步状态</span>
      <Md3Tag :type="statusTagType" size="sm">{{ statusText }}</Md3Tag>
    </div>
    <div class="panel-body">
      <div class="status-item">
        <span class="label">总文件数</span>
        <span class="value">{{ progress.total }}</span>
      </div>
      <div class="status-item">
        <span class="label">已同步</span>
        <span class="value">{{ progress.transferred }}</span>
      </div>
      <div class="status-item">
        <span class="label">当前文件</span>
        <span class="value text-ellipsis">{{ progress.current_file || '-' }}</span>
      </div>
      <div class="status-item" v-if="progress.speed">
        <span class="label">速度</span>
        <span class="value">{{ progress.speed }}</span>
      </div>
    </div>
    <div class="panel-progress" v-if="progress.total > 0">
      <Md3Progress
        :percentage="syncPercentage"
        :color="progressColor"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Md3Tag, Md3Progress } from '@/components/md3'
import type { SyncStatus, SyncProgress } from '@/stores/syncStore'

const props = defineProps<{
  syncStatus: SyncStatus
  progress: SyncProgress
}>()

const statusTagType = computed(() => {
  const map: Record<string, 'primary' | 'success' | 'warning' | 'danger' | 'info'> = {
    idle: 'info',
    scanning: 'warning',
    syncing: 'primary',
    completed: 'success',
    error: 'danger',
  }
  return map[props.syncStatus] || 'info'
})

const statusText = computed(() => {
  const map: Record<string, string> = {
    idle: '待同步',
    scanning: '扫描中',
    syncing: '同步中',
    completed: '已完成',
    error: '出错',
  }
  return map[props.syncStatus] || '未知'
})

const syncPercentage = computed(() => {
  if (props.progress.total === 0 && props.syncStatus === 'idle') return 0
  return props.progress.total
})

const progressColor = computed(() => {
  if (props.syncStatus === 'completed') return 'var(--md3-success)'
  if (props.syncStatus === 'error') return 'var(--md3-error)'
  return ''
})
</script>

<style scoped>
.sync-panel {
  padding: var(--md3-space-md);
  background: var(--md3-glass-bg);
  backdrop-filter: var(--md3-glass-blur);
  -webkit-backdrop-filter: var(--md3-glass-blur);
  border: 1px solid var(--md3-glass-border);
  border-radius: var(--md3-shape-md);
  transition: border-color var(--md3-motion-duration-medium) var(--md3-motion-easing-standard);
}

.sync-panel:hover {
  border-color: var(--md3-card-border-hover);
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--md3-space-md);
}

.panel-title {
  font-weight: 600;
  font-size: 16px;
  color: var(--md3-on-surface);
}

.panel-body {
  display: flex;
  flex-direction: column;
  gap: var(--md3-space-xs);
  margin-bottom: var(--md3-space-md);
}

.status-item {
  display: flex;
  justify-content: space-between;
  font-size: 13px;
}

.status-item .label {
  color: var(--md3-on-surface-variant);
}

.status-item .value {
  color: var(--md3-on-surface);
  font-weight: 500;
}

.status-item .value.text-ellipsis {
  max-width: 160px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.panel-progress {
  margin-top: var(--md3-space-xs);
}
</style>
