import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { request } from '@/api'

/** 进程基本信息接口 */
export interface ProcessInfo {
  pid: number
  ppid: number
  user: string
  cpu_percent: number
  mem_percent: number
  vsz: number
  rss: number
  tty: string
  status: string // running/sleeping/zombie/stopped/idle/unknown
  start_time: string
  cpu_time: string
  thread_count: number
  name: string
  command: string
  cwd: string
}

/** 进程详细信息接口 */
export interface ProcessDetail extends ProcessInfo {
  environ: string[]
  fd_count: number
  net_connections: number
  cgroup: string
  status_file: Record<string, string>
}

/** 告警配置接口 */
export interface AlertConfig {
  cpu_threshold: number
  mem_threshold: number
  duration_seconds: number
}

/** 异常数据接口 */
export interface AnomalyData {
  zombies: number[]
  high_cpu: { pid: number; cpu_percent: number; duration: number }[]
  high_mem: { pid: number; mem_percent: number; duration: number }[]
  total_anomalies: number
}

export const useProcessStore = defineStore('process', () => {
  // ==================== State ====================

  const currentAlias = ref('')
  const processes = ref<ProcessInfo[]>([])
  const loading = ref(false)
  const streaming = ref(false)
  const ws = ref<WebSocket | null>(null)
  const timestamp = ref(0)
  const count = ref(0)

  // Search & Filter
  const searchQuery = ref('')
  const statusFilter = ref<string[]>([])
  const userFilter = ref('')

  // Sorting
  const sortColumn = ref<string>('cpu_percent')
  const sortOrder = ref<'asc' | 'desc' | null>('desc')

  // Selection
  const selectedPids = ref<Set<number>>(new Set())

  // Alert config
  const alertConfig = ref<AlertConfig>({ cpu_threshold: 90, mem_threshold: 80, duration_seconds: 5 })
  const anomalies = ref<AnomalyData | null>(null)

  // Refresh interval (ms): 1000, 3000, 10000, 0 (manual)
  const refreshInterval = ref(3000)
  let refreshTimer: ReturnType<typeof setInterval> | null = null

  // ==================== Computed ====================

  /** 过滤并排序后的进程列表 */
  const filteredProcesses = computed(() => {
    let result = processes.value

    // Search: match against pid (as string), name, user, command (case-insensitive substring)
    if (searchQuery.value) {
      const query = searchQuery.value.toLowerCase()
      result = result.filter((p) => {
        return (
          String(p.pid).includes(query) ||
          p.name.toLowerCase().includes(query) ||
          p.user.toLowerCase().includes(query) ||
          p.command.toLowerCase().includes(query)
        )
      })
    }

    // Status filter: if statusFilter has items, only include processes with matching status
    if (statusFilter.value.length > 0) {
      result = result.filter((p) => statusFilter.value.includes(p.status))
    }

    // User filter: if userFilter is set, only include processes with matching user
    if (userFilter.value) {
      result = result.filter((p) => p.user === userFilter.value)
    }

    // Sort: if sortOrder is not null, sort by sortColumn in sortOrder direction
    if (sortOrder.value !== null) {
      const col = sortColumn.value
      const order = sortOrder.value
      result = [...result].sort((a, b) => {
        const valA = a[col as keyof ProcessInfo]
        const valB = b[col as keyof ProcessInfo]
        if (typeof valA === 'number' && typeof valB === 'number') {
          return order === 'asc' ? valA - valB : valB - valA
        }
        // Fallback: compare as strings
        const strA = String(valA ?? '')
        const strB = String(valB ?? '')
        return order === 'asc' ? strA.localeCompare(strB) : strB.localeCompare(strA)
      })
    }

    return result
  })

  /** 从当前进程列表中提取唯一用户名，返回排序后的字符串数组 */
  const uniqueUsers = computed(() => {
    const users = new Set(processes.value.map((p) => p.user))
    return Array.from(users).sort()
  })

  /** 将所有异常 PID 合并为一个 Set 用于快速查找 */
  const anomalyPidSet = computed(() => {
    if (!anomalies.value) {
      return new Set<number>()
    }
    const pids = new Set<number>()
    anomalies.value.zombies.forEach((pid) => pids.add(pid))
    anomalies.value.high_cpu.forEach((item) => pids.add(item.pid))
    anomalies.value.high_mem.forEach((item) => pids.add(item.pid))
    return pids
  })

  /** 已选中的进程数量 */
  const selectedCount = computed(() => selectedPids.value.size)

  // ==================== Utility Functions ====================

  /** 将 KB 转换为人类可读格式 (KB/MB/GB) */
  function formatBytes(kb: number): string {
    if (!kb || kb <= 0) return '0 KB'
    if (kb < 1024) return `${kb.toFixed(0)} KB`
    const mb = kb / 1024
    if (mb < 1024) return `${mb.toFixed(1)} MB`
    const gb = mb / 1024
    return `${gb.toFixed(2)} GB`
  }

  /** 格式化 ps TIME 列 (e.g., "01:23:45" or "1:23" 保持原样) */
  function formatDuration(timeStr: string): string {
    if (!timeStr) return '00:00:00'
    return timeStr
  }

  /** 检查某个 PID 是否处于异常状态 */
  function isAnomaly(pid: number): { isZombie: boolean; isHighCpu: boolean; isHighMem: boolean } {
    if (!anomalies.value) {
      return { isZombie: false, isHighCpu: false, isHighMem: false }
    }
    return {
      isZombie: anomalies.value.zombies.includes(pid),
      isHighCpu: anomalies.value.high_cpu.some((item) => item.pid === pid),
      isHighMem: anomalies.value.high_mem.some((item) => item.pid === pid),
    }
  }

  // ==================== API Methods ====================

  /** 获取所有进程列表 */
  async function fetchProcessList(alias?: string) {
    const a = alias || currentAlias.value
    if (!a) return
    loading.value = true
    try {
      const res = await request.get<{ processes: ProcessInfo[]; count: number; timestamp: number }>('/process/list', {
        params: { alias: a },
      })
      processes.value = res.processes || []
      count.value = res.count ?? res.processes?.length ?? 0
      timestamp.value = res.timestamp ?? Date.now()
    } catch (err) {
      console.error('Failed to fetch process list:', err)
    } finally {
      loading.value = false
    }
    // 获取进程列表后同时获取异常数据
    await fetchAnomalies(a)
  }

  /** 获取单个进程的详细信息 */
  async function fetchProcessDetail(pid: number, alias?: string): Promise<ProcessDetail | null> {
    const a = alias || currentAlias.value
    if (!a) return null
    try {
      const res = await request.get<ProcessDetail>('/process/detail', { params: { alias: a, pid } })
      return res
    } catch (err) {
      console.error(`Failed to fetch process detail for pid ${pid}:`, err)
      return null
    }
  }

  /** 终止进程 */
  async function killProcess(pid: number, signal: string, alias?: string) {
    const a = alias || currentAlias.value
    if (!a) return
    try {
      await request.post('/process/kill', { alias: a, pid, signal })
    } catch (err) {
      console.error(`Failed to kill process ${pid}:`, err)
      throw err
    }
  }

  /** 设置进程 nice 值 */
  async function setNice(pid: number, niceValue: number, alias?: string) {
    const a = alias || currentAlias.value
    if (!a) return
    try {
      await request.post('/process/nice', { alias: a, pid, nice_value: niceValue })
    } catch (err) {
      console.error(`Failed to set nice value for process ${pid}:`, err)
      throw err
    }
  }

  /** 批量终止进程 */
  async function batchKill(pids: number[], signal: string, alias?: string) {
    const a = alias || currentAlias.value
    if (!a) return
    try {
      await request.post('/process/batch/kill', { alias: a, pids, signal })
    } catch (err) {
      console.error('Failed to batch kill processes:', err)
      throw err
    }
  }

  /** 服务控制 */
  async function serviceControl(serviceName: string, action: string, alias?: string) {
    const a = alias || currentAlias.value
    if (!a) return
    try {
      await request.post('/process/service/control', { alias: a, service_name: serviceName, action })
    } catch (err) {
      console.error(`Failed to control service ${serviceName}:`, err)
      throw err
    }
  }

  /** 获取告警配置 */
  async function fetchAlertConfig(alias?: string) {
    const a = alias || currentAlias.value
    if (!a) return
    try {
      const res = await request.get<AlertConfig>('/process/alert-config', { params: { alias: a } })
      alertConfig.value = res
    } catch (err) {
      console.error('Failed to fetch alert config:', err)
    }
  }

  /** 保存告警配置 */
  async function saveAlertConfig(config: AlertConfig, alias?: string) {
    const a = alias || currentAlias.value
    if (!a) return
    try {
      await request.put('/process/alert-config', { alias: a, ...config })
      alertConfig.value = config
    } catch (err) {
      console.error('Failed to save alert config:', err)
      throw err
    }
  }

  /** 获取异常数据 */
  async function fetchAnomalies(alias?: string) {
    const a = alias || currentAlias.value
    if (!a) return
    try {
      const res = await request.get<AnomalyData>('/process/alerts', { params: { alias: a } })
      anomalies.value = res
    } catch (err) {
      console.error('Failed to fetch anomalies:', err)
    }
  }

  // ==================== WebSocket Methods ====================

  /** 连接 WebSocket 实时流 */
  function connectWebSocket(alias?: string) {
    const a = alias || currentAlias.value
    if (!a) return
    if (ws.value) disconnect()
    const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:'
    const url = `${protocol}//${location.host}/api/process/ws/stream?alias=${encodeURIComponent(a)}`
    ws.value = new WebSocket(url)
    ws.value.onopen = () => {
      streaming.value = true
    }
    ws.value.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        if (data.type === 'pong') return
        if (data.type === 'process_stream') {
          processes.value = data.processes || []
          count.value = data.count ?? data.processes?.length ?? 0
          timestamp.value = data.timestamp ?? Date.now()
          // 每次更新后获取异常数据
          fetchAnomalies(a)
        }
      } catch {
        // Ignore parse errors
      }
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

  /** 断开 WebSocket 连接 */
  function disconnect() {
    if (ws.value) {
      ws.value.close()
      ws.value = null
    }
    streaming.value = false
  }

  // ==================== Selection Methods ====================

  /** 切换单个 PID 的选中状态 */
  function toggleSelection(pid: number) {
    const newSet = new Set(selectedPids.value)
    if (newSet.has(pid)) {
      newSet.delete(pid)
    } else {
      newSet.add(pid)
    }
    selectedPids.value = newSet
  }

  /** 选中当前过滤后的所有进程 */
  function selectAll() {
    selectedPids.value = new Set(filteredProcesses.value.map((p) => p.pid))
  }

  /** 取消所有选中 */
  function deselectAll() {
    selectedPids.value = new Set()
  }

  // ==================== Refresh Control ====================

  /** 启动自动刷新 */
  function startAutoRefresh() {
    stopAutoRefresh()
    if (refreshInterval.value > 0) {
      refreshTimer = setInterval(() => {
        fetchProcessList()
      }, refreshInterval.value)
    }
  }

  /** 停止自动刷新 */
  function stopAutoRefresh() {
    if (refreshTimer !== null) {
      clearInterval(refreshTimer)
      refreshTimer = null
    }
  }

  /** 设置刷新间隔并自动重启 */
  function setRefreshInterval(ms: number) {
    refreshInterval.value = ms
    startAutoRefresh()
  }

  // ==================== Return ====================

  return {
    // State
    currentAlias,
    processes,
    loading,
    streaming,
    ws,
    timestamp,
    count,
    searchQuery,
    statusFilter,
    userFilter,
    sortColumn,
    sortOrder,
    selectedPids,
    alertConfig,
    anomalies,
    refreshInterval,
    // Computed
    filteredProcesses,
    uniqueUsers,
    anomalyPidSet,
    selectedCount,
    // Utilities
    formatBytes,
    formatDuration,
    isAnomaly,
    // API Methods
    fetchProcessList,
    fetchProcessDetail,
    killProcess,
    setNice,
    batchKill,
    serviceControl,
    fetchAlertConfig,
    saveAlertConfig,
    fetchAnomalies,
    // WebSocket Methods
    connectWebSocket,
    disconnect,
    // Selection Methods
    toggleSelection,
    selectAll,
    deselectAll,
    // Refresh Control
    startAutoRefresh,
    stopAutoRefresh,
    setRefreshInterval,
  }
})
