import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { request } from '@/api'

export interface PortInfo {
  protocol: string
  port: number
  local_address: string
  pid: number
  process_name: string
  status: string
}

export interface CheckResult {
  port: number
  occupied: boolean
  details: PortInfo[]
}

export interface KillResult {
  success: boolean
  message: string
  killed?: { pid: number; process_name: string }[]
  failed?: { pid: number; process_name: string; error: string }[]
}

export const usePortStore = defineStore('port', () => {
  const ports = ref<PortInfo[]>([])
  const loading = ref(false)
  const totalCount = ref(0)

  const searchQuery = ref('')
  const protocolFilter = ref('')
  const statusFilter = ref('')
  const sortColumn = ref<string>('port')
  const sortOrder = ref<'asc' | 'desc'>('asc')

  const filteredPorts = computed(() => {
    let result = ports.value

    if (searchQuery.value) {
      const q = searchQuery.value.toLowerCase()
      result = result.filter((p) => {
        return (
          String(p.port).includes(q) ||
          String(p.pid).includes(q) ||
          p.process_name.toLowerCase().includes(q) ||
          p.local_address.toLowerCase().includes(q)
        )
      })
    }

    if (protocolFilter.value) {
      result = result.filter((p) => p.protocol === protocolFilter.value)
    }

    if (statusFilter.value) {
      result = result.filter((p) => p.status === statusFilter.value)
    }

    if (sortColumn.value) {
      const col = sortColumn.value
      const order = sortOrder.value === 'asc' ? 1 : -1
      result = [...result].sort((a, b) => {
        const va = a[col as keyof PortInfo]
        const vb = b[col as keyof PortInfo]
        if (typeof va === 'number' && typeof vb === 'number') {
          return (va - vb) * order
        }
        return String(va).localeCompare(String(vb)) * order
      })
    }

    return result
  })

  const occupiedPorts = computed(() => new Set(ports.value.map((p) => p.port)))

  async function fetchPortList() {
    loading.value = true
    try {
      const res = await request.get<{ ports: PortInfo[]; count: number }>('/port/list')
      ports.value = res.ports || []
      totalCount.value = res.count ?? res.ports?.length ?? 0
      return ports.value
    } catch (err) {
      console.error('Failed to fetch port list:', err)
      return []
    } finally {
      loading.value = false
    }
  }

  async function checkPort(port: number): Promise<CheckResult | null> {
    try {
      const res = await request.get<CheckResult>('/port/check', { params: { port } })
      return res
    } catch (err) {
      console.error(`Failed to check port ${port}:`, err)
      return null
    }
  }

  async function killByPort(port: number, force: boolean = false): Promise<KillResult | null> {
    try {
      const res = await request.post<KillResult>('/port/kill-by-port', { port, force })
      return res
    } catch (err: any) {
      console.error(`Failed to kill port ${port}:`, err)
      return { success: false, message: err?.message || '操作失败' }
    }
  }

  async function killByPid(pid: number, force: boolean = false): Promise<KillResult | null> {
    try {
      const res = await request.post<KillResult>('/port/kill-by-pid', { pid, force })
      return res
    } catch (err: any) {
      console.error(`Failed to kill pid ${pid}:`, err)
      return { success: false, message: err?.message || '操作失败' }
    }
  }

  function toggleSort(column: string) {
    if (sortColumn.value === column) {
      sortOrder.value = sortOrder.value === 'asc' ? 'desc' : 'asc'
    } else {
      sortColumn.value = column
      sortOrder.value = 'asc'
    }
  }

  return {
    ports,
    loading,
    totalCount,
    searchQuery,
    protocolFilter,
    statusFilter,
    sortColumn,
    sortOrder,
    filteredPorts,
    occupiedPorts,
    fetchPortList,
    checkPort,
    killByPort,
    killByPid,
    toggleSort,
  }
})
