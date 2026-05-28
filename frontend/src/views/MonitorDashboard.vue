<template>
  <div class="monitor-dashboard">
    <Md3PageHeader title="全维度资源监控">
      <template #subtitle>
        <span>实时监控仪表盘</span>
      </template>
      <template #actions>
        <Md3Select v-model="selectedAlias" :options="selectOptions" placeholder="选择服务器" style="width: 200px" @update:model-value="onAccountChange" />
        <Md3Button size="sm" @click="refreshAll" :disabled="!selectedAlias"><Md3Icon name="refresh" size="1em" />刷新</Md3Button>
        <Md3Button size="sm" @click="toggleStream" :type="streaming ? 'danger' : 'primary'">
          <Md3Icon name="monitor" size="1em" />{{ streaming ? '停止推送' : '实时推送' }}
        </Md3Button>
        <Md3Button size="sm" @click="goLargeScreen"><Md3Icon name="fullscreen" size="1em" />大屏模式</Md3Button>
      </template>
    </Md3PageHeader>
    <Md3Divider />

    <template v-if="!selectedAlias">
      <Md3Empty description="请先选择一台服务器查看监控" />
    </template>

    <template v-else-if="!snapshot && loading">
      <div class="loading-state">
        <Md3Icon name="loading" size="24" class="is-loading icon-lg" />
        <span>正在采集监控数据...</span>
      </div>
    </template>

    <template v-else-if="snapshot">
      <!-- Status Banner -->
      <div class="status-banner">
        <div class="status-item"><Md3Icon name="monitor" size="16" class="icon-sm" /> {{ snapshot.hostname }}</div>
        <div class="status-item"><Md3Icon name="timer" size="16" class="icon-sm" /> 运行: {{ formatUptime(snapshot.uptime) }}</div>
        <div class="status-item"><Md3Icon name="cpu" size="16" class="icon-sm" /> 负载: {{ snapshot.load.load_1m.toFixed(2) }} / {{ snapshot.load.load_5m.toFixed(2) }} / {{ snapshot.load.load_15m.toFixed(2) }}</div>
        <div class="status-item"><Md3Icon name="connection" size="16" class="icon-sm" /> 进程: {{ snapshot.load.running }}/{{ snapshot.load.total_processes }}</div>
        <div class="status-item" v-if="streaming"><Md3Icon name="loading" size="16" class="is-loading icon-sm" /> 实时</div>
      </div>

      <!-- Gauge Row -->
      <div class="grid-12 gap-12">
        <div class="span-6"><Md3Card class="gauge-card"><MonitorGaugeChart :value="snapshot.cpu.usage_percent" title="CPU 使用率" height="180px" /></Md3Card></div>
        <div class="span-6"><Md3Card class="gauge-card"><MonitorGaugeChart :value="snapshot.memory.usage_percent" title="内存使用率" height="180px" /></Md3Card></div>
        <div class="span-6"><Md3Card class="gauge-card"><MonitorGaugeChart :value="diskUsageAvg" title="磁盘使用率" height="180px" /></Md3Card></div>
        <div class="span-6"><Md3Card class="gauge-card"><MonitorGaugeChart :value="dockerCpuAvg" title="Docker CPU" height="180px" :max="100" /></Md3Card></div>
      </div>

      <!-- Tabs -->
      <Md3Tabs v-model="activeTab" :tabs="tabItems" class="monitor-tabs" />

      <!-- Tab: Overview -->
      <div v-if="activeTab === 'overview'" class="tab-panel">
        <div class="grid-12 gap-12">
          <div class="span-16">
            <Md3Card class="chart-card">
              <template #header><span class="card-title"><Md3Icon name="cpu" size="16" class="icon-sm" /> CPU 使用率历史 (最近 60 个采样点)</span></template>
              <MonitorLineChart :data="cpuSeries" color="#1a73e8" yAxisName="%" height="220px" />
            </Md3Card>
          </div>
          <div class="span-8">
            <Md3Card class="chart-card">
              <template #header><span class="card-title"><Md3Icon name="coin" size="16" class="icon-sm" /> 内存分布</span></template>
              <MonitorPieChart :data="memPieData" height="220px" />
            </Md3Card>
          </div>
        </div>
        <div class="grid-12 gap-12 mt-12">
          <div class="span-16">
            <Md3Card class="chart-card">
              <template #header><span class="card-title"><Md3Icon name="coin" size="16" class="icon-sm" /> 内存使用率历史</span></template>
              <MonitorLineChart :data="memSeries" color="#22c55e" yAxisName="%" height="220px" />
            </Md3Card>
          </div>
          <div class="span-8">
            <Md3Card class="chart-card">
              <template #header><span class="card-title"><Md3Icon name="connection" size="16" class="icon-sm" /> 网络连接状态</span></template>
              <MonitorPieChart :data="connPieData" height="220px" :donut="true" />
            </Md3Card>
          </div>
        </div>
      </div>

      <!-- Tab: CPU -->
      <div v-if="activeTab === 'cpu'" class="tab-panel">
        <div class="grid-12 gap-12">
          <div class="span-12">
            <Md3Card class="chart-card">
              <template #header><span class="card-title">CPU 核心使用率热力图</span></template>
              <MonitorHeatmap :data="coreHeatData" height="260px" />
            </Md3Card>
          </div>
          <div class="span-12">
            <Md3Card class="chart-card">
              <template #header><span class="card-title">CPU 详情</span></template>
              <div class="info-grid">
                <div class="info-row"><span class="info-label">使用率</span><span class="info-value" :style="{ color: cpuColor }">{{ snapshot.cpu.usage_percent }}%</span></div>
                <div class="info-row"><span class="info-label">用户态</span><span class="info-value">{{ snapshot.cpu.user_percent }}%</span></div>
                <div class="info-row"><span class="info-label">系统态</span><span class="info-value">{{ snapshot.cpu.system_percent }}%</span></div>
                <div class="info-row"><span class="info-label">I/O 等待</span><span class="info-value">{{ snapshot.cpu.iowait_percent }}%</span></div>
                <div class="info-row"><span class="info-label">核心数</span><span class="info-value">{{ snapshot.cpu.cores }}</span></div>
              </div>
            </Md3Card>
          </div>
        </div>
        <div class="grid-12 gap-12 mt-12">
          <div class="span-24">
            <Md3Card class="chart-card">
              <template #header><span class="card-title">Top 进程 (CPU)</span></template>
              <Md3Table :columns="procColumns" :data="snapshot.top_processes.slice(0, 8)" stripe>
                <template #cpu_percent="{ row }"><span :style="{ color: (row.cpu_percent as number) > 50 ? '#ef4444' : '#22c55e' }">{{ row.cpu_percent }}%</span></template>
                <template #mem_percent="{ row }">{{ row.mem_percent }}%</template>
              </Md3Table>
            </Md3Card>
          </div>
        </div>
      </div>

      <!-- Tab: Memory -->
      <div v-if="activeTab === 'memory'" class="tab-panel">
        <div class="grid-12 gap-12">
          <div class="span-8">
            <Md3Card class="chart-card">
              <template #header><span class="card-title">内存概览</span></template>
              <div class="info-grid">
                <div class="info-row"><span class="info-label">总计</span><span class="info-value">{{ store.formatBytes(snapshot.memory.total) }}</span></div>
                <div class="info-row"><span class="info-label">已用</span><span class="info-value" :style="{ color: memColor }">{{ store.formatBytes(snapshot.memory.used) }}</span></div>
                <div class="info-row"><span class="info-label">可用</span><span class="info-value">{{ store.formatBytes(snapshot.memory.available) }}</span></div>
                <div class="info-row"><span class="info-label">空闲</span><span class="info-value">{{ store.formatBytes(snapshot.memory.free) }}</span></div>
              </div>
              <div v-if="snapshot.memory.swap" style="margin-top: 12px; border-top: 1px solid var(--md3-glass-border); padding-top: 12px;">
                <div class="info-grid">
                  <div class="info-row"><span class="info-label">Swap 总计</span><span class="info-value">{{ store.formatBytes(snapshot.memory.swap.total) }}</span></div>
                  <div class="info-row"><span class="info-label">Swap 已用</span><span class="info-value">{{ store.formatBytes(snapshot.memory.swap.used) }}</span></div>
                  <div class="info-row"><span class="info-label">Swap 使用率</span><span class="info-value">{{ snapshot.memory.swap.usage_percent }}%</span></div>
                </div>
              </div>
            </Md3Card>
          </div>
          <div class="span-16">
            <Md3Card class="chart-card">
              <template #header><span class="card-title">内存使用率趋势</span></template>
              <MonitorLineChart :data="memSeries" color="#22c55e" yAxisName="%" height="300px" />
            </Md3Card>
          </div>
        </div>
      </div>

      <!-- Tab: Disk -->
      <div v-if="activeTab === 'disk'" class="tab-panel">
        <div class="grid-12 gap-12">
          <div class="span-24">
            <Md3Card class="chart-card">
              <template #header><span class="card-title">挂载点详情</span></template>
              <Md3Table :columns="diskColumns" :data="snapshot.disks" stripe>
                <template #usage_percent="{ row }">
                  <div class="disk-progress">
                    <Md3Progress :percentage="row.usage_percent as number" :color="diskColor(row.usage_percent as number)" />
                    <span class="disk-pct">{{ row.usage_percent }}%</span>
                  </div>
                </template>
                <template #used="{ row }">{{ store.formatBytes(row.used as number) }}</template>
                <template #total="{ row }">{{ store.formatBytes(row.total as number) }}</template>
              </Md3Table>
            </Md3Card>
          </div>
        </div>
      </div>

      <!-- Tab: Network -->
      <div v-if="activeTab === 'network'" class="tab-panel">
        <div class="grid-12 gap-12">
          <div class="span-24">
            <Md3Card class="chart-card">
              <template #header><span class="card-title">网络接口流量</span></template>
              <Md3Table :columns="netColumns" :data="snapshot.network" stripe>
                <template #rx_bytes_per_sec="{ row }">{{ store.formatBytes(row.rx_bytes_per_sec as number) }}/s</template>
                <template #tx_bytes_per_sec="{ row }">{{ store.formatBytes(row.tx_bytes_per_sec as number) }}/s</template>
                <template #rx_packets_per_sec="{ row }">{{ row.rx_packets_per_sec }} pkt/s</template>
                <template #tx_packets_per_sec="{ row }">{{ row.tx_packets_per_sec }} pkt/s</template>
              </Md3Table>
            </Md3Card>
          </div>
        </div>
        <div class="grid-12 gap-12 mt-12">
          <div class="span-12">
            <Md3Card class="chart-card">
              <template #header><span class="card-title">TCP 连接状态</span></template>
              <MonitorPieChart :data="connPieData" height="240px" />
            </Md3Card>
          </div>
          <div class="span-12">
            <Md3Card class="chart-card">
              <template #header><span class="card-title">连接计数</span></template>
              <div class="conn-grid">
                <div v-for="(v, k) in snapshot.connections" :key="k" class="conn-item">
                  <span class="conn-state">{{ k }}</span>
                  <span class="conn-count">{{ v }}</span>
                </div>
              </div>
            </Md3Card>
          </div>
        </div>
      </div>

      <!-- Tab: Docker -->
      <div v-if="activeTab === 'docker'" class="tab-panel">
        <div class="grid-12 gap-12">
          <div class="span-24">
            <Md3Card class="chart-card">
              <template #header><span class="card-title">容器资源使用</span></template>
              <Md3Table v-if="snapshot.docker_containers.length" :columns="dockerColumns" :data="snapshot.docker_containers" stripe>
                <template #cpu_percent="{ row }"><span :style="{ color: (row.cpu_percent as number) > 50 ? '#ef4444' : '#22c55e' }">{{ row.cpu_percent }}%</span></template>
                <template #mem_percent="{ row }"><span :style="{ color: (row.mem_percent as number) > 80 ? '#ef4444' : '#22c55e' }">{{ row.mem_percent }}%</span></template>
                <template #mem_used="{ row }">{{ store.formatBytes(row.mem_used as number) }}</template>
                <template #mem_total="{ row }">{{ store.formatBytes(row.mem_total as number) }}</template>
              </Md3Table>
              <Md3Empty v-else description="当前无 Docker 容器运行" />
            </Md3Card>
          </div>
        </div>
      </div>

      <!-- Tab: Middleware -->
      <div v-if="activeTab === 'middleware'" class="tab-panel">
        <Md3Card class="chart-card">
          <template #header><span class="card-title">中间件健康状态</span></template>
          <div class="mw-grid">
            <div v-for="(mw, name) in middlewareHealth" :key="name" class="mw-card" :class="{ alive: mw.alive }">
              <div class="mw-icon">
                <Md3Icon name="check-circle" size="28" class="icon-mw" v-if="mw.alive" /><Md3Icon name="alert-circle" size="28" class="icon-mw icon-danger" v-else />
              </div>
              <div class="mw-name">{{ String(name).toUpperCase() }}</div>
              <div class="mw-status">{{ mw.alive ? '运行中' : '未检测到' }}</div>
            </div>
          </div>
        </Md3Card>
      </div>

      <!-- Tab: Processes -->
      <div v-if="activeTab === 'processes'" class="tab-panel">
        <Md3Card class="chart-card">
          <template #header><span class="card-title">进程列表 (Top {{ snapshot.top_processes.length }})</span></template>
          <Md3Table :columns="procColumns" :data="snapshot.top_processes" stripe>
            <template #cpu_percent="{ row }"><span :style="{ color: (row.cpu_percent as number) > 50 ? '#ef4444' : '#22c55e' }">{{ row.cpu_percent }}%</span></template>
            <template #mem_percent="{ row }">{{ row.mem_percent }}%</template>
          </Md3Table>
        </Md3Card>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount, markRaw } from 'vue'
import { useRouter } from 'vue-router'
import { Md3Icon } from '@/components/md3'
import { useMonitorStore } from '@/stores/monitorStore'
import { useSshAccountStore } from '@/stores/sshAccountStore'
import {
  Md3PageHeader, Md3Divider, Md3Card, Md3Select, Md3Tabs, Md3Table, Md3Progress, Md3Empty,
} from '@/components/md3'
import Md3Button from '@/components/Md3Button.vue'
import MonitorLineChart from '@/components/MonitorLineChart.vue'
import MonitorGaugeChart from '@/components/MonitorGaugeChart.vue'
import MonitorPieChart from '@/components/MonitorPieChart.vue'
import MonitorHeatmap from '@/components/MonitorHeatmap.vue'

const POLL_INTERVAL = 5000

const router = useRouter()
const store = useMonitorStore()
const sshStore = useSshAccountStore()

const selectedAlias = ref('')
const activeTab = ref('overview')
const streaming = ref(false)
let pollTimer: ReturnType<typeof setInterval> | null = null

const selectOptions = computed(() =>
  sshStore.accounts.map(a => ({ label: `${a.alias} (${a.host})`, value: a.alias }))
)

const snapshot = computed(() => store.snapshot)
const loading = computed(() => store.loading)

const cpuSeries = computed(() => store.history.slice(-60).map(h => ({ time: h.timestamp, value: h.cpu?.usage_percent ?? 0 })))
const memSeries = computed(() => store.history.slice(-60).map(h => ({ time: h.timestamp, value: h.memory?.usage_percent ?? 0 })))

const diskUsageAvg = computed(() => {
  if (!snapshot.value?.disks?.length) return 0
  const main = snapshot.value.disks.find(d => d.mount === '/')
  return main ? main.usage_percent : snapshot.value.disks[0].usage_percent
})

const dockerCpuAvg = computed(() => {
  if (!snapshot.value?.docker_containers?.length) return 0
  const sum = snapshot.value.docker_containers.reduce((s, c) => s + c.cpu_percent, 0)
  return Math.round(sum / snapshot.value.docker_containers.length)
})

const coreHeatData = computed(() =>
  (snapshot.value?.cores || []).map(c => ({ name: `Core ${c.core}`, value: c.usage_percent }))
)

const memPieData = computed(() => {
  if (!snapshot.value?.memory) return []
  const m = snapshot.value.memory
  return [
    { name: '已使用', value: m.used },
    { name: '可用', value: m.available },
  ]
})

const connPieData = computed(() => {
  if (!snapshot.value?.connections) return []
  return Object.entries(snapshot.value.connections).map(([k, v]) => ({ name: k, value: v }))
})

const cpuColor = computed(() => (snapshot.value?.cpu?.usage_percent ?? 0) > 90 ? '#ef4444' : (snapshot.value?.cpu?.usage_percent ?? 0) > 75 ? '#f59e0b' : '#22c55e')
const memColor = computed(() => (snapshot.value?.memory?.usage_percent ?? 0) > 90 ? '#ef4444' : (snapshot.value?.memory?.usage_percent ?? 0) > 75 ? '#f59e0b' : '#22c55e')

const middlewareHealth = computed(() => {
  const h = (snapshot.value as any)?.middleware_health
  return h || { mysql: { alive: false }, redis: { alive: false }, rabbitmq: { alive: false }, nginx: { alive: false } }
})

const tabItems = [
  { label: '概览', value: 'overview', icon: markRaw({ template: '<Md3Icon name="monitor" size="1em" />', components: { Md3Icon } }) },
  { label: 'CPU', value: 'cpu', icon: markRaw({ template: '<Md3Icon name="cpu" size="1em" />', components: { Md3Icon } }) },
  { label: '内存', value: 'memory', icon: markRaw({ template: '<Md3Icon name="coin" size="1em" />', components: { Md3Icon } }) },
  { label: '磁盘', value: 'disk', icon: markRaw({ template: '<Md3Icon name="folder" size="1em" />', components: { Md3Icon } }) },
  { label: '网络', value: 'network', icon: markRaw({ template: '<Md3Icon name="connection" size="1em" />', components: { Md3Icon } }) },
  { label: 'Docker', value: 'docker', icon: markRaw({ template: '<Md3Icon name="docker" size="1em" />', components: { Md3Icon } }) },
  { label: '中间件', value: 'middleware', icon: markRaw({ template: '<Md3Icon name="timer" size="1em" />', components: { Md3Icon } }) },
  { label: '进程', value: 'processes', icon: markRaw({ template: '<Md3Icon name="monitor" size="1em" />', components: { Md3Icon } }) },
]

const diskColumns = [
  { prop: 'mount', label: '挂载点' },
  { prop: 'filesystem', label: '设备' },
  { prop: 'total', label: '总量' },
  { prop: 'used', label: '已用' },
  { prop: 'available', label: '可用' },
  { prop: 'usage_percent', label: '使用率' },
]

const netColumns = [
  { prop: 'interface', label: '接口' },
  { prop: 'rx_bytes_per_sec', label: '下行速率' },
  { prop: 'tx_bytes_per_sec', label: '上行速率' },
  { prop: 'rx_packets_per_sec', label: '下行包' },
  { prop: 'tx_packets_per_sec', label: '上行包' },
]

const procColumns = [
  { prop: 'pid', label: 'PID' },
  { prop: 'user', label: '用户' },
  { prop: 'cpu_percent', label: 'CPU%' },
  { prop: 'mem_percent', label: '内存%' },
  { prop: 'command', label: '命令' },
]

const dockerColumns = [
  { prop: 'name', label: '容器名' },
  { prop: 'container_id', label: 'ID' },
  { prop: 'cpu_percent', label: 'CPU%' },
  { prop: 'mem_percent', label: '内存%' },
  { prop: 'mem_used', label: '内存使用' },
  { prop: 'mem_total', label: '内存限制' },
  { prop: 'pids', label: 'PIDs' },
]

function formatUptime(seconds: number) {
  const d = Math.floor(seconds / 86400)
  const h = Math.floor((seconds % 86400) / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  return `${d}d ${h}h ${m}m`
}

function diskColor(pct: number) {
  return pct > 90 ? '#ef4444' : pct > 75 ? '#f59e0b' : '#22c55e'
}

function onAccountChange(value: string | number | (string | number)[]) {
  const alias = String(value)
  store.currentAlias = alias
  refreshAll()
}

async function refreshAll() {
  if (!selectedAlias.value) return
  store.currentAlias = selectedAlias.value
  await store.fetchSnapshot()
}

function toggleStream() {
  if (streaming.value) {
    store.disconnect()
    streaming.value = false
    stopPolling()
  } else {
    store.connectWebSocket(selectedAlias.value)
    streaming.value = true
  }
}

function startPolling() {
  if (pollTimer) return
  pollTimer = setInterval(() => {
    if (selectedAlias.value && !streaming.value) {
      store.fetchSnapshot()
    }
  }, POLL_INTERVAL)
}

function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

function goLargeScreen() {
  router.push('/monitor/large-screen')
}

onMounted(async () => {
  await sshStore.fetchAccounts()
  const defaultAcc = sshStore.accounts.find(a => a.default)
  const firstAcc = sshStore.accounts[0]
  const alias = defaultAcc?.alias || firstAcc?.alias || ''
  if (alias) {
    selectedAlias.value = alias
    store.currentAlias = alias
    await store.fetchSnapshot()
    startPolling()
  }
})

onBeforeUnmount(() => {
  store.disconnect()
  stopPolling()
})
</script>

<style scoped>
.monitor-dashboard {
  padding: 0;
}

.loading-state {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--md3-space-md);
  padding: 80px 0;
  color: var(--md3-on-surface-variant);
}

.icon-lg {
  width: 24px;
  height: 24px;
}

.icon-sm {
  width: 16px;
  height: 16px;
}

.icon-mw {
  width: 28px;
  height: 28px;
}

.icon-danger {
  color: #ef4444;
}

.is-loading {
  animation: rotating 2s linear infinite;
}

@keyframes rotating {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.grid-12 {
  display: grid;
  grid-template-columns: repeat(12, 1fr);
}

.gap-12 {
  gap: var(--md3-space-md);
}

.mt-12 {
  margin-top: var(--md3-space-md);
}

.span-6 {
  grid-column: span 3;
}

.span-8 {
  grid-column: span 4;
}

.span-12 {
  grid-column: span 6;
}

.span-16 {
  grid-column: span 8;
}

.span-24 {
  grid-column: span 12;
}

.status-banner {
  display: flex;
  gap: var(--md3-space-xl);
  flex-wrap: wrap;
  padding: var(--md3-space-md) var(--md3-space-lg);
  background: var(--md3-surface-container);
  border: 1px solid var(--md3-outline-variant);
  border-radius: var(--md3-shape-md);
  margin-bottom: var(--md3-space-md);
  font-size: 13px;
  color: var(--md3-on-surface-variant);
}

.status-item {
  display: flex;
  align-items: center;
  gap: var(--md3-space-xs);
}

.gauge-card :deep(.md3-card-body) {
  padding: var(--md3-space-sm);
}

.monitor-tabs {
  margin-bottom: var(--md3-space-lg);
}

.tab-panel {
  min-height: 200px;
}

.chart-card {
  margin-bottom: 0;
}

.chart-card :deep(.md3-card-header) {
  padding-bottom: var(--md3-space-xs);
}

.card-title {
  display: flex;
  align-items: center;
  gap: var(--md3-space-xs);
  font-size: 13px;
  font-weight: 600;
  color: var(--md3-on-surface);
}

.info-grid {
  display: flex;
  flex-direction: column;
  gap: var(--md3-space-sm);
  padding: var(--md3-space-sm) 0;
}

.info-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 13px;
  padding: var(--md3-space-xs) 0;
  border-bottom: 1px solid var(--md3-outline-variant);
}

.info-row:last-child {
  border-bottom: none;
}

.info-label {
  color: var(--md3-on-surface-variant);
}

.info-value {
  font-weight: 600;
  color: var(--md3-on-surface);
}

.disk-progress {
  display: flex;
  align-items: center;
  gap: var(--md3-space-sm);
}

.disk-pct {
  font-size: 12px;
  color: var(--md3-on-surface-variant);
  white-space: nowrap;
}

.conn-grid {
  display: flex;
  flex-wrap: wrap;
  gap: var(--md3-space-sm);
  padding: var(--md3-space-sm) 0;
}

.conn-item {
  display: flex;
  align-items: center;
  gap: var(--md3-space-sm);
  padding: var(--md3-space-xs) var(--md3-space-md);
  background: var(--md3-surface-container-low);
  border-radius: var(--md3-shape-sm);
  font-size: 13px;
}

.conn-state {
  color: var(--md3-on-surface-variant);
}

.conn-count {
  font-weight: 700;
  color: var(--md3-primary);
}

.mw-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  gap: var(--md3-space-md);
  padding: var(--md3-space-sm) 0;
}

.mw-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--md3-space-sm);
  padding: var(--md3-space-xl) var(--md3-space-lg);
  background: var(--md3-surface-container-low);
  border: 1px solid var(--md3-outline-variant);
  border-radius: var(--md3-shape-md);
  transition: box-shadow var(--md3-motion-duration-short) var(--md3-motion-easing-standard);
}

.mw-card:hover {
  box-shadow: var(--md3-elevation-level1);
}

.mw-card.alive {
  border-color: rgba(34, 197, 94, 0.3);
}

.mw-name {
  font-weight: 600;
  font-size: 14px;
  color: var(--md3-on-surface);
}

.mw-status {
  font-size: 12px;
  color: var(--md3-on-surface-variant);
}
</style>