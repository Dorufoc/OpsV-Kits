import { defineStore } from 'pinia'
import { ref } from 'vue'
import { request } from '@/api'

interface AuditLogEntry {
  id: string
  user_id: string
  username: string
  timestamp: string
  ip_address: string
  action_type: string
  module: string
  detail: Record<string, any> | null
  status: string
  client_info: string
  request_path: string
  request_method: string
  response_code: number
  duration_ms: number
  hash: string
  sensitive: boolean
}

interface AuditLogQueryParams {
  user_id?: string
  username?: string
  time_start?: string
  time_end?: string
  action_types?: string[]
  modules?: string[]
  status?: string
  request_path?: string
  keyword?: string
  page: number
  page_size: number
  order_by?: string
  order_dir?: string
}

interface AuditLogPageResult {
  total: number
  page: number
  page_size: number
  total_pages: number
  items: AuditLogEntry[]
}

interface AuditLogStatistics {
  trend: Array<{ bucket: string; count: number }>
  module_distribution: Array<{ module: string; count: number }>
  action_distribution: Array<{ action_type: string; count: number }>
  user_ranking: Array<{ username: string; count: number }>
  anomalies: Array<Record<string, any>>
}

interface AuditArchiveInfo {
  filename: string
  size_bytes: number
  record_count: number
  period_start: string
  period_end: string
}

interface SavedQuery {
  id: string
  name: string
  params: AuditLogQueryParams
  saved_at: string
}

const STORAGE_KEY = 'audit-log-saved-queries'

export const useAuditLogStore = defineStore('auditLog', () => {
  const logs = ref<AuditLogEntry[]>([])
  const total = ref(0)
  const page = ref(1)
  const pageSize = ref(20)
  const totalPages = ref(0)
  const currentQuery = ref<AuditLogQueryParams | null>(null)
  const selectedLog = ref<AuditLogEntry | null>(null)
  const statistics = ref<AuditLogStatistics | null>(null)
  const archives = ref<AuditArchiveInfo[]>([])
  const savedQueries = ref<SavedQuery[]>([])
  const exportTask = ref<{ task_id: string; status: string; download_url: string } | null>(null)
  const loading = ref(false)
  const loadingStats = ref(false)
  const verifyResult = ref<{ total: number; passed: number; failed: number; failed_ids: string[] } | null>(null)

  async function queryLogs(params: AuditLogQueryParams) {
    loading.value = true
    try {
      const res = await request.post<AuditLogPageResult>('/audit-log/query', params)
      logs.value = res.items
      total.value = res.total
      page.value = res.page
      pageSize.value = res.page_size
      totalPages.value = res.total_pages
      currentQuery.value = params
      return res
    } finally {
      loading.value = false
    }
  }

  async function getLogDetail(logId: string) {
    const res = await request.get<AuditLogEntry>(`/audit-log/${logId}`)
    selectedLog.value = res
    return res
  }

  async function loadStatistics(timeStart?: string, timeEnd?: string, granularity?: string) {
    loadingStats.value = true
    try {
      const params: Record<string, any> = {}
      if (timeStart !== undefined) params.time_start = timeStart
      if (timeEnd !== undefined) params.time_end = timeEnd
      if (granularity !== undefined) params.granularity = granularity
      const res = await request.get<AuditLogStatistics>('/audit-log/statistics', { params })
      statistics.value = res
      return res
    } finally {
      loadingStats.value = false
    }
  }

  async function exportLogs(params: AuditLogQueryParams, format: string) {
    const res = await request.post<{ task_id: string; status: string; download_url: string }>('/audit-log/export', {
      ...params,
      format,
    })
    exportTask.value = res
    return res
  }

  function downloadExport(taskId: string, format: string): string {
    return `/api/audit-log/export/${taskId}?format=${encodeURIComponent(format)}`
  }

  async function verifyIntegrity(logId?: string) {
    const data: Record<string, any> = {}
    if (logId !== undefined) data.log_id = logId
    const res = await request.post<{ total: number; passed: number; failed: number; failed_ids: string[] }>('/audit-log/verify', data)
    verifyResult.value = res
    return res
  }

  async function loadArchives() {
    const res = await request.get<AuditArchiveInfo[]>('/audit-log/archives')
    archives.value = res
    return res
  }

  async function loadRecentLogs(limit?: number) {
    const params: Record<string, any> = {}
    if (limit !== undefined) params.limit = limit
    const res = await request.get<AuditLogEntry[]>('/audit-log/recent', { params })
    return res
  }

  function saveQuery(name: string, params: AuditLogQueryParams) {
    const entry: SavedQuery = {
      id: crypto.randomUUID(),
      name,
      params,
      saved_at: new Date().toISOString(),
    }
    savedQueries.value.push(entry)
    persistSavedQueries()
    return entry
  }

  function deleteSavedQuery(id: string) {
    savedQueries.value = savedQueries.value.filter((q) => q.id !== id)
    persistSavedQueries()
  }

  function loadSavedQueries() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY)
      if (raw) {
        savedQueries.value = JSON.parse(raw)
      }
    } catch {
      savedQueries.value = []
    }
  }

  function persistSavedQueries() {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(savedQueries.value))
  }

  function clearSelection() {
    selectedLog.value = null
  }

  loadSavedQueries()

  return {
    logs,
    total,
    page,
    pageSize,
    totalPages,
    currentQuery,
    selectedLog,
    statistics,
    archives,
    savedQueries,
    exportTask,
    loading,
    loadingStats,
    verifyResult,
    queryLogs,
    getLogDetail,
    loadStatistics,
    exportLogs,
    downloadExport,
    verifyIntegrity,
    loadArchives,
    loadRecentLogs,
    saveQuery,
    deleteSavedQuery,
    loadSavedQueries,
    clearSelection,
  }
})
