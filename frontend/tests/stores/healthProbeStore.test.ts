import { describe, it, expect, vi, beforeEach } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useHealthProbeStore } from '@/stores/healthProbeStore'
import * as api from '@/api'

describe('HealthProbe Store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  describe('状态初始化', () => {
    it('应该正确初始化 targets 为空数组', () => {
      const store = useHealthProbeStore()
      expect(store.targets).toEqual([])
    })

    it('应该正确初始化 overview 为 null', () => {
      const store = useHealthProbeStore()
      expect(store.overview).toBeNull()
    })

    it('应该正确初始化 currentTarget 为 null', () => {
      const store = useHealthProbeStore()
      expect(store.currentTarget).toBeNull()
    })

    it('应该正确初始化 currentStats 为 null', () => {
      const store = useHealthProbeStore()
      expect(store.currentStats).toBeNull()
    })

    it('应该正确初始化 currentLogs 为 null', () => {
      const store = useHealthProbeStore()
      expect(store.currentLogs).toBeNull()
    })

    it('应该正确初始化 loading 为 false', () => {
      const store = useHealthProbeStore()
      expect(store.loading).toBe(false)
    })

    it('应该正确初始化 probing 为 false', () => {
      const store = useHealthProbeStore()
      expect(store.probing).toBe(false)
    })
  })

  describe('fetchOverview', () => {
    it('应该获取健康探测概览', async () => {
      const mockTargets = [
        { id: '1', name: 'Web', probe_type: 'http' as const, target: 'https://example.com', interval_seconds: 30, timeout_seconds: 5, enabled: true, failure_threshold: 3, recovery_threshold: 2, tags: [], current_status: 'available' as const, consecutive_failures: 0, consecutive_successes: 5, created_at: '', updated_at: '' },
      ]
      const mockOverview = { total_targets: 1, available_count: 1, unavailable_count: 0, unknown_count: 0, targets: mockTargets }
      vi.mocked(api.healthProbeApi.getOverview).mockResolvedValue(mockOverview as any)

      const store = useHealthProbeStore()
      await store.fetchOverview()

      expect(store.overview).toEqual(mockOverview)
      expect(store.targets).toEqual(mockTargets)
    })

    it('请求期间 loading 应该为 true', async () => {
      vi.mocked(api.healthProbeApi.getOverview).mockImplementation(async () => {
        const store = useHealthProbeStore()
        expect(store.loading).toBe(true)
        return { total_targets: 0, available_count: 0, unavailable_count: 0, unknown_count: 0, targets: [] }
      })

      const store = useHealthProbeStore()
      await store.fetchOverview()
      expect(store.loading).toBe(false)
    })

    it('请求失败时 loading 应该恢复为 false', async () => {
      vi.mocked(api.healthProbeApi.getOverview).mockRejectedValue(new Error('Network error'))

      const store = useHealthProbeStore()
      await expect(store.fetchOverview()).rejects.toThrow()
      expect(store.loading).toBe(false)
    })
  })

  describe('fetchTargets', () => {
    it('应该获取探测目标列表', async () => {
      const mockTargets = [
        { id: '1', name: 'Web', probe_type: 'http' as const, target: 'https://example.com', interval_seconds: 30, timeout_seconds: 5, enabled: true, failure_threshold: 3, recovery_threshold: 2, tags: [], current_status: 'available' as const, consecutive_failures: 0, consecutive_successes: 5, created_at: '', updated_at: '' },
      ]
      vi.mocked(api.healthProbeApi.listTargets).mockResolvedValue(mockTargets as any)

      const store = useHealthProbeStore()
      await store.fetchTargets()

      expect(store.targets).toEqual(mockTargets)
    })

    it('应该支持 tag 和 probeType 筛选参数', async () => {
      vi.mocked(api.healthProbeApi.listTargets).mockResolvedValue([] as any)

      const store = useHealthProbeStore()
      await store.fetchTargets('production', 'http')

      expect(api.healthProbeApi.listTargets).toHaveBeenCalledWith('production', 'http')
    })

    it('请求期间 loading 应该为 true', async () => {
      vi.mocked(api.healthProbeApi.listTargets).mockImplementation(async () => {
        const store = useHealthProbeStore()
        expect(store.loading).toBe(true)
        return []
      })

      const store = useHealthProbeStore()
      await store.fetchTargets()
      expect(store.loading).toBe(false)
    })

    it('请求失败时 loading 应该恢复为 false', async () => {
      vi.mocked(api.healthProbeApi.listTargets).mockRejectedValue(new Error('Network error'))

      const store = useHealthProbeStore()
      await expect(store.fetchTargets()).rejects.toThrow()
      expect(store.loading).toBe(false)
    })
  })

  describe('createTarget', () => {
    it('应该创建探测目标并添加到列表', async () => {
      const newTarget = { id: '2', name: 'DB', probe_type: 'tcp' as const, target: 'db.example.com:5432', interval_seconds: 60, timeout_seconds: 5, enabled: true, failure_threshold: 3, recovery_threshold: 2, tags: [], current_status: 'unknown' as const, consecutive_failures: 0, consecutive_successes: 0, created_at: '', updated_at: '' }
      vi.mocked(api.healthProbeApi.createTarget).mockResolvedValue(newTarget as any)

      const store = useHealthProbeStore()
      const result = await store.createTarget({ name: 'DB', probe_type: 'tcp', target: 'db.example.com:5432' })

      expect(store.targets).toContainEqual(newTarget)
      expect(result).toEqual(newTarget)
    })
  })

  describe('updateTarget', () => {
    it('应该更新探测目标并同步列表', async () => {
      const store = useHealthProbeStore()
      store.targets = [
        { id: '1', name: 'Web', probe_type: 'http' as const, target: 'https://example.com', interval_seconds: 30, timeout_seconds: 5, enabled: true, failure_threshold: 3, recovery_threshold: 2, tags: [], current_status: 'available' as const, consecutive_failures: 0, consecutive_successes: 5, created_at: '', updated_at: '' },
      ] as any

      const updatedTarget = { id: '1', name: 'Web Updated', probe_type: 'http' as const, target: 'https://example.com', interval_seconds: 60, timeout_seconds: 10, enabled: true, failure_threshold: 3, recovery_threshold: 2, tags: [], current_status: 'available' as const, consecutive_failures: 0, consecutive_successes: 5, created_at: '', updated_at: '' }
      vi.mocked(api.healthProbeApi.updateTarget).mockResolvedValue(updatedTarget as any)

      const result = await store.updateTarget('1', { name: 'Web Updated' })

      expect(store.targets[0]).toEqual(updatedTarget)
      expect(result).toEqual(updatedTarget)
    })

    it('更新当前选中的目标时应该同步 currentTarget', async () => {
      const store = useHealthProbeStore()
      store.targets = [
        { id: '1', name: 'Web', probe_type: 'http' as const, target: 'https://example.com', interval_seconds: 30, timeout_seconds: 5, enabled: true, failure_threshold: 3, recovery_threshold: 2, tags: [], current_status: 'available' as const, consecutive_failures: 0, consecutive_successes: 5, created_at: '', updated_at: '' },
      ] as any
      store.currentTarget = store.targets[0]

      const updatedTarget = { id: '1', name: 'Web Updated', probe_type: 'http' as const, target: 'https://example.com', interval_seconds: 60, timeout_seconds: 10, enabled: true, failure_threshold: 3, recovery_threshold: 2, tags: [], current_status: 'available' as const, consecutive_failures: 0, consecutive_successes: 5, created_at: '', updated_at: '' }
      vi.mocked(api.healthProbeApi.updateTarget).mockResolvedValue(updatedTarget as any)

      await store.updateTarget('1', { name: 'Web Updated' })

      expect(store.currentTarget).toEqual(updatedTarget)
    })

    it('更新非当前选中的目标时不应修改 currentTarget', async () => {
      const store = useHealthProbeStore()
      store.targets = [
        { id: '1', name: 'Web', probe_type: 'http' as const, target: 'https://example.com', interval_seconds: 30, timeout_seconds: 5, enabled: true, failure_threshold: 3, recovery_threshold: 2, tags: [], current_status: 'available' as const, consecutive_failures: 0, consecutive_successes: 5, created_at: '', updated_at: '' },
        { id: '2', name: 'DB', probe_type: 'tcp' as const, target: 'db:5432', interval_seconds: 60, timeout_seconds: 5, enabled: true, failure_threshold: 3, recovery_threshold: 2, tags: [], current_status: 'unknown' as const, consecutive_failures: 0, consecutive_successes: 0, created_at: '', updated_at: '' },
      ] as any
      store.currentTarget = store.targets[0]

      const updatedTarget = { id: '2', name: 'DB Updated', probe_type: 'tcp' as const, target: 'db:5432', interval_seconds: 60, timeout_seconds: 5, enabled: true, failure_threshold: 3, recovery_threshold: 2, tags: [], current_status: 'available' as const, consecutive_failures: 0, consecutive_successes: 5, created_at: '', updated_at: '' }
      vi.mocked(api.healthProbeApi.updateTarget).mockResolvedValue(updatedTarget as any)

      await store.updateTarget('2', { name: 'DB Updated' })

      expect(store.currentTarget?.id).toBe('1')
    })
  })

  describe('deleteTarget', () => {
    it('应该从列表中删除探测目标', async () => {
      vi.mocked(api.healthProbeApi.deleteTarget).mockResolvedValue({} as any)

      const store = useHealthProbeStore()
      store.targets = [
        { id: '1', name: 'Web', probe_type: 'http' as const, target: 'https://example.com', interval_seconds: 30, timeout_seconds: 5, enabled: true, failure_threshold: 3, recovery_threshold: 2, tags: [], current_status: 'available' as const, consecutive_failures: 0, consecutive_successes: 5, created_at: '', updated_at: '' },
        { id: '2', name: 'DB', probe_type: 'tcp' as const, target: 'db:5432', interval_seconds: 60, timeout_seconds: 5, enabled: true, failure_threshold: 3, recovery_threshold: 2, tags: [], current_status: 'unknown' as const, consecutive_failures: 0, consecutive_successes: 0, created_at: '', updated_at: '' },
      ] as any

      await store.deleteTarget('1')

      expect(store.targets).toHaveLength(1)
      expect(store.targets[0].id).toBe('2')
    })

    it('删除当前选中的目标时应该清空 currentTarget', async () => {
      vi.mocked(api.healthProbeApi.deleteTarget).mockResolvedValue({} as any)

      const store = useHealthProbeStore()
      store.targets = [
        { id: '1', name: 'Web', probe_type: 'http' as const, target: 'https://example.com', interval_seconds: 30, timeout_seconds: 5, enabled: true, failure_threshold: 3, recovery_threshold: 2, tags: [], current_status: 'available' as const, consecutive_failures: 0, consecutive_successes: 5, created_at: '', updated_at: '' },
      ] as any
      store.currentTarget = store.targets[0]

      await store.deleteTarget('1')

      expect(store.currentTarget).toBeNull()
    })

    it('删除非当前选中的目标时不应修改 currentTarget', async () => {
      vi.mocked(api.healthProbeApi.deleteTarget).mockResolvedValue({} as any)

      const store = useHealthProbeStore()
      store.targets = [
        { id: '1', name: 'Web', probe_type: 'http' as const, target: 'https://example.com', interval_seconds: 30, timeout_seconds: 5, enabled: true, failure_threshold: 3, recovery_threshold: 2, tags: [], current_status: 'available' as const, consecutive_failures: 0, consecutive_successes: 5, created_at: '', updated_at: '' },
        { id: '2', name: 'DB', probe_type: 'tcp' as const, target: 'db:5432', interval_seconds: 60, timeout_seconds: 5, enabled: true, failure_threshold: 3, recovery_threshold: 2, tags: [], current_status: 'unknown' as const, consecutive_failures: 0, consecutive_successes: 0, created_at: '', updated_at: '' },
      ] as any
      store.currentTarget = store.targets[0]

      await store.deleteTarget('2')

      expect(store.currentTarget?.id).toBe('1')
    })
  })

  describe('probeNow', () => {
    it('应该立即执行探测并更新目标状态', async () => {
      const mockResult = { id: 'pr1', target_id: '1', timestamp: '', probe_type: 'http' as const, target: 'https://example.com', success: true, response_time_ms: 50 }
      vi.mocked(api.healthProbeApi.probeNow).mockResolvedValue(mockResult as any)

      const updatedTarget = { id: '1', name: 'Web', probe_type: 'http' as const, target: 'https://example.com', interval_seconds: 30, timeout_seconds: 5, enabled: true, failure_threshold: 3, recovery_threshold: 2, tags: [], current_status: 'available' as const, consecutive_failures: 0, consecutive_successes: 6, created_at: '', updated_at: '' }
      vi.mocked(api.healthProbeApi.getTarget).mockResolvedValue(updatedTarget as any)

      const store = useHealthProbeStore()
      store.targets = [
        { id: '1', name: 'Web', probe_type: 'http' as const, target: 'https://example.com', interval_seconds: 30, timeout_seconds: 5, enabled: true, failure_threshold: 3, recovery_threshold: 2, tags: [], current_status: 'available' as const, consecutive_failures: 0, consecutive_successes: 5, created_at: '', updated_at: '' },
      ] as any

      const result = await store.probeNow('1')

      expect(result).toEqual(mockResult)
      expect(store.targets[0]).toEqual(updatedTarget)
    })

    it('探测当前选中的目标时应该同步 currentTarget', async () => {
      const mockResult = { id: 'pr1', target_id: '1', timestamp: '', probe_type: 'http' as const, target: 'https://example.com', success: true, response_time_ms: 50 }
      vi.mocked(api.healthProbeApi.probeNow).mockResolvedValue(mockResult as any)

      const updatedTarget = { id: '1', name: 'Web', probe_type: 'http' as const, target: 'https://example.com', interval_seconds: 30, timeout_seconds: 5, enabled: true, failure_threshold: 3, recovery_threshold: 2, tags: [], current_status: 'available' as const, consecutive_failures: 0, consecutive_successes: 6, created_at: '', updated_at: '' }
      vi.mocked(api.healthProbeApi.getTarget).mockResolvedValue(updatedTarget as any)

      const store = useHealthProbeStore()
      store.targets = [
        { id: '1', name: 'Web', probe_type: 'http' as const, target: 'https://example.com', interval_seconds: 30, timeout_seconds: 5, enabled: true, failure_threshold: 3, recovery_threshold: 2, tags: [], current_status: 'available' as const, consecutive_failures: 0, consecutive_successes: 5, created_at: '', updated_at: '' },
      ] as any
      store.currentTarget = store.targets[0]

      await store.probeNow('1')

      expect(store.currentTarget).toEqual(updatedTarget)
    })

    it('请求期间 probing 应该为 true', async () => {
      vi.mocked(api.healthProbeApi.probeNow).mockImplementation(async () => {
        const store = useHealthProbeStore()
        expect(store.probing).toBe(true)
        return { id: 'pr1', target_id: '1', timestamp: '', probe_type: 'http' as const, target: '', success: true }
      })

      const store = useHealthProbeStore()
      store.targets = [{ id: '1' } as any]
      await store.probeNow('1')
      expect(store.probing).toBe(false)
    })

    it('请求失败时 probing 应该恢复为 false', async () => {
      vi.mocked(api.healthProbeApi.probeNow).mockRejectedValue(new Error('Network error'))

      const store = useHealthProbeStore()
      store.targets = [{ id: '1' } as any]
      await expect(store.probeNow('1')).rejects.toThrow()
      expect(store.probing).toBe(false)
    })
  })

  describe('fetchStatistics', () => {
    it('应该获取探测统计', async () => {
      const mockStats = { target_id: '1', uptime_percent: 99.5, total_probes: 1000, success_count: 995, failure_count: 5, current_status: 'available' as const }
      vi.mocked(api.healthProbeApi.getStatistics).mockResolvedValue(mockStats as any)

      const store = useHealthProbeStore()
      const result = await store.fetchStatistics('1')

      expect(store.currentStats).toEqual(mockStats)
      expect(result).toEqual(mockStats)
    })

    it('应该支持自定义 hours 参数', async () => {
      const mockStats = { target_id: '1', uptime_percent: 99.5, total_probes: 1000, success_count: 995, failure_count: 5, current_status: 'available' as const }
      vi.mocked(api.healthProbeApi.getStatistics).mockResolvedValue(mockStats as any)

      const store = useHealthProbeStore()
      await store.fetchStatistics('1', 48)

      expect(api.healthProbeApi.getStatistics).toHaveBeenCalledWith('1', 48)
    })
  })

  describe('fetchLogs', () => {
    it('应该获取探测日志', async () => {
      const mockLogs = { items: [{ id: 'pr1', target_id: '1', timestamp: '', probe_type: 'http' as const, target: '', success: true }], total: 1, limit: 20, offset: 0 }
      vi.mocked(api.healthProbeApi.getLogs).mockResolvedValue(mockLogs as any)

      const store = useHealthProbeStore()
      const result = await store.fetchLogs('1')

      expect(store.currentLogs).toEqual(mockLogs)
      expect(result).toEqual(mockLogs)
    })

    it('应该支持筛选参数', async () => {
      const mockLogs = { items: [], total: 0, limit: 20, offset: 0 }
      vi.mocked(api.healthProbeApi.getLogs).mockResolvedValue(mockLogs as any)

      const store = useHealthProbeStore()
      await store.fetchLogs('1', { limit: 10, offset: 5, success: true })

      expect(api.healthProbeApi.getLogs).toHaveBeenCalledWith('1', { limit: 10, offset: 5, success: true })
    })
  })

  describe('selectTarget', () => {
    it('应该设置当前选中的目标', () => {
      const store = useHealthProbeStore()
      const target = { id: '1', name: 'Web' } as any
      store.selectTarget(target)

      expect(store.currentTarget).toEqual(target)
    })

    it('选择目标时应该清空 currentStats 和 currentLogs', () => {
      const store = useHealthProbeStore()
      store.currentStats = { target_id: '1' } as any
      store.currentLogs = { items: [], total: 0, limit: 20, offset: 0 }

      store.selectTarget({ id: '2' } as any)

      expect(store.currentStats).toBeNull()
      expect(store.currentLogs).toBeNull()
    })

    it('传入 null 应该清空 currentTarget', () => {
      const store = useHealthProbeStore()
      store.currentTarget = { id: '1' } as any
      store.selectTarget(null)

      expect(store.currentTarget).toBeNull()
    })
  })
})
