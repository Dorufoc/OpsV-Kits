<template>
  <div class="file-browser">
    <div class="browser-toolbar">
      <Md3Button size="sm" :disabled="!canGoBack" @click="$emit('navigate', parentPath)" :icon="BackIcon">上级</Md3Button>
      <nav class="path-breadcrumb" aria-label="Breadcrumb">
        <ol class="breadcrumb-list">
          <li v-for="(seg, index) in pathSegments" :key="index" class="breadcrumb-item">
            <span
              v-if="index < pathSegments.length - 1"
              class="breadcrumb-link"
              @click="navigateToSegment(index)"
            >{{ seg.name }}</span>
            <span v-else class="breadcrumb-current">{{ seg.name }}</span>
            <span v-if="index < pathSegments.length - 1" class="breadcrumb-separator">/</span>
          </li>
        </ol>
      </nav>
    </div>

    <div class="browser-actions">
      <div class="dropdown-wrapper" v-if="showCreate">
        <Md3Button size="sm" variant="primary" :icon="PlusIcon" @click="toggleDropdown">新建</Md3Button>
        <div v-if="dropdownOpen" class="dropdown-menu" @click.stop>
          <button class="dropdown-item" @click="handleMkdir">文件夹</button>
          <button class="dropdown-item" @click="handleCreateFile">文件</button>
        </div>
      </div>
      <Md3Button size="sm" @click="$emit('upload')" :icon="UploadIcon" v-if="showUpload">上传</Md3Button>
      <Md3Input
        v-model="searchQuery"
        placeholder="搜索文件..."
        type="search"
        class="search-input"
        @update:modelValue="onSearch"
      >
        <template #prefix>
          <Md3Icon name="magnify" size="16" class="icon-inline" />
        </template>
      </Md3Input>
    </div>

    <div class="file-table-wrapper">
      <table class="md3-table md3-table--stripe md3-table--hover">
        <thead>
          <tr>
            <th class="md3-table-cell md3-table-header perm-select-cell">
              <Md3Checkbox
                :model-value="isAllSelected"
                :indeterminate="isIndeterminate"
                @update:model-value="toggleSelectAll"
              />
            </th>
            <th class="md3-table-cell md3-table-header" style="min-width: 220px">名称</th>
            <th class="md3-table-cell md3-table-header" style="width: 100px; text-align: right">大小</th>
            <th class="md3-table-cell md3-table-header" style="width: 120px">权限</th>
            <th class="md3-table-cell md3-table-header" style="width: 120px">所有者</th>
            <th class="md3-table-cell md3-table-header" style="width: 160px">修改时间</th>
            <th class="md3-table-cell md3-table-header" style="width: 300px; text-align: right">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="(row, idx) in filteredItems"
            :key="idx"
            class="md3-table-row"
            :class="{ 'md3-table-row--selected': isRowSelected(row) }"
            @click="onRowClick(row)"
            @dblclick="onRowDblClick(row)"
          >
            <td class="md3-table-cell md3-table-body perm-select-cell" @click.stop>
              <Md3Checkbox
                :model-value="selectedPaths || []"
                :value="row.path"
                @update:model-value="emit('update:selectedPaths', $event as string[])"
              />
            </td>
            <td class="md3-table-cell md3-table-body">
              <div class="file-name">
                <Md3Icon v-if="row.is_dir" name="folder-open" size="18" class="folder-icon" />
                <Md3Icon v-else name="text-box" size="18" class="file-icon" />
                <span>{{ row.name }}</span>
              </div>
            </td>
            <td class="md3-table-cell md3-table-body" style="text-align: right">
              <span v-if="row.is_dir">-</span>
              <span v-else>{{ formatSize(row.size) }}</span>
            </td>
            <td class="md3-table-cell md3-table-body">
              <span class="perm-badge">{{ row.permission }}</span>
            </td>
            <td class="md3-table-cell md3-table-body">{{ row.owner }}</td>
            <td class="md3-table-cell md3-table-body">{{ row.modified }}</td>
            <td class="md3-table-cell md3-table-body" style="text-align: right">
              <div class="action-buttons">
                <Md3Button :icon="DownloadIcon" size="sm" @click.stop="$emit('download', row)">下载</Md3Button>
                <Md3Button :icon="EditIcon" size="sm" @click.stop="$emit('rename', row)">重命名</Md3Button>
                <Md3Button :icon="CopyIcon" size="sm" @click.stop="$emit('copy', row)">复制</Md3Button>
                <Md3Button :icon="LockIcon" size="sm" @click.stop="$emit('chmod', row)">权限</Md3Button>
                <Md3Button :icon="DeleteIcon" size="sm" variant="danger" @click.stop="confirmDelete(row)">删除</Md3Button>
              </div>
            </td>
          </tr>
          <tr v-if="filteredItems.length === 0">
            <td colspan="7" class="md3-table-empty">暂无文件</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div class="browser-status">
      <span>{{ filteredItems.length }} 项</span>
      <span v-if="(selectedPaths || []).length > 0" class="selected-info">
        已选择 {{ (selectedPaths || []).length }} 项
      </span>
    </div>
  </div>
</template>

<script setup lang="ts">
import Md3Button from '@/components/Md3Button.vue'
import Md3Input from '@/components/md3/Md3Input.vue'
import Md3Checkbox from '@/components/md3/Md3Checkbox.vue'
import { Md3Confirm, Md3Icon } from '@/components/md3'
import { computed, ref, onMounted, onUnmounted, defineComponent, h } from 'vue'

// Icon wrappers for Md3Button compatibility
const BackIcon = defineComponent(() => () => h(Md3Icon, { name: 'arrow-left' }))
const PlusIcon = defineComponent(() => () => h(Md3Icon, { name: 'plus' }))
const UploadIcon = defineComponent(() => () => h(Md3Icon, { name: 'upload' }))
const DownloadIcon = defineComponent(() => () => h(Md3Icon, { name: 'download' }))
const EditIcon = defineComponent(() => () => h(Md3Icon, { name: 'pencil' }))
const CopyIcon = defineComponent(() => () => h(Md3Icon, { name: 'content-copy' }))
const DeleteIcon = defineComponent(() => () => h(Md3Icon, { name: 'delete' }))
const LockIcon = defineComponent(() => () => h(Md3Icon, { name: 'lock' }))

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
  selectedPaths?: string[]
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
  chmod: [item: FileItem]
  search: [query: string]
  rowClick: [item: FileItem]
  rowDblClick: [item: FileItem]
  'update:selectedPaths': [paths: string[]]
}>()

const searchQuery = ref('')
const selectedItem = ref<FileItem | null>(null)
const dropdownOpen = ref(false)

const isAllSelected = computed(() => {
  if (filteredItems.value.length === 0) return false
  return filteredItems.value.every((item) => props.selectedPaths?.includes(item.path))
})

const isIndeterminate = computed(() => {
  if (!props.selectedPaths?.length) return false
  const selectedInView = filteredItems.value.filter((item) =>
    props.selectedPaths?.includes(item.path)
  ).length
  return selectedInView > 0 && selectedInView < filteredItems.value.length
})

function toggleSelectAll() {
  if (isAllSelected.value) {
    const viewPaths = new Set(filteredItems.value.map((i) => i.path))
    emit(
      'update:selectedPaths',
      (props.selectedPaths || []).filter((p) => !viewPaths.has(p))
    )
  } else {
    const existing = new Set(props.selectedPaths || [])
    filteredItems.value.forEach((i) => existing.add(i.path))
    emit('update:selectedPaths', Array.from(existing))
  }
}

function isRowSelected(row: FileItem): boolean {
  return props.selectedPaths?.includes(row.path) || false
}

function toggleDropdown() {
  dropdownOpen.value = !dropdownOpen.value
}

function closeDropdown() {
  dropdownOpen.value = false
}

function handleMkdir() {
  closeDropdown()
  emit('mkdir')
}

function handleCreateFile() {
  closeDropdown()
  emit('createFile')
}

onMounted(() => {
  document.addEventListener('click', closeDropdown)
})

onUnmounted(() => {
  document.removeEventListener('click', closeDropdown)
})

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

function onSearch(value: string | number) {
  emit('search', String(value))
}

async function confirmDelete(row: FileItem) {
  const confirmed = await Md3Confirm.show({
    title: '确认删除',
    message: `确认删除 "${row.name}"?`,
  })
  if (confirmed) {
    emit('delete', row)
  }
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
  gap: var(--md3-space-sm);
  background: var(--md3-glass-bg);
  backdrop-filter: var(--md3-glass-blur);
  -webkit-backdrop-filter: var(--md3-glass-blur);
  border: 1px solid var(--md3-glass-border);
  border-radius: var(--md3-shape-sm);
  padding: var(--md3-space-md);
  transition: box-shadow var(--md3-motion-duration-medium) var(--md3-motion-easing-standard);
}

.file-browser:hover {
  box-shadow: var(--md3-elevation-level1);
}

.browser-toolbar {
  display: flex;
  align-items: center;
  gap: var(--md3-space-md);
}

.path-breadcrumb {
  flex: 1;
}

.breadcrumb-list {
  display: flex;
  align-items: center;
  gap: var(--md3-space-xs);
  list-style: none;
  margin: 0;
  padding: 0;
}

.breadcrumb-item {
  display: inline-flex;
  align-items: center;
  gap: var(--md3-space-xs);
}

.breadcrumb-link {
  color: var(--md3-primary);
  cursor: pointer;
  transition: opacity var(--md3-motion-duration-short) var(--md3-motion-easing-standard);
}

.breadcrumb-link:hover {
  opacity: 0.8;
  text-decoration: underline;
}

.breadcrumb-current {
  color: var(--md3-on-surface);
  font-weight: 500;
}

.breadcrumb-separator {
  color: var(--md3-on-surface-variant);
  opacity: 0.5;
}

.browser-actions {
  display: flex;
  align-items: center;
  gap: var(--md3-space-sm);
}

.dropdown-wrapper {
  position: relative;
}

.dropdown-menu {
  position: absolute;
  top: calc(100% + var(--md3-space-xs));
  left: 0;
  min-width: 160px;
  padding: var(--md3-space-xs) 0;
  background: var(--md3-surface-container);
  border: 1px solid var(--md3-outline-variant);
  border-radius: var(--md3-shape-sm);
  box-shadow: var(--md3-elevation-level2);
  z-index: 1000;
  animation: dropdown-enter 0.15s var(--md3-motion-easing-standard);
}

@keyframes dropdown-enter {
  from {
    opacity: 0;
    transform: translateY(-4px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.dropdown-item {
  width: 100%;
  display: flex;
  align-items: center;
  padding: var(--md3-space-sm) var(--md3-space-md);
  border: none;
  background: transparent;
  color: var(--md3-on-surface);
  font-size: 14px;
  text-align: left;
  cursor: pointer;
  transition: background var(--md3-motion-duration-short) var(--md3-motion-easing-standard);
}

.dropdown-item:hover {
  background: var(--md3-on-surface-variant-transparent);
}

.dropdown-item:active {
  background: var(--md3-state-layer-active);
}

.icon-inline {
  width: 16px;
  height: 16px;
  color: var(--md3-on-surface-variant);
}

.search-input {
  width: 200px;
  margin-left: auto;
}

.file-table-wrapper {
  overflow-x: auto;
}

.file-name {
  display: flex;
  align-items: center;
  gap: var(--md3-space-sm);
}

.folder-icon {
  width: 18px;
  height: 18px;
  color: var(--md3-warning);
  flex-shrink: 0;
}

.file-icon {
  width: 18px;
  height: 18px;
  color: var(--md3-on-surface-variant);
  flex-shrink: 0;
}

.action-buttons {
  display: inline-flex;
  align-items: center;
  gap: var(--md3-space-xs);
}

.perm-select-cell {
  width: 44px;
  padding-left: var(--md3-space-sm) !important;
}

.perm-badge {
  font-family: var(--md3-font-mono);
  font-size: 0.75rem;
  letter-spacing: 0.5px;
  color: var(--md3-primary);
  background: var(--md3-primary-container);
  padding: 2px 8px;
  border-radius: var(--md3-shape-xs);
}
</style>
