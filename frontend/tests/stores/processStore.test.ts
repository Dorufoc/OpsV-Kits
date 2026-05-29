/**
 * Process Store 单元测试
 * 测试进程列表获取、过滤排序、操作控制、异常检测和刷新机制
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useProcessStore } from '@/stores/processStore'
import * as api from '@/api'

describe('Process Store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  describe('状态初始化', () => {
    it('应该正确初始化 processes 为空数组', () => {
      const store = useProcessStore()
      expect(store.processes).toEqual([])
    })

    it('应该正确初始化 loading 为 false', () => {
      const store = useProcessStore()
      expect(store.loading).toBe(false)
    })

    it('应该正确初始化 streaming 为 false', () => {
      const store = useProcessStore()
      expect(store.streaming).toBe(false)
    })

    it('应该正确初始化 searchQuery 为空字符串', () => {
      const store = useProcessStore()
      expect(store.searchQuery).toBe('')
    })

    it('应该正确初始化 statusFilter 为空数组', () => {
      const store = useProcessStore()
      expect(store.statusFilter).toEqual([])
    })

    it('应该正确初始化 userFilter 为空字符串', () => {
      const store = useProcessStore()
      expect(store.userFilter).toBe('')
    })

    it('应该正确初始化 sortColumn 为 cpu_percent', () => {
      const store = useProcessStore()
      expect(store.sortColumn).toBe('cpu_percent')
    })

    it('应该正确初始化 sortOrder 为 desc', () => {
      const store = useProcessStore()
      expect(store.sortOrder).toBe('desc')
    })

    it('应该正确初始化 selectedPids 为空 Set', () => {
      const store = useProcessStore()
      expect(store.selectedPids).toEqual(new Set())
    })

    it('应该正确初始化 alertConfig 默认值', () => {
      const store = useProcessStore()
      expect(store.alertConfig.cpu_threshold).toBe(90)
      expect(store.alertConfig.mem_threshold).toBe(80)
      expect(store.alertConfig.duration_seconds).toBe(5)
    })

    it('应该正确初始化 refreshInterval 为 3000', () => {
      const store = useProcessStore()
      expect(store.refreshInterval).toBe(3000)
    })
  })

  describe('filteredProcesses 计算属性', () => {
    const mockProcesses = [
      { pid: 1, ppid: 0, user: 'root', cpu_percent: 15, mem_percent: 5, name: 'nginx', command: '/usr/sbin/nginx', status: 'running', vsz: 1000, rss: 500, tty: '?', start_time: '10:00', cpu_time: '01:00', thread_count: 1 },
      { pid: 2, ppid: 0, user: 'www', cpu_percent: 35, mem_percent: 20, name: 'node', command: 'node app.js', status: 'running', vsz: 2000, rss: 1000, tty: '?', start_time: '11:00', cpu_time: '02:00', thread_count: 4 },
      { pid: 3, ppid: 0, user: 'root', cpu_percent: 0, mem_percent: 1, name: 'cron', command: '/usr/sbin/cron', status: 'sleeping', vsz: 500, rss: 200, tty: '?', start_time: '09:00', cpu_time: '00:10', thread_count: 1 },
    ]

    it('没有过滤条件时应该返回所有进程', () => {
      const store = useProcessStore()
      store.processes = mockProcesses as any
      expect(store.filteredProcesses).toHaveLength(3)
    })

    it('应该根据 searchQuery 搜索过滤', () => {
      const store = useProcessStore()
      store.processes = mockProcesses as any
      store.searchQuery = 'nginx'
      expect(store.filteredProcesses).toHaveLength(1)
      expect(store.filteredProcesses[0].name).toBe('nginx')
    })

    it('搜索应该不区分大小写', () => {
      const store = useProcessStore()
      store.processes = mockProcesses as any
      store.searchQuery = 'NGINX'
      expect(store.filteredProcesses).toHaveLength(1)
    })

    it('搜索应该匹配 pid', () => {
      const store = useProcessStore()
      store.processes = mockProcesses as any
      store.searchQuery = '2'
      expect(store.filteredProcesses).toHaveLength(1)
      expect(store.filteredProcesses[0].pid).toBe(2)
    })

    it('搜索应该匹配 user', () => {
      const store = useProcessStore()
      store.processes = mockProcesses as any
      store.searchQuery = 'www'
      expect(store.filteredProcesses).toHaveLength(1)
      expect(store.filteredProcesses[0].user).toBe('www')
    })

    it('搜索应该匹配 command', () => {
      const store = useProcessStore()
      store.processes = mockProcesses as any
      store.searchQuery = 'app.js'
      expect(store.filteredProcesses).toHaveLength(1)
    })

    it('应该根据 statusFilter 过滤', () => {
      const store = useProcessStore()
      store.processes = mockProcesses as any
      store.statusFilter = ['sleeping']
      expect(store.filteredProcesses).toHaveLength(1)
      expect(store.filteredProcesses[0].status).toBe('sleeping')
    })

    it('应该支持多状态过滤', () => {
      const store = useProcessStore()
      store.processes = mockProcesses as any
      store.statusFilter = ['running', 'sleeping']
      expect(store.filteredProcesses).toHaveLength(3)
    })

    it('应该根据 userFilter 过滤', () => {
      const store = useProcessStore()
      store.processes = mockProcesses as any
      store.userFilter = 'root'
      expect(store.filteredProcesses).toHaveLength(2)
    })

    it('应该按 cpu_percent 降序排序', () => {
      const store = useProcessStore()
      store.processes = mockProcesses as any
      store.sortColumn = 'cpu_percent'
      store.sortOrder = 'desc'
      expect(store.filteredProcesses[0].cpu_percent).toBe(35)
      expect(store.filteredProcesses[2].cpu_percent).toBe(0)
    })

    it('应该按 cpu_percent 升序排序', () => {
      const store = useProcessStore()
      store.processes = mockProcesses as any
      store.sortColumn = 'cpu_percent'
      store.sortOrder = 'asc'
      expect(store.filteredProcesses[0].cpu_percent).toBe(0)
      expect(store.filteredProcesses[2].cpu_percent).toBe(35)
    })

    it('sortOrder 为 null 时不应该排序', () => {
      const store = useProcessStore()
      store.processes = mockProcesses as any
      store.sortColumn = 'cpu_percent'
      store.sortOrder = null
      expect(store.filteredProcesses[0].pid).toBe(1)
    })
  })

  describe('uniqueUsers 计算属性', () => {
    it('应该返回去重并排序的用户列表', () => {
      const store = useProcessStore()
      store.processes = [
        { pid: 1, user: 'root' },
        { pid: 2, user: 'www' },
        { pid: 3, user: 'root' },
        { pid: 4, user: 'admin' },
      ] as any
      expect(store.uniqueUsers).toEqual(['admin', 'root', 'www'])
    })

    it('空进程列表时应该返回空数组', () => {
      const store = useProcessStore()
      expect(store.uniqueUsers).toEqual([])
    })
  })

  describe('selectedCount 计算属性', () => {
    it('应该返回已选中进程数量', () => {
      const store = useProcessStore()
      store.selectedPids = new Set([1, 2, 3])
      expect(store.selectedCount).toBe(3)
    })

    it('没有选中项时应该返回 0', () => {
      const store = useProcessStore()
      expect(store.selectedCount).toBe(0)
    })
  })

  describe('fetchProcessList', () => {
    it('应该获取进程列表', async () => {
      const mockResponse = {
        processes: [
          { pid: 1, name: 'nginx', user: 'root', cpu_percent: 10, mem_percent: 5 },
        ],
        count: 1,
        timestamp: 1234567890,
      }
      vi.spyOn(api, 'request').mockResolvedValue(mockResponse as any)

      const store = useProcessStore()
      store.currentAlias = 'test-server'
      await store.fetchProcessList()

      expect(store.processes.length).toBe(1)
      expect(store.count).toBe(1)
      expect(store.timestamp).toBe(1234567890)
    })

    it('请求期间 loading 应该为 true', async () => {
      vi.spyOn(api, 'request').mockImplementation(async () => {
        const store = useProcessStore()
        expect(store.loading).toBe(true)
        return { processes: [], count: 0, timestamp: Date.now() }
      })

      const store = useProcessStore()
      store.currentAlias = 'test-server'
      await store.fetchProcessList()
      expect(store.loading).toBe(false)
    })

    it('请求失败时 loading 应该恢复为 false', async () => {
      vi.spyOn(api, 'request').mockRejectedValue(new Error('Network error'))

      const store = useProcessStore()
      store.currentAlias = 'test-server'
      await store.fetchProcessList()
      expect(store.loading).toBe(false)
    })

    it('当没有 alias 时应该直接返回', async () => {
      const store = useProcessStore()
      const result = await store.fetchProcessList()
      expect(result).toBeUndefined()
    })
  })

  describe('killProcess', () => {
    it('应该调用终止进程 API', async () => {
      vi.spyOn(api, 'request').mockResolvedValue({} as any)

      const store = useProcessStore()
      store.currentAlias = 'test-server'
      await store.killProcess(1234, 'SIGTERM')

      expect(api.request.post).toHaveBeenCalledWith('/process/kill', {
        alias: 'test-server',
        pid: 1234,
        signal: 'SIGTERM',
      })
    })

    it('请求失败时应该抛出错误', async () => {
      const error = new Error('Permission denied')
      vi.spyOn(api, 'request').mockRejectedValue(error)

      const store = useProcessStore()
      store.currentAlias = 'test-server'
      await expect(store.killProcess(1234, 'SIGTERM')).rejects.toThrow('Permission denied')
    })

    it('当没有 alias 时应该直接返回', async () => {
      const store = useProcessStore()
      const result = await store.killProcess(1234, 'SIGTERM')
      expect(result).toBeUndefined()
    })
  })

  describe('setNice', () => {
    it('应该调用设置 nice 值 API', async () => {
      vi.spyOn(api, 'request').mockResolvedValue({} as any)

      const store = useProcessStore()
      store.currentAlias = 'test-server'
      await store.setNice(1234, -10)

      expect(api.request.post).toHaveBeenCalledWith('/process/nice', {
        alias: 'test-server',
        pid: 1234,
        nice_value: -10,
      })
    })

    it('请求失败时应该抛出错误', async () => {
      const error = new Error('Permission denied')
      vi.spyOn(api, 'request').mockRejectedValue(error)

      const store = useProcessStore()
      store.currentAlias = 'test-server'
      await expect(store.setNice(1234, -10)).rejects.toThrow('Permission denied')
    })
  })

  describe('batchKill', () => {
    it('应该调用批量终止进程 API', async () => {
      vi.spyOn(api, 'request').mockResolvedValue({} as any)

      const store = useProcessStore()
      store.currentAlias = 'test-server'
      await store.batchKill([1, 2, 3], 'SIGTERM')

      expect(api.request.post).toHaveBeenCalledWith('/process/batch/kill', {
        alias: 'test-server',
        pids: [1, 2, 3],
        signal: 'SIGTERM',
      })
    })

    it('请求失败时应该抛出错误', async () => {
      vi.spyOn(api, 'request').mockRejectedValue(new Error('Batch kill failed'))

      const store = useProcessStore()
      store.currentAlias = 'test-server'
      await expect(store.batchKill([1, 2], 'SIGKILL')).rejects.toThrow('Batch kill failed')
    })
  })

  describe('serviceControl', () => {
    it('应该调用服务控制 API', async () => {
      vi.spyOn(api, 'request').mockResolvedValue({} as any)

      const store = useProcessStore()
      store.currentAlias = 'test-server'
      await store.serviceControl('nginx', 'restart')

      expect(api.request.post).toHaveBeenCalledWith('/process/service/control', {
        alias: 'test-server',
        service_name: 'nginx',
        action: 'restart',
      })
    })

    it('请求失败时应该抛出错误', async () => {
      vi.spyOn(api, 'request').mockRejectedValue(new Error('Service not found'))

      const store = useProcessStore()
      store.currentAlias = 'test-server'
      await expect(store.serviceControl('unknown', 'restart')).rejects.toThrow('Service not found')
    })
  })

  describe('Alert Config', () => {
    it('fetchAlertConfig 应该获取告警配置', async () => {
      const mockConfig = { cpu_threshold: 80, mem_threshold: 70, duration_seconds: 10 }
      vi.spyOn(api, 'request').mockResolvedValue(mockConfig as any)

      const store = useProcessStore()
      store.currentAlias = 'test-server'
      await store.fetchAlertConfig()

      expect(store.alertConfig).toEqual(mockConfig)
    })

    it('saveAlertConfig 应该保存告警配置', async () => {
      vi.spyOn(api, 'request').mockResolvedValue({} as any)

      const store = useProcessStore()
      store.currentAlias = 'test-server'
      const newConfig = { cpu_threshold: 95, mem_threshold: 85, duration_seconds: 30 }
      await store.saveAlertConfig(newConfig)

      expect(api.request.put).toHaveBeenCalledWith('/process/alert-config', {
        alias: 'test-server',
        ...newConfig,
      })
      expect(store.alertConfig).toEqual(newConfig)
    })
  })

  describe('fetchAnomalies', () => {
    it('应该获取异常数据', async () => {
      const mockAnomalies = {
        zombies: [100, 200],
        high_cpu: [{ pid: 300, cpu_percent: 95, duration: 60 }],
        high_mem: [{ pid: 400, mem_percent: 90, duration: 30 }],
        total_anomalies: 4,
      }
      vi.spyOn(api, 'request').mockResolvedValue(mockAnomalies as any)

      const store = useProcessStore()
      store.currentAlias = 'test-server'
      await store.fetchAnomalies()

      expect(store.anomalies).toEqual(mockAnomalies)
    })
  })

  describe('isAnomaly', () => {
    it('没有异常数据时应该返回全部 false', () => {
      const store = useProcessStore()
      store.anomalies = null
      expect(store.isAnomaly(100)).toEqual({ isZombie: false, isHighCpu: false, isHighMem: false })
    })

    it('应该正确检测僵尸进程', () => {
      const store = useProcessStore()
      store.anomalies = { zombies: [100], high_cpu: [], high_mem: [], total_anomalies: 1 }
      expect(store.isAnomaly(100).isZombie).toBe(true)
      expect(store.isAnomaly(200).isZombie).toBe(false)
    })

    it('应该正确检测高 CPU 进程', () => {
      const store = useProcessStore()
      store.anomalies = { zombies: [], high_cpu: [{ pid: 300, cpu_percent: 95, duration: 60 }], high_mem: [], total_anomalies: 1 }
      expect(store.isAnomaly(300).isHighCpu).toBe(true)
      expect(store.isAnomaly(100).isHighCpu).toBe(false)
    })

    it('应该正确检测高内存进程', () => {
      const store = useProcessStore()
      store.anomalies = { zombies: [], high_cpu: [], high_mem: [{ pid: 400, mem_percent: 90, duration: 30 }], total_anomalies: 1 }
      expect(store.isAnomaly(400).isHighMem).toBe(true)
      expect(store.isAnomaly(100).isHighMem).toBe(false)
    })
  })

  describe('anomalyPidSet 计算属性', () => {
    it('没有异常数据时应该返回空 Set', () => {
      const store = useProcessStore()
      store.anomalies = null
      expect(store.anomalyPidSet).toEqual(new Set())
    })

    it('应该合并所有异常 PID', () => {
      const store = useProcessStore()
      store.anomalies = {
        zombies: [100],
        high_cpu: [{ pid: 200, cpu_percent: 95, duration: 60 }],
        high_mem: [{ pid: 300, mem_percent: 90, duration: 30 }],
        total_anomalies: 3,
      }
      expect(store.anomalyPidSet).toEqual(new Set([100, 200, 300]))
    })
  })

  describe('Selection Methods', () => {
    it('toggleSelection 应该切换单个 PID 的选中状态', () => {
      const store = useProcessStore()
      store.selectedPids = new Set([1, 2])
      store.toggleSelection(2)
      expect(store.selectedPids).toEqual(new Set([1]))
      store.toggleSelection(2)
      expect(store.selectedPids).toEqual(new Set([1, 2]))
    })

    it('selectAll 应该选中过滤后的所有进程', () => {
      const store = useProcessStore()
      store.processes = [{ pid: 1 }, { pid: 2 }, { pid: 3 }] as any
      store.selectAll()
      expect(store.selectedPids).toEqual(new Set([1, 2, 3]))
    })

    it('deselectAll 应该取消所有选中', () => {
      const store = useProcessStore()
      store.selectedPids = new Set([1, 2, 3])
      store.deselectAll()
      expect(store.selectedPids).toEqual(new Set())
    })
  })

  describe('formatBytes', () => {
    it('0 KB 应该返回 "0 KB"', () => {
      const store = useProcessStore()
      expect(store.formatBytes(0)).toBe('0 KB')
    })

    it('小于 1024 KB 应该返回 KB', () => {
      const store = useProcessStore()
      expect(store.formatBytes(500)).toBe('500 KB')
    })

    it('1024 KB 应该返回 MB', () => {
      const store = useProcessStore()
      expect(store.formatBytes(1024)).toBe('1.0 MB')
    })

    it('1048576 KB 应该返回 GB', () => {
      const store = useProcessStore()
      expect(store.formatBytes(1048576)).toBe('1.00 GB')
    })
  })

  describe('Refresh Control', () => {
    it('startAutoRefresh 应该启动定时刷新', () => {
      vi.useFakeTimers()
      const store = useProcessStore()
      store.currentAlias = 'test-server'
      store.refreshInterval = 3000

      const fetchSpy = vi.spyOn(store, 'fetchProcessList').mockResolvedValue(undefined as any)
      store.startAutoRefresh()

      vi.advanceTimersByTime(3000)
      expect(fetchSpy).toHaveBeenCalled()

      store.stopAutoRefresh()
      vi.useRealTimers()
    })

    it('stopAutoRefresh 应该停止定时刷新', () => {
      vi.useFakeTimers()
      const store = useProcessStore()
      store.refreshInterval = 3000
      const fetchSpy = vi.spyOn(store, 'fetchProcessList').mockResolvedValue(undefined as any)

      store.startAutoRefresh()
      store.stopAutoRefresh()
      vi.advanceTimersByTime(3000)
      expect(fetchSpy).toHaveBeenCalledTimes(0)

      vi.useRealTimers()
    })

    it('setRefreshInterval 应该更新间隔并启动刷新', () => {
      vi.useFakeTimers()
      const store = useProcessStore()
      store.currentAlias = 'test-server'
      const fetchSpy = vi.spyOn(store, 'fetchProcessList').mockResolvedValue(undefined as any)

      store.setRefreshInterval(1000)
      vi.advanceTimersByTime(1000)
      expect(fetchSpy).toHaveBeenCalled()

      store.stopAutoRefresh()
      vi.useRealTimers()
    })

    it('refreshInterval 为 0 时不应该启动定时', () => {
      const store = useProcessStore()
      store.refreshInterval = 0
      const fetchSpy = vi.spyOn(store, 'fetchProcessList').mockResolvedValue(undefined as any)

      store.startAutoRefresh()
      expect(fetchSpy).not.toHaveBeenCalled()

      store.stopAutoRefresh()
    })
  })

  describe('fetchProcessDetail', () => {
    it('应该获取进程详情', async () => {
      const mockDetail = { pid: 1234, name: 'nginx', environ: [], fd_count: 10, net_connections: 5, cgroup: '', status_file: {} }
      vi.spyOn(api, 'request').mockResolvedValue(mockDetail as any)

      const store = useProcessStore()
      store.currentAlias = 'test-server'
      const result = await store.fetchProcessDetail(1234)

      expect(result).toEqual(mockDetail)
    })

    it('请求失败时应该返回 null', async () => {
      vi.spyOn(api, 'request').mockRejectedValue(new Error('Not found'))

      const store = useProcessStore()
      store.currentAlias = 'test-server'
      const result = await store.fetchProcessDetail(9999)

      expect(result).toBeNull()
    })

    it('当没有 alias 时应该返回 null', async () => {
      const store = useProcessStore()
      const result = await store.fetchProcessDetail(1234)
      expect(result).toBeNull()
    })
  })
})
