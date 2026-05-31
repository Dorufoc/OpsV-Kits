<template>
  <div class="container-stats-panel">
    <div class="stats-header">
      <span class="stats-title">资源统计</span>
      <div class="stats-actions">
        <Md3Switch v-model="autoRefresh" @update:model-value="toggleRefresh" />
        <span class="auto-refresh-label">自动刷新</span>
      </div>
    </div>

    <div class="stats-grid">
      <div class="stat-card">
        <div class="stat-icon cpu-icon">
          <Md3Icon name="chip" size="24" />
        </div>
        <div class="stat-content">
          <div class="stat-label">CPU 使用率</div>
          <div class="stat-value">{{ stats.cpu_percent || '0.00' }}%</div>
          <div class="stat-bar">
            <div class="stat-bar-fill" :style="{ width: stats.cpu_percent + '%' }"></div>
          </div>
        </div>
      </div>

      <div class="stat-card">
        <div class="stat-icon memory-icon">
          <Md3Icon name="memory" size="24" />
        </div>
        <div class="stat-content">
          <div class="stat-label">内存使用</div>
          <div class="stat-value">{{ formatMemory(stats.mem_usage, stats.mem_limit) }}</div>
          <div class="stat-bar">
            <div class="stat-bar-fill" :style="{ width: memoryPercent + '%' }" :class="{ 'memory-warning': memoryPercent > 80 }"></div>
          </div>
          <div class="stat-detail">{{ memoryPercent }}%</div>
        </div>
      </div>

      <div class="stat-card">
        <div class="stat-icon network-icon">
          <Md3Icon name="wifi" size="24" />
        </div>
        <div class="stat-content">
          <div class="stat-label">网络 I/O</div>
          <div class="stat-value-net">
            <div class="net-row">
              <span class="net-label">↓ 接收:</span>
              <span class="net-value">{{ formatBytes(stats.net_rx || 0) }}</span>
            </div>
            <div class="net-row">
              <span class="net-label">↑ 发送:</span>
              <span class="net-value">{{ formatBytes(stats.net_tx || 0) }}</span>
            </div>
          </div>
        </div>
      </div>

      <div class="stat-card">
        <div class="stat-icon disk-icon">
          <Md3Icon name="hard-drive" size="24" />
        </div>
        <div class="stat-content">
          <div class="stat-label">磁盘 I/O</div>
          <div class="stat-value-net">
            <div class="net-row">
              <span class="net-label">↓ 读取:</span>
              <span class="net-value">{{ formatBytes(stats.block_read || 0) }}</span>
            </div>
            <div class="net-row">
              <span class="net-label">↑ 写入:</span>
              <span class="net-value">{{ formatBytes(stats.block_write || 0) }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div class="stats-detail" v-if="stats.pids !== undefined">
      <div class="detail-item">
        <span class="detail-label">进程数:</span>
        <span class="detail-value">{{ stats.pids }}</span>
      </div>
      <div class="detail-item">
        <span class="detail-label">容器 ID:</span>
        <span class="detail-value mono-text">{{ containerId }}</span>
      </div>
    </div>

    <div class="stats-updated" v-if="lastUpdated">
      最后更新: {{ lastUpdated }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { Md3Icon, Md3Switch } from '@/components/md3'
import { useDockerStore } from '@/stores/dockerStore'

const props = defineProps<{
  containerId: string
}>()

const dockerStore = useDockerStore()
const stats = ref<any>({})
const autoRefresh = ref(false)
const lastUpdated = ref('')
const refreshTimer = ref<number | null>(null)

const memoryPercent = computed(() => {
  if (!stats.value.mem_usage || !stats.value.mem_limit) return 0
  return Math.round((stats.value.mem_usage / stats.value.mem_limit) * 100)
})

let refreshInterval: number | null = null

async function loadStats() {
  try {
    const data = await dockerStore.getContainerStats(props.containerId)
    if (data && data.length > 0) {
      const raw = data[0]
      const memUsageRaw = raw.MemUsage || raw.mem_usage || '0B / 0B'
      const memParts = memUsageRaw.split('/')
      const netIORaw = raw.NetIO || raw.net_io || raw.net_rx || '0B / 0B'
      const blockIORaw = raw.BlockIO || raw.block_io || raw.block_read || '0B / 0B'

      stats.value = {
        cpu_percent: parseCPUPercent(raw.CPUPerc || raw.cpu_percent),
        mem_usage: parseBytes(memParts[0] || '0B'),
        mem_limit: parseBytes(memParts[1] || '0B'),
        net_rx: parseBytes(netIORaw, 'in'),
        net_tx: parseBytes(netIORaw, 'out'),
        block_read: parseBytes(blockIORaw, 'in'),
        block_write: parseBytes(blockIORaw, 'out'),
        pids: raw.PIDs || raw.pids || 0,
      }
      lastUpdated.value = new Date().toLocaleTimeString('zh-CN')
    }
  } catch (e) {
    console.error('加载容器统计失败:', e)
  }
}

function parseCPUPercent(value: string): number {
  if (!value) return 0
  const num = parseFloat(value.replace('%', ''))
  return isNaN(num) ? 0 : Math.round(num * 100) / 100
}

function parseBytes(value: string | number, direction?: 'in' | 'out'): number {
  if (typeof value === 'number') return value
  if (!value) return 0
  if (direction) {
    const parts = value.split('/')
    const idx = direction === 'in' ? 0 : 1
    value = parts[idx] || '0B'
  }
  value = value.trim()
  const multipliers: Record<string, number> = {
    'TiB': 1024 ** 4,
    'T': 1024 ** 4,
    'GiB': 1024 ** 3,
    'G': 1024 ** 3,
    'MiB': 1024 ** 2,
    'M': 1024 ** 2,
    'KiB': 1024,
    'K': 1024,
    'B': 1,
  }
  const sortedUnits = Object.keys(multipliers).sort((a, b) => b.length - a.length)
  for (const unit of sortedUnits) {
    if (value.endsWith(unit)) {
      const numStr = value.slice(0, -unit.length).trim()
      const num = parseFloat(numStr)
      return isNaN(num) ? 0 : Math.round(num * multipliers[unit])
    }
  }
  const num = parseFloat(value)
  return isNaN(num) ? 0 : num
}

function formatMemory(usage: number, limit: number): string {
  return `${formatBytes(usage)} / ${formatBytes(limit)}`
}

function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return (bytes / Math.pow(k, i)).toFixed(1) + ' ' + sizes[i]
}

function toggleRefresh(value: boolean) {
  if (value) {
    loadStats()
    refreshInterval = window.setInterval(loadStats, 3000)
  } else {
    if (refreshInterval) {
      clearInterval(refreshInterval)
      refreshInterval = null
    }
  }
}

onMounted(() => {
  loadStats()
})

onUnmounted(() => {
  if (refreshInterval) {
    clearInterval(refreshInterval)
  }
})
</script>

<style scoped>
.container-stats-panel {
  padding: var(--md3-space-md);
  background: var(--md3-surface-container-low);
  border-radius: var(--md3-shape-md);
  border: 1px solid var(--md3-outline-variant);
}

.stats-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--md3-space-md);
  padding-bottom: var(--md3-space-sm);
  border-bottom: 1px solid var(--md3-outline-variant);
}

.stats-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--md3-on-surface);
}

.stats-actions {
  display: flex;
  align-items: center;
  gap: var(--md3-space-xs);
}

.auto-refresh-label {
  font-size: 12px;
  color: var(--md3-on-surface-variant);
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--md3-space-md);
}

.stat-card {
  display: flex;
  gap: var(--md3-space-md);
  padding: var(--md3-space-md);
  background: var(--md3-surface-container);
  border-radius: var(--md3-shape-sm);
  border: 1px solid var(--md3-outline-variant);
  transition: border-color var(--md3-motion-duration-short) var(--md3-motion-easing-standard);
}

.stat-card:hover {
  border-color: var(--md3-card-border-hover);
}

.stat-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 48px;
  height: 48px;
  border-radius: var(--md3-shape-sm);
  flex-shrink: 0;
}

.cpu-icon {
  background: var(--md3-primary-container);
  color: var(--md3-on-primary-container);
}

.memory-icon {
  background: var(--md3-secondary-container);
  color: var(--md3-on-secondary-container);
}

.network-icon {
  background: var(--md3-tertiary-container);
  color: var(--md3-on-tertiary-container);
}

.disk-icon {
  background: var(--md3-surface-container-high);
  color: var(--md3-on-surface-variant);
}

.stat-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: var(--md3-space-xs);
  min-width: 0;
}

.stat-label {
  font-size: 12px;
  color: var(--md3-on-surface-variant);
  font-weight: 500;
}

.stat-value {
  font-size: 20px;
  font-weight: 600;
  color: var(--md3-on-surface);
  font-family: var(--md3-font-mono);
}

.stat-value-net {
  display: flex;
  flex-direction: column;
  gap: var(--md3-space-xs);
}

.net-row {
  display: flex;
  align-items: center;
  gap: var(--md3-space-xs);
  font-size: 13px;
}

.net-label {
  color: var(--md3-on-surface-variant);
  font-size: 11px;
}

.net-value {
  font-family: var(--md3-font-mono);
  color: var(--md3-on-surface);
  font-weight: 500;
}

.stat-bar {
  height: 6px;
  background: var(--md3-surface-container-highest);
  border-radius: var(--md3-shape-xs);
  overflow: hidden;
  margin-top: var(--md3-space-xs);
}

.stat-bar-fill {
  height: 100%;
  background: var(--md3-primary);
  border-radius: var(--md3-shape-xs);
  transition: width var(--md3-motion-duration-medium) var(--md3-motion-easing-standard);
}

.stat-bar-fill.memory-warning {
  background: var(--md3-error);
}

.stat-detail {
  font-size: 11px;
  color: var(--md3-on-surface-variant);
  text-align: right;
  margin-top: var(--md3-space-xs);
}

.stats-detail {
  display: flex;
  gap: var(--md3-space-lg);
  margin-top: var(--md3-space-md);
  padding-top: var(--md3-space-sm);
  border-top: 1px solid var(--md3-outline-variant);
}

.detail-item {
  display: flex;
  align-items: center;
  gap: var(--md3-space-xs);
  font-size: 12px;
}

.detail-label {
  color: var(--md3-on-surface-variant);
}

.detail-value {
  color: var(--md3-on-surface);
  font-family: var(--md3-font-mono);
}

.mono-text {
  font-size: 11px;
}

.stats-updated {
  margin-top: var(--md3-space-sm);
  font-size: 11px;
  color: var(--md3-outline);
  text-align: right;
}

@media (max-width: 768px) {
  .stats-grid {
    grid-template-columns: 1fr;
  }
}
</style>
