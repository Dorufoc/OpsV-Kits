import { describe, it, expect, vi, beforeEach } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useEventTriggerStore } from '@/stores/eventTriggerStore'
import * as api from '@/api'

describe('EventTrigger Store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  describe('状态初始化', () => {
    it('应该正确初始化 sources 为空数组', () => {
      const store = useEventTriggerStore()
      expect(store.sources).toEqual([])
    })

    it('应该正确初始化 routes 为空数组', () => {
      const store = useEventTriggerStore()
      expect(store.routes).toEqual([])
    })

    it('应该正确初始化 eventLogs 为空数组', () => {
      const store = useEventTriggerStore()
      expect(store.eventLogs).toEqual([])
    })

    it('应该正确初始化 loading 为 false', () => {
      const store = useEventTriggerStore()
      expect(store.loading).toBe(false)
    })
  })

  describe('fetchSources', () => {
    it('应该获取事件源列表', async () => {
      const mockSources = [
        { id: '1', name: 'Webhook Source', source_type: 'webhook', config: {}, status: 'active', event_count: 10, created_at: '', updated_at: '' },
      ]
      vi.mocked(api.eventTriggerApi.listSources).mockResolvedValue({ items: mockSources } as any)

      const store = useEventTriggerStore()
      await store.fetchSources()

      expect(store.sources).toEqual(mockSources)
    })

    it('API 返回无 items 时应该设为空数组', async () => {
      vi.mocked(api.eventTriggerApi.listSources).mockResolvedValue({} as any)

      const store = useEventTriggerStore()
      await store.fetchSources()

      expect(store.sources).toEqual([])
    })

    it('请求期间 loading 应该为 true', async () => {
      vi.mocked(api.eventTriggerApi.listSources).mockImplementation(async () => {
        const store = useEventTriggerStore()
        expect(store.loading).toBe(true)
        return { items: [] }
      })

      const store = useEventTriggerStore()
      await store.fetchSources()
      expect(store.loading).toBe(false)
    })

    it('请求失败时 loading 应该恢复为 false', async () => {
      vi.mocked(api.eventTriggerApi.listSources).mockRejectedValue(new Error('Network error'))

      const store = useEventTriggerStore()
      await expect(store.fetchSources()).rejects.toThrow()
      expect(store.loading).toBe(false)
    })
  })

  describe('createSource', () => {
    it('应该创建事件源并添加到列表', async () => {
      const newSource = { id: '2', name: 'New Source', source_type: 'webhook', config: {}, status: 'active', event_count: 0, created_at: '', updated_at: '' }
      vi.mocked(api.eventTriggerApi.createSource).mockResolvedValue(newSource as any)

      const store = useEventTriggerStore()
      const result = await store.createSource({ name: 'New Source' })

      expect(store.sources).toContainEqual(newSource)
      expect(result).toEqual(newSource)
    })
  })

  describe('updateSource', () => {
    it('应该更新事件源并同步列表', async () => {
      const store = useEventTriggerStore()
      store.sources = [
        { id: '1', name: 'Old', source_type: 'webhook', config: {}, status: 'active', event_count: 5, created_at: '', updated_at: '' },
      ] as any

      const updatedSource = { id: '1', name: 'Updated', source_type: 'webhook', config: {}, status: 'inactive', event_count: 5, created_at: '', updated_at: '' }
      vi.mocked(api.eventTriggerApi.updateSource).mockResolvedValue(updatedSource as any)

      const result = await store.updateSource('1', { name: 'Updated' })

      expect(store.sources[0]).toEqual(updatedSource)
      expect(result).toEqual(updatedSource)
    })

    it('更新不存在的源时不应修改列表', async () => {
      const store = useEventTriggerStore()
      store.sources = [
        { id: '1', name: 'Old', source_type: 'webhook', config: {}, status: 'active', event_count: 5, created_at: '', updated_at: '' },
      ] as any

      const updatedSource = { id: '99', name: 'Updated', source_type: 'webhook', config: {}, status: 'inactive', event_count: 5, created_at: '', updated_at: '' }
      vi.mocked(api.eventTriggerApi.updateSource).mockResolvedValue(updatedSource as any)

      await store.updateSource('99', { name: 'Updated' })

      expect(store.sources).toHaveLength(1)
      expect(store.sources[0].id).toBe('1')
    })
  })

  describe('deleteSource', () => {
    it('应该从列表中删除事件源', async () => {
      vi.mocked(api.eventTriggerApi.deleteSource).mockResolvedValue({} as any)

      const store = useEventTriggerStore()
      store.sources = [
        { id: '1', name: 'S1', source_type: 'webhook', config: {}, status: 'active', event_count: 5, created_at: '', updated_at: '' },
        { id: '2', name: 'S2', source_type: 'cron', config: {}, status: 'active', event_count: 3, created_at: '', updated_at: '' },
      ] as any

      await store.deleteSource('1')

      expect(store.sources).toHaveLength(1)
      expect(store.sources[0].id).toBe('2')
    })
  })

  describe('fetchRoutes', () => {
    it('应该获取路由列表', async () => {
      const mockRoutes = [
        { id: 'r1', source_id: '1', workflow_id: 'w1', transforms: [], enabled: true, created_at: '' },
      ]
      vi.mocked(api.eventTriggerApi.listRoutes).mockResolvedValue({ items: mockRoutes } as any)

      const store = useEventTriggerStore()
      await store.fetchRoutes()

      expect(store.routes).toEqual(mockRoutes)
    })

    it('API 返回无 items 时应该设为空数组', async () => {
      vi.mocked(api.eventTriggerApi.listRoutes).mockResolvedValue({} as any)

      const store = useEventTriggerStore()
      await store.fetchRoutes()

      expect(store.routes).toEqual([])
    })

    it('应该支持 sourceId 参数', async () => {
      vi.mocked(api.eventTriggerApi.listRoutes).mockResolvedValue({ items: [] } as any)

      const store = useEventTriggerStore()
      await store.fetchRoutes('src-1')

      expect(api.eventTriggerApi.listRoutes).toHaveBeenCalledWith('src-1')
    })
  })

  describe('createRoute', () => {
    it('应该创建路由并添加到列表', async () => {
      const newRoute = { id: 'r2', source_id: '1', workflow_id: 'w2', transforms: [], enabled: true, created_at: '' }
      vi.mocked(api.eventTriggerApi.createRoute).mockResolvedValue(newRoute as any)

      const store = useEventTriggerStore()
      const result = await store.createRoute({ source_id: '1', workflow_id: 'w2' })

      expect(store.routes).toContainEqual(newRoute)
      expect(result).toEqual(newRoute)
    })
  })

  describe('updateRoute', () => {
    it('应该更新路由并同步列表', async () => {
      const store = useEventTriggerStore()
      store.routes = [
        { id: 'r1', source_id: '1', workflow_id: 'w1', transforms: [], enabled: true, created_at: '' },
      ] as any

      const updatedRoute = { id: 'r1', source_id: '1', workflow_id: 'w1', transforms: [], enabled: false, created_at: '' }
      vi.mocked(api.eventTriggerApi.updateRoute).mockResolvedValue(updatedRoute as any)

      const result = await store.updateRoute('r1', { enabled: false })

      expect(store.routes[0]).toEqual(updatedRoute)
      expect(result).toEqual(updatedRoute)
    })
  })

  describe('deleteRoute', () => {
    it('应该从列表中删除路由', async () => {
      vi.mocked(api.eventTriggerApi.deleteRoute).mockResolvedValue({} as any)

      const store = useEventTriggerStore()
      store.routes = [
        { id: 'r1', source_id: '1', workflow_id: 'w1', transforms: [], enabled: true, created_at: '' },
        { id: 'r2', source_id: '1', workflow_id: 'w2', transforms: [], enabled: true, created_at: '' },
      ] as any

      await store.deleteRoute('r1')

      expect(store.routes).toHaveLength(1)
      expect(store.routes[0].id).toBe('r2')
    })
  })

  describe('fetchEventLogs', () => {
    it('应该获取事件日志列表', async () => {
      const mockLogs = [
        { id: 'l1', source_id: '1', source_name: 'Webhook', event_type: 'push', raw_data: {}, filtered: false, matched_routes: [], triggered_workflows: [], status: 'success', received_at: '' },
      ]
      vi.mocked(api.eventTriggerApi.listLogs).mockResolvedValue({ items: mockLogs } as any)

      const store = useEventTriggerStore()
      await store.fetchEventLogs()

      expect(store.eventLogs).toEqual(mockLogs)
    })

    it('API 返回无 items 时应该设为空数组', async () => {
      vi.mocked(api.eventTriggerApi.listLogs).mockResolvedValue({} as any)

      const store = useEventTriggerStore()
      await store.fetchEventLogs()

      expect(store.eventLogs).toEqual([])
    })

    it('请求期间 loading 应该为 true', async () => {
      vi.mocked(api.eventTriggerApi.listLogs).mockImplementation(async () => {
        const store = useEventTriggerStore()
        expect(store.loading).toBe(true)
        return { items: [] }
      })

      const store = useEventTriggerStore()
      await store.fetchEventLogs()
      expect(store.loading).toBe(false)
    })

    it('请求失败时 loading 应该恢复为 false', async () => {
      vi.mocked(api.eventTriggerApi.listLogs).mockRejectedValue(new Error('Network error'))

      const store = useEventTriggerStore()
      await expect(store.fetchEventLogs()).rejects.toThrow()
      expect(store.loading).toBe(false)
    })

    it('应该支持筛选参数', async () => {
      vi.mocked(api.eventTriggerApi.listLogs).mockResolvedValue({ items: [] } as any)

      const store = useEventTriggerStore()
      await store.fetchEventLogs('src-1', 'push', 'success')

      expect(api.eventTriggerApi.listLogs).toHaveBeenCalledWith('src-1', 'push', 'success')
    })
  })

  describe('replayEvent', () => {
    it('应该重放事件', async () => {
      const mockResult = { success: true, log_id: 'l1' }
      vi.mocked(api.eventTriggerApi.replayEvent).mockResolvedValue(mockResult as any)

      const store = useEventTriggerStore()
      const result = await store.replayEvent('l1')

      expect(result).toEqual(mockResult)
      expect(api.eventTriggerApi.replayEvent).toHaveBeenCalledWith('l1')
    })
  })
})
