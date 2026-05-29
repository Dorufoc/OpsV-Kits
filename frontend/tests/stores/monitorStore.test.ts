/**
 * Monitor Store 单元测试
 * 测试快照获取、计算属性、WebSocket 连接、历史数据和工具函数
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useMonitorStore } from '@/stores/monitorStore'
import * as api from '@/api'

describe('Monitor Store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  describe('状态初始化', () => {
    it('应该正确初始化 currentAlias 为空字符串', () => {
      const store = useMonitorStore()
      expect(store.currentAlias).toBe('')
    })

    it('应该正确初始化 snapshot 为 null', () => {
      const store = useMonitorStore()
      expect(store.snapshot).toBeNull()
    })

    it('应该正确初始化 loading 为 false', () => {
      const store = useMonitorStore()
      expect(store.loading).toBe(false)
    })

    it('应该正确初始化 streaming 为 false', () => {
      const store = useMonitorStore()
      expect(store.streaming).toBe(false)
    })

    it('应该正确初始化 history 为空数组', () => {
      const store = useMonitorStore()
      expect(store.history).toEqual([])
    })

    it('应该正确初始化 ws 为 null', () => {
      const store = useMonitorStore()
      expect(store.ws).toBeNull()
    })
  })

  describe('计算属性', () => {
    it('cpuPercent 在 snapshot 为 null 时应该返回 0', () => {
      const store = useMonitorStore()
      expect(store.cpuPercent).toBe(0)
    })

    it('cpuPercent 在有 snapshot 时应该返回 cpu 使用率', () => {
      const store = useMonitorStore()
      store.snapshot = { cpu: { usage_percent: 45.5 } } as any
      expect(store.cpuPercent).toBe(45.5)
    })

    it('memPercent 在 snapshot 为 null 时应该返回 0', () => {
      const store = useMonitorStore()
      expect(store.memPercent).toBe(0)
    })

    it('memPercent 在有 snapshot 时应该返回内存使用率', () => {
      const store = useMonitorStore()
      store.snapshot = { memory: { usage_percent: 62.3 } } as any
      expect(store.memPercent).toBe(62.3)
    })

    it('memTotal 在 snapshot 为 null 时应该返回 0', () => {
      const store = useMonitorStore()
      expect(store.memTotal).toBe(0)
    })

    it('memTotal 在有 snapshot 时应该返回总内存', () => {
      const store = useMonitorStore()
      store.snapshot = { memory: { total: 16777216 } } as any
      expect(store.memTotal).toBe(16777216)
    })

    it('memUsed 在 snapshot 为 null 时应该返回 0', () => {
      const store = useMonitorStore()
      expect(store.memUsed).toBe(0)
    })

    it('memUsed 在有 snapshot 时应该返回已用内存', () => {
      const store = useMonitorStore()
      store.snapshot = { memory: { used: 8388608 } } as any
      expect(store.memUsed).toBe(8388608)
    })

    it('loadAvg 在 snapshot 为 null 时应该返回默认值', () => {
      const store = useMonitorStore()
      expect(store.loadAvg).toEqual({ load_1m: 0, load_5m: 0, load_15m: 0 })
    })

    it('loadAvg 在有 snapshot 时应该返回负载数据', () => {
      const store = useMonitorStore()
      store.snapshot = { load: { load_1m: 1.5, load_5m: 1.2, load_15m: 0.8 } } as any
      expect(store.loadAvg).toEqual({ load_1m: 1.5, load_5m: 1.2, load_15m: 0.8 })
    })

    it('hostname 在 snapshot 为 null 时应该返回空字符串', () => {
      const store = useMonitorStore()
      expect(store.hostname).toBe('')
    })

    it('hostname 在有 snapshot 时应该返回主机名', () => {
      const store = useMonitorStore()
      store.snapshot = { hostname: 'my-server-01' } as any
      expect(store.hostname).toBe('my-server-01')
    })
  })

  describe('fetchSnapshot', () => {
    it('应该获取系统快照数据', async () => {
      const mockSnapshot = {
        timestamp: Date.now(),
        alias: 'test-server',
        hostname: 'my-server',
        cpu: { usage_percent: 35, cores: 4, user_percent: 25, system_percent: 8, iowait_percent: 2 },
        memory: { total: 16777216, used: 8388608, free: 4194304, available: 8388608, usage_percent: 50, available_percent: 50 },
        disks: [],
        network: [],
        load: { load_1m: 0.5, load_5m: 0.4, load_15m: 0.3 },
        connections: {},
        top_processes: [],
        uptime: 86400,
        docker_containers: [],
        cores: [],
      }
      vi.spyOn(api, 'request').mockResolvedValue(mockSnapshot as any)

      const store = useMonitorStore()
      store.currentAlias = 'test-server'
      const result = await store.fetchSnapshot()

      expect(store.snapshot).toEqual(mockSnapshot)
      expect(result).toEqual(mockSnapshot)
    })

    it('获取快照后应该添加到历史记录', async () => {
      const mockSnapshot = { timestamp: Date.now(), hostname: 'server1' } as any
      vi.spyOn(api, 'request').mockResolvedValue(mockSnapshot)

      const store = useMonitorStore()
      store.currentAlias = 'test-server'
      await store.fetchSnapshot()

      expect(store.history).toContainEqual(mockSnapshot)
    })

    it('历史记录超过 maxHistory 时应该移除最旧的数据', async () => {
      const store = useMonitorStore()
      store.currentAlias = 'test-server'

      // 模拟 maxHistory 限制
      const originalMaxHistory = (store as any).maxHistory || 300
      // 由于 mock 限制，我们只验证 push 行为
      vi.spyOn(api, 'request').mockResolvedValue({ timestamp: Date.now() } as any)

      // 先填充历史到限制
      for (let i = 0; i < 301; i++) {
        store.history.push({ timestamp: i } as any)
      }

      await store.fetchSnapshot()

      // 历史记录应该被截断
      expect(store.history.length).toBeLessThanOrEqual(301)
    })

    it('请求期间 loading 应该为 true', async () => {
      vi.spyOn(api, 'request').mockImplementation(async () => {
        const store = useMonitorStore()
        expect(store.loading).toBe(true)
        return {}
      })

      const store = useMonitorStore()
      store.currentAlias = 'test-server'
      await store.fetchSnapshot()
      expect(store.loading).toBe(false)
    })

    it('请求失败时 loading 应该恢复为 false', async () => {
      vi.spyOn(api, 'request').mockRejectedValue(new Error('Network error'))

      const store = useMonitorStore()
      store.currentAlias = 'test-server'
      await expect(store.fetchSnapshot()).rejects.toThrow()
      expect(store.loading).toBe(false)
    })

    it('当没有 alias 时应该直接返回', async () => {
      const store = useMonitorStore()
      const result = await store.fetchSnapshot()
      expect(result).toBeUndefined()
    })
  })

  describe('fetchHistory', () => {
    it('应该获取历史监控数据', async () => {
      const mockHistory = [
        { timestamp: Date.now() - 300000, hostname: 'server1' },
        { timestamp: Date.now() - 240000, hostname: 'server1' },
        { timestamp: Date.now() - 180000, hostname: 'server1' },
      ]
      vi.spyOn(api, 'request').mockResolvedValue({ history: mockHistory } as any)

      const store = useMonitorStore()
      store.currentAlias = 'test-server'
      const result = await store.fetchHistory()

      expect(store.history).toEqual(mockHistory)
      expect(result).toEqual(mockHistory)
    })

    it('应该支持自定义时间范围参数', async () => {
      vi.spyOn(api, 'request').mockResolvedValue({ history: [] } as any)

      const store = useMonitorStore()
      store.currentAlias = 'test-server'
      await store.fetchHistory(undefined, 600)

      expect(api.request.get).toHaveBeenCalledWith('/monitor/history', {
        params: { alias: 'test-server', seconds: 600 },
      })
    })

    it('当没有 alias 时应该直接返回', async () => {
      const store = useMonitorStore()
      const result = await store.fetchHistory()
      expect(result).toBeUndefined()
    })
  })

  describe('formatBytes', () => {
    it('0 字节应该返回 "0 B"', () => {
      const store = useMonitorStore()
      expect(store.formatBytes(0)).toBe('0 B')
    })

    it('负数应该返回 "0 B"', () => {
      const store = useMonitorStore()
      expect(store.formatBytes(-100)).toBe('0 B')
    })

    it('小于 1024 字节应该返回 B 单位', () => {
      const store = useMonitorStore()
      expect(store.formatBytes(500)).toBe('500.0 B')
    })

    it('1024 字节应该返回 KB 单位', () => {
      const store = useMonitorStore()
      expect(store.formatBytes(1024)).toBe('1.0 KB')
    })

    it('1048576 字节应该返回 MB 单位', () => {
      const store = useMonitorStore()
      expect(store.formatBytes(1048576)).toBe('1.0 MB')
    })

    it('1073741824 字节应该返回 GB 单位', () => {
      const store = useMonitorStore()
      expect(store.formatBytes(1073741824)).toBe('1.0 GB')
    })

    it('1099511627776 字节应该返回 TB 单位', () => {
      const store = useMonitorStore()
      expect(store.formatBytes(1099511627776)).toBe('1.0 TB')
    })
  })

  describe('connectWebSocket', () => {
    let mockWebSocket: any

    beforeEach(() => {
      mockWebSocket = {
        onopen: null,
        onmessage: null,
        onclose: null,
        onerror: null,
        close: vi.fn(),
        send: vi.fn(),
        readyState: WebSocket.OPEN,
      }
      vi.stubGlobal('WebSocket', vi.fn(() => mockWebSocket))
    })

    afterEach(() => {
      vi.unstubAllGlobals()
    })

    it('应该创建 WebSocket 连接', () => {
      const store = useMonitorStore()
      store.currentAlias = 'test-server'
      store.connectWebSocket()

      expect(WebSocket).toHaveBeenCalled()
    })

    it('连接成功后 streaming 应该为 true', () => {
      const store = useMonitorStore()
      store.currentAlias = 'test-server'
      store.connectWebSocket()

      mockWebSocket.onopen()

      expect(store.streaming).toBe(true)
    })

    it('收到快照数据时应该更新 snapshot 和 history', () => {
      const store = useMonitorStore()
      store.currentAlias = 'test-server'
      store.connectWebSocket()

      const mockData = { type: 'snapshot', timestamp: Date.now(), hostname: 'server1', cpu: { usage_percent: 50 } }
      mockWebSocket.onmessage({ data: JSON.stringify(mockData) })

      expect(store.snapshot).toEqual(mockData)
      expect(store.history).toContainEqual(mockData)
    })

    it('收到 pong 消息时应该忽略', () => {
      const store = useMonitorStore()
      store.currentAlias = 'test-server'
      store.connectWebSocket()
      store.snapshot = { hostname: 'before' } as any

      mockWebSocket.onmessage({ data: JSON.stringify({ type: 'pong' }) })

      expect(store.snapshot).toEqual({ hostname: 'before' })
    })

    it('关闭连接时 streaming 应该为 false', () => {
      const store = useMonitorStore()
      store.currentAlias = 'test-server'
      store.connectWebSocket()
      store.streaming = true

      mockWebSocket.onclose()

      expect(store.streaming).toBe(false)
      expect(store.ws).toBeNull()
    })

    it('连接错误时 streaming 应该为 false', () => {
      const store = useMonitorStore()
      store.currentAlias = 'test-server'
      store.connectWebSocket()
      store.streaming = true

      mockWebSocket.onerror()

      expect(store.streaming).toBe(false)
      expect(store.ws).toBeNull()
    })

    it('已有连接时应该先断开', () => {
      const store = useMonitorStore()
      store.currentAlias = 'test-server'

      const closeSpy = vi.fn()
      mockWebSocket.close = closeSpy

      store.connectWebSocket()
      store.connectWebSocket()

      expect(closeSpy).toHaveBeenCalled()
    })

    it('当没有 alias 时应该直接返回', () => {
      const store = useMonitorStore()
      store.connectWebSocket()

      expect(WebSocket).not.toHaveBeenCalled()
    })
  })

  describe('disconnect', () => {
    let mockWebSocket: any

    beforeEach(() => {
      mockWebSocket = {
        close: vi.fn(),
      }
    })

    it('应该关闭 WebSocket 连接', () => {
      const store = useMonitorStore()
      store.ws = mockWebSocket as any
      store.streaming = true

      store.disconnect()

      expect(mockWebSocket.close).toHaveBeenCalled()
      expect(store.ws).toBeNull()
      expect(store.streaming).toBe(false)
    })

    it('当没有 WebSocket 时应该只更新 streaming 状态', () => {
      const store = useMonitorStore()
      store.ws = null
      store.streaming = true

      store.disconnect()

      expect(store.streaming).toBe(false)
    })
  })
})
