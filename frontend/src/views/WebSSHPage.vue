<template>
  <div class="webssh-page">
    <div class="webssh-layout">
      <div class="webssh-sidebar">
        <SessionManager
          :sessions="websshStore.sessions"
          :history-records="websshStore.historyRecords"
          :active-session-id="websshStore.activeSessionId"
          @select="switchSession"
          @disconnect="handleDisconnect"
          @new-session="showConnectDialog = true"
          @reconnect="handleReconnect"
          @delete-history="handleDeleteHistory"
        />
      </div>

      <div class="webssh-main">
        <div class="session-header" v-if="activeSession">
          <div class="session-info">
            <component :is="Connection" class="session-icon" />
            <span class="session-label">
              当前会话: {{ activeSession.alias || activeSession.host }}
              ({{ activeSession.username }}@{{ activeSession.host }})
            </span>
          </div>
          <Md3Button size="sm" variant="text" :icon="FullScreen" @click="toggleFullscreen">{{ isFullscreen ? '退出全屏' : '全屏' }}</Md3Button>
        </div>

        <div class="terminal-area" ref="terminalAreaRef">
          <Terminal
            v-if="activeSession"
            ref="terminalRef"
            :session-name="activeSession.alias || activeSession.host"
            :show-toolbar="true"
            :font-size="terminalSettings.font_size"
            :font-family="terminalSettings.font_family"
            :theme="terminalSettings.theme as 'dark' | 'light'"
            @data="onTerminalData"
            @resize="onTerminalResize"
          />
          <Md3Empty
            v-else
            description="请新建或选择一个 SSH 会话"
            :image-size="120"
          />
        </div>

        <div class="terminal-footer" v-if="activeSession">
          <Md3Button size="sm" variant="text" :icon="DocumentCopy" @click="handlePaste">粘贴</Md3Button>
          <Md3Button size="sm" variant="text" :icon="Search" @click="openSearch">搜索</Md3Button>
          <Md3Button size="sm" variant="text" :icon="Upload" @click="handleUpload">上传</Md3Button>
          <Md3Button size="sm" variant="text" :icon="Download" @click="handleDownload">下载</Md3Button>
          <Md3Button size="sm" variant="text" :icon="Setting" @click="showSettings = true">设置</Md3Button>
          <Md3Button size="sm" variant="text" :icon="Tickets" @click="openHistoryDialog">历史</Md3Button>
          <Md3Button size="sm" variant="text" :icon="QuestionFilled" @click="showHelp = true">帮助</Md3Button>
        </div>
      </div>
    </div>

    <WebSSHConnectDialog
      v-model:visible="showConnectDialog"
      @connect="handleConnect"
    />

    <Md3Dialog v-model:visible="showSettings" title="终端设置">
      <div class="settings-form">
        <div class="settings-row">
          <span class="settings-label">主题</span>
          <Md3Select
            v-model="terminalSettings.theme"
            :options="themeOptions"
            class="settings-select"
          />
        </div>
        <div class="settings-row">
          <span class="settings-label">字体</span>
          <Md3Select
            v-model="terminalSettings.font_family"
            :options="fontOptions"
            class="settings-select"
          />
        </div>
        <div class="settings-row">
          <span class="settings-label">字号</span>
          <Md3Input
            type="number"
            v-model.number="terminalSettings.font_size"
            :min="10"
            :max="24"
            class="settings-input-narrow"
          />
        </div>
        <div class="settings-row">
          <span class="settings-label">编码</span>
          <Md3Select
            v-model="terminalSettings.encoding"
            :options="encodingOptions"
            class="settings-select"
          />
        </div>
      </div>
      <template #footer>
        <Md3Button @click="showSettings = false">关闭</Md3Button>
      </template>
    </Md3Dialog>

    <Md3Dialog v-model:visible="showSearch" title="终端搜索" width="400px">
      <div class="search-form">
        <Md3Input v-model="searchQuery" label="搜索内容" placeholder="输入要搜索的文本" @keydown.enter="doSearch" />
        <div class="search-options">
          <label class="search-option">
            <input type="checkbox" v-model="searchCaseSensitive" /> 区分大小写
          </label>
        </div>
      </div>
      <template #footer>
        <Md3Button @click="showSearch = false">关闭</Md3Button>
        <Md3Button variant="primary" @click="doSearch">搜索</Md3Button>
      </template>
    </Md3Dialog>

    <Md3Dialog v-model:visible="showUpload" title="上传文件" width="420px">
      <div class="upload-form">
        <div class="upload-drop-zone" @click="triggerFileInput" @dragover.prevent @drop.prevent="handleFileDrop">
          <Md3Icon name="upload" class="upload-icon" />
          <p>点击选择文件或将文件拖拽到此处</p>
          <p class="upload-hint">文件将通过 SSH 通道上传到远程服务器</p>
        </div>
        <input type="file" ref="fileInputRef" class="hidden-file-input" @change="onFileSelected" multiple />
        <Md3Input v-model="uploadRemotePath" label="远程路径" placeholder="如: /tmp/" />
        <div v-if="uploadFiles.length > 0" class="upload-file-list">
          <div v-for="(f, i) in uploadFiles" :key="i" class="upload-file-item">
            <span>{{ f.name }}</span>
            <span class="upload-file-size">{{ formatFileSize(f.size) }}</span>
          </div>
        </div>
      </div>
      <template #footer>
        <Md3Button @click="showUpload = false">取消</Md3Button>
        <Md3Button variant="primary" @click="doUpload" :disabled="uploadFiles.length === 0">上传</Md3Button>
      </template>
    </Md3Dialog>

    <Md3Dialog v-model:visible="showDownload" title="下载文件" width="420px">
      <div class="download-form">
        <Md3Input v-model="downloadRemotePath" label="远程文件路径" placeholder="如: /var/log/syslog" />
        <p class="download-hint">输入远程服务器上的文件路径，将下载到本地</p>
      </div>
      <template #footer>
        <Md3Button @click="showDownload = false">取消</Md3Button>
        <Md3Button variant="primary" @click="doDownload" :disabled="!downloadRemotePath">下载</Md3Button>
      </template>
    </Md3Dialog>

    <Md3Dialog v-model:visible="showHistory" title="会话历史" width="500px">
      <div class="history-list">
        <div v-if="historyLines.length === 0 && !historyLoading" class="history-empty">暂无历史命令</div>
        <div v-if="historyLoading" class="history-loading">加载中...</div>
        <div v-for="(line, i) in historyLines" :key="i" class="history-line" @click="replayHistoryLine(line)">
          <span class="history-index">{{ i + 1 }}</span>
          <span class="history-text">{{ line }}</span>
        </div>
      </div>
      <template #footer>
        <Md3Button @click="showHistory = false">关闭</Md3Button>
      </template>
    </Md3Dialog>

    <Md3Dialog v-model:visible="showHelp" title="快捷键帮助" width="460px">
      <div class="help-content">
        <div class="help-section">
          <h4>终端操作</h4>
          <div class="help-row"><kbd>Ctrl+C</kbd><span>中断当前命令</span></div>
          <div class="help-row"><kbd>Ctrl+D</kbd><span>退出当前 Shell / 发送 EOF</span></div>
          <div class="help-row"><kbd>Ctrl+L</kbd><span>清屏</span></div>
          <div class="help-row"><kbd>Ctrl+Z</kbd><span>挂起当前进程</span></div>
          <div class="help-row"><kbd>Ctrl+R</kbd><span>搜索历史命令</span></div>
          <div class="help-row"><kbd>Tab</kbd><span>自动补全</span></div>
        </div>
        <div class="help-section">
          <h4>工具栏</h4>
          <div class="help-row"><span>复制选中</span><span>复制终端中选中的文本到剪贴板</span></div>
          <div class="help-row"><span>复制全部</span><span>复制终端缓冲区中所有内容</span></div>
          <div class="help-row"><span>粘贴</span><span>将剪贴板内容发送到终端</span></div>
          <div class="help-row"><span>清屏</span><span>清除终端屏幕内容</span></div>
          <div class="help-row"><span>冻结</span><span>暂停终端输出，解冻后恢复</span></div>
          <div class="help-row"><span>全屏</span><span>切换终端全屏模式</span></div>
        </div>
      </div>
      <template #footer>
        <Md3Button @click="showHelp = false">关闭</Md3Button>
      </template>
    </Md3Dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount, h, defineComponent } from 'vue'
import { Md3Icon } from '@/components/md3'
import Md3Button from '@/components/Md3Button.vue'
import {
  Md3PageHeader,
  Md3Divider,
  Md3Dialog,
  Md3Select,
  Md3Input,
  Md3Empty,
} from '@/components/md3'
import { useWebsshStore, type HistoryRecord } from '@/stores/websshStore'
import { useSshAccountStore } from '@/stores/sshAccountStore'
import { request } from '@/api'
import Terminal from '@/components/Terminal.vue'
import SessionManager from '@/components/SessionManager.vue'
import WebSSHConnectDialog from '@/views/WebSSHConnectDialog.vue'

const createIcon = (name: string) => defineComponent(() => () => h(Md3Icon, { name }))

const Connection = createIcon('connection')
const FullScreen = createIcon('fullscreen')
const DocumentCopy = createIcon('content-copy')
const Search = createIcon('magnify')
const Upload = createIcon('upload')
const Download = createIcon('download')
const Setting = createIcon('cog')
const Tickets = createIcon('tag')
const QuestionFilled = createIcon('help-circle')

const websshStore = useWebsshStore()
const sshStore = useSshAccountStore()

const showConnectDialog = ref(false)
const showSettings = ref(false)
const showSearch = ref(false)
const showUpload = ref(false)
const showDownload = ref(false)
const showHistory = ref(false)
const showHelp = ref(false)
const isFullscreen = ref(false)
const terminalRef = ref<InstanceType<typeof Terminal>>()
const terminalAreaRef = ref<HTMLElement>()
const webSocketRef = ref<WebSocket | null>(null)
const fileInputRef = ref<HTMLInputElement>()

const terminalSettings = ref({
  theme: 'dark',
  font_family: "'Fira Code', monospace",
  font_size: 14,
  encoding: 'utf-8',
})

const searchQuery = ref('')
const searchCaseSensitive = ref(false)

const uploadFiles = ref<File[]>([])
const uploadRemotePath = ref('/tmp/')

const downloadRemotePath = ref('')

const historyLines = ref<string[]>([])
const historyLoading = ref(false)

const themeOptions = [
  { label: 'Dark', value: 'dark' },
  { label: 'Light', value: 'light' },
]

const fontOptions = [
  { label: 'Fira Code', value: "'Fira Code', monospace" },
  { label: 'Cascadia Code', value: "'Cascadia Code', monospace" },
  { label: 'Consolas', value: 'Consolas, monospace' },
  { label: 'Courier New', value: "'Courier New', monospace" },
]

const encodingOptions = [
  { label: 'UTF-8', value: 'utf-8' },
  { label: 'GBK', value: 'gbk' },
  { label: 'ISO-8859-1', value: 'iso-8859-1' },
]

const activeSession = computed(() => {
  return websshStore.sessions.find(s => s.id === websshStore.activeSessionId)
})

async function handleConnect(config: any) {
  try {
    const session = await websshStore.connect(config)
    showConnectDialog.value = false
    initWebSocket(session.id)
  } catch {
  }
}

function switchSession(sessionId: string) {
  websshStore.setActiveSession(sessionId)
  const session = websshStore.sessions.find(s => s.id === sessionId)
  if (session && session.status === 'online') {
    initWebSocket(sessionId)
  }
}

async function handleDisconnect(sessionId: string) {
  await websshStore.disconnect(sessionId)
  if (webSocketRef.value) {
    webSocketRef.value.close()
    webSocketRef.value = null
  }
}

async function handleReconnect(record: HistoryRecord) {
  try {
    const config: any = {
      account_alias: record.account_alias || undefined,
      host: record.host,
      port: record.port,
      username: record.username,
      use_saved_account: !!record.account_alias,
    }
    const session = await websshStore.connect(config)
    initWebSocket(session.id)
  } catch {
  }
}

async function handleDeleteHistory(sessionId: string) {
  try {
    await request.delete(`/webssh/sessions/history/${sessionId}`)
    websshStore.historyRecords = websshStore.historyRecords.filter(r => r.session_id !== sessionId)
  } catch {}
}

function initWebSocket(sessionId: string) {
  if (webSocketRef.value) {
    webSocketRef.value.close()
  }
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const wsUrl = `${protocol}//${window.location.host}/api/webssh/ws/${sessionId}`
  const ws = new WebSocket(wsUrl)
  ws.onopen = () => {
    terminalRef.value?.focus()
  }
  ws.onmessage = (event) => {
    try {
      const msg = JSON.parse(event.data)
      if (msg.type === 'data') {
        terminalRef.value?.write(msg.content)
      } else if (msg.type === 'disconnected') {
        terminalRef.value?.writeln('\r\n\x1b[31m连接已断开\x1b[0m')
      }
    } catch {
      terminalRef.value?.write(event.data)
    }
  }
  ws.onclose = () => {
    terminalRef.value?.writeln('\r\n\x1b[31m连接已断开\x1b[0m')
  }
  webSocketRef.value = ws
}

function onTerminalData(data: string) {
  if (webSocketRef.value?.readyState === WebSocket.OPEN) {
    webSocketRef.value.send(JSON.stringify({ type: 'input', data }))
  }
}

function onTerminalResize(cols: number, rows: number) {
  if (webSocketRef.value?.readyState === WebSocket.OPEN) {
    webSocketRef.value.send(JSON.stringify({ type: 'resize', width: cols, height: rows }))
  }
  if (activeSession.value) {
    websshStore.resizeTerminal(activeSession.value.id, cols, rows)
  }
}

function toggleFullscreen() {
  if (!terminalAreaRef.value) return
  if (document.fullscreenElement) {
    document.exitFullscreen()
    isFullscreen.value = false
  } else {
    terminalAreaRef.value.requestFullscreen()
    isFullscreen.value = true
  }
}

function handlePaste() {
  navigator.clipboard.readText().then(text => {
    onTerminalData(text)
  }).catch(() => {})
}

function openSearch() {
  searchQuery.value = ''
  showSearch.value = true
}

function doSearch() {
  const term = terminalRef.value?.getTerminal()
  if (!term || !searchQuery.value) return

  const buffer = term.buffer.active
  const query = searchCaseSensitive.value ? searchQuery.value : searchQuery.value.toLowerCase()

  for (let i = 0; i < buffer.length; i++) {
    const line = buffer.getLine(i)
    if (line) {
      const text = line.translateToString(false)
      const haystack = searchCaseSensitive.value ? text : text.toLowerCase()
      const idx = haystack.indexOf(query)
      if (idx !== -1) {
        term.select(idx, i, query.length)
        term.scrollToLine(i)
        break
      }
    }
  }
}

function handleUpload() {
  uploadFiles.value = []
  uploadRemotePath.value = '/tmp/'
  showUpload.value = true
}

function triggerFileInput() {
  fileInputRef.value?.click()
}

function onFileSelected(event: Event) {
  const target = event.target as HTMLInputElement
  if (target.files) {
    uploadFiles.value = Array.from(target.files)
  }
}

function handleFileDrop(event: DragEvent) {
  if (event.dataTransfer?.files) {
    uploadFiles.value = Array.from(event.dataTransfer.files)
  }
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

async function doUpload() {
  if (uploadFiles.value.length === 0 || !activeSession.value) return

  const sessionId = activeSession.value.id
  const remotePath = uploadRemotePath.value

  for (const file of uploadFiles.value) {
    try {
      const content = await file.arrayBuffer()
      const base64 = btoa(String.fromCharCode(...new Uint8Array(content)))

      if (webSocketRef.value?.readyState === WebSocket.OPEN) {
        webSocketRef.value.send(JSON.stringify({
          type: 'upload',
          session_id: sessionId,
          filename: file.name,
          remote_path: remotePath,
          content_base64: base64,
        }))
      }

      terminalRef.value?.writeln(`\r\n\x1b[32m上传: ${file.name} -> ${remotePath}${file.name}\x1b[0m`)
    } catch {
      terminalRef.value?.writeln(`\r\n\x1b[31m上传失败: ${file.name}\x1b[0m`)
    }
  }

  showUpload.value = false
  uploadFiles.value = []
}

function handleDownload() {
  downloadRemotePath.value = ''
  showDownload.value = true
}

async function doDownload() {
  if (!downloadRemotePath.value || !activeSession.value) return

  const sessionId = activeSession.value.id
  const remotePath = downloadRemotePath.value

  try {
    const res: any = await request.post('/webssh/download', {
      session_id: sessionId,
      path: remotePath,
    })

    if (res.content_base64) {
      const binary = atob(res.content_base64)
      const bytes = new Uint8Array(binary.length)
      for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i)

      const filename = remotePath.split('/').pop() || 'download'
      const blob = new Blob([bytes])
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = filename
      a.click()
      URL.revokeObjectURL(url)
    }
  } catch {
    terminalRef.value?.writeln(`\r\n\x1b[31m下载失败: ${remotePath}\x1b[0m`)
  }

  showDownload.value = false
}

async function openHistoryDialog() {
  showHistory.value = true
  historyLoading.value = true
  historyLines.value = []

  if (activeSession.value) {
    try {
      const lines = await websshStore.getHistory(activeSession.value.id)
      historyLines.value = Array.isArray(lines) ? lines : []
    } catch {
      historyLines.value = []
    }
  }

  historyLoading.value = false
}

function replayHistoryLine(line: string) {
  onTerminalData(line + '\n')
  showHistory.value = false
}

onMounted(() => {
  websshStore.listSessions()
  websshStore.fetchHistory()
  sshStore.fetchAccounts()
})

onBeforeUnmount(() => {
  if (webSocketRef.value) {
    webSocketRef.value.close()
  }
})
</script>

<style scoped>
.webssh-page {
  padding: 0;
  display: flex;
  flex-direction: column;
  height: 100%;
}

.webssh-layout {
  display: flex;
  gap: var(--md3-space-lg);
  flex: 1;
  min-height: 500px;
}

.webssh-sidebar {
  width: 220px;
  flex-shrink: 0;
  border: 1px solid var(--md3-glass-border);
  border-radius: var(--md3-shape-md);
  background: var(--md3-glass-bg);
  backdrop-filter: var(--md3-glass-blur);
  -webkit-backdrop-filter: var(--md3-glass-blur);
  overflow: hidden;
  transition: border-color var(--md3-motion-duration-medium) var(--md3-motion-easing-standard);
}

.webssh-sidebar:hover {
  border-color: var(--md3-card-border-hover);
}

.webssh-main {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.session-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--md3-space-sm) var(--md3-space-md);
  background: var(--md3-glass-bg);
  backdrop-filter: var(--md3-glass-blur);
  -webkit-backdrop-filter: var(--md3-glass-blur);
  border: 1px solid var(--md3-glass-border);
  border-bottom: none;
  border-radius: var(--md3-shape-sm) var(--md3-shape-sm) 0 0;
}

.session-info {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
}

.session-label {
  font-weight: 500;
}

.terminal-area {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.terminal-area :deep(.terminal-wrapper) {
  border-top-left-radius: 0;
  border-top-right-radius: 0;
  flex: 1;
}

.terminal-footer {
  display: flex;
  align-items: center;
  gap: var(--md3-space-xs);
  padding: var(--md3-space-xs) var(--md3-space-sm);
  background: var(--md3-glass-bg);
  backdrop-filter: var(--md3-glass-blur);
  -webkit-backdrop-filter: var(--md3-glass-blur);
  border: 1px solid var(--md3-glass-border);
  border-top: none;
  border-radius: 0 0 var(--md3-shape-sm) var(--md3-shape-sm);
}

.session-icon {
  width: 16px;
  height: 16px;
}

.settings-form {
  display: flex;
  flex-direction: column;
  gap: var(--md3-space-lg);
}

.settings-row {
  display: flex;
  align-items: center;
  gap: var(--md3-space-md);
}

.settings-label {
  width: 80px;
  font-size: 14px;
  color: var(--md3-on-surface);
  flex-shrink: 0;
}

.settings-select {
  flex: 1;
}

.settings-input-narrow {
  width: 120px;
}

.search-form {
  display: flex;
  flex-direction: column;
  gap: var(--md3-space-md);
}

.search-options {
  display: flex;
  align-items: center;
  gap: var(--md3-space-md);
}

.search-option {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: var(--md3-on-surface);
  cursor: pointer;
}

.upload-form {
  display: flex;
  flex-direction: column;
  gap: var(--md3-space-md);
}

.upload-drop-zone {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--md3-space-xs);
  padding: var(--md3-space-xl);
  border: 2px dashed var(--md3-outline-variant);
  border-radius: var(--md3-shape-sm);
  cursor: pointer;
  color: var(--md3-on-surface-variant);
  transition: border-color var(--md3-motion-duration-short) var(--md3-motion-easing-standard);
}

.upload-drop-zone:hover {
  border-color: var(--md3-primary);
}

.upload-icon {
  width: 32px;
  height: 32px;
}

.upload-hint {
  font-size: 12px;
  opacity: 0.6;
}

.hidden-file-input {
  display: none;
}

.upload-file-list {
  max-height: 120px;
  overflow-y: auto;
  border: 1px solid var(--md3-glass-border);
  border-radius: var(--md3-shape-xs);
}

.upload-file-item {
  display: flex;
  justify-content: space-between;
  padding: 4px var(--md3-space-sm);
  font-size: 13px;
  border-bottom: 1px solid var(--md3-surface-container-low);
}

.upload-file-size {
  color: var(--md3-on-surface-variant);
  font-size: 12px;
}

.download-form {
  display: flex;
  flex-direction: column;
  gap: var(--md3-space-md);
}

.download-hint {
  font-size: 12px;
  color: var(--md3-on-surface-variant);
  opacity: 0.7;
}

.history-list {
  max-height: 320px;
  overflow-y: auto;
}

.history-empty,
.history-loading {
  padding: var(--md3-space-lg);
  text-align: center;
  color: var(--md3-on-surface-variant);
  font-size: 13px;
}

.history-line {
  display: flex;
  align-items: center;
  gap: var(--md3-space-sm);
  padding: 4px var(--md3-space-sm);
  font-family: var(--md3-font-mono);
  font-size: 13px;
  cursor: pointer;
  border-bottom: 1px solid var(--md3-surface-container-low);
  transition: background var(--md3-motion-duration-short) var(--md3-motion-easing-standard);
}

.history-line:hover {
  background: var(--md3-surface-container-low);
}

.history-index {
  width: 28px;
  flex-shrink: 0;
  color: var(--md3-outline);
  font-size: 11px;
  text-align: right;
}

.history-text {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.help-content {
  display: flex;
  flex-direction: column;
  gap: var(--md3-space-lg);
}

.help-section h4 {
  font-size: 13px;
  font-weight: 600;
  color: var(--md3-on-surface);
  margin-bottom: var(--md3-space-xs);
}

.help-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 4px 0;
  font-size: 13px;
  color: var(--md3-on-surface-variant);
}

.help-row kbd {
  padding: 2px 8px;
  background: var(--md3-surface-container-high);
  border: 1px solid var(--md3-outline-variant);
  border-radius: var(--md3-shape-xs);
  font-family: var(--md3-font-mono);
  font-size: 12px;
  color: var(--md3-on-surface);
}
</style>
