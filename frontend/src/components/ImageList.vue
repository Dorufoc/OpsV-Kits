<template>
  <div class="image-list">
    <div class="file-table-wrapper">
      <table class="md3-table md3-table--stripe md3-table--hover">
        <thead>
          <tr>
            <th class="md3-table-cell md3-table-header" style="min-width: 240px">镜像名称</th>
            <th class="md3-table-cell md3-table-header" style="width: 100px">ID</th>
            <th class="md3-table-cell md3-table-header" style="width: 100px; text-align: right">大小</th>
            <th class="md3-table-cell md3-table-header" style="width: 160px">创建时间</th>
            <th class="md3-table-cell md3-table-header" style="width: 80px; text-align: center">使用</th>
            <th class="md3-table-cell md3-table-header" style="width: 300px; text-align: right">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(row, idx) in images" :key="idx" class="md3-table-row">
            <td class="md3-table-cell md3-table-body">
              <div class="image-name">
                <Md3Icon name="coin" size="16" class="icon-inline" />
                <span>{{ row.repository || '<none>' }}:{{ row.tag || '<none>' }}</span>
              </div>
            </td>
            <td class="md3-table-cell md3-table-body">
              <code class="image-id">{{ row.id.substring(0, 12) }}</code>
            </td>
            <td class="md3-table-cell md3-table-body" style="text-align: right">{{ row.size }}</td>
            <td class="md3-table-cell md3-table-body">{{ row.created }}</td>
            <td class="md3-table-cell md3-table-body" style="text-align: center">
              <Md3Tag v-if="row.in_use" variant="success">使用中</Md3Tag>
              <Md3Tag v-else variant="info">未使用</Md3Tag>
            </td>
            <td class="md3-table-cell md3-table-body" style="text-align: right">
              <div class="action-buttons">
                <Md3Button size="sm" @click="$emit('pull', row)">
                  <Md3Icon name="download" size="14" />拉取
                </Md3Button>
                <Md3Button size="sm" @click="$emit('build', row)">
                  <Md3Icon name="refresh" size="14" />构建
                </Md3Button>
                <Md3Button size="sm" variant="danger" :disabled="row.in_use" @click="confirmDelete(row)">
                  <Md3Icon name="delete" size="14" />删除
                </Md3Button>
              </div>
            </td>
          </tr>
          <tr v-if="images.length === 0">
            <td colspan="6" class="md3-table-empty">暂无镜像</td>
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
import type { DockerImage } from '@/stores/dockerStore'

defineProps<{
  images: DockerImage[]
}>()

const emit = defineEmits<{
  pull: [item: DockerImage]
  build: [item: DockerImage]
  delete: [item: DockerImage]
}>()

async function confirmDelete(row: DockerImage) {
  const confirmed = await Md3Confirm.show({
    title: '确认删除镜像',
    message: '确认删除该镜像？此操作不可撤销。',
  })
  if (confirmed) {
    emit('delete', row)
  }
}
</script>

<style scoped>
.image-list {
  background: var(--md3-glass-bg);
  backdrop-filter: var(--md3-glass-blur);
  -webkit-backdrop-filter: var(--md3-glass-blur);
  border: 1px solid var(--md3-glass-border);
  border-radius: var(--md3-shape-sm);
  overflow: hidden;
  transition: box-shadow var(--md3-motion-duration-medium) var(--md3-motion-easing-standard);
}

.image-list:hover {
  box-shadow: var(--md3-elevation-level1);
}

.file-table-wrapper {
  overflow-x: auto;
}

.image-name {
  display: flex;
  align-items: center;
  gap: var(--md3-space-sm);
}

.icon-inline {
  width: 16px;
  height: 16px;
  color: var(--md3-on-surface-variant);
}

.action-buttons {
  display: inline-flex;
  align-items: center;
  gap: var(--md3-space-xs);
}

.image-id {
  font-family: var(--md3-font-mono);
  font-size: 12px;
  background: var(--md3-surface-container-low);
  padding: 1px 4px;
  border-radius: var(--md3-shape-xs);
}
</style>
