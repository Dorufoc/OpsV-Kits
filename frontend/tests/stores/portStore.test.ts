import { describe, it, expect, vi, beforeEach } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { usePortStore } from '@/stores/portStore'
import { mockGet, mockPost } from '../setup'

describe('Port Store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  describe('状态初始化', () => {
    it('应该正确初始化 ports 为空数组', () => {
      const store = usePortStore()
      expect(store.ports).toEqual([])
    })

    it('应该正确初始化 loading 为 false', () => {
      const store = usePortStore()
      expect(store.loading).toBe(false)
    })

    it('应该正确初始化 totalCount 为 0', () => {
      const store = usePortStore()
      expect(store.totalCount).toBe(0)
    })

    it('应该正确初始化 searchQuery 为空字符串', () => {
      const store = usePortStore()
      expect(store.searchQuery).toBe('')
    })

    it('应该正确初始化 protocolFilter 为空字符串', () => {
      const store = usePortStore()
      expect(store.protocolFilter).toBe('')
    })

    it('应该正确初始化 statusFilter 为空字符串', () => {
      const store = usePortStore()
      expect(store.statusFilter).toBe('')
    })

    it('应该正确初始化 sortColumn 为 port', () => {
      const store = usePortStore()
      expect(store.sortColumn).toBe('port')
    })

    it('应该正确初始化 sortOrder 为 asc', () => {
      const store = usePortStore()
      expect(store.sortOrder).toBe('asc')
    })
  })

  describe('计算属性 - filteredPorts', () => {
    const mockPorts = [
      { protocol: 'tcp', port: 80, local_address: '0.0.0.0', pid: 1234, process_name: 'nginx', status: 'LISTEN' },
      { protocol: 'tcp', port: 443, local_address: '0.0.0.0', pid: 1234, process_name: 'nginx', status: 'LISTEN' },
      { protocol: 'udp', port: 53, local_address: '0.0.0.0', pid: 5678, process_name: 'dnsmasq', status: '' },
      { protocol: 'tcp', port: 3306, local_address: '127.0.0.1', pid: 9101, process_name: 'mysqld', status: 'LISTEN' },
    ]

    it('没有筛选条件时应该返回全部端口', () => {
      const store = usePortStore()
      store.ports = mockPorts as any

      expect(store.filteredPorts).toHaveLength(4)
    })

    it('应该按 searchQuery 筛选', () => {
      const store = usePortStore()
      store.ports = mockPorts as any
      store.searchQuery = 'nginx'

      expect(store.filteredPorts).toHaveLength(2)
    })

    it('应该按端口号搜索', () => {
      const store = usePortStore()
      store.ports = mockPorts as any
      store.searchQuery = '80'

      expect(store.filteredPorts).toHaveLength(1)
      expect(store.filteredPorts[0].port).toBe(80)
    })

    it('应该按 PID 搜索', () => {
      const store = usePortStore()
      store.ports = mockPorts as any
      store.searchQuery = '5678'

      expect(store.filteredPorts).toHaveLength(1)
      expect(store.filteredPorts[0].process_name).toBe('dnsmasq')
    })

    it('应该按 local_address 搜索', () => {
      const store = usePortStore()
      store.ports = mockPorts as any
      store.searchQuery = '127.0.0.1'

      expect(store.filteredPorts).toHaveLength(1)
      expect(store.filteredPorts[0].port).toBe(3306)
    })

    it('应该按 protocolFilter 筛选', () => {
      const store = usePortStore()
      store.ports = mockPorts as any
      store.protocolFilter = 'udp'

      expect(store.filteredPorts).toHaveLength(1)
      expect(store.filteredPorts[0].protocol).toBe('udp')
    })

    it('应该按 statusFilter 筛选', () => {
      const store = usePortStore()
      store.ports = mockPorts as any
      store.statusFilter = 'LISTEN'

      expect(store.filteredPorts).toHaveLength(3)
    })

    it('应该组合多个筛选条件', () => {
      const store = usePortStore()
      store.ports = mockPorts as any
      store.searchQuery = 'nginx'
      store.protocolFilter = 'tcp'

      expect(store.filteredPorts).toHaveLength(2)
    })

    it('应该按 sortColumn 和 sortOrder 排序', () => {
      const store = usePortStore()
      store.ports = mockPorts as any
      store.sortColumn = 'port'
      store.sortOrder = 'desc'

      const result = store.filteredPorts
      expect(result[0].port).toBe(3306)
      expect(result[result.length - 1].port).toBe(53)
    })

    it('应该按字符串列排序', () => {
      const store = usePortStore()
      store.ports = mockPorts as any
      store.sortColumn = 'process_name'
      store.sortOrder = 'asc'

      const result = store.filteredPorts
      expect(result[0].process_name).toBe('dnsmasq')
    })
  })

  describe('计算属性 - occupiedPorts', () => {
    it('应该返回所有已占用端口的集合', () => {
      const store = usePortStore()
      store.ports = [
        { protocol: 'tcp', port: 80, local_address: '0.0.0.0', pid: 1234, process_name: 'nginx', status: 'LISTEN' },
        { protocol: 'tcp', port: 443, local_address: '0.0.0.0', pid: 1234, process_name: 'nginx', status: 'LISTEN' },
      ] as any

      expect(store.occupiedPorts).toEqual(new Set([80, 443]))
    })

    it('没有端口时应该返回空集合', () => {
      const store = usePortStore()
      expect(store.occupiedPorts).toEqual(new Set())
    })
  })

  describe('fetchPortList', () => {
    it('应该获取端口列表', async () => {
      const mockPorts = [
        { protocol: 'tcp', port: 80, local_address: '0.0.0.0', pid: 1234, process_name: 'nginx', status: 'LISTEN' },
      ]
      mockGet.mockResolvedValue({ ports: mockPorts, count: 1 })

      const store = usePortStore()
      const result = await store.fetchPortList()

      expect(store.ports).toEqual(mockPorts)
      expect(store.totalCount).toBe(1)
      expect(result).toEqual(mockPorts)
    })

    it('API 返回无 ports 时应该设为空数组', async () => {
      mockGet.mockResolvedValue({})

      const store = usePortStore()
      const result = await store.fetchPortList()

      expect(store.ports).toEqual([])
      expect(store.totalCount).toBe(0)
      expect(result).toEqual([])
    })

    it('请求期间 loading 应该为 true', async () => {
      mockGet.mockImplementation(async () => {
        const store = usePortStore()
        expect(store.loading).toBe(true)
        return { ports: [], count: 0 }
      })

      const store = usePortStore()
      await store.fetchPortList()
      expect(store.loading).toBe(false)
    })

    it('请求失败时 loading 应该恢复为 false 并返回空数组', async () => {
      mockGet.mockRejectedValue(new Error('Network error'))

      const store = usePortStore()
      const result = await store.fetchPortList()

      expect(store.loading).toBe(false)
      expect(result).toEqual([])
    })
  })

  describe('checkPort', () => {
    it('应该检查端口占用情况', async () => {
      const mockResult = { port: 80, occupied: true, details: [{ protocol: 'tcp', port: 80, local_address: '0.0.0.0', pid: 1234, process_name: 'nginx', status: 'LISTEN' }] }
      mockGet.mockResolvedValue(mockResult)

      const store = usePortStore()
      const result = await store.checkPort(80)

      expect(result).toEqual(mockResult)
      expect(mockGet).toHaveBeenCalledWith('/port/check', { params: { port: 80 } })
    })

    it('请求失败时应该返回 null', async () => {
      mockGet.mockRejectedValue(new Error('Network error'))

      const store = usePortStore()
      const result = await store.checkPort(80)

      expect(result).toBeNull()
    })
  })

  describe('killByPort', () => {
    it('应该按端口终止进程', async () => {
      const mockResult = { success: true, message: 'Killed', killed: [{ pid: 1234, process_name: 'nginx' }] }
      mockPost.mockResolvedValue(mockResult)

      const store = usePortStore()
      const result = await store.killByPort(80)

      expect(result).toEqual(mockResult)
      expect(mockPost).toHaveBeenCalledWith('/port/kill-by-port', { port: 80, force: false })
    })

    it('应该支持强制终止', async () => {
      const mockResult = { success: true, message: 'Force killed', killed: [{ pid: 1234, process_name: 'nginx' }] }
      mockPost.mockResolvedValue(mockResult)

      const store = usePortStore()
      await store.killByPort(80, true)

      expect(mockPost).toHaveBeenCalledWith('/port/kill-by-port', { port: 80, force: true })
    })

    it('请求失败时应该返回错误结果', async () => {
      const error = new Error('Permission denied')
      mockPost.mockRejectedValue(error)

      const store = usePortStore()
      const result = await store.killByPort(80)

      expect(result).toEqual({ success: false, message: 'Permission denied' })
    })
  })

  describe('killByPid', () => {
    it('应该按 PID 终止进程', async () => {
      const mockResult = { success: true, message: 'Killed', killed: [{ pid: 1234, process_name: 'nginx' }] }
      mockPost.mockResolvedValue(mockResult)

      const store = usePortStore()
      const result = await store.killByPid(1234)

      expect(result).toEqual(mockResult)
      expect(mockPost).toHaveBeenCalledWith('/port/kill-by-pid', { pid: 1234, force: false })
    })

    it('应该支持强制终止', async () => {
      const mockResult = { success: true, message: 'Force killed' }
      mockPost.mockResolvedValue(mockResult)

      const store = usePortStore()
      await store.killByPid(1234, true)

      expect(mockPost).toHaveBeenCalledWith('/port/kill-by-pid', { pid: 1234, force: true })
    })

    it('请求失败时应该返回错误结果', async () => {
      const error = new Error('No such process')
      mockPost.mockRejectedValue(error)

      const store = usePortStore()
      const result = await store.killByPid(9999)

      expect(result).toEqual({ success: false, message: 'No such process' })
    })
  })

  describe('toggleSort', () => {
    it('同一列应该切换排序方向', () => {
      const store = usePortStore()
      expect(store.sortColumn).toBe('port')
      expect(store.sortOrder).toBe('asc')

      store.toggleSort('port')
      expect(store.sortOrder).toBe('desc')

      store.toggleSort('port')
      expect(store.sortOrder).toBe('asc')
    })

    it('切换到新列应该重置为升序', () => {
      const store = usePortStore()
      store.sortOrder = 'desc'

      store.toggleSort('process_name')
      expect(store.sortColumn).toBe('process_name')
      expect(store.sortOrder).toBe('asc')
    })
  })
})
