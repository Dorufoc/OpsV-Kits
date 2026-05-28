<template>
  <div class="container-list">
    <el-table :data="containers" style="width: 100%" size="small" stripe @selection-change="onSelectionChange">
      <el-table-column type="selection" width="40" />
      <el-table-column label="名称" min-width="160">
        <template #default="{ row }">
          <div class="container-name">
            <el-tag :type="stateTagType(row.state)" size="small" round>{{ row.state }}</el-tag>
            <span>{{ row.name }}</span>
          </div>
        </template>
      </el-table-column>
      <el-table-column prop="image" label="镜像" min-width="160" />
      <el-table-column prop="status" label="状态" min-width="140">
        <template #default="{ row }">
          <span :style="{ color: row.state === 'running' ? '#67c23a' : '#909399' }">
            {{ row.status }}
          </span>
        </template>
      </el-table-column>
      <el-table-column prop="ports" label="端口" min-width="160">
        <template #default="{ row }">
          <span class="ports-text">{{ row.ports || '-' }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="created" label="创建时间" width="160" />
      <el-table-column label="操作" width="420" fixed="right">
        <template #default="{ row }">
          <Md3Button :icon="VideoPlay" size="sm" @click="$emit('start', row)" :disabled="row.state === 'running'">启动</Md3Button>
          <Md3Button :icon="VideoPause" size="sm" @click="$emit('stop', row)" :disabled="row.state !== 'running'">停止</Md3Button>
          <Md3Button :icon="Refresh" size="sm" @click="$emit('restart', row)">重启</Md3Button>
          <Md3Button :icon="Tickets" size="sm" @click="$emit('logs', row)">日志</Md3Button>
          <Md3Button :icon="Monitor" size="sm" @click="$emit('terminal', row)" :disabled="row.state !== 'running'">终端</Md3Button>
          <el-popconfirm title="确认删除?" @confirm="$emit('delete', row)">
            <template #reference>
              <Md3Button :icon="Delete" size="sm" variant="danger">删除</Md3Button>
            </template>
          </el-popconfirm>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup lang="ts">
import Md3Button from '@/components/Md3Button.vue'
import {
  VideoPlay, VideoPause, Refresh,
  Tickets, Monitor, Delete,
} from '@element-plus/icons-vue'
import type { DockerContainer } from '@/stores/dockerStore'

defineProps<{
  containers: DockerContainer[]
}>()

const emit = defineEmits<{
  start: [item: DockerContainer]
  stop: [item: DockerContainer]
  restart: [item: DockerContainer]
  logs: [item: DockerContainer]
  terminal: [item: DockerContainer]
  delete: [item: DockerContainer]
  selectionChange: [items: DockerContainer[]]
}>()

function stateTagType(state: string) {
  const map: Record<string, string> = {
    running: 'success',
    exited: 'info',
    paused: 'warning',
    created: 'primary',
  }
  return map[state] || 'info'
}

function onSelectionChange(selection: DockerContainer[]) {
  emit('selectionChange', selection)
}
</script>

<style scoped>
.container-list {
  background: var(--md3-glass-bg);
  backdrop-filter: var(--md3-glass-blur);
  -webkit-backdrop-filter: var(--md3-glass-blur);
  border: 1px solid var(--md3-glass-border);
  border-radius: var(--md3-shape-sm);
  overflow: hidden;
  transition: box-shadow var(--md3-motion-duration-medium) var(--md3-motion-easing-standard);
}

.container-list:hover {
  box-shadow: var(--md3-elevation-level1);
}

.container-name {
  display: flex;
  align-items: center;
  gap: var(--md3-space-sm);
}

.ports-text {
  font-family: var(--md3-font-mono);
  font-size: 12px;
}
</style>
