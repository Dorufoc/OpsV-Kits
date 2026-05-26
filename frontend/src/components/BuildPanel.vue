<template>
  <div class="build-panel">
    <div class="panel-section">
      <div class="panel-header">
        <span class="panel-title">编译状态</span>
        <el-tag :type="buildTagType" size="small">{{ buildText }}</el-tag>
      </div>
    </div>
    <div class="panel-section">
      <div class="panel-header">
        <span class="panel-title">运行状态</span>
        <el-tag :type="runTagType" size="small">{{ runText }}</el-tag>
      </div>
    </div>
    <div class="panel-section task-logs" v-if="logs.length > 0">
      <div class="panel-header">
        <span class="panel-title">运行日志</span>
      </div>
      <div class="logs-container" ref="logContainer">
        <div
          v-for="(log, index) in logs"
          :key="index"
          class="log-entry"
          :class="log.level.toLowerCase()"
        >
          <span class="log-time">{{ log.timestamp }}</span>
          <span class="log-level">[{{ log.level }}]</span>
          <span class="log-msg">{{ log.message }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch, nextTick } from 'vue'
import type { BuildStatus, RunStatus, BuildLog } from '@/stores/buildStore'

const props = defineProps<{
  buildStatus: BuildStatus
  runStatus: RunStatus
  logs: BuildLog[]
}>()

const logContainer = ref<HTMLElement>()

const buildTagType = computed(() => {
  const map: Record<string, string> = {
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

const runTagType = computed(() => {
  const map: Record<string, string> = {
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

watch(() => props.logs.length, async () => {
  await nextTick()
  if (logContainer.value) {
    logContainer.value.scrollTop = logContainer.value.scrollHeight
  }
})
</script>

<style scoped>
.build-panel {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.panel-section {
  padding: 12px;
  background: #f8f9fa;
  border-radius: 6px;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.panel-title {
  font-weight: 600;
  font-size: 14px;
}

.task-logs {
  flex: 1;
}

.logs-container {
  max-height: 200px;
  overflow-y: auto;
  background: #1e1e1e;
  color: #d4d4d4;
  padding: 8px;
  border-radius: 4px;
  font-family: 'Cascadia Code', 'Fira Code', 'Consolas', monospace;
  font-size: 12px;
  line-height: 1.6;
}

.log-entry {
  display: flex;
  gap: 8px;
  white-space: nowrap;
}

.log-entry.info {
  color: #d4d4d4;
}

.log-entry.warn {
  color: #ce9178;
}

.log-entry.error {
  color: #f44747;
}

.log-time {
  color: #6a9955;
  flex-shrink: 0;
}

.log-level {
  flex-shrink: 0;
  min-width: 48px;
}

.log-msg {
  overflow: hidden;
  text-overflow: ellipsis;
}
</style>
