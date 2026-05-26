<template>
  <div class="file-browser">
    <div class="browser-toolbar">
      <el-button size="small" :disabled="!canGoBack" @click="$emit('navigate', parentPath)">
        <el-icon><Back /></el-icon> 上级
      </el-button>
      <el-breadcrumb class="path-breadcrumb" separator="/">
        <el-breadcrumb-item
          v-for="(seg, index) in pathSegments"
          :key="index"
          :to="index < pathSegments.length - 1 ? '' : undefined"
        >
          <span
            v-if="index < pathSegments.length - 1"
            class="breadcrumb-link"
            @click="navigateToSegment(index)"
          >{{ seg.name }}</span>
          <span v-else>{{ seg.name }}</span>
        </el-breadcrumb-item>
      </el-breadcrumb>
    </div>

    <div class="browser-actions">
      <el-dropdown trigger="click" v-if="showCreate">
        <el-button size="small" type="primary">
          <el-icon><Plus /></el-icon> 新建
        </el-button>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item @click="$emit('mkdir')">文件夹</el-dropdown-item>
            <el-dropdown-item @click="$emit('createFile')">文件</el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
      <el-button size="small" @click="$emit('upload')" v-if="showUpload">
        <el-icon><Upload /></el-icon> 上传
      </el-button>
      <el-input
        v-model="searchQuery"
        placeholder="搜索文件..."
        size="small"
        clearable
        class="search-input"
        @input="onSearch"
      >
        <template #prefix>
          <el-icon><Search /></el-icon>
        </template>
      </el-input>
    </div>

    <el-table
      :data="filteredItems"
      style="width: 100%"
      size="small"
      stripe
      highlight-current-row
      @row-click="onRowClick"
      @row-dblclick="onRowDblClick"
    >
      <el-table-column label="名称" min-width="240">
        <template #default="{ row }">
          <div class="file-name">
            <el-icon v-if="row.is_dir" class="folder-icon"><FolderOpened /></el-icon>
            <el-icon v-else class="file-icon"><Document /></el-icon>
            <span>{{ row.name }}</span>
          </div>
        </template>
      </el-table-column>
      <el-table-column prop="size" label="大小" width="100" align="right">
        <template #default="{ row }">
          <span v-if="row.is_dir">-</span>
          <span v-else>{{ formatSize(row.size) }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="permission" label="权限" width="120" />
      <el-table-column prop="owner" label="所有者" width="120" />
      <el-table-column prop="modified" label="修改时间" width="160" />
      <el-table-column label="操作" width="200" fixed="right">
        <template #default="{ row }">
          <el-button size="small" text @click.stop="$emit('download', row)">
            <el-icon><Download /></el-icon>
          </el-button>
          <el-button size="small" text @click.stop="$emit('rename', row)">
            <el-icon><Edit /></el-icon>
          </el-button>
          <el-button size="small" text @click.stop="$emit('copy', row)">
            <el-icon><CopyDocument /></el-icon>
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

    <div class="browser-status">
      <span>{{ filteredItems.length }} 项</span>
      <span v-if="selectedItem" class="selected-info">
        已选择: {{ selectedItem.name }}
      </span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import {
  Back, Plus, Upload, Search,
  FolderOpened, Document,
  Download, Edit, CopyDocument, Delete,
} from '@element-plus/icons-vue'

export interface FileItem {
  name: string
  path: string
  is_dir: boolean
  size: number
  permission: string
  owner: string
  group: string
  modified: string
}

const props = defineProps<{
  currentPath: string
  items: FileItem[]
  showCreate?: boolean
  showUpload?: boolean
}>()

const emit = defineEmits<{
  navigate: [path: string]
  mkdir: []
  createFile: []
  upload: []
  download: [item: FileItem]
  rename: [item: FileItem]
  copy: [item: FileItem]
  delete: [item: FileItem]
  search: [query: string]
  rowClick: [item: FileItem]
  rowDblClick: [item: FileItem]
}>()

const searchQuery = ref('')
const selectedItem = ref<FileItem | null>(null)

const pathSegments = computed(() => {
  const parts = props.currentPath.replace(/\\/g, '/').split('/').filter(Boolean)
  let accumulated = ''
  return parts.map(seg => {
    accumulated += '/' + seg
    return { name: seg, fullPath: accumulated }
  })
})

const parentPath = computed(() => {
  const parts = props.currentPath.replace(/\\/g, '/').split('/').filter(Boolean)
  parts.pop()
  return '/' + parts.join('/')
})

const canGoBack = computed(() => {
  return props.currentPath !== '/' && props.currentPath !== ''
})

const filteredItems = computed(() => {
  if (!searchQuery.value) return props.items
  const q = searchQuery.value.toLowerCase()
  return props.items.filter(item => item.name.toLowerCase().includes(q))
})

function navigateToSegment(index: number) {
  const seg = pathSegments.value[index]
  if (seg) {
    emit('navigate', seg.fullPath)
  }
}

function onRowClick(row: FileItem) {
  selectedItem.value = row
  emit('rowClick', row)
}

function onRowDblClick(row: FileItem) {
  selectedItem.value = row
  emit('rowDblClick', row)
  if (row.is_dir) {
    emit('navigate', row.path)
  }
}

function onSearch(query: string) {
  emit('search', query)
}

function formatSize(bytes: number): string {
  if (bytes === 0) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  const k = 1024
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + units[i]
}
</script>

<style scoped>
.file-browser {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.browser-toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
}

.path-breadcrumb {
  flex: 1;
}

.breadcrumb-link {
  color: #409eff;
  cursor: pointer;
}

.breadcrumb-link:hover {
  text-decoration: underline;
}

.browser-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.search-input {
  width: 200px;
  margin-left: auto;
}

.file-name {
  display: flex;
  align-items: center;
  gap: 6px;
}

.folder-icon {
  color: #e6a23c;
}

.file-icon {
  color: #909399;
}

.browser-status {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: #909399;
}

.selected-info {
  color: #409eff;
}
</style>
