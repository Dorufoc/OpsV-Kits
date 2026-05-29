<template>
  <div class="redis-panel">
    <template v-if="!isConnected">
      <div class="connect-prompt">
        <Md3Button variant="primary" @click="handleConnect" :disabled="containerState !== 'running'">
          连接 Redis
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
            :session-name="`Redis CLI (${redisConnection?.host}:${redisConnection?.port})`"
            :show-toolbar="true"
            @data="handleTerminalInput"
            @resize="handleTerminalResize"
          />
        </div>
        <div v-show="activeTab === 'browse'" class="browse-tab">
          <div class="browse-layout">
            <div class="browse-left">
              <RedisKeyList
                :container-id="containerId"
                :account-alias="accountAlias"
                @select="handleKeySelect"
              />
            </div>
            <div class="browse-right">
              <RedisKeyDetail
                :key-info="store.redisKeyInfo"
                :container-id="containerId"
                :account-alias="accountAlias"
                @deleted="handleKeyDeleted"
              />
              <Md3Empty v-if="!store.redisKeyInfo" description="选择左侧 Key 查看详情" />
            </div>
          </div>
        </div>
        <div v-show="activeTab === 'stats'" class="stats-tab">
          <template v-if="store.redisDbStats">
            <div class="stats-grid">
              <div class="stat-item">
                <span class="stat-label">Key 总数</span>
                <span class="stat-value">{{ store.redisDbStats.key_count }}</span>
              </div>
              <div class="stat-item">
                <span class="stat-label">内存使用</span>
                <span class="stat-value">{{ store.redisDbStats.used_memory_human }}</span>
              </div>
              <div class="stat-item">
                <span class="stat-label">内存(字节)</span>
                <span class="stat-value">{{ store.redisDbStats.used_memory_bytes }}</span>
              </div>
            </div>
          </template>
          <Md3Empty v-else description="加载中..." />
        </div>
      </div>
      <div class="panel-actions">
        <Md3Button variant="text" size="sm" @click="handleDisconnect">断开连接</Md3Button>
      </div>
    </template>
    <DbLoginDialog
      db-type="redis"
      :visible="showLoginDialog"
      @close="showLoginDialog = false"
      @submit="handleLoginSubmit"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onBeforeUnmount } from 'vue'
import { useDbToolkitStore } from '@/stores/dbToolkitStore'
import type { RedisConnectionParams } from '@/types/db-toolkit'
import Terminal from '@/components/Terminal.vue'
import RedisKeyList from '@/components/RedisKeyList.vue'
import RedisKeyDetail from '@/components/RedisKeyDetail.vue'
import DbLoginDialog from '@/components/DbLoginDialog.vue'
import { Md3Tabs, Md3Empty } from '@/components/md3'
import Md3Button from '@/components/Md3Button.vue'

const props = defineProps<{
  containerId: string
  accountAlias: string
  containerState: string
}>()

const store = useDbToolkitStore()
const isConnected = ref(false)
const redisConnection = ref<RedisConnectionParams | null>(null)
const showLoginDialog = ref(false)
const activeTab = ref('cli')
const terminalRef = ref<InstanceType<typeof Terminal>>()
let ws: WebSocket | null = null

const tabItems = [
  { label: 'CLI 终端', value: 'cli' },
  { label: '可视化浏览', value: 'browse' },
  { label: '数据库概览', value: 'stats' },
]

async function handleConnect() {
  if (props.containerState !== 'running') return
  try {
    const result = await store.detectClient('redis', props.accountAlias, props.containerId)
    if (!result.installed) {
      alert(result.error || '容器内未安装 Redis 客户端')
      return
    }
    showLoginDialog.value = true
  } catch (e: any) {
    alert('探测失败: ' + (e.message || e))
  }
}

function handleLoginSubmit(params: RedisConnectionParams) {
  showLoginDialog.value = false
  store.connectRedis(params)
  redisConnection.value = params
  isConnected.value = true
  connectWebSocket()
  loadStats()
}

function handleDisconnect() {
  disconnectWebSocket()
  store.disconnectRedis()
  redisConnection.value = null
  isConnected.value = false
  activeTab.value = 'cli'
}

function connectWebSocket() {
  if (ws) disconnectWebSocket()
  const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:'
  const url = `${protocol}//${location.host}/api/db-toolkit/ws/redis-cli/${props.containerId}`
  ws = new WebSocket(url)
  ws.onopen = () => {
    ws?.send(JSON.stringify({
      account_alias: props.accountAlias,
      connection: redisConnection.value,
    }))
  }
  ws.onmessage = (event) => {
    const msg = JSON.parse(event.data)
    if (msg.type === 'data') {
      const content = msg.content.replace(/Warning: Using a password with '-a'.*?\n/g, '')
      if (content) terminalRef.value?.write(content)
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

async function handleKeySelect(key: string) {
  await store.loadRedisKeyDetail(props.accountAlias, props.containerId, key)
}

function handleKeyDeleted() {
  store.redisKeyInfo = null
  handleKeySelect('*')
}

async function loadStats() {
  try {
    await store.loadRedisDbStats(props.accountAlias, props.containerId)
  } catch {
  }
}

onBeforeUnmount(() => {
  disconnectWebSocket()
})
</script>

<style scoped>
.redis-panel {
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

.browse-layout {
  display: flex;
  gap: var(--md3-space-md);
}

.browse-left {
  width: 300px;
  flex-shrink: 0;
}

.browse-right {
  flex: 1;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--md3-space-md);
}

.stat-item {
  display: flex;
  flex-direction: column;
  gap: var(--md3-space-xs);
  padding: var(--md3-space-md);
  background: var(--md3-surface-container-low);
  border-radius: var(--md3-shape-xs);
}

.stat-label {
  font-size: 12px;
  color: var(--md3-on-surface-variant);
}

.stat-value {
  font-size: 20px;
  font-weight: 600;
  color: var(--md3-on-surface);
}

.panel-actions {
  display: flex;
  justify-content: flex-end;
}
</style>
