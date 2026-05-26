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
      <el-table-column label="操作" width="200" fixed="right">
        <template #default="{ row }">
          <el-button size="small" text @click="$emit('pull', row)">
            <el-icon><Download /></el-icon>
          </el-button>
          <el-button size="small" text @click="$emit('build', row)">
            <el-icon><Refresh /></el-icon>
          </el-button>
          <el-popconfirm title="确认删除镜像?" @confirm="$emit('delete', row)">
            <template #reference>
              <el-button size="small" text type="danger" :disabled="row.in_use">
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
.image-name {
  display: flex;
  align-items: center;
  gap: 6px;
}

.image-id {
  font-family: 'Consolas', monospace;
  font-size: 12px;
  background: #f5f7fa;
  padding: 1px 4px;
  border-radius: 2px;
}
</style>
