<template>
  <div class="vite-status-card">
    <div class="panel-header">
      <span class="panel-title">环境状态</span>
    </div>
    <div class="status-list">
      <div class="status-row">
        <div class="status-icon" :class="nodeIconClass">
          <Md3Icon :name="nodeStatus?.installed ? 'check-circle' : 'x-circle'" />
        </div>
        <div class="status-info">
          <span class="status-label">Node.js</span>
          <span class="status-value">{{ nodeDisplay }}</span>
        </div>
        <Md3Tag :type="nodeTagType" size="sm">{{ nodeTagText }}</Md3Tag>
      </div>
      <div class="status-row">
        <div class="status-icon" :class="nginxIconClass">
          <Md3Icon :name="nginxStatus?.installed ? (nginxStatus?.running ? 'check-circle' : 'alert-circle') : 'x-circle'" />
        </div>
        <div class="status-info">
          <span class="status-label">Nginx</span>
          <span class="status-value">{{ nginxDisplay }}</span>
        </div>
        <Md3Tag :type="nginxTagType" size="sm">{{ nginxTagText }}</Md3Tag>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Md3Tag, Md3Icon } from '@/components/md3'
import type { NodeStatus, NginxStatus } from '@/stores/viteDeployStore'

const props = defineProps<{
  nodeStatus: NodeStatus | null
  nginxStatus: NginxStatus | null
}>()

const nodeDisplay = computed(() => {
  if (!props.nodeStatus?.installed) return '未安装'
  return props.nodeStatus.version || '已安装'
})

const nodeTagType = computed(() => {
  if (!props.nodeStatus?.installed) return 'danger'
  return 'success'
})

const nodeTagText = computed(() => {
  if (!props.nodeStatus?.installed) return '缺失'
  return '正常'
})

const nodeIconClass = computed(() => {
  if (!props.nodeStatus?.installed) return 'status-icon--danger'
  return 'status-icon--success'
})

const nginxDisplay = computed(() => {
  if (!props.nginxStatus?.installed) return '未安装'
  if (!props.nginxStatus?.running) return '已安装 / 未运行'
  return '已安装 / 运行中'
})

const nginxTagType = computed(() => {
  if (!props.nginxStatus?.installed) return 'danger'
  if (!props.nginxStatus?.running) return 'warning'
  return 'success'
})

const nginxTagText = computed(() => {
  if (!props.nginxStatus?.installed) return '缺失'
  if (!props.nginxStatus?.running) return '警告'
  return '正常'
})

const nginxIconClass = computed(() => {
  if (!props.nginxStatus?.installed) return 'status-icon--danger'
  if (!props.nginxStatus?.running) return 'status-icon--warning'
  return 'status-icon--success'
})
</script>

<style scoped>
.vite-status-card {
  padding: var(--md3-space-md);
  background: var(--md3-glass-bg);
  backdrop-filter: var(--md3-glass-blur);
  -webkit-backdrop-filter: var(--md3-glass-blur);
  border: 1px solid var(--md3-glass-border);
  border-radius: var(--md3-shape-md);
  transition: box-shadow var(--md3-motion-duration-medium) var(--md3-motion-easing-standard);
}

.vite-status-card:hover {
  box-shadow: var(--md3-elevation-level1);
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

.status-list {
  display: flex;
  flex-direction: column;
  gap: var(--md3-space-sm);
}

.status-row {
  display: flex;
  align-items: center;
  gap: var(--md3-space-sm);
  padding: var(--md3-space-sm) var(--md3-space-md);
  background: var(--md3-surface-container-low);
  border-radius: var(--md3-shape-sm);
}

.status-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  flex-shrink: 0;
}

.status-icon :deep(svg) {
  width: 20px;
  height: 20px;
}

.status-icon--success {
  color: var(--md3-success);
}

.status-icon--warning {
  color: var(--md3-warning);
}

.status-icon--danger {
  color: var(--md3-error);
}

.status-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.status-label {
  font-size: 13px;
  font-weight: 500;
  color: var(--md3-on-surface);
}

.status-value {
  font-size: 12px;
  color: var(--md3-on-surface-variant);
}
</style>
