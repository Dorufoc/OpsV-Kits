<template>
  <div class="file-manager-page">
    <el-page-header title="OpsV-Kits">
      <template #content>
        <span>远程文件管理</span>
      </template>
    </el-page-header>
    <el-divider />

    <div class="file-manager-layout">
      <div class="file-sidebar">
        <div class="sidebar-section">
          <div class="sidebar-label">SSH 账户</div>
          <el-menu :default-active="selectedAccount" class="account-menu">
            <el-menu-item
              v-for="acc in sshAccounts"
              :key="acc.alias"
              :index="acc.alias"
              @click="switchAccount(acc)"
            >
              <el-icon><User /></el-icon>
              <span>{{ acc.alias }}</span>
            </el-menu-item>
          </el-menu>
          <Md3Button size="sm" class="add-account-btn" :icon="Plus" @click="goToSshAccounts">添加</Md3Button>
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
              <el-icon><Collection /></el-icon>
              <span>{{ bm.label }}</span>
            </div>
          </div>
        </div>
      </div>

      <div class="file-main">
        <FileBrowser
          ref="fileBrowserRef"
          :current-path="currentPath"
          :items="fileItems"
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
        />
      </div>
    </div>

    <div class="quick-command-area">
      <el-divider />
      <div class="command-header">
        <span class="command-title">快速命令</span>
        <div class="command-actions">
          <Md3Button size="sm" @click="clearHistory">清空</Md3Button>
        </div>
      </div>
      <div class="command-input-row">
        <el-input
          v-model="quickCommand"
          placeholder="输入 Linux 命令（如：df -h）"
          size="small"
          clearable
          @keyup.enter="executeCommand"
        >
          <template #append>
            <Md3Button @click="executeCommand">执行</Md3Button>
          </template>
        </el-input>
      </div>
      <div class="command-output" ref="commandOutputRef">
        <div v-for="(entry, index) in commandHistory" :key="index" class="command-entry">
          <div class="command-prompt">$ {{ entry.command }}</div>
          <pre class="command-result">{{ entry.output }}</pre>
        </div>
      </div>
    </div>

    <el-dialog v-model="showMkdirDialog" title="新建文件夹" width="400px">
      <el-input v-model="newDirName" placeholder="文件夹名称" />
      <template #footer>
        <Md3Button @click="showMkdirDialog = false">取消</Md3Button>
        <Md3Button variant="primary" @click="createDirectory">确定</Md3Button>
      </template>
    </el-dialog>

    <el-dialog v-model="showCreateFileDialog" title="新建文件" width="400px">
      <el-input v-model="newFileName" placeholder="文件名（如：test.txt）" />
      <template #footer>
        <Md3Button @click="showCreateFileDialog = false">取消</Md3Button>
        <Md3Button variant="primary" @click="createFile">确定</Md3Button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import Md3Button from '@/components/Md3Button.vue'
import { User, Plus, Collection } from '@element-plus/icons-vue'
import { useRouter } from 'vue-router'
import { useSshAccountStore } from '@/stores/sshAccountStore'
import { request } from '@/api'
import FileBrowser, { type FileItem } from '@/components/FileBrowser.vue'

const router = useRouter()
const sshStore = useSshAccountStore()

const selectedAccount = ref('')
const currentPath = ref('/')
const fileItems = ref<FileItem[]>([])
const quickCommand = ref('')
const commandHistory = ref<Array<{ command: string; output: string }>>([])
const commandOutputRef = ref<HTMLElement>()
const fileBrowserRef = ref()

const showMkdirDialog = ref(false)
const showCreateFileDialog = ref(false)
const newDirName = ref('')
const newFileName = ref('')

const sshAccounts = ref(sshStore.accounts)

const bookmarks = [
  { label: '/var/log', path: '/var/log' },
  { label: '/etc', path: '/etc' },
  { label: '/tmp', path: '/tmp' },
  { label: '/home', path: '/home' },
]

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
  border-right: none !important;
  background: transparent;
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

.bookmark-item:hover {
  background: var(--md3-primary-container);
  color: var(--md3-primary);
}

.file-main {
  flex: 1;
  overflow: auto;
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
