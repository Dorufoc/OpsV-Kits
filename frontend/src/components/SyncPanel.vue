<template>
  <div class="sync-panel">
    <div class="panel-header">
      <span class="panel-title">同步状态</span>
      <el-tag :type="statusTagType" size="small">{{ statusText }}</el-tag>
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
      <el-progress
        :percentage="syncPercentage"
        :status="syncStatus === 'completed' ? 'success' : syncStatus === 'error' ? 'exception' : undefined"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { SyncStatus, SyncProgress } from '@/stores/syncStore'

const props = defineProps<{
  syncStatus: SyncStatus
  progress: SyncProgress
}>()

const statusTagType = computed(() => {
  const map: Record<string, string> = {
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
</script>

<style scoped>
.sync-panel {
  padding: 12px;
  background: #f8f9fa;
  border-radius: 6px;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.panel-title {
  font-weight: 600;
  font-size: 14px;
}

.panel-body {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-bottom: 12px;
}

.status-item {
  display: flex;
  justify-content: space-between;
  font-size: 13px;
}

.status-item .label {
  color: #909399;
}

.status-item .value {
  color: #303133;
  font-weight: 500;
}

.status-item .value.text-ellipsis {
  max-width: 160px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.panel-progress {
  margin-top: 4px;
}
</style>
