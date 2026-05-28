<template>
  <div class="build-panel">
    <div class="panel-section">
      <div class="panel-header">
        <span class="panel-title">编译状态</span>
        <Md3Tag :type="buildTagType" size="sm">{{ buildText }}</Md3Tag>
      </div>
    </div>
    <div class="panel-section">
      <div class="panel-header">
        <span class="panel-title">运行状态</span>
        <Md3Tag :type="runTagType" size="sm">{{ runText }}</Md3Tag>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Md3Tag } from '@/components/md3'
import type { BuildStatus, RunStatus } from '@/stores/buildStore'

const props = defineProps<{
  buildStatus: BuildStatus
  runStatus: RunStatus
}>()

type TagType = 'primary' | 'success' | 'warning' | 'danger' | 'info'

const buildTagType = computed((): TagType => {
  const map: Partial<Record<BuildStatus, TagType>> = {
    idle: 'info',
    building: 'warning',
    success: 'success',
    failed: 'danger',
  }
  return map[props.buildStatus] || 'info'
})

const buildText = computed(() => {
  const map: Record<string, string> = {
    idle: '待编译',
    building: '编译中',
    success: '成功',
    failed: '失败',
  }
  return map[props.buildStatus] || '未知'
})

const runTagType = computed((): TagType => {
  const map: Partial<Record<RunStatus, TagType>> = {
    idle: 'info',
    running: 'success',
    stopped: 'warning',
  }
  return map[props.runStatus] || 'info'
})

const runText = computed(() => {
  const map: Record<string, string> = {
    idle: '未运行',
    running: '运行中',
    stopped: '已停止',
  }
  return map[props.runStatus] || '未知'
})
</script>

<style scoped>
.build-panel {
  display: flex;
  flex-direction: column;
  gap: var(--md3-space-md);
}

.panel-section {
  padding: var(--md3-space-md);
  background: var(--md3-glass-bg);
  backdrop-filter: var(--md3-glass-blur);
  -webkit-backdrop-filter: var(--md3-glass-blur);
  border: 1px solid var(--md3-glass-border);
  border-radius: var(--md3-shape-sm);
  transition: box-shadow var(--md3-motion-duration-medium) var(--md3-motion-easing-standard);
}

.panel-section:hover {
  box-shadow: var(--md3-elevation-level1);
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--md3-space-sm);
}

.panel-title {
  font-weight: 600;
  font-size: 14px;
  color: var(--md3-on-surface);
}
</style>
