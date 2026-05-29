<template>
  <div class="file-manager-page">
    <Md3PageHeader title="远程文件管理" />
    <Md3Divider />

    <div class="file-manager-layout">
      <div class="file-sidebar">
        <div class="sidebar-section">
          <div class="sidebar-label">SSH 账户</div>
          <nav class="account-menu">
            <div
              v-for="acc in sshAccounts"
              :key="acc.alias"
              :class="['account-item', { active: selectedAccount === acc.alias }]"
              @click="switchAccount(acc)"
            >
              <Md3Icon name="account" class="icon-sidebar" />
              <span>{{ acc.alias }}</span>
            </div>
          </nav>
          <Md3Button size="sm" class="add-account-btn" @click="goToSshAccounts"><Md3Icon name="plus" size="sm" />添加</Md3Button>
        </div>
        <div class="sidebar-section">
          <div class="sidebar-label">快速导航</div>
          <div class="bookmark-list">
            <div
              v-for="bm in bookmarks"
              :key="bm.path"
              class="bookmark-item"
              @click="navigateTo(bm.path)"
            >
                <Md3Icon name="collection" class="icon-sidebar" />
              <span>{{ bm.label }}</span>
            </div>
          </div>
        </div>
      </div>

      <div class="file-main">
        <div v-if="selectedPaths.length > 0" class="batch-toolbar">
          <span class="batch-info">已选 {{ selectedPaths.length }} 项</span>
          <div class="batch-actions">
            <Md3Button size="sm" @click="showChmodDialog = true"><Md3Icon name="lock" size="sm" />批量修改权限</Md3Button>
            <Md3Button size="sm" variant="danger" @click="handleBatchDelete"><Md3Icon name="delete" size="sm" />批量删除</Md3Button>
            <Md3Button size="sm" @click="selectedPaths = []"><Md3Icon name="close" size="sm" />取消选择</Md3Button>
          </div>
        </div>
        <FileBrowser
          ref="fileBrowserRef"
          :current-path="currentPath"
          :items="fileItems"
          :selected-paths="selectedPaths"
          show-create
          show-upload
          @navigate="navigateTo"
          @mkdir="showMkdirDialog = true"
          @create-file="showCreateFileDialog = true"
          @upload="handleUpload"
          @download="handleDownload"
          @rename="handleRename"
          @copy="handleCopy"
          @delete="handleDelete"
          @chmod="openSingleChmod"
          @update:selected-paths="selectedPaths = $event"
        />
      </div>
    </div>

    <div class="quick-command-area">
      <Md3Divider />
      <div class="command-header">
        <span class="command-title">快速命令</span>
        <div class="command-actions">
          <Md3Button size="sm" @click="clearHistory">清空</Md3Button>
        </div>
      </div>
      <div class="command-input-row">
        <Md3Input
          v-model="quickCommand"
          placeholder="输入 Linux 命令（如：df -h）"
          @keyup.enter="executeCommand"
        />
        <Md3Button @click="executeCommand">执行</Md3Button>
      </div>
      <div class="command-output" ref="commandOutputRef">
        <div v-for="(entry, index) in commandHistory" :key="index" class="command-entry">
          <div class="command-prompt">$ {{ entry.command }}</div>
          <pre class="command-result">{{ entry.output }}</pre>
        </div>
      </div>
    </div>

    <Md3Dialog v-model:visible="showMkdirDialog" title="新建文件夹" width="400px">
      <Md3Input v-model="newDirName" placeholder="文件夹名称" />
      <template #footer>
        <Md3Button @click="showMkdirDialog = false">取消</Md3Button>
        <Md3Button variant="primary" @click="createDirectory">确定</Md3Button>
      </template>
    </Md3Dialog>

    <Md3Dialog v-model:visible="showCreateFileDialog" title="新建文件" width="400px">
      <Md3Input v-model="newFileName" placeholder="文件名（如：test.txt）" />
      <template #footer>
        <Md3Button @click="showCreateFileDialog = false">取消</Md3Button>
        <Md3Button variant="primary" @click="createFile">确定</Md3Button>
      </template>
    </Md3Dialog>

    <Md3Dialog v-model:visible="showChmodDialog" :title="chmodDialogTitle" width="420px">
      <PermissionEditor
        v-model="chmodMode"
        :show-recursive="chmodRecursiveItems.length > 0"
        v-model:recursive="chmodRecursive"
      />
      <template #footer>
        <Md3Button @click="showChmodDialog = false">取消</Md3Button>
        <Md3Button variant="primary" @click="applyChmod">应用</Md3Button>
      </template>
    </Md3Dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { 
  Md3PageHeader, 
  Md3Divider, 
  Md3Dialog, 
  Md3Input,
} from '@/components/md3'
import Md3Button from '@/components/Md3Button.vue'
import { Md3Icon, Md3Confirm } from '@/components/md3'
import { useRouter } from 'vue-router'
import { useSshAccountStore } from '@/stores/sshAccountStore'
import { request } from '@/api'
import FileBrowser, { type FileItem } from '@/components/FileBrowser.vue'
import PermissionEditor from '@/components/PermissionEditor.vue'

const router = useRouter()
const sshStore = useSshAccountStore()

const selectedAccount = ref('')
const currentPath = ref('/')
const fileItems = ref<FileItem[]>([])
const selectedPaths = ref<string[]>([])
const quickCommand = ref('')
const commandHistory = ref<Array<{ command: string; output: string }>>([])
const commandOutputRef = ref<HTMLElement>()
const fileBrowserRef = ref()

const showMkdirDialog = ref(false)
const showCreateFileDialog = ref(false)
const showChmodDialog = ref(false)
const newDirName = ref('')
const newFileName = ref('')

const chmodMode = ref(0o644)
const chmodRecursive = ref(false)
const chmodPaths = ref<string[]>([])
const chmodSingleItem = ref<FileItem | null>(null)

const sshAccounts = ref(sshStore.accounts)

const bookmarks = [
  { label: '/var/log', path: '/var/log' },
  { label: '/etc', path: '/etc' },
  { label: '/tmp', path: '/tmp' },
  { label: '/home', path: '/home' },
]

const chmodDialogTitle = computed(() => {
  if (chmodSingleItem.value) {
    return `修改权限: ${chmodSingleItem.value.name}`
  }
  return `批量修改权限 (${selectedPaths.value.length} 项)`
})

const chmodRecursiveItems = computed(() => {
  const paths = chmodPaths.value.length > 0 ? chmodPaths.value : selectedPaths.value
  return fileItems.value.filter((item) => paths.includes(item.path) && item.is_dir)
})

function openSingleChmod(item: FileItem) {
  chmodSingleItem.value = item
  chmodPaths.value = [item.path]
  const permStr = item.permission
  if (permStr && permStr.length >= 10) {
    let mode = 0
    if (permStr[1] !== '-') mode |= 0o400
    if (permStr[2] !== '-') mode |= 0o200
    if (permStr[3] !== '-') mode |= 0o100
    if (permStr[4] !== '-') mode |= 0o040
    if (permStr[5] !== '-') mode |= 0o020
    if (permStr[6] !== '-') mode |= 0o010
    if (permStr[7] !== '-') mode |= 0o004
    if (permStr[8] !== '-') mode |= 0o002
    if (permStr[9] !== '-') mode |= 0o001
    chmodMode.value = mode
  }
  chmodRecursive.value = false
  showChmodDialog.value = true
}

async function applyChmod() {
  const paths = chmodPaths.value.length > 0 ? chmodPaths.value : selectedPaths.value
  const mode = '0' + chmodMode.value.toString(8).padStart(3, '0')
  try {
    if (chmodSingleItem.value && paths.length === 1) {
      await request.post('/files/chmod', {
        path: paths[0],
        mode,
        alias: selectedAccount.value,
      })
    } else {
      await request.post('/files/batch/chmod', {
        paths,
        mode,
        recursive: chmodRecursive.value,
        alias: selectedAccount.value,
      })
    }
    showChmodDialog.value = false
    chmodSingleItem.value = null
    chmodPaths.value = []
    chmodRecursive.value = false
    selectedPaths.value = []
    loadDirectory(currentPath.value)
  } catch {
  }
}

async function handleBatchDelete() {
  const confirmed = await Md3Confirm.show({
    title: '确认批量删除',
    message: `确认删除选中的 ${selectedPaths.value.length} 项?`,
  })
  if (!confirmed) return
  try {
    await request.post('/files/batch/delete', {
      paths: selectedPaths.value,
      alias: selectedAccount.value,
    })
    selectedPaths.value = []
    loadDirectory(currentPath.value)
  } catch {
  }
}

function switchAccount(acc: any) {
  selectedAccount.value = acc.alias
  loadDirectory('/')
}

async function loadDirectory(path: string) {
  if (!selectedAccount.value) return
  currentPath.value = path
  try {
    const res = await request.get<any>('/files/list', {
      params: { path, alias: selectedAccount.value },
    })
    fileItems.value = res.entries || []
  } catch {
    fileItems.value = []
  }
}

function navigateTo(path: string) {
  loadDirectory(path)
}

function goToSshAccounts() {
  router.push('/ssh-accounts')
}

async function handleUpload() {
  const input = document.createElement('input')
  input.type = 'file'
  input.multiple = true
  input.onchange = async () => {
    if (!input.files) return
    const formData = new FormData()
    for (const file of Array.from(input.files)) {
      formData.append('files', file)
    }
    formData.append('path', currentPath.value)
    formData.append('alias', selectedAccount.value)
    try {
      await request.post('/files/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      loadDirectory(currentPath.value)
    } catch {
    }
  }
  input.click()
}

async function handleDownload(item: FileItem) {
  try {
    const blob = await request.get<Blob>(`/files/download`, {
      params: { path: item.path, alias: selectedAccount.value },
      responseType: 'blob',
    })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = item.name
    a.click()
    URL.revokeObjectURL(url)
  } catch {
  }
}

async function handleRename(item: FileItem) {
  const newName = prompt('新名称:', item.name)
  if (newName && newName !== item.name) {
    const parentPath = item.path.substring(0, item.path.lastIndexOf('/'))
    const dst = parentPath + '/' + newName
    try {
      await request.post('/files/rename', {
        src: item.path,
        dst: dst,
        alias: selectedAccount.value,
      })
      loadDirectory(currentPath.value)
    } catch {
    }
  }
}

async function handleCopy(item: FileItem) {
  const dest = prompt('目标路径:', item.path + '_copy')
  if (dest) {
    try {
      await request.post('/files/copy', {
        src: item.path,
        dst: dest,
        alias: selectedAccount.value,
      })
      loadDirectory(currentPath.value)
    } catch {
    }
  }
}

async function handleDelete(item: FileItem) {
  try {
    await request.post('/files/delete', {
      path: item.path,
      alias: selectedAccount.value,
    })
    loadDirectory(currentPath.value)
  } catch {
  }
}

async function createDirectory() {
  if (!newDirName.value) return
  try {
    await request.post('/files/mkdir', {
      path: currentPath.value + '/' + newDirName.value,
      alias: selectedAccount.value,
    })
    showMkdirDialog.value = false
    newDirName.value = ''
    loadDirectory(currentPath.value)
  } catch {
  }
}

async function createFile() {
  if (!newFileName.value) return
  try {
    const fullPath = currentPath.value === '/'
      ? '/' + newFileName.value
      : currentPath.value + '/' + newFileName.value
    await request.post('/files/content', {
      path: fullPath,
      content: '',
      alias: selectedAccount.value,
    })
    showCreateFileDialog.value = false
    newFileName.value = ''
    loadDirectory(currentPath.value)
  } catch {
  }
}

async function executeCommand() {
  if (!quickCommand.value || !selectedAccount.value) return
  const cmd = quickCommand.value
  try {
    const res = await request.post<any>('/command/exec', {
      command: cmd,
      alias: selectedAccount.value,
    })
    commandHistory.value.push({ command: cmd, output: res.stdout || res.stderr || '' })
    quickCommand.value = ''
    setTimeout(() => {
      if (commandOutputRef.value) {
        commandOutputRef.value.scrollTop = commandOutputRef.value.scrollHeight
      }
    }, 50)
  } catch {
  }
}

function clearHistory() {
  commandHistory.value = []
}

onMounted(() => {
  if (sshAccounts.value.length > 0) {
    selectedAccount.value = sshAccounts.value[0].alias
    loadDirectory('/')
  }
})
</script>

<style scoped>
.file-manager-page {
  padding: 0;
}

.file-manager-layout {
  display: flex;
  gap: var(--md3-space-lg);
  height: 400px;
}

.file-sidebar {
  width: 200px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: var(--md3-space-lg);
  padding: var(--md3-space-md);
  background: var(--md3-glass-bg);
  backdrop-filter: var(--md3-glass-blur);
  -webkit-backdrop-filter: var(--md3-glass-blur);
  border: 1px solid var(--md3-glass-border);
  border-radius: var(--md3-shape-md);
  transition: box-shadow var(--md3-motion-duration-medium) var(--md3-motion-easing-standard);
}

.file-sidebar:hover {
  box-shadow: var(--md3-elevation-level1);
}

.sidebar-section {
  display: flex;
  flex-direction: column;
  gap: var(--md3-space-xs);
}

.sidebar-label {
  font: var(--md3-type-label-small);
  color: var(--md3-outline);
  text-transform: uppercase;
  letter-spacing: 1px;
  padding: var(--md3-space-xs) 0;
}

.account-menu {
  border: none;
  background: transparent;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.account-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  cursor: pointer;
  border-radius: var(--md3-shape-sm);
  font-size: 14px;
  color: var(--md3-on-surface);
  transition: background var(--md3-motion-duration-short) var(--md3-motion-easing-standard);
}

.account-item .icon-sidebar {
  width: 16px;
  height: 16px;
  flex-shrink: 0;
}

.account-item:hover {
  background: var(--md3-on-surface-variant);
  opacity: 0.1;
}

.account-item.active {
  background: var(--md3-primary-container);
  color: var(--md3-primary);
}

.add-account-btn {
  width: 100%;
  margin-top: var(--md3-space-xs);
}

.bookmark-list {
  display: flex;
  flex-direction: column;
}

.bookmark-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px var(--md3-space-sm);
  cursor: pointer;
  border-radius: var(--md3-shape-sm);
  font-size: 13px;
  color: var(--md3-on-surface-variant);
  transition: background var(--md3-motion-duration-short) var(--md3-motion-easing-standard),
              color var(--md3-motion-duration-short) var(--md3-motion-easing-standard);
}

.bookmark-item .icon-sidebar {
  width: 16px;
  height: 16px;
  flex-shrink: 0;
}

.bookmark-item:hover {
  background: var(--md3-primary-container);
  color: var(--md3-primary);
}

.file-main {
  flex: 1;
  overflow: auto;
  display: flex;
  flex-direction: column;
  gap: var(--md3-space-sm);
}

.batch-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--md3-space-sm) var(--md3-space-md);
  background: var(--md3-primary-container);
  border-radius: var(--md3-shape-md);
  border: 1px solid var(--md3-outline-variant);
  animation: toolbar-enter 0.2s var(--md3-motion-easing-standard);
}

@keyframes toolbar-enter {
  from {
    opacity: 0;
    transform: translateY(-8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.batch-info {
  font: var(--md3-type-title-small);
  color: var(--md3-on-primary-container);
}

.batch-actions {
  display: flex;
  gap: var(--md3-space-sm);
}

.quick-command-area {
  margin-top: var(--md3-space-sm);
}

.command-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--md3-space-sm);
}

.command-title {
  font: var(--md3-type-title-small);
}

.command-input-row {
  margin-bottom: var(--md3-space-sm);
}

.command-output {
  max-height: 200px;
  overflow-y: auto;
  background: var(--md3-inverse-surface);
  color: var(--md3-inverse-on-surface);
  padding: var(--md3-space-sm);
  border-radius: var(--md3-shape-sm);
  font-family: var(--md3-font-mono);
  font-size: 12px;
  line-height: 1.6;
}

.command-entry {
  margin-bottom: var(--md3-space-sm);
}

.command-prompt {
  color: var(--md3-success);
}

.command-result {
  margin: 2px 0 0 0;
  white-space: pre-wrap;
  word-break: break-all;
  color: var(--md3-inverse-on-surface);
}
</style>
