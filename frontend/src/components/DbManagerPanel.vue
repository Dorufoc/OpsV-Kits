<template>
  <div class="db-manager-panel">
    <template v-if="!isConnected">
      <div class="connect-prompt">
        <DbConnectionManager
          :deploy-mode="deployMode"
          :account-alias="accountAlias"
          :container-id="containerId"
          @connect="handleConnect"
        />
      </div>
    </template>

    <template v-else>
      <div class="manager-layout" :class="{ 'sidebar-collapsed': store.sidebarCollapsed }">
        <div class="manager-sidebar">
          <DbSidebar
            :db-type="activeDbType"
            :account-alias="accountAlias"
            :container-id="effectiveContainerId"
            @select-table="handleSelectTable"
            @select-database="handleSelectDatabase"
            @select-redis-db="handleSelectRedisDb"
            @disconnect="handleDisconnect"
          />
        </div>

        <div class="sidebar-toggle" @click="store.toggleSidebar()">
          <Md3Icon :name="store.sidebarCollapsed ? 'chevron-right' : 'chevron-left'" size="16" />
        </div>

        <div class="manager-content">
          <div class="content-tabs">
            <Md3Tabs v-model="currentTab" :tabs="viewTabs" />
          </div>

          <div class="content-body">
            <div v-show="store.currentViewMode === 'query'">
              <SqlQueryEditor
                :account-alias="accountAlias"
                :container-id="effectiveContainerId ?? ''"
                :loading="store.mysqlQueryLoading"
                @execute="handleExecuteQuery"
              />
              <SqlResultTable :result="store.mysqlQueryResult" />
            </div>

            <div v-show="store.currentViewMode === 'data'">
              <DataEditor
                :account-alias="accountAlias"
                :container-id="effectiveContainerId"
                :table-name="selectedTableName"
              />
            </div>

            <div v-show="store.currentViewMode === 'structure'">
              <TableInfoPanel
                :container-id="effectiveContainerId ?? ''"
                :account-alias="accountAlias"
              />
            </div>

            <div v-show="store.currentViewMode === 'redis-browse'">
              <div class="redis-browse-layout">
                <RedisKeyList
                  :container-id="effectiveContainerId ?? ''"
                  :account-alias="accountAlias"
                  @select="handleRedisKeySelect"
                />
                <div class="redis-detail-area">
                  <RedisKeyDetail
                    :key-info="store.redisKeyInfo"
                    :container-id="effectiveContainerId ?? ''"
                    :account-alias="accountAlias"
                    @deleted="handleRedisKeyDeleted"
                  />
                  <Md3Empty v-if="!store.redisKeyInfo" description="选择左侧 Key 查看详情" />
                </div>
              </div>
            </div>

            <div v-show="store.currentViewMode === 'redis-stats'">
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

            <div v-show="store.currentViewMode === 'cli'" class="cli-view">
              <div v-if="showReconnectBanner && store.currentViewMode === 'cli'" class="reconnect-banner">
                <Md3Icon name="alert-circle" size="16" />
                <span>连接已断开</span>
                <Md3Button variant="primary" size="sm" @click="reconnectWs">重新连接</Md3Button>
              </div>
              <Terminal
                ref="terminalRef"
                :session-name="cliSessionName"
                :show-toolbar="true"
                @data="handleTerminalInput"
                @resize="handleTerminalResize"
              />
            </div>

            <div v-show="store.currentViewMode === 'welcome'">
              <Md3Empty description="选择左侧对象开始操作，或切换到查询/终端标签" />
            </div>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onBeforeUnmount } from 'vue'
import { useDbToolkitStore } from '@/stores/dbToolkitStore'
import type { DeployMode, SavedConnection, DbType, DbViewMode } from '@/types/db-toolkit'
import DbSidebar from '@/components/DbSidebar.vue'
import DbConnectionManager from '@/components/DbConnectionManager.vue'
import SqlQueryEditor from '@/components/SqlQueryEditor.vue'
import SqlResultTable from '@/components/SqlResultTable.vue'
import DataEditor from '@/components/DataEditor.vue'
import TableInfoPanel from '@/components/TableInfoPanel.vue'
import RedisKeyList from '@/components/RedisKeyList.vue'
import RedisKeyDetail from '@/components/RedisKeyDetail.vue'
import Terminal from '@/components/Terminal.vue'
import { Md3Tabs, Md3Icon, Md3Empty, Md3Message } from '@/components/md3'
import Md3Button from '@/components/Md3Button.vue'

const props = withDefaults(defineProps<{
  deployMode: DeployMode
  accountAlias: string
  containerId?: string
  containerState?: string
}>(), {
  containerState: '',
})

const store = useDbToolkitStore()
const terminalRef = ref<InstanceType<typeof Terminal>>()
const selectedTableName = ref('')
const wsConnected = ref(false)
const showReconnectBanner = ref(false)
let ws: WebSocket | null = null

const isConnected = computed(() => !!store.mysqlConnection || !!store.redisConnection)

const activeDbType = computed<DbType>(() => {
  return store.activeConnection?.dbType ?? 'mysql'
})

const effectiveContainerId = computed(() => {
  if (props.deployMode === 'docker') return props.containerId
  return undefined
})

const currentTab = computed({
  get: () => store.currentViewMode as string | number,
  set: (val: string | number) => store.setViewMode(val as DbViewMode),
})

const viewTabs = computed(() => {
  if (activeDbType.value === 'mysql') {
    return [
      { label: 'SQL 查询', value: 'query' },
      { label: '数据浏览', value: 'data' },
      { label: '表结构', value: 'structure' },
      { label: 'CLI 终端', value: 'cli' },
    ]
  }
  return [
    { label: 'Key 浏览', value: 'redis-browse' },
    { label: '数据库概览', value: 'redis-stats' },
    { label: 'CLI 终端', value: 'cli' },
  ]
})

const cliSessionName = computed(() => {
  if (activeDbType.value === 'mysql') {
    return `MySQL CLI (${store.mysqlConnection?.host}:${store.mysqlConnection?.port})`
  }
  return `Redis CLI (${store.redisConnection?.host}:${store.redisConnection?.port})`
})

function handleConnect(conn: SavedConnection) {
  store.setActiveConnection(conn)
  if (activeDbType.value === 'mysql') {
    store.setViewMode('query')
  } else {
    store.setViewMode('redis-browse')
    loadRedisStats()
  }
  connectWebSocket()
}

function handleDisconnect() {
  disconnectWebSocket()
  store.setActiveConnection(null)
  store.disconnectMysql()
  store.disconnectRedis()
  store.setViewMode('welcome')
  selectedTableName.value = ''
}

function handleSelectTable(tableName: string) {
  selectedTableName.value = tableName
  store.setViewMode('data')
}

function handleSelectDatabase(_dbName: string) {
  store.setViewMode('data')
}

function handleSelectRedisDb(_dbIndex: number) {
  store.setViewMode('redis-browse')
  loadRedisStats()
}

async function handleExecuteQuery(sql: string) {
  try {
    await store.executeMysqlQuery(props.accountAlias, effectiveContainerId.value, sql)
  } catch (e: any) {
    Md3Message.error(e?.response?.data?.detail || e?.message || '查询执行失败')
  }
}

async function handleRedisKeySelect(key: string) {
  try {
    await store.loadRedisKeyDetail(props.accountAlias, effectiveContainerId.value, key)
  } catch (e: any) {
    Md3Message.error(e?.response?.data?.detail || e?.message || '加载 Key 详情失败')
  }
}

function handleRedisKeyDeleted() {
  store.redisKeyInfo = null
}

async function loadRedisStats() {
  try {
    await store.loadRedisDbStats(props.accountAlias, effectiveContainerId.value)
  } catch (e: any) {
    Md3Message.error(e?.response?.data?.detail || e?.message || '加载 Redis 统计信息失败')
  }
}

function connectWebSocket() {
  if (ws) disconnectWebSocket()
  const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:'
  const containerPart = effectiveContainerId.value ? `/${effectiveContainerId.value}` : ''
  const dbType = activeDbType.value
  const url = `${protocol}//${location.host}/api/db-toolkit/ws/${dbType}-cli${containerPart}`
  ws = new WebSocket(url)
  ws.onopen = () => {
    wsConnected.value = true
    showReconnectBanner.value = false
    const connection = dbType === 'mysql' ? store.mysqlConnection : store.redisConnection
    ws?.send(JSON.stringify({
      account_alias: props.accountAlias,
      connection,
    }))
  }
  ws.onmessage = (event) => {
    const msg = JSON.parse(event.data)
    if (msg.type === 'data') {
      let content = msg.content
      if (dbType === 'redis') {
        content = content.replace(/Warning: Using a password with '-a'.*?\n/g, '')
      }
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
    wsConnected.value = false
    showReconnectBanner.value = true
    terminalRef.value?.writeln('\r\nWebSocket 连接错误')
    Md3Message.error('WebSocket 连接错误')
  }
  ws.onclose = () => {
    wsConnected.value = false
    showReconnectBanner.value = true
    ws = null
  }
}

function disconnectWebSocket() {
  if (ws) {
    ws.close()
    ws = null
  }
}

function reconnectWs() {
  disconnectWebSocket()
  connectWebSocket()
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

onBeforeUnmount(() => {
  disconnectWebSocket()
})
</script>

<style scoped>
.db-manager-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 400px;
}

.connect-prompt {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--md3-space-3xl) var(--md3-space-xl);
}

.manager-layout {
  display: flex;
  height: 100%;
  position: relative;
}

.manager-sidebar {
  width: 240px;
  flex-shrink: 0;
  transition: width var(--md3-motion-duration-medium) var(--md3-motion-easing-emphasized);
  overflow: hidden;
}

.sidebar-collapsed .manager-sidebar {
  width: 0;
  border-right: none;
}

.sidebar-toggle {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  flex-shrink: 0;
  cursor: pointer;
  color: var(--md3-on-surface-variant);
  background: var(--md3-surface-container-low);
  border-right: 1px solid var(--md3-outline-variant);
  transition: background var(--md3-motion-duration-short) var(--md3-motion-easing-standard),
              color var(--md3-motion-duration-short) var(--md3-motion-easing-standard);
}

.sidebar-toggle:hover {
  background: var(--md3-surface-container);
  color: var(--md3-primary);
}

.manager-content {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.content-tabs {
  flex-shrink: 0;
  padding: var(--md3-space-xs) var(--md3-space-md);
  border-bottom: 1px solid var(--md3-outline-variant);
}

.content-body {
  flex: 1;
  overflow-y: auto;
  padding: var(--md3-space-md);
}

.cli-view {
  height: 400px;
}

.reconnect-banner {
  display: flex;
  align-items: center;
  gap: var(--md3-space-sm);
  padding: var(--md3-space-sm) var(--md3-space-md);
  background: rgba(244, 67, 54, 0.1);
  border-radius: var(--md3-shape-xs);
  margin-bottom: var(--md3-space-sm);
  color: var(--md3-error, #f44336);
  font-size: 13px;
}

.redis-browse-layout {
  display: flex;
  gap: var(--md3-space-md);
  min-height: 300px;
}

.redis-browse-layout > :first-child {
  width: 300px;
  flex-shrink: 0;
}

.redis-detail-area {
  flex: 1;
  display: flex;
  flex-direction: column;
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
  border: 1px solid var(--md3-outline-variant);
}

.stat-label {
  font: var(--md3-type-body-small);
  color: var(--md3-on-surface-variant);
}

.stat-value {
  font: var(--md3-type-headline-small);
  font-weight: 600;
  color: var(--md3-on-surface);
}

@media (max-width: 768px) {
  .manager-layout {
    flex-direction: column;
  }

  .manager-sidebar {
    width: 100% !important;
    max-height: 40vh;
    border-right: none;
    border-bottom: 1px solid var(--md3-outline-variant);
  }

  .sidebar-collapsed .manager-sidebar {
    max-height: 0;
    width: 100% !important;
  }

  .sidebar-toggle {
    width: 100%;
    height: 20px;
    border-right: none;
    border-bottom: 1px solid var(--md3-outline-variant);
  }

  .redis-browse-layout {
    flex-direction: column;
  }

  .redis-browse-layout > :first-child {
    width: 100%;
  }

  .stats-grid {
    grid-template-columns: 1fr;
  }
}
</style>
