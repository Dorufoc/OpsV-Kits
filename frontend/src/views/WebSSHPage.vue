<template>
  <div class="webssh-page">
    <el-page-header title="OpsV-Kits">
      <template #content>
        <span>WebSSH 终端</span>
      </template>
      <template #extra>
        <Md3Button size="sm" variant="primary" :icon="Plus" @click="showConnectDialog = true">新建</Md3Button>
      </template>
    </el-page-header>
    <el-divider />

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
            <el-icon :size="16"><Connection /></el-icon>
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
            @data="onTerminalData"
            @resize="onTerminalResize"
          />
          <el-empty
            v-else
            description="请新建或选择一个 SSH 会话"
            :image-size="120"
          />
        </div>

        <div class="terminal-footer" v-if="activeSession">
          <Md3Button size="sm" variant="text" :icon="DocumentCopy">粘贴</Md3Button>
          <Md3Button size="sm" variant="text" :icon="Search" @click="openSearch">搜索</Md3Button>
          <Md3Button size="sm" variant="text" :icon="Upload">上传</Md3Button>
          <Md3Button size="sm" variant="text" :icon="Download">下载</Md3Button>
          <Md3Button size="sm" variant="text" :icon="Setting" @click="showSettings = true">设置</Md3Button>
          <Md3Button size="sm" variant="text" :icon="Tickets">历史</Md3Button>
          <Md3Button size="sm" variant="text" :icon="QuestionFilled">帮助</Md3Button>
        </div>
      </div>
    </div>

    <WebSSHConnectDialog
      v-model:visible="showConnectDialog"
      @connect="handleConnect"
    />

    <el-dialog v-model="showSettings" title="终端设置" width="480px">
      <el-form label-width="80px">
        <el-form-item label="主题">
          <el-select v-model="terminalSettings.theme" style="width: 100%">
            <el-option label="Dark" value="dark" />
            <el-option label="Light" value="light" />
          </el-select>
        </el-form-item>
        <el-form-item label="字体">
          <el-select v-model="terminalSettings.font_family" style="width: 100%">
            <el-option label="Fira Code" value="'Fira Code', monospace" />
            <el-option label="Cascadia Code" value="'Cascadia Code', monospace" />
            <el-option label="Consolas" value="Consolas, monospace" />
            <el-option label="Courier New" value="'Courier New', monospace" />
          </el-select>
        </el-form-item>
        <el-form-item label="字号">
          <el-input-number v-model="terminalSettings.font_size" :min="10" :max="24" />
        </el-form-item>
        <el-form-item label="编码">
          <el-select v-model="terminalSettings.encoding" style="width: 100%">
            <el-option label="UTF-8" value="utf-8" />
            <el-option label="GBK" value="gbk" />
            <el-option label="ISO-8859-1" value="iso-8859-1" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <Md3Button @click="showSettings = false">关闭</Md3Button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import {
  Plus, Connection, FullScreen,
  DocumentCopy, Search, Upload, Download,
  Setting, Tickets, QuestionFilled,
} from '@element-plus/icons-vue'
import Md3Button from '@/components/Md3Button.vue'
import { useWebsshStore, type HistoryRecord } from '@/stores/websshStore'
import { useSshAccountStore } from '@/stores/sshAccountStore'
import { request } from '@/api'
import Terminal from '@/components/Terminal.vue'
import SessionManager from '@/components/SessionManager.vue'
import WebSSHConnectDialog from '@/views/WebSSHConnectDialog.vue'

const websshStore = useWebsshStore()
const sshStore = useSshAccountStore()

const showConnectDialog = ref(false)
const showSettings = ref(false)
const isFullscreen = ref(false)
const terminalRef = ref<InstanceType<typeof Terminal>>()
const terminalAreaRef = ref<HTMLElement>()
const webSocketRef = ref<WebSocket | null>(null)

const terminalSettings = ref({
  theme: 'dark',
  font_family: "'Fira Code', monospace",
  font_size: 14,
  encoding: 'utf-8',
})

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
}

async function handleDisconnect(sessionId: string) {
  await websshStore.disconnect(sessionId)
}

function handleReconnect(_record: HistoryRecord) {
  showConnectDialog.value = true
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

function openSearch() {
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
  transition: box-shadow var(--md3-motion-duration-medium) var(--md3-motion-easing-standard);
}

.webssh-sidebar:hover {
  box-shadow: var(--md3-elevation-level1);
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
</style>
