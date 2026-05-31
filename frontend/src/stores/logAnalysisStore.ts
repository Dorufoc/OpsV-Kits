import { defineStore } from 'pinia'
import { ref } from 'vue'
import { request } from '@/api'

export type LogLevel = 'DEBUG' | 'INFO' | 'WARN' | 'ERROR' | 'CRITICAL'
export type SourceType = 'system' | 'docker' | 'tcp' | 'udp' | 'file'
export type SourceStatus = 'running' | 'stopped' | 'error'
export type PatternType = 'keyword' | 'regex' | 'level'
export type AggregationType = 'trend' | 'source_distribution' | 'level_distribution' | 'keyword_frequency'
export type GranularityType = 'minute' | 'hour' | 'day'

export interface LogEntry {
  id: number
  timestamp: number
  source: string
  level: string
  content: string
  structured_data: Record<string, any> | null
  container_name: string | null
  container_id: string | null
  labels: Record<string, any> | null
  host: string | null
}

export interface LogSearchRequest {
  query: string
  filters?: Record<string, any>
  page?: number
  page_size?: number
}

export interface LogFilterRequest {
  filters: Record<string, any>
  page?: number
  page_size?: number
}

export interface LogPageResult {
  total: number
  page: number
  page_size: number
  results: LogEntry[]
}

export interface AggregationParams {
  type: AggregationType
  time_start: number
  time_end: number
  granularity?: GranularityType
  level?: string
  keyword?: string
  top_n?: number
}

export interface AggregationResult {
  data: any[]
}

export interface CollectionSource {
  id: string
  type: SourceType
  alias: string
  path: string | null
  container: string | null
  host: string | null
  port: number | null
  enabled: boolean
  labels: Record<string, any> | null
  status: SourceStatus
}

export interface SourceCreateRequest {
  type: SourceType
  alias: string
  path?: string | null
  container?: string | null
  host?: string | null
  port?: number | null
  enabled?: boolean
  labels?: Record<string, any> | null
}

export interface SourceUpdateRequest {
  type?: SourceType
  alias?: string
  path?: string | null
  container?: string | null
  host?: string | null
  port?: number | null
  enabled?: boolean
  labels?: Record<string, any> | null
}

export interface AlertRule {
  id: number
  name: string
  pattern: string
  pattern_type: PatternType
  time_window: number
  threshold: number
  enabled: boolean
  silence_period: number
  created_at: number
}

export interface AlertRuleCreateRequest {
  name: string
  pattern: string
  pattern_type?: PatternType
  time_window?: number
  threshold?: number
  enabled?: boolean
  silence_period?: number
}

export interface AlertRuleUpdateRequest {
  name?: string
  pattern?: string
  pattern_type?: PatternType
  time_window?: number
  threshold?: number
  enabled?: boolean
  silence_period?: number
}

export interface AlertEvent {
  id: number
  rule_id: number
  triggered_at: number
  match_count: number
  notified: number
  detail: string
}

export interface LogContextResult {
  target: LogEntry | null
  before: LogEntry[]
  after: LogEntry[]
}

export const useLogAnalysisStore = defineStore('logAnalysis', () => {
  const searchResult = ref<LogPageResult>({ total: 0, page: 1, page_size: 50, results: [] })
  const realtimeLogs = ref<LogEntry[]>([])
  const realtimeConnected = ref(false)
  const aggregationData = ref<any[]>([])
  const alertRules = ref<AlertRule[]>([])
  const alertEvents = ref<AlertEvent[]>([])
  const sources = ref<CollectionSource[]>([])
  const loading = ref(false)
  let ws: WebSocket | null = null

  const MAX_REALTIME_LOGS = 500

  async function searchLogs(data: LogSearchRequest) {
    loading.value = true
    try {
      const res = await request.post<LogPageResult>('/log-analysis/search', {
        query: data.query,
        filters: data.filters ?? {},
        page: data.page ?? 1,
        page_size: data.page_size ?? 50,
      })
      searchResult.value = res
    } finally {
      loading.value = false
    }
  }

  async function filterLogs(data: LogFilterRequest) {
    loading.value = true
    try {
      const res = await request.post<LogPageResult>('/log-analysis/filter', {
        filters: data.filters,
        page: data.page ?? 1,
        page_size: data.page_size ?? 50,
      })
      searchResult.value = res
    } finally {
      loading.value = false
    }
  }

  async function fetchAggregation(params: AggregationParams) {
    loading.value = true
    try {
      const reqParams: Record<string, any> = {
        type: params.type,
        time_start: params.time_start,
        time_end: params.time_end,
      }
      if (params.granularity) reqParams.granularity = params.granularity
      if (params.level) reqParams.level = params.level
      if (params.keyword) reqParams.keyword = params.keyword
      if (params.top_n) reqParams.top_n = params.top_n
      const res = await request.get<AggregationResult>('/log-analysis/aggregation', { params: reqParams })
      aggregationData.value = res.data
    } finally {
      loading.value = false
    }
  }

  async function fetchSources() {
    const res = await request.get<{ sources: CollectionSource[] }>('/log-analysis/sources')
    sources.value = res.sources ?? []
  }

  async function createSource(data: SourceCreateRequest) {
    const res = await request.post<{ id: string }>('/log-analysis/sources', data)
    await fetchSources()
    return res.id
  }

  async function updateSource(sourceId: string, data: SourceUpdateRequest) {
    await request.put(`/log-analysis/sources/${sourceId}`, data)
    await fetchSources()
  }

  async function deleteSource(sourceId: string) {
    await request.delete(`/log-analysis/sources/${sourceId}`)
    sources.value = sources.value.filter(s => s.id !== sourceId)
  }

  async function startSource(sourceId: string) {
    await request.post(`/log-analysis/sources/${sourceId}/start`)
    await fetchSources()
  }

  async function stopSource(sourceId: string) {
    await request.post(`/log-analysis/sources/${sourceId}/stop`)
    await fetchSources()
  }

  async function fetchAlertRules() {
    const res = await request.get<{ rules: AlertRule[] }>('/log-analysis/alerts/rules')
    alertRules.value = res.rules ?? []
  }

  async function createAlertRule(data: AlertRuleCreateRequest) {
    const res = await request.post<{ id: number }>('/log-analysis/alerts/rules', data)
    await fetchAlertRules()
    return res.id
  }

  async function updateAlertRule(ruleId: number, data: AlertRuleUpdateRequest) {
    await request.put(`/log-analysis/alerts/rules/${ruleId}`, data)
    await fetchAlertRules()
  }

  async function deleteAlertRule(ruleId: number) {
    await request.delete(`/log-analysis/alerts/rules/${ruleId}`)
    alertRules.value = alertRules.value.filter(r => r.id !== ruleId)
  }

  async function toggleAlertRule(ruleId: number, enabled: boolean) {
    await request.post(`/log-analysis/alerts/rules/${ruleId}/toggle`, { enabled })
    await fetchAlertRules()
  }

  async function fetchAlertEvents(params?: { rule_id?: number; hours?: number; limit?: number }) {
    const reqParams: Record<string, any> = {}
    if (params?.rule_id !== undefined) reqParams.rule_id = params.rule_id
    if (params?.hours !== undefined) reqParams.hours = params.hours
    if (params?.limit !== undefined) reqParams.limit = params.limit
    const res = await request.get<{ events: AlertEvent[] }>('/log-analysis/alerts/events', { params: reqParams })
    alertEvents.value = res.events ?? []
  }

  async function fetchLogContext(logId: number, before: number = 5, after: number = 5) {
    return request.get<LogContextResult>('/log-analysis/context', {
      params: { log_id: logId, before, after },
    })
  }

  function connectRealtime() {
    if (ws) disconnectRealtime()
    const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:'
    const url = `${protocol}//${location.host}/api/log-analysis/ws/stream`
    ws = new WebSocket(url)
    ws.onopen = () => { realtimeConnected.value = true }
    ws.onclose = () => { realtimeConnected.value = false }
    ws.onmessage = (event) => {
      try {
        const entry: LogEntry = JSON.parse(event.data)
        realtimeLogs.value.unshift(entry)
        if (realtimeLogs.value.length > MAX_REALTIME_LOGS) {
          realtimeLogs.value.splice(MAX_REALTIME_LOGS)
        }
      } catch {}
    }
    ws.onerror = () => { realtimeConnected.value = false }
  }

  function sendWsFilter(filters: Record<string, any>) {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: 'filter', filters }))
    }
  }

  function disconnectRealtime() {
    if (ws) {
      ws.close()
      ws = null
    }
    realtimeConnected.value = false
  }

  return {
    searchResult,
    realtimeLogs,
    realtimeConnected,
    aggregationData,
    alertRules,
    alertEvents,
    sources,
    loading,
    searchLogs,
    filterLogs,
    fetchAggregation,
    fetchSources,
    createSource,
    updateSource,
    deleteSource,
    startSource,
    stopSource,
    fetchAlertRules,
    createAlertRule,
    updateAlertRule,
    deleteAlertRule,
    toggleAlertRule,
    fetchAlertEvents,
    fetchLogContext,
    connectRealtime,
    sendWsFilter,
    disconnectRealtime,
  }
})
