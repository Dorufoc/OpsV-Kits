import { describe, it, expect, vi, beforeEach } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useLogAnalysisStore } from '@/stores/logAnalysisStore'
import { mockGet, mockPost, mockPut, mockDelete } from '../setup'

describe('LogAnalysis Store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  describe('状态初始化', () => {
    it('应该正确初始化 searchResult', () => {
      const store = useLogAnalysisStore()
      expect(store.searchResult).toEqual({ total: 0, page: 1, page_size: 50, results: [] })
    })

    it('应该正确初始化 realtimeLogs 为空数组', () => {
      const store = useLogAnalysisStore()
      expect(store.realtimeLogs).toEqual([])
    })

    it('应该正确初始化 realtimeConnected 为 false', () => {
      const store = useLogAnalysisStore()
      expect(store.realtimeConnected).toBe(false)
    })

    it('应该正确初始化 aggregationData 为空数组', () => {
      const store = useLogAnalysisStore()
      expect(store.aggregationData).toEqual([])
    })

    it('应该正确初始化 alertRules 为空数组', () => {
      const store = useLogAnalysisStore()
      expect(store.alertRules).toEqual([])
    })

    it('应该正确初始化 alertEvents 为空数组', () => {
      const store = useLogAnalysisStore()
      expect(store.alertEvents).toEqual([])
    })

    it('应该正确初始化 sources 为空数组', () => {
      const store = useLogAnalysisStore()
      expect(store.sources).toEqual([])
    })

    it('应该正确初始化 loading 为 false', () => {
      const store = useLogAnalysisStore()
      expect(store.loading).toBe(false)
    })
  })

  describe('searchLogs', () => {
    it('应该搜索日志', async () => {
      const mockResult = { total: 1, page: 1, page_size: 50, results: [{ id: 1, timestamp: 0, source: 'syslog', level: 'INFO', content: 'test', structured_data: null, container_name: null, container_id: null, labels: null, host: null }] }
      mockPost.mockResolvedValue(mockResult)

      const store = useLogAnalysisStore()
      await store.searchLogs({ query: 'error' })

      expect(store.searchResult).toEqual(mockResult)
    })

    it('请求期间 loading 应该为 true', async () => {
      mockPost.mockImplementation(async () => {
        const store = useLogAnalysisStore()
        expect(store.loading).toBe(true)
        return { total: 0, page: 1, page_size: 50, results: [] }
      })

      const store = useLogAnalysisStore()
      await store.searchLogs({ query: 'test' })
      expect(store.loading).toBe(false)
    })

    it('请求失败时 loading 应该恢复为 false', async () => {
      mockPost.mockRejectedValue(new Error('Network error'))

      const store = useLogAnalysisStore()
      await expect(store.searchLogs({ query: 'test' })).rejects.toThrow()
      expect(store.loading).toBe(false)
    })

    it('应该使用默认分页参数', async () => {
      mockPost.mockResolvedValue({ total: 0, page: 1, page_size: 50, results: [] })

      const store = useLogAnalysisStore()
      await store.searchLogs({ query: 'test' })

      expect(mockPost).toHaveBeenCalledWith('/log-analysis/search', {
        query: 'test',
        filters: {},
        page: 1,
        page_size: 50,
      })
    })
  })

  describe('filterLogs', () => {
    it('应该筛选日志', async () => {
      const mockResult = { total: 0, page: 1, page_size: 50, results: [] }
      mockPost.mockResolvedValue(mockResult)

      const store = useLogAnalysisStore()
      await store.filterLogs({ filters: { level: 'ERROR' } })

      expect(store.searchResult).toEqual(mockResult)
    })

    it('请求期间 loading 应该为 true', async () => {
      mockPost.mockImplementation(async () => {
        const store = useLogAnalysisStore()
        expect(store.loading).toBe(true)
        return { total: 0, page: 1, page_size: 50, results: [] }
      })

      const store = useLogAnalysisStore()
      await store.filterLogs({ filters: {} })
      expect(store.loading).toBe(false)
    })
  })

  describe('fetchAggregation', () => {
    it('应该获取聚合数据', async () => {
      const mockAggregation = { data: [{ time: '2024-01-01', count: 10 }] }
      mockGet.mockResolvedValue(mockAggregation)

      const store = useLogAnalysisStore()
      await store.fetchAggregation({ type: 'trend', time_start: 0, time_end: 1000 })

      expect(store.aggregationData).toEqual([{ time: '2024-01-01', count: 10 }])
    })

    it('请求期间 loading 应该为 true', async () => {
      mockGet.mockImplementation(async () => {
        const store = useLogAnalysisStore()
        expect(store.loading).toBe(true)
        return { data: [] }
      })

      const store = useLogAnalysisStore()
      await store.fetchAggregation({ type: 'trend', time_start: 0, time_end: 1000 })
      expect(store.loading).toBe(false)
    })

    it('应该支持可选参数', async () => {
      mockGet.mockResolvedValue({ data: [] })

      const store = useLogAnalysisStore()
      await store.fetchAggregation({
        type: 'level_distribution',
        time_start: 0,
        time_end: 1000,
        granularity: 'hour',
        level: 'ERROR',
        keyword: 'timeout',
        top_n: 10,
      })

      expect(mockGet).toHaveBeenCalledWith('/log-analysis/aggregation', {
        params: {
          type: 'level_distribution',
          time_start: 0,
          time_end: 1000,
          granularity: 'hour',
          level: 'ERROR',
          keyword: 'timeout',
          top_n: 10,
        },
      })
    })
  })

  describe('fetchSources', () => {
    it('应该获取采集源列表', async () => {
      const mockSources = [{ id: '1', type: 'system' as const, alias: 'syslog', path: '/var/log/syslog', container: null, host: null, port: null, enabled: true, labels: null, status: 'running' as const }]
      mockGet.mockResolvedValue({ sources: mockSources })

      const store = useLogAnalysisStore()
      await store.fetchSources()

      expect(store.sources).toEqual(mockSources)
    })

    it('API 返回无 sources 时应该设为空数组', async () => {
      mockGet.mockResolvedValue({})

      const store = useLogAnalysisStore()
      await store.fetchSources()

      expect(store.sources).toEqual([])
    })
  })

  describe('createSource', () => {
    it('应该创建采集源并刷新列表', async () => {
      mockPost.mockResolvedValue({ id: '2' })
      mockGet.mockResolvedValue({ sources: [] })

      const store = useLogAnalysisStore()
      const result = await store.createSource({ type: 'docker', alias: 'docker-logs' })

      expect(result).toBe('2')
      expect(mockGet).toHaveBeenCalledWith('/log-analysis/sources')
    })
  })

  describe('updateSource', () => {
    it('应该更新采集源并刷新列表', async () => {
      mockPut.mockResolvedValue({})
      mockGet.mockResolvedValue({ sources: [] })

      const store = useLogAnalysisStore()
      await store.updateSource('1', { alias: 'updated' })

      expect(mockPut).toHaveBeenCalledWith('/log-analysis/sources/1', { alias: 'updated' })
      expect(mockGet).toHaveBeenCalledWith('/log-analysis/sources')
    })
  })

  describe('deleteSource', () => {
    it('应该删除采集源', async () => {
      mockDelete.mockResolvedValue({})

      const store = useLogAnalysisStore()
      store.sources = [
        { id: '1', type: 'system' as const, alias: 'syslog', path: '/var/log/syslog', container: null, host: null, port: null, enabled: true, labels: null, status: 'running' as const },
        { id: '2', type: 'docker' as const, alias: 'docker', path: null, container: 'app', host: null, port: null, enabled: true, labels: null, status: 'running' as const },
      ] as any

      await store.deleteSource('1')

      expect(store.sources).toHaveLength(1)
      expect(store.sources[0].id).toBe('2')
    })
  })

  describe('startSource', () => {
    it('应该启动采集源并刷新列表', async () => {
      mockPost.mockResolvedValue({})
      mockGet.mockResolvedValue({ sources: [] })

      const store = useLogAnalysisStore()
      await store.startSource('1')

      expect(mockPost).toHaveBeenCalledWith('/log-analysis/sources/1/start')
    })
  })

  describe('stopSource', () => {
    it('应该停止采集源并刷新列表', async () => {
      mockPost.mockResolvedValue({})
      mockGet.mockResolvedValue({ sources: [] })

      const store = useLogAnalysisStore()
      await store.stopSource('1')

      expect(mockPost).toHaveBeenCalledWith('/log-analysis/sources/1/stop')
    })
  })

  describe('fetchAlertRules', () => {
    it('应该获取告警规则列表', async () => {
      const mockRules = [{ id: 1, name: 'High Error Rate', pattern: 'ERROR', pattern_type: 'keyword' as const, time_window: 300, threshold: 10, enabled: true, silence_period: 600, created_at: 0 }]
      mockGet.mockResolvedValue({ rules: mockRules })

      const store = useLogAnalysisStore()
      await store.fetchAlertRules()

      expect(store.alertRules).toEqual(mockRules)
    })

    it('API 返回无 rules 时应该设为空数组', async () => {
      mockGet.mockResolvedValue({})

      const store = useLogAnalysisStore()
      await store.fetchAlertRules()

      expect(store.alertRules).toEqual([])
    })
  })

  describe('createAlertRule', () => {
    it('应该创建告警规则并刷新列表', async () => {
      mockPost.mockResolvedValue({ id: 2 })
      mockGet.mockResolvedValue({ rules: [] })

      const store = useLogAnalysisStore()
      const result = await store.createAlertRule({ name: 'New Rule', pattern: 'CRITICAL' })

      expect(result).toBe(2)
      expect(mockGet).toHaveBeenCalledWith('/log-analysis/alerts/rules')
    })
  })

  describe('updateAlertRule', () => {
    it('应该更新告警规则并刷新列表', async () => {
      mockPut.mockResolvedValue({})
      mockGet.mockResolvedValue({ rules: [] })

      const store = useLogAnalysisStore()
      await store.updateAlertRule(1, { threshold: 20 })

      expect(mockPut).toHaveBeenCalledWith('/log-analysis/alerts/rules/1', { threshold: 20 })
    })
  })

  describe('deleteAlertRule', () => {
    it('应该删除告警规则', async () => {
      mockDelete.mockResolvedValue({})

      const store = useLogAnalysisStore()
      store.alertRules = [
        { id: 1, name: 'Rule 1', pattern: 'ERROR', pattern_type: 'keyword' as const, time_window: 300, threshold: 10, enabled: true, silence_period: 600, created_at: 0 },
        { id: 2, name: 'Rule 2', pattern: 'WARN', pattern_type: 'keyword' as const, time_window: 300, threshold: 20, enabled: true, silence_period: 600, created_at: 0 },
      ] as any

      await store.deleteAlertRule(1)

      expect(store.alertRules).toHaveLength(1)
      expect(store.alertRules[0].id).toBe(2)
    })
  })

  describe('toggleAlertRule', () => {
    it('应该切换告警规则状态并刷新列表', async () => {
      mockPost.mockResolvedValue({})
      mockGet.mockResolvedValue({ rules: [] })

      const store = useLogAnalysisStore()
      await store.toggleAlertRule(1, false)

      expect(mockPost).toHaveBeenCalledWith('/log-analysis/alerts/rules/1/toggle', { enabled: false })
    })
  })

  describe('fetchAlertEvents', () => {
    it('应该获取告警事件列表', async () => {
      const mockEvents = [{ id: 1, rule_id: 1, triggered_at: 0, match_count: 15, notified: 1, detail: 'Error rate exceeded' }]
      mockGet.mockResolvedValue({ events: mockEvents })

      const store = useLogAnalysisStore()
      await store.fetchAlertEvents()

      expect(store.alertEvents).toEqual(mockEvents)
    })

    it('API 返回无 events 时应该设为空数组', async () => {
      mockGet.mockResolvedValue({})

      const store = useLogAnalysisStore()
      await store.fetchAlertEvents()

      expect(store.alertEvents).toEqual([])
    })

    it('应该支持筛选参数', async () => {
      mockGet.mockResolvedValue({ events: [] })

      const store = useLogAnalysisStore()
      await store.fetchAlertEvents({ rule_id: 1, hours: 24, limit: 10 })

      expect(mockGet).toHaveBeenCalledWith('/log-analysis/alerts/events', {
        params: { rule_id: 1, hours: 24, limit: 10 },
      })
    })
  })

  describe('fetchLogContext', () => {
    it('应该获取日志上下文', async () => {
      const mockContext = { target: null, before: [], after: [] }
      mockGet.mockResolvedValue(mockContext)

      const store = useLogAnalysisStore()
      const result = await store.fetchLogContext(42)

      expect(result).toEqual(mockContext)
      expect(mockGet).toHaveBeenCalledWith('/log-analysis/context', {
        params: { log_id: 42, before: 5, after: 5 },
      })
    })

    it('应该支持自定义上下文行数', async () => {
      mockGet.mockResolvedValue({ target: null, before: [], after: [] })

      const store = useLogAnalysisStore()
      await store.fetchLogContext(42, 10, 10)

      expect(mockGet).toHaveBeenCalledWith('/log-analysis/context', {
        params: { log_id: 42, before: 10, after: 10 },
      })
    })
  })

  describe('connectRealtime', () => {
    it('应该建立 WebSocket 连接', async () => {
      const store = useLogAnalysisStore()
      store.connectRealtime()

      await vi.waitFor(() => {
        expect(store.realtimeConnected).toBe(true)
      })
    })
  })

  describe('disconnectRealtime', () => {
    it('应该断开 WebSocket 连接', async () => {
      const store = useLogAnalysisStore()
      store.connectRealtime()
      await vi.waitFor(() => expect(store.realtimeConnected).toBe(true))

      store.disconnectRealtime()

      expect(store.realtimeConnected).toBe(false)
    })
  })

  describe('sendWsFilter', () => {
    it('应该在连接打开时发送筛选条件', async () => {
      const store = useLogAnalysisStore()
      store.connectRealtime()
      await vi.waitFor(() => expect(store.realtimeConnected).toBe(true))

      store.sendWsFilter({ level: 'ERROR' })

      expect(store.realtimeConnected).toBe(true)
    })
  })
})
