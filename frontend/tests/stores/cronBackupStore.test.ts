import { describe, it, expect, vi, beforeEach } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useCronBackupStore } from '@/stores/cronBackupStore'
import * as api from '@/api'

describe('CronBackup Store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  describe('状态初始化', () => {
    it('应该正确初始化 currentAlias 为空字符串', () => {
      const store = useCronBackupStore()
      expect(store.currentAlias).toBe('')
    })

    it('应该正确初始化 cronJobs 为空数组', () => {
      const store = useCronBackupStore()
      expect(store.cronJobs).toEqual([])
    })

    it('应该正确初始化 backupPolicies 为空数组', () => {
      const store = useCronBackupStore()
      expect(store.backupPolicies).toEqual([])
    })

    it('应该正确初始化 backupHistory 为空数组', () => {
      const store = useCronBackupStore()
      expect(store.backupHistory).toEqual([])
    })

    it('应该正确初始化 logPolicies 为空数组', () => {
      const store = useCronBackupStore()
      expect(store.logPolicies).toEqual([])
    })

    it('应该正确初始化 executionLogs 为空数组', () => {
      const store = useCronBackupStore()
      expect(store.executionLogs).toEqual([])
    })

    it('应该正确初始化 diskAlert 为 null', () => {
      const store = useCronBackupStore()
      expect(store.diskAlert).toBeNull()
    })

    it('应该正确初始化 loading 为 false', () => {
      const store = useCronBackupStore()
      expect(store.loading).toBe(false)
    })

    it('应该正确初始化 runningBackup 为 null', () => {
      const store = useCronBackupStore()
      expect(store.runningBackup).toBeNull()
    })

    it('应该正确初始化 runningLogCleanup 为 null', () => {
      const store = useCronBackupStore()
      expect(store.runningLogCleanup).toBeNull()
    })
  })

  describe('setAccountAlias', () => {
    it('应该更新 currentAlias', () => {
      const store = useCronBackupStore()
      store.setAccountAlias('test-server')
      expect(store.currentAlias).toBe('test-server')
    })
  })

  describe('fetchCronJobs', () => {
    it('应该获取定时任务列表', async () => {
      const mockJobs = [{ id: 'j1', name: 'backup', cron_expression: '0 2 * * *' }]
      vi.mocked(api.cronBackupApi.listCronJobs).mockResolvedValue({ items: mockJobs } as any)

      const store = useCronBackupStore()
      store.setAccountAlias('test-server')
      const result = await store.fetchCronJobs()

      expect(store.cronJobs).toEqual(mockJobs)
      expect(result).toEqual({ items: mockJobs })
    })

    it('请求期间 loading 应该为 true', async () => {
      vi.mocked(api.cronBackupApi.listCronJobs).mockImplementation(async () => {
        const store = useCronBackupStore()
        expect(store.loading).toBe(true)
        return { items: [] }
      })

      const store = useCronBackupStore()
      store.setAccountAlias('test-server')
      await store.fetchCronJobs()
      expect(store.loading).toBe(false)
    })

    it('请求失败时 loading 应该恢复为 false', async () => {
      vi.mocked(api.cronBackupApi.listCronJobs).mockRejectedValue(new Error('Network error'))

      const store = useCronBackupStore()
      store.setAccountAlias('test-server')
      await expect(store.fetchCronJobs()).rejects.toThrow()
      expect(store.loading).toBe(false)
    })

    it('当没有 alias 时应该直接返回', async () => {
      const store = useCronBackupStore()
      const result = await store.fetchCronJobs()
      expect(result).toBeUndefined()
    })

    it('应该支持传入 alias 参数', async () => {
      vi.mocked(api.cronBackupApi.listCronJobs).mockResolvedValue({ items: [] } as any)

      const store = useCronBackupStore()
      await store.fetchCronJobs('direct-alias')

      expect(api.cronBackupApi.listCronJobs).toHaveBeenCalledWith('direct-alias')
    })

    it('API 返回无 items 时应该设为空数组', async () => {
      vi.mocked(api.cronBackupApi.listCronJobs).mockResolvedValue({} as any)

      const store = useCronBackupStore()
      store.setAccountAlias('test-server')
      await store.fetchCronJobs()

      expect(store.cronJobs).toEqual([])
    })
  })

  describe('createCronJob', () => {
    it('应该创建定时任务并刷新列表', async () => {
      const newData = { name: 'new-job', cron_expression: '* * * * *', task_type: 'shell' as const, command: 'ls', status: 'enabled' as const, account_alias: 'test-server' }
      vi.mocked(api.cronBackupApi.createCronJob).mockResolvedValue({ id: 'j2', ...newData } as any)
      vi.mocked(api.cronBackupApi.listCronJobs).mockResolvedValue({ items: [] } as any)

      const store = useCronBackupStore()
      store.setAccountAlias('test-server')
      const result = await store.createCronJob(newData)

      expect(api.cronBackupApi.createCronJob).toHaveBeenCalledWith('test-server', newData)
      expect(api.cronBackupApi.listCronJobs).toHaveBeenCalledWith('test-server')
    })

    it('当没有 alias 时应该直接返回', async () => {
      const store = useCronBackupStore()
      const result = await store.createCronJob({})
      expect(result).toBeUndefined()
    })
  })

  describe('updateCronJob', () => {
    it('应该更新定时任务并刷新列表', async () => {
      vi.mocked(api.cronBackupApi.updateCronJob).mockResolvedValue({} as any)
      vi.mocked(api.cronBackupApi.listCronJobs).mockResolvedValue({ items: [] } as any)

      const store = useCronBackupStore()
      store.setAccountAlias('test-server')
      const result = await store.updateCronJob('j1', { name: 'updated' })

      expect(api.cronBackupApi.updateCronJob).toHaveBeenCalledWith('j1', 'test-server', { name: 'updated' })
      expect(api.cronBackupApi.listCronJobs).toHaveBeenCalledWith('test-server')
    })
  })

  describe('deleteCronJob', () => {
    it('应该删除定时任务并刷新列表', async () => {
      vi.mocked(api.cronBackupApi.deleteCronJob).mockResolvedValue({} as any)
      vi.mocked(api.cronBackupApi.listCronJobs).mockResolvedValue({ items: [] } as any)

      const store = useCronBackupStore()
      store.setAccountAlias('test-server')
      await store.deleteCronJob('j1')

      expect(api.cronBackupApi.deleteCronJob).toHaveBeenCalledWith('j1', 'test-server')
      expect(api.cronBackupApi.listCronJobs).toHaveBeenCalledWith('test-server')
    })
  })

  describe('fetchExecutionLogs', () => {
    it('应该获取执行日志', async () => {
      const mockLogs = [{ id: 'el1', task_id: 'j1', status: 'success' }]
      vi.mocked(api.cronBackupApi.getCronJobLogs).mockResolvedValue({ items: mockLogs } as any)

      const store = useCronBackupStore()
      store.setAccountAlias('test-server')
      const result = await store.fetchExecutionLogs('j1')

      expect(store.executionLogs).toEqual(mockLogs)
      expect(api.cronBackupApi.getCronJobLogs).toHaveBeenCalledWith('j1', 'test-server', undefined)
    })

    it('应该支持 limit 参数', async () => {
      vi.mocked(api.cronBackupApi.getCronJobLogs).mockResolvedValue({ items: [] } as any)

      const store = useCronBackupStore()
      store.setAccountAlias('test-server')
      await store.fetchExecutionLogs('j1', undefined, 10)

      expect(api.cronBackupApi.getCronJobLogs).toHaveBeenCalledWith('j1', 'test-server', 10)
    })
  })

  describe('fetchBackupPolicies', () => {
    it('应该获取备份策略列表', async () => {
      const mockPolicies = [{ id: 'p1', name: 'daily-backup', backup_type: 'website' }]
      vi.mocked(api.cronBackupApi.listBackupPolicies).mockResolvedValue({ items: mockPolicies } as any)

      const store = useCronBackupStore()
      store.setAccountAlias('test-server')
      const result = await store.fetchBackupPolicies()

      expect(store.backupPolicies).toEqual(mockPolicies)
    })

    it('请求期间 loading 应该为 true', async () => {
      vi.mocked(api.cronBackupApi.listBackupPolicies).mockImplementation(async () => {
        const store = useCronBackupStore()
        expect(store.loading).toBe(true)
        return { items: [] }
      })

      const store = useCronBackupStore()
      store.setAccountAlias('test-server')
      await store.fetchBackupPolicies()
      expect(store.loading).toBe(false)
    })
  })

  describe('createBackupPolicy', () => {
    it('应该创建备份策略并刷新列表', async () => {
      vi.mocked(api.cronBackupApi.createBackupPolicy).mockResolvedValue({} as any)
      vi.mocked(api.cronBackupApi.listBackupPolicies).mockResolvedValue({ items: [] } as any)

      const store = useCronBackupStore()
      store.setAccountAlias('test-server')
      await store.createBackupPolicy({ name: 'new-policy' })

      expect(api.cronBackupApi.createBackupPolicy).toHaveBeenCalledWith('test-server', { name: 'new-policy' })
      expect(api.cronBackupApi.listBackupPolicies).toHaveBeenCalledWith('test-server')
    })
  })

  describe('updateBackupPolicy', () => {
    it('应该更新备份策略并刷新列表', async () => {
      vi.mocked(api.cronBackupApi.updateBackupPolicy).mockResolvedValue({} as any)
      vi.mocked(api.cronBackupApi.listBackupPolicies).mockResolvedValue({ items: [] } as any)

      const store = useCronBackupStore()
      store.setAccountAlias('test-server')
      await store.updateBackupPolicy('p1', { name: 'updated' })

      expect(api.cronBackupApi.updateBackupPolicy).toHaveBeenCalledWith('p1', 'test-server', { name: 'updated' })
    })
  })

  describe('deleteBackupPolicy', () => {
    it('应该删除备份策略并刷新列表', async () => {
      vi.mocked(api.cronBackupApi.deleteBackupPolicy).mockResolvedValue({} as any)
      vi.mocked(api.cronBackupApi.listBackupPolicies).mockResolvedValue({ items: [] } as any)

      const store = useCronBackupStore()
      store.setAccountAlias('test-server')
      await store.deleteBackupPolicy('p1')

      expect(api.cronBackupApi.deleteBackupPolicy).toHaveBeenCalledWith('p1', 'test-server')
    })
  })

  describe('runBackupNow', () => {
    it('应该立即执行备份', async () => {
      vi.mocked(api.cronBackupApi.runBackupNow).mockResolvedValue({ success: true } as any)
      vi.mocked(api.cronBackupApi.listBackupHistory).mockResolvedValue({ items: [] } as any)
      vi.mocked(api.cronBackupApi.listBackupPolicies).mockResolvedValue({ items: [] } as any)

      const store = useCronBackupStore()
      store.setAccountAlias('test-server')
      const result = await store.runBackupNow('p1')

      expect(store.runningBackup).toBeNull()
      expect(api.cronBackupApi.runBackupNow).toHaveBeenCalledWith('p1', 'test-server')
    })

    it('执行期间 runningBackup 应该为当前 policyId', async () => {
      vi.mocked(api.cronBackupApi.runBackupNow).mockImplementation(async () => {
        const store = useCronBackupStore()
        expect(store.runningBackup).toBe('p1')
        return { success: true }
      })
      vi.mocked(api.cronBackupApi.listBackupHistory).mockResolvedValue({ items: [] } as any)
      vi.mocked(api.cronBackupApi.listBackupPolicies).mockResolvedValue({ items: [] } as any)

      const store = useCronBackupStore()
      store.setAccountAlias('test-server')
      await store.runBackupNow('p1')

      expect(store.runningBackup).toBeNull()
    })

    it('执行失败时 runningBackup 应该恢复为 null', async () => {
      vi.mocked(api.cronBackupApi.runBackupNow).mockRejectedValue(new Error('Backup failed'))

      const store = useCronBackupStore()
      store.setAccountAlias('test-server')
      await expect(store.runBackupNow('p1')).rejects.toThrow()
      expect(store.runningBackup).toBeNull()
    })
  })

  describe('fetchBackupHistory', () => {
    it('应该获取备份历史', async () => {
      const mockHistory = [{ id: 'h1', policy_id: 'p1', status: 'success' }]
      vi.mocked(api.cronBackupApi.listBackupHistory).mockResolvedValue({ items: mockHistory } as any)

      const store = useCronBackupStore()
      store.setAccountAlias('test-server')
      const result = await store.fetchBackupHistory()

      expect(store.backupHistory).toEqual(mockHistory)
    })
  })

  describe('fetchLogPolicies', () => {
    it('应该获取日志策略列表', async () => {
      const mockPolicies = [{ id: 'lp1', name: 'log-cleanup', log_path_pattern: '/var/log/*.log' }]
      vi.mocked(api.cronBackupApi.listLogPolicies).mockResolvedValue({ items: mockPolicies } as any)

      const store = useCronBackupStore()
      store.setAccountAlias('test-server')
      await store.fetchLogPolicies()

      expect(store.logPolicies).toEqual(mockPolicies)
    })

    it('请求期间 loading 应该为 true', async () => {
      vi.mocked(api.cronBackupApi.listLogPolicies).mockImplementation(async () => {
        const store = useCronBackupStore()
        expect(store.loading).toBe(true)
        return { items: [] }
      })

      const store = useCronBackupStore()
      store.setAccountAlias('test-server')
      await store.fetchLogPolicies()
      expect(store.loading).toBe(false)
    })
  })

  describe('createLogPolicy', () => {
    it('应该创建日志策略并刷新列表', async () => {
      vi.mocked(api.cronBackupApi.createLogPolicy).mockResolvedValue({} as any)
      vi.mocked(api.cronBackupApi.listLogPolicies).mockResolvedValue({ items: [] } as any)

      const store = useCronBackupStore()
      store.setAccountAlias('test-server')
      await store.createLogPolicy({ name: 'new-policy' })

      expect(api.cronBackupApi.createLogPolicy).toHaveBeenCalledWith('test-server', { name: 'new-policy' })
    })
  })

  describe('updateLogPolicy', () => {
    it('应该更新日志策略并刷新列表', async () => {
      vi.mocked(api.cronBackupApi.updateLogPolicy).mockResolvedValue({} as any)
      vi.mocked(api.cronBackupApi.listLogPolicies).mockResolvedValue({ items: [] } as any)

      const store = useCronBackupStore()
      store.setAccountAlias('test-server')
      await store.updateLogPolicy('lp1', { name: 'updated' })

      expect(api.cronBackupApi.updateLogPolicy).toHaveBeenCalledWith('lp1', 'test-server', { name: 'updated' })
    })
  })

  describe('deleteLogPolicy', () => {
    it('应该删除日志策略并刷新列表', async () => {
      vi.mocked(api.cronBackupApi.deleteLogPolicy).mockResolvedValue({} as any)
      vi.mocked(api.cronBackupApi.listLogPolicies).mockResolvedValue({ items: [] } as any)

      const store = useCronBackupStore()
      store.setAccountAlias('test-server')
      await store.deleteLogPolicy('lp1')

      expect(api.cronBackupApi.deleteLogPolicy).toHaveBeenCalledWith('lp1', 'test-server')
    })
  })

  describe('previewLogCleanup', () => {
    it('应该预览日志清理结果', async () => {
      const mockPreview = [{ path: '/var/log/test.log', size: 1024 }]
      vi.mocked(api.cronBackupApi.previewLogCleanup).mockResolvedValue({ items: mockPreview } as any)

      const store = useCronBackupStore()
      store.setAccountAlias('test-server')
      const result = await store.previewLogCleanup('lp1')

      expect(api.cronBackupApi.previewLogCleanup).toHaveBeenCalledWith('lp1', 'test-server')
    })
  })

  describe('runLogCleanupNow', () => {
    it('应该立即执行日志清理', async () => {
      vi.mocked(api.cronBackupApi.runLogCleanupNow).mockResolvedValue({ success: true } as any)
      vi.mocked(api.cronBackupApi.listLogPolicies).mockResolvedValue({ items: [] } as any)

      const store = useCronBackupStore()
      store.setAccountAlias('test-server')
      await store.runLogCleanupNow('lp1')

      expect(store.runningLogCleanup).toBeNull()
      expect(api.cronBackupApi.runLogCleanupNow).toHaveBeenCalledWith('lp1', 'test-server')
    })

    it('执行期间 runningLogCleanup 应该为当前 policyId', async () => {
      vi.mocked(api.cronBackupApi.runLogCleanupNow).mockImplementation(async () => {
        const store = useCronBackupStore()
        expect(store.runningLogCleanup).toBe('lp1')
        return { success: true }
      })
      vi.mocked(api.cronBackupApi.listLogPolicies).mockResolvedValue({ items: [] } as any)

      const store = useCronBackupStore()
      store.setAccountAlias('test-server')
      await store.runLogCleanupNow('lp1')

      expect(store.runningLogCleanup).toBeNull()
    })

    it('执行失败时 runningLogCleanup 应该恢复为 null', async () => {
      vi.mocked(api.cronBackupApi.runLogCleanupNow).mockRejectedValue(new Error('Cleanup failed'))

      const store = useCronBackupStore()
      store.setAccountAlias('test-server')
      await expect(store.runLogCleanupNow('lp1')).rejects.toThrow()
      expect(store.runningLogCleanup).toBeNull()
    })
  })

  describe('fetchDiskAlert', () => {
    it('应该获取磁盘告警信息', async () => {
      const mockAlert = { has_alert: true, alerts: [], disk_usage: [], log_sizes: [] }
      vi.mocked(api.cronBackupApi.getDiskAlert).mockResolvedValue(mockAlert as any)

      const store = useCronBackupStore()
      store.setAccountAlias('test-server')
      const result = await store.fetchDiskAlert()

      expect(store.diskAlert).toEqual(mockAlert)
      expect(result).toEqual(mockAlert)
    })

    it('当没有 alias 时应该直接返回', async () => {
      const store = useCronBackupStore()
      const result = await store.fetchDiskAlert()
      expect(result).toBeUndefined()
    })
  })
})
