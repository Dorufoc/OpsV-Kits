<template>
  <div class="container-list">
    <div class="file-table-wrapper">
      <table class="md3-table md3-table--stripe md3-table--hover">
        <thead>
          <tr>
            <th class="md3-table-cell md3-table-header" style="width: 40px; text-align: center">
              <input type="checkbox" :checked="isAllSelected" @change="toggleSelectAll" />
            </th>
            <th class="md3-table-cell md3-table-header" style="min-width: 160px">名称</th>
            <th class="md3-table-cell md3-table-header" style="min-width: 160px">镜像</th>
            <th class="md3-table-cell md3-table-header" style="min-width: 140px">状态</th>
            <th class="md3-table-cell md3-table-header" style="min-width: 160px">端口</th>
            <th class="md3-table-cell md3-table-header" style="width: 160px">创建时间</th>
            <th class="md3-table-cell md3-table-header" style="width: 420px; text-align: right">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(row, idx) in containers" :key="idx" class="md3-table-row">
            <td class="md3-table-cell md3-table-body" style="text-align: center">
              <input type="checkbox" :checked="isSelected(row)" @change="toggleRow(row)" />
            </td>
            <td class="md3-table-cell md3-table-body">
              <div class="container-name">
                <Md3Tag :variant="stateTagVariant(row.state)">{{ row.state }}</Md3Tag>
                <span>{{ row.name }}</span>
              </div>
            </td>
            <td class="md3-table-cell md3-table-body">{{ row.image }}</td>
            <td class="md3-table-cell md3-table-body">
              <span :style="{ color: row.state === 'running' ? 'var(--md3-success)' : 'var(--md3-on-surface-variant)' }">
                {{ row.status }}
              </span>
            </td>
            <td class="md3-table-cell md3-table-body">
              <span class="ports-text">{{ row.ports || '-' }}</span>
            </td>
            <td class="md3-table-cell md3-table-body">{{ row.created }}</td>
            <td class="md3-table-cell md3-table-body" style="text-align: right">
              <div class="action-buttons">
                <Md3Button size="sm" @click="$emit('start', row)" :disabled="row.state === 'running'">
                  <Md3Icon name="play" size="14" />启动
                </Md3Button>
                <Md3Button size="sm" @click="$emit('stop', row)" :disabled="row.state !== 'running'">
                  <Md3Icon name="pause" size="14" />停止
                </Md3Button>
                <Md3Button size="sm" @click="$emit('restart', row)">
                  <Md3Icon name="refresh" size="14" />重启
                </Md3Button>
                <Md3Button size="sm" @click="$emit('logs', row)">
                  <Md3Icon name="tag" size="14" />日志
                </Md3Button>
                <Md3Button size="sm" @click="$emit('terminal', row)" :disabled="row.state !== 'running'">
                  <Md3Icon name="monitor" size="14" />终端
                </Md3Button>
                <Md3Button size="sm" variant="danger" @click="confirmDelete(row)">
                  <Md3Icon name="delete" size="14" />删除
                </Md3Button>
              </div>
            </td>
          </tr>
          <tr v-if="containers.length === 0">
            <td colspan="7" class="md3-table-empty">暂无容器</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup lang="ts">
import Md3Button from '@/components/Md3Button.vue'
import Md3Tag from '@/components/md3/Md3Tag.vue'
import { Md3Confirm, Md3Icon } from '@/components/md3'
import type { DockerContainer } from '@/stores/dockerStore'
import { ref, computed } from 'vue'

const props = defineProps<{
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

const selectedRows = ref<DockerContainer[]>([])

function stateTagVariant(state: string) {
  const map: Record<string, 'success' | 'info' | 'warning' | 'primary'> = {
    running: 'success',
    exited: 'info',
    paused: 'warning',
    created: 'primary',
  }
  return map[state] || 'info'
}

function isSelected(row: DockerContainer): boolean {
  return selectedRows.value.includes(row)
}

const isAllSelected = computed(() => {
  return props.containers.length > 0 && selectedRows.value.length === props.containers.length
})

function toggleRow(row: DockerContainer) {
  const idx = selectedRows.value.indexOf(row)
  if (idx === -1) {
    selectedRows.value.push(row)
  } else {
    selectedRows.value.splice(idx, 1)
  }
  emit('selectionChange', selectedRows.value)
}

function toggleSelectAll() {
  if (isAllSelected.value) {
    selectedRows.value = []
  } else {
    selectedRows.value = [...props.containers]
  }
  emit('selectionChange', selectedRows.value)
}

async function confirmDelete(row: DockerContainer) {
  const confirmed = await Md3Confirm.show({
    title: '确认删除',
    message: `确认删除容器 "${row.name}"?`,
  })
  if (confirmed) {
    emit('delete', row)
  }
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

.file-table-wrapper {
  overflow-x: auto;
}

.container-name {
  display: flex;
  align-items: center;
  gap: var(--md3-space-sm);
}

.action-buttons {
  display: inline-flex;
  align-items: center;
  gap: var(--md3-space-xs);
}

.ports-text {
  font-family: var(--md3-font-mono);
  font-size: 12px;
}
</style>
