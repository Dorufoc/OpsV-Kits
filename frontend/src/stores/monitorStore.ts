import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { request } from '@/api'

export interface SnapshotData {
  timestamp: number
  alias: string
  hostname: string
  cpu: { usage_percent: number; cores: number; user_percent: number; system_percent: number; iowait_percent: number }
  cores: { core: number; usage_percent: number }[]
  memory: { total: number; used: number; free: number; available: number; usage_percent: number; available_percent: number; swap?: { total: number; used: number; free: number; usage_percent: number } }
  disks: { filesystem: string; total: number; used: number; available: number; usage_percent: number; mount: string }[]
  network: { interface: string; rx_bytes_per_sec: number; tx_bytes_per_sec: number; rx_packets_per_sec: number; tx_packets_per_sec: number }[]
  load: { load_1m: number; load_5m: number; load_15m: number; running: number; total_processes: number }
  connections: Record<string, number>
  top_processes: { pid: number; user: string; cpu_percent: number; mem_percent: number; command: string }[]
  uptime: number
  docker_containers: {
    name: string; container_id: string; cpu_percent: number; mem_percent: number
    mem_used: number; mem_total: number; net_rx: number; net_tx: number
    block_read: number; block_write: number; pids: number
  }[]
}

export const useMonitorStore = defineStore('monitor', () => {
  const currentAlias = ref('')
  const snapshot = ref<SnapshotData | null>(null)
  const loading = ref(false)
  const streaming = ref(false)
  const ws = ref<WebSocket | null>(null)
  const history = ref<SnapshotData[]>([])
  const maxHistory = 300

  const cpuPercent = computed(() => snapshot.value?.cpu?.usage_percent ?? 0)
  const memPercent = computed(() => snapshot.value?.memory?.usage_percent ?? 0)
  const memTotal = computed(() => snapshot.value?.memory?.total ?? 0)
  const memUsed = computed(() => snapshot.value?.memory?.used ?? 0)
  const loadAvg = computed(() => snapshot.value?.load ?? { load_1m: 0, load_5m: 0, load_15m: 0 })
  const hostname = computed(() => snapshot.value?.hostname ?? '')

  function formatBytes(bytes: number): string {
    if (!bytes || bytes <= 0) return '0 B'
    const units = ['B', 'KB', 'MB', 'GB', 'TB']
    const i = Math.floor(Math.log(bytes) / Math.log(1024))
    return (bytes / Math.pow(1024, i)).toFixed(1) + ' ' + units[i]
  }

  async function fetchSnapshot(alias?: string) {
    const a = alias || currentAlias.value
    if (!a) return

    const now = Date.now()
    const recentThreshold = 5000

    const existing = history.value
      .filter((h) => h.alias === a && now - h.timestamp * 1000 < recentThreshold)
      .sort((x, y) => y.timestamp - x.timestamp)

    if (existing.length > 0) {
      snapshot.value = existing[0]
      return existing[0]
    }

    loading.value = true
    try {
      const res = await request.get<SnapshotData>('/monitor/snapshot', { params: { alias: a } })
      snapshot.value = res
      history.value.push(res)
      if (history.value.length > maxHistory) history.value.shift()
      return res
    } finally {
      loading.value = false
    }
  }

  function connectWebSocket(alias?: string) {
    const a = alias || currentAlias.value
    if (!a) return
    if (ws.value) disconnect()
    const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:'
    const url = `${protocol}//${location.host}/api/monitor/ws/stream?alias=${encodeURIComponent(a)}`
    ws.value = new WebSocket(url)
    ws.value.onopen = () => {
      streaming.value = true
      fetchHistory(a).then((hist) => {
        if (hist && hist.length > 0) {
          snapshot.value = hist[hist.length - 1]
        }
      })
    }
    ws.value.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        if (data.type === 'pong') return
        snapshot.value = data
        history.value.push(data)
        if (history.value.length > maxHistory) history.value.shift()
      } catch {}
    }
    ws.value.onclose = () => {
      streaming.value = false
      ws.value = null
    }
    ws.value.onerror = () => {
      streaming.value = false
      ws.value = null
    }
  }

  function disconnect() {
    if (ws.value) {
      ws.value.close()
      ws.value = null
    }
    streaming.value = false
  }

  async function fetchHistory(alias?: string, seconds = 300) {
    const a = alias || currentAlias.value
    if (!a) return
    const res = await request.get<{ history: SnapshotData[] }>('/monitor/history', { params: { alias: a, seconds } })
    history.value = res.history || []
    return history.value
  }

  async function initWithHistory(alias?: string) {
    const a = alias || currentAlias.value
    if (!a) return
    const hist = await fetchHistory(a, 300)
    if (hist && hist.length > 0) {
      snapshot.value = hist[hist.length - 1]
    }
  }

  return {
    currentAlias, snapshot, loading, streaming, ws, history,
    cpuPercent, memPercent, memTotal, memUsed, loadAvg, hostname,
    formatBytes, fetchSnapshot, connectWebSocket, disconnect, fetchHistory,
    initWithHistory,
  }
})
