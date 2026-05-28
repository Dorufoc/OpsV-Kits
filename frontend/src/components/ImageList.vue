<template>
  <div class="image-list">
    <el-table :data="images" style="width: 100%" size="small" stripe>
      <el-table-column label="镜像名称" min-width="240">
        <template #default="{ row }">
          <div class="image-name">
            <el-icon :size="16"><Coin /></el-icon>
            <span>{{ row.repository || '<none>' }}:{{ row.tag || '<none>' }}</span>
          </div>
        </template>
      </el-table-column>
      <el-table-column prop="id" label="ID" width="100">
        <template #default="{ row }">
          <code class="image-id">{{ row.id.substring(0, 12) }}</code>
        </template>
      </el-table-column>
      <el-table-column prop="size" label="大小" width="100" align="right" />
      <el-table-column prop="created" label="创建时间" width="160" />
      <el-table-column label="使用" width="80" align="center">
        <template #default="{ row }">
          <el-tag v-if="row.in_use" type="success" size="small">使用中</el-tag>
          <el-tag v-else type="info" size="small">未使用</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="300" fixed="right">
        <template #default="{ row }">
          <Md3Button :icon="Download" size="sm" @click="$emit('pull', row)">拉取</Md3Button>
          <Md3Button :icon="Refresh" size="sm" @click="$emit('build', row)">构建</Md3Button>
          <el-popconfirm title="确认删除镜像?" @confirm="$emit('delete', row)">
            <template #reference>
              <Md3Button :icon="Delete" size="sm" variant="danger" :disabled="row.in_use">删除</Md3Button>
            </template>
          </el-popconfirm>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup lang="ts">
import Md3Button from '@/components/Md3Button.vue'
import { Coin, Download, Refresh, Delete } from '@element-plus/icons-vue'
import type { DockerImage } from '@/stores/dockerStore'

defineProps<{
  images: DockerImage[]
}>()

defineEmits<{
  pull: [item: DockerImage]
  build: [item: DockerImage]
  delete: [item: DockerImage]
}>()
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

.image-name {
  display: flex;
  align-items: center;
  gap: var(--md3-space-sm);
}

.image-id {
  font-family: var(--md3-font-mono);
  font-size: 12px;
  background: var(--md3-surface-container-low);
  padding: 1px 4px;
  border-radius: var(--md3-shape-xs);
}
</style>
