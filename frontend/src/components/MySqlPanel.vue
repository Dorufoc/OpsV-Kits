<template>
  <div class="mysql-panel">
    <template v-if="!isConnected">
      <div class="connect-prompt">
        <Md3Button variant="primary" @click="handleConnect" :disabled="containerState !== 'running'">
          连接 MySQL
        </Md3Button>
        <span v-if="containerState !== 'running'" class="disabled-hint">容器未运行</span>
      </div>
    </template>
    <template v-else>
      <Md3Tabs v-model="activeTab" :tabs="tabItems" />
      <div class="tab-content">
        <div v-show="activeTab === 'cli'" class="cli-tab">
          <Terminal
            ref="terminalRef"
            :session-name="`MySQL CLI (${mysqlConnection?.host}:${mysqlConnection?.port})`"
            :show-toolbar="true"
            @data="handleTerminalInput"
            @resize="handleTerminalResize"
          />
        </div>
        <div v-show="activeTab === 'query'" class="query-tab">
          <SqlQueryEditor
            :account-alias="accountAlias"
            :container-id="containerId"
            :loading="store.mysqlQueryLoading"
            @execute="handleExecuteQuery"
          />
          <SqlResultTable :result="store.mysqlQueryResult" />
        </div>
        <div v-show="activeTab === 'tables'" class="tables-tab">
          <TableInfoPanel :container-id="containerId" :account-alias="accountAlias" />
        </div>
      </div>
      <div class="panel-actions">
        <Md3Button variant="text" size="sm" @click="handleDisconnect">断开连接</Md3Button>
      </div>
    </template>
    <DbLoginDialog
      deploy-mode="docker"
      :account-alias="accountAlias"
      :container-id="containerId"
      :visible="showLoginDialog"
      @close="showLoginDialog = false"
      @submit="handleLoginSubmit"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onBeforeUnmount } from 'vue'
import { useDbToolkitStore } from '@/stores/dbToolkitStore'
import type { MySqlConnectionParams } from '@/types/db-toolkit'
import Terminal from '@/components/Terminal.vue'
import SqlQueryEditor from '@/components/SqlQueryEditor.vue'
import SqlResultTable from '@/components/SqlResultTable.vue'
import TableInfoPanel from '@/components/TableInfoPanel.vue'
import DbLoginDialog from '@/components/DbLoginDialog.vue'
import { Md3Tabs } from '@/components/md3'
import Md3Button from '@/components/Md3Button.vue'

const props = defineProps<{
  containerId: string
  accountAlias: string
  containerState: string
}>()

const store = useDbToolkitStore()
const isConnected = ref(false)
const mysqlConnection = ref<MySqlConnectionParams | null>(null)
const showLoginDialog = ref(false)
const activeTab = ref('cli')
const terminalRef = ref<InstanceType<typeof Terminal>>()
let ws: WebSocket | null = null

const tabItems = [
  { label: 'CLI 终端', value: 'cli' },
  { label: '可视化查询', value: 'query' },
  { label: '数据表信息', value: 'tables' },
]

async function handleConnect() {
  if (props.containerState !== 'running') return
  try {
    const result = await store.detectClient('mysql', props.accountAlias, props.containerId)
    if (!result.installed) {
      console.warn('MySQL客户端检测失败:', result.error)
      alert(result.error || '容器内未安装 MySQL 客户端')
      return
    }
    showLoginDialog.value = true
  } catch (e: any) {
    console.error('MySQL客户端探测失败:', e)
    alert('探测失败: ' + (e.message || e))
  }
}

function handleLoginSubmit(params: any) {
  showLoginDialog.value = false
  const conn = params.connection as MySqlConnectionParams
  store.connectMysql(conn)
  mysqlConnection.value = conn
  isConnected.value = true
  connectWebSocket()
}

function handleDisconnect() {
  disconnectWebSocket()
  store.disconnectMysql()
  mysqlConnection.value = null
  isConnected.value = false
  activeTab.value = 'cli'
}

function connectWebSocket() {
  if (ws) disconnectWebSocket()
  const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:'
  const url = `${protocol}//${location.host}/api/db-toolkit/ws/mysql-cli/${props.containerId}`
  ws = new WebSocket(url)
  ws.onopen = () => {
    ws?.send(JSON.stringify({
      account_alias: props.accountAlias,
      connection: mysqlConnection.value,
    }))
  }
  ws.onmessage = (event) => {
    const msg = JSON.parse(event.data)
    if (msg.type === 'data') {
      terminalRef.value?.write(msg.content)
    } else if (msg.type === 'info') {
      terminalRef.value?.writeln('连接已建立')
    } else if (msg.type === 'error') {
      terminalRef.value?.writeln(`\r\n错误: ${msg.message}`)
    } else if (msg.type === 'disconnected') {
      terminalRef.value?.writeln('\r\n连接已断开')
    }
  }
  ws.onerror = () => {
    terminalRef.value?.writeln('\r\nWebSocket 连接错误')
  }
  ws.onclose = () => {
    ws = null
  }
}

function disconnectWebSocket() {
  if (ws) {
    ws.close()
    ws = null
  }
}

function handleTerminalInput(data: string) {
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ type: 'input', data }))
  }
}

function handleTerminalResize(cols: number, rows: number) {
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ type: 'resize', width: cols, height: rows }))
  }
}

async function handleExecuteQuery(sql: string) {
  await store.executeMysqlQuery(props.accountAlias, props.containerId, sql)
}

onBeforeUnmount(() => {
  disconnectWebSocket()
})
</script>

<style scoped>
.mysql-panel {
  display: flex;
  flex-direction: column;
  gap: var(--md3-space-md);
}

.connect-prompt {
  display: flex;
  align-items: center;
  gap: var(--md3-space-sm);
  padding: var(--md3-space-lg);
  justify-content: center;
}

.disabled-hint {
  font-size: 12px;
  color: var(--md3-on-surface-variant);
}

.tab-content {
  min-height: 300px;
}

.cli-tab {
  height: 400px;
}

.query-tab {
  display: flex;
  flex-direction: column;
  gap: var(--md3-space-md);
}

.panel-actions {
  display: flex;
  justify-content: flex-end;
}
</style>
