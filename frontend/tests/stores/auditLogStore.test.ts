import { describe, it, expect, vi, beforeEach } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useAuditLogStore } from '@/stores/auditLogStore'
import * as api from '@/api'

const mockLogEntry = {
  id: 'log-1',
  user_id: 'u1',
  username: 'admin',
  timestamp: '2024-01-01T00:00:00Z',
  ip_address: '127.0.0.1',
  action_type: 'create',
  module: 'docker',
  detail: null,
  status: 'success',
  client_info: 'Chrome',
  request_path: '/api/test',
  request_method: 'POST',
  response_code: 200,
  duration_ms: 50,
  hash: 'abc123',
  sensitive: false,
}

const mockPageResult = {
  total: 1,
  page: 1,
  page_size: 20,
  total_pages: 1,
  items: [mockLogEntry],
}

const mockStatistics = {
  trend: [{ bucket: '2024-01', count: 10 }],
  module_distribution: [{ module: 'docker', count: 5 }],
  action_distribution: [{ action_type: 'create', count: 3 }],
  user_ranking: [{ username: 'admin', count: 8 }],
  anomalies: [],
}

describe('AuditLog Store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    localStorage.clear()
  })

  describe('状态初始化', () => {
    it('应该正确初始化 logs 为空数组', () => {
      const store = useAuditLogStore()
      expect(store.logs).toEqual([])
    })

    it('应该正确初始化分页状态', () => {
      const store = useAuditLogStore()
      expect(store.total).toBe(0)
      expect(store.page).toBe(1)
      expect(store.pageSize).toBe(20)
      expect(store.totalPages).toBe(0)
    })

    it('应该正确初始化 currentQuery 为 null', () => {
      const store = useAuditLogStore()
      expect(store.currentQuery).toBeNull()
    })

    it('应该正确初始化 selectedLog 为 null', () => {
      const store = useAuditLogStore()
      expect(store.selectedLog).toBeNull()
    })

    it('应该正确初始化 statistics 为 null', () => {
      const store = useAuditLogStore()
      expect(store.statistics).toBeNull()
    })

    it('应该正确初始化 archives 为空数组', () => {
      const store = useAuditLogStore()
      expect(store.archives).toEqual([])
    })

    it('应该正确初始化 savedQueries 为空数组', () => {
      const store = useAuditLogStore()
      expect(store.savedQueries).toEqual([])
    })

    it('应该正确初始化 exportTask 为 null', () => {
      const store = useAuditLogStore()
      expect(store.exportTask).toBeNull()
    })

    it('应该正确初始化 loading 为 false', () => {
      const store = useAuditLogStore()
      expect(store.loading).toBe(false)
    })

    it('应该正确初始化 loadingStats 为 false', () => {
      const store = useAuditLogStore()
      expect(store.loadingStats).toBe(false)
    })

    it('应该正确初始化 verifyResult 为 null', () => {
      const store = useAuditLogStore()
      expect(store.verifyResult).toBeNull()
    })
  })

  describe('queryLogs', () => {
    const queryParams = { page: 1, page_size: 20 }

    it('应该查询日志并更新状态', async () => {
      vi.mocked(api.request.post).mockResolvedValue(mockPageResult as any)

      const store = useAuditLogStore()
      const result = await store.queryLogs(queryParams)

      expect(store.logs).toEqual([mockLogEntry])
      expect(store.total).toBe(1)
      expect(store.page).toBe(1)
      expect(store.pageSize).toBe(20)
      expect(store.totalPages).toBe(1)
      expect(store.currentQuery).toEqual(queryParams)
      expect(result).toEqual(mockPageResult)
    })

    it('请求期间 loading 应该为 true', async () => {
      vi.mocked(api.request.post).mockImplementation(async () => {
        const store = useAuditLogStore()
        expect(store.loading).toBe(true)
        return mockPageResult
      })

      const store = useAuditLogStore()
      await store.queryLogs(queryParams)
      expect(store.loading).toBe(false)
    })

    it('请求失败时 loading 应该恢复为 false', async () => {
      vi.mocked(api.request.post).mockRejectedValue(new Error('Network error'))

      const store = useAuditLogStore()
      await expect(store.queryLogs(queryParams)).rejects.toThrow()
      expect(store.loading).toBe(false)
    })

    it('应该调用正确的 API 端点', async () => {
      vi.mocked(api.request.post).mockResolvedValue(mockPageResult as any)

      const store = useAuditLogStore()
      await store.queryLogs(queryParams)

      expect(api.request.post).toHaveBeenCalledWith('/audit-log/query', queryParams)
    })
  })

  describe('getLogDetail', () => {
    it('应该获取日志详情并设置 selectedLog', async () => {
      vi.mocked(api.request.get).mockResolvedValue(mockLogEntry as any)

      const store = useAuditLogStore()
      const result = await store.getLogDetail('log-1')

      expect(store.selectedLog).toEqual(mockLogEntry)
      expect(result).toEqual(mockLogEntry)
    })

    it('应该调用正确的 API 端点', async () => {
      vi.mocked(api.request.get).mockResolvedValue(mockLogEntry as any)

      const store = useAuditLogStore()
      await store.getLogDetail('log-1')

      expect(api.request.get).toHaveBeenCalledWith('/audit-log/log-1')
    })
  })

  describe('loadStatistics', () => {
    it('应该加载统计数据并更新状态', async () => {
      vi.mocked(api.request.get).mockResolvedValue(mockStatistics as any)

      const store = useAuditLogStore()
      const result = await store.loadStatistics('2024-01-01', '2024-12-31', 'month')

      expect(store.statistics).toEqual(mockStatistics)
      expect(result).toEqual(mockStatistics)
    })

    it('请求期间 loadingStats 应该为 true', async () => {
      vi.mocked(api.request.get).mockImplementation(async () => {
        const store = useAuditLogStore()
        expect(store.loadingStats).toBe(true)
        return mockStatistics
      })

      const store = useAuditLogStore()
      await store.loadStatistics()
      expect(store.loadingStats).toBe(false)
    })

    it('请求失败时 loadingStats 应该恢复为 false', async () => {
      vi.mocked(api.request.get).mockRejectedValue(new Error('Network error'))

      const store = useAuditLogStore()
      await expect(store.loadStatistics()).rejects.toThrow()
      expect(store.loadingStats).toBe(false)
    })

    it('不带参数时应该不传查询参数', async () => {
      vi.mocked(api.request.get).mockResolvedValue(mockStatistics as any)

      const store = useAuditLogStore()
      await store.loadStatistics()

      expect(api.request.get).toHaveBeenCalledWith('/audit-log/statistics', { params: {} })
    })

    it('带参数时应该传递查询参数', async () => {
      vi.mocked(api.request.get).mockResolvedValue(mockStatistics as any)

      const store = useAuditLogStore()
      await store.loadStatistics('2024-01-01', '2024-12-31', 'month')

      expect(api.request.get).toHaveBeenCalledWith('/audit-log/statistics', {
        params: { time_start: '2024-01-01', time_end: '2024-12-31', granularity: 'month' },
      })
    })
  })

  describe('exportLogs', () => {
    it('应该导出日志并设置 exportTask', async () => {
      const mockExportResult = { task_id: 'task-1', status: 'processing', download_url: '' }
      vi.mocked(api.request.post).mockResolvedValue(mockExportResult as any)

      const store = useAuditLogStore()
      const result = await store.exportLogs({ page: 1, page_size: 20 }, 'csv')

      expect(store.exportTask).toEqual(mockExportResult)
      expect(result).toEqual(mockExportResult)
    })
  })

  describe('downloadExport', () => {
    it('应该返回正确的下载 URL', () => {
      const store = useAuditLogStore()
      const url = store.downloadExport('task-1', 'csv')

      expect(url).toBe('/api/audit-log/export/task-1?format=csv')
    })

    it('应该对 format 进行 URL 编码', () => {
      const store = useAuditLogStore()
      const url = store.downloadExport('task-1', 'csv export')

      expect(url).toContain('format=csv%20export')
    })
  })

  describe('verifyIntegrity', () => {
    it('应该验证完整性并设置 verifyResult', async () => {
      const mockVerify = { total: 100, passed: 98, failed: 2, failed_ids: ['id1', 'id2'] }
      vi.mocked(api.request.post).mockResolvedValue(mockVerify as any)

      const store = useAuditLogStore()
      const result = await store.verifyIntegrity()

      expect(store.verifyResult).toEqual(mockVerify)
      expect(result).toEqual(mockVerify)
    })

    it('带 logId 时应该传递参数', async () => {
      const mockVerify = { total: 1, passed: 1, failed: 0, failed_ids: [] }
      vi.mocked(api.request.post).mockResolvedValue(mockVerify as any)

      const store = useAuditLogStore()
      await store.verifyIntegrity('log-1')

      expect(api.request.post).toHaveBeenCalledWith('/audit-log/verify', { log_id: 'log-1' })
    })

    it('不带 logId 时应该传空对象', async () => {
      const mockVerify = { total: 100, passed: 100, failed: 0, failed_ids: [] }
      vi.mocked(api.request.post).mockResolvedValue(mockVerify as any)

      const store = useAuditLogStore()
      await store.verifyIntegrity()

      expect(api.request.post).toHaveBeenCalledWith('/audit-log/verify', {})
    })
  })

  describe('loadArchives', () => {
    it('应该加载归档列表', async () => {
      const mockArchives = [
        { filename: 'audit-2024.tar.gz', size_bytes: 1024, record_count: 500, period_start: '2024-01-01', period_end: '2024-06-30' },
      ]
      vi.mocked(api.request.get).mockResolvedValue(mockArchives as any)

      const store = useAuditLogStore()
      const result = await store.loadArchives()

      expect(store.archives).toEqual(mockArchives)
      expect(result).toEqual(mockArchives)
    })
  })

  describe('loadRecentLogs', () => {
    it('应该加载最近日志', async () => {
      vi.mocked(api.request.get).mockResolvedValue([mockLogEntry] as any)

      const store = useAuditLogStore()
      const result = await store.loadRecentLogs(10)

      expect(result).toEqual([mockLogEntry])
    })

    it('不带 limit 时应该不传参数', async () => {
      vi.mocked(api.request.get).mockResolvedValue([] as any)

      const store = useAuditLogStore()
      await store.loadRecentLogs()

      expect(api.request.get).toHaveBeenCalledWith('/audit-log/recent', { params: {} })
    })

    it('带 limit 时应该传递参数', async () => {
      vi.mocked(api.request.get).mockResolvedValue([] as any)

      const store = useAuditLogStore()
      await store.loadRecentLogs(5)

      expect(api.request.get).toHaveBeenCalledWith('/audit-log/recent', { params: { limit: 5 } })
    })
  })

  describe('saveQuery', () => {
    it('应该保存查询并添加到 savedQueries', () => {
      const store = useAuditLogStore()
      const params = { page: 1, page_size: 20 }
      const entry = store.saveQuery('测试查询', params)

      expect(entry.name).toBe('测试查询')
      expect(entry.params).toEqual(params)
      expect(entry.id).toBeTruthy()
      expect(entry.saved_at).toBeTruthy()
      expect(store.savedQueries).toHaveLength(1)
    })

    it('应该持久化到 localStorage', () => {
      const store = useAuditLogStore()
      store.saveQuery('持久化查询', { page: 1, page_size: 20 })

      const stored = localStorage.getItem('audit-log-saved-queries')
      expect(stored).toBeTruthy()
      const parsed = JSON.parse(stored!)
      expect(parsed).toHaveLength(1)
      expect(parsed[0].name).toBe('持久化查询')
    })
  })

  describe('deleteSavedQuery', () => {
    it('应该从 savedQueries 中删除指定查询', () => {
      const store = useAuditLogStore()
      const entry = store.saveQuery('查询1', { page: 1, page_size: 20 })
      store.saveQuery('查询2', { page: 1, page_size: 20 })

      expect(store.savedQueries).toHaveLength(2)
      store.deleteSavedQuery(entry.id)
      expect(store.savedQueries).toHaveLength(1)
      expect(store.savedQueries[0].name).toBe('查询2')
    })

    it('删除后应该更新 localStorage', () => {
      const store = useAuditLogStore()
      const entry = store.saveQuery('查询1', { page: 1, page_size: 20 })

      store.deleteSavedQuery(entry.id)

      const stored = localStorage.getItem('audit-log-saved-queries')
      const parsed = JSON.parse(stored!)
      expect(parsed).toHaveLength(0)
    })
  })

  describe('loadSavedQueries', () => {
    it('应该从 localStorage 加载已保存查询', () => {
      const savedData = [
        { id: 'q1', name: '查询1', params: { page: 1, page_size: 20 }, saved_at: '2024-01-01' },
      ]
      localStorage.setItem('audit-log-saved-queries', JSON.stringify(savedData))

      const store = useAuditLogStore()
      store.loadSavedQueries()

      expect(store.savedQueries).toEqual(savedData)
    })

    it('localStorage 为空时应该保持空数组', () => {
      const store = useAuditLogStore()
      store.loadSavedQueries()

      expect(store.savedQueries).toEqual([])
    })

    it('localStorage 数据损坏时应该重置为空数组', () => {
      localStorage.setItem('audit-log-saved-queries', 'invalid-json')

      const store = useAuditLogStore()
      store.loadSavedQueries()

      expect(store.savedQueries).toEqual([])
    })
  })

  describe('clearSelection', () => {
    it('应该清除 selectedLog', async () => {
      vi.mocked(api.request.get).mockResolvedValue(mockLogEntry as any)

      const store = useAuditLogStore()
      await store.getLogDetail('log-1')
      expect(store.selectedLog).not.toBeNull()

      store.clearSelection()
      expect(store.selectedLog).toBeNull()
    })
  })
})
