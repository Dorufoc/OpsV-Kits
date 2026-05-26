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
      <el-table-column label="操作" width="280" fixed="right">
        <template #default="{ row }">
          <el-button size="small" text @click="$emit('start', row)" :disabled="row.state === 'running'">
            <el-icon><VideoPlay /></el-icon>
          </el-button>
          <el-button size="small" text @click="$emit('stop', row)" :disabled="row.state !== 'running'">
            <el-icon><VideoPause /></el-icon>
          </el-button>
          <el-button size="small" text @click="$emit('restart', row)">
            <el-icon><Refresh /></el-icon>
          </el-button>
          <el-button size="small" text @click="$emit('logs', row)">
            <el-icon><Tickets /></el-icon>
          </el-button>
          <el-button size="small" text @click="$emit('terminal', row)" :disabled="row.state !== 'running'">
            <el-icon><Monitor /></el-icon>
          </el-button>
          <el-popconfirm title="确认删除?" @confirm="$emit('delete', row)">
            <template #reference>
              <el-button size="small" text type="danger">
                <el-icon><Delete /></el-icon>
              </el-button>
            </template>
          </el-popconfirm>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup lang="ts">
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
.container-name {
  display: flex;
  align-items: center;
  gap: 6px;
}

.ports-text {
  font-family: 'Consolas', monospace;
  font-size: 12px;
}
</style>
