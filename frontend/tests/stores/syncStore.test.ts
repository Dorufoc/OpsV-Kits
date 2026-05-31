/**
 * Sync Store 单元测试
 * 测试同步启动/停止、状态获取、轮询机制和等待完成
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useSyncStore } from '@/stores/syncStore'
import { request } from '@/api'

// 辅助函数：mock request 的所有方法返回相同值
function mockAllRequestMethods(value: any) {
  vi.mocked(request.get).mockResolvedValue(value)
  vi.mocked(request.post).mockResolvedValue(value)
  vi.mocked(request.put).mockResolvedValue(value)
  vi.mocked(request.delete).mockResolvedValue(value)
}

// 辅助函数：mock request 的所有方法为拒绝
function mockAllRequestReject(error: Error) {
  vi.mocked(request.get).mockRejectedValue(error)
  vi.mocked(request.post).mockRejectedValue(error)
  vi.mocked(request.put).mockRejectedValue(error)
  vi.mocked(request.delete).mockRejectedValue(error)
}

// 辅助函数：mock request 的所有方法为自定义实现
function mockAllRequestImplementation(fn: (...args: any[]) => Promise<any>) {
  vi.mocked(request.get).mockImplementation(fn)
  vi.mocked(request.post).mockImplementation(fn)
  vi.mocked(request.put).mockImplementation(fn)
  vi.mocked(request.delete).mockImplementation(fn)
}

describe('Sync Store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    vi.useFakeTimers({ shouldAdvanceTime: true })
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  describe('状态初始化', () => {
    it('应该正确初始化 syncStatus 为 idle', () => {
      const store = useSyncStore()
      expect(store.syncStatus).toBe('idle')
    })

    it('应该正确初始化 currentTaskId 为空字符串', () => {
      const store = useSyncStore()
      expect(store.currentTaskId).toBe('')
    })

    it('应该正确初始化 syncLogs 为空数组', () => {
      const store = useSyncStore()
      expect(store.syncLogs).toEqual([])
    })

    it('应该正确初始化 progress 默认值', () => {
      const store = useSyncStore()
      expect(store.progress.total).toBe(0)
      expect(store.progress.transferred).toBe(0)
      expect(store.progress.current_file).toBe('')
      expect(store.progress.bytes_transferred).toBe(0)
      expect(store.progress.speed).toBe('')
    })
  })

  describe('setLogCallback', () => {
    it('应该设置日志回调函数', () => {
      const store = useSyncStore()
      const callback = vi.fn()
      store.setLogCallback(callback)

      // 通过行为验证回调已设置
      store.startSync({
        local_path: '/local',
        remote_path: '/remote',
        account_alias: 'test',
      }).catch(() => {})
    })
  })

  describe('startSync', () => {
    it('应该启动同步并设置状态为 syncing', async () => {
      mockAllRequestMethods({ sync_id: 'sync-123' })

      const store = useSyncStore()
      await store.startSync({
        local_path: '/local/path',
        remote_path: '/remote/path',
        account_alias: 'test-server',
      })

      expect(store.syncStatus).toBe('syncing')
      expect(store.currentTaskId).toBe('sync-123')
    })

    it('应该清空 syncLogs', async () => {
      const store = useSyncStore()
      store.syncLogs = ['old log 1', 'old log 2']
      mockAllRequestMethods({ sync_id: 'sync-123' })

      await store.startSync({
        local_path: '/local/path',
        remote_path: '/remote/path',
        account_alias: 'test-server',
      })

      expect(store.syncLogs).toEqual([])
    })

    it('应该先设置 scanning 状态', async () => {
      const store = useSyncStore()
      // 在 mock 中检查中间状态
      mockAllRequestImplementation(async () => {
        const s = useSyncStore()
        expect(s.syncStatus).toBe('scanning')
        return { sync_id: 'sync-123' }
      })

      await store.startSync({
        local_path: '/local/path',
        remote_path: '/remote/path',
        account_alias: 'test-server',
      })
    })

    it('失败时应该设置状态为 error', async () => {
      mockAllRequestReject(new Error('Sync start failed'))

      const store = useSyncStore()
      await expect(store.startSync({
        local_path: '/local/path',
        remote_path: '/remote/path',
        account_alias: 'test-server',
      })).rejects.toThrow()

      expect(store.syncStatus).toBe('error')
    })

    it('应该调用正确的 API', async () => {
      mockAllRequestMethods({ sync_id: 'sync-123' })

      const store = useSyncStore()
      await store.startSync({
        local_path: '/local/path',
        remote_path: '/remote/path',
        account_alias: 'test-server',
      })

      expect(request.post).toHaveBeenCalledWith('/sync/start', {
        local_path: '/local/path',
        remote_path: '/remote/path',
        account_alias: 'test-server',
      })
    })
  })

  describe('stopSync', () => {
    it('应该调用停止 API', async () => {
      mockAllRequestMethods({})

      const store = useSyncStore()
      store.currentTaskId = 'sync-123'
      await store.stopSync()

      expect(request.post).toHaveBeenCalledWith('/sync/stop', { sync_id: 'sync-123' })
    })

    it('应该设置 syncStatus 为 idle', async () => {
      mockAllRequestMethods({})

      const store = useSyncStore()
      store.syncStatus = 'syncing'
      store.currentTaskId = 'sync-123'
      await store.stopSync()

      expect(store.syncStatus).toBe('idle')
    })

    it('应该清空 currentTaskId', async () => {
      mockAllRequestMethods({})

      const store = useSyncStore()
      store.currentTaskId = 'sync-123'
      await store.stopSync()

      expect(store.currentTaskId).toBe('')
    })

    it('API 失败时不应该抛出异常', async () => {
      mockAllRequestReject(new Error('Stop failed'))

      const store = useSyncStore()
      store.currentTaskId = 'sync-123'
      await expect(store.stopSync()).resolves.toBeUndefined()
    })

    it('应该停止轮询', async () => {
      mockAllRequestMethods({ sync_id: 'sync-123' })

      const store = useSyncStore()
      store.currentTaskId = 'sync-123'
      await store.startSync({
        local_path: '/local/path',
        remote_path: '/remote/path',
        account_alias: 'test-server',
      })

      await store.stopSync()

      // 轮询应该已停止
      await vi.advanceTimersByTimeAsync(1000)
      // startSync 调用 request.post，startPolling 被 stopSync 停止，所以 request.get 不应被调用
      expect(request.get).not.toHaveBeenCalled()
    })
  })

  describe('getSyncStatus', () => {
    it('应该获取同步状态', async () => {
      const mockStatus = { status: 'syncing', progress: 0.5, message: 'Syncing file.txt' }
      mockAllRequestMethods(mockStatus)

      const store = useSyncStore()
      store.currentTaskId = 'sync-123'
      const result = await store.getSyncStatus()

      expect(result).toEqual(mockStatus)
      expect(store.syncStatus).toBe('syncing')
    })

    it('应该更新 progress', async () => {
      const mockStatus = { status: 'syncing', progress: 0.75, message: 'Syncing images/' }
      mockAllRequestMethods(mockStatus)

      const store = useSyncStore()
      store.currentTaskId = 'sync-123'
      await store.getSyncStatus()

      expect(store.progress.total).toBe(75)
      expect(store.progress.transferred).toBe(75)
      expect(store.progress.current_file).toBe('Syncing images/')
    })

    it('没有 currentTaskId 时应该直接返回', async () => {
      const store = useSyncStore()
      const result = await store.getSyncStatus()
      expect(result).toBeUndefined()
    })

    it('请求失败时应该抛出错误', async () => {
      mockAllRequestReject(new Error('Status fetch failed'))

      const store = useSyncStore()
      store.currentTaskId = 'sync-123'
      await expect(store.getSyncStatus()).rejects.toThrow('获取状态失败')
    })
  })

  describe('startPolling', () => {
    it('轮询应该定期获取状态', async () => {
      const store = useSyncStore()
      store.currentTaskId = 'sync-123'

      const statusResponses = [
        { status: 'syncing', progress: 0.3, phase: 'syncing' },
        { status: 'syncing', progress: 0.6, phase: 'syncing' },
        { status: 'completed', progress: 1.0, message: '同步完成' },
      ]
      let callIndex = 0
      mockAllRequestImplementation(async () => {
        const res = statusResponses[callIndex++] || statusResponses[statusResponses.length - 1]
        return res
      })

      store.startPolling()

      // 第一次轮询
      await vi.advanceTimersByTimeAsync(1000)
      expect(store.syncStatus).toBe('syncing')

      // 第二次轮询
      await vi.advanceTimersByTimeAsync(1000)
      expect(store.progress.total).toBe(60)

      // 第三次轮询 (completed)
      await vi.advanceTimersByTimeAsync(1000)
      expect(store.syncStatus).toBe('completed')
      expect(store.progress.total).toBe(100)

      store.stopPolling()
    })

    it('phase 为 scanning 时应该设置 scanning 状态', async () => {
      const store = useSyncStore()
      store.currentTaskId = 'sync-123'

      mockAllRequestMethods({ status: 'syncing', phase: 'scanning' })
      store.startPolling()

      await vi.advanceTimersByTimeAsync(1000)

      expect(store.syncStatus).toBe('scanning')

      store.stopPolling()
    })

    it('状态为 failed 时应该停止轮询', async () => {
      const store = useSyncStore()
      store.currentTaskId = 'sync-123'

      mockAllRequestMethods({ status: 'failed', error: 'Connection lost' })
      store.startPolling()

      await vi.advanceTimersByTimeAsync(1000)

      expect(store.syncStatus).toBe('failed')
      expect(store.progress.current_file).toBe('Connection lost')

      store.stopPolling()
    })

    it('状态为 stopped 时应该停止轮询', async () => {
      const store = useSyncStore()
      store.currentTaskId = 'sync-123'

      mockAllRequestMethods({ status: 'stopped' })
      store.startPolling()

      await vi.advanceTimersByTimeAsync(1000)

      // 轮询应该已停止
      expect(request.get).toHaveBeenCalledTimes(1)

      store.stopPolling()
    })

    it('轮询失败且状态不是 idle 时应该设置 error 并停止', async () => {
      const store = useSyncStore()
      store.currentTaskId = 'sync-123'
      store.syncStatus = 'syncing'

      mockAllRequestReject(new Error('Network error'))
      store.startPolling()

      await vi.advanceTimersByTimeAsync(1000)

      expect(store.syncStatus).toBe('error')

      store.stopPolling()
    })

    it('轮询失败但状态是 idle 时不应该改变状态', async () => {
      const store = useSyncStore()
      store.currentTaskId = 'sync-123'
      store.syncStatus = 'idle'

      mockAllRequestReject(new Error('Network error'))
      store.startPolling()

      await vi.advanceTimersByTimeAsync(1000)

      expect(store.syncStatus).toBe('idle')

      store.stopPolling()
    })

    it('没有 currentTaskId 时应该不请求', async () => {
      const store = useSyncStore()
      store.currentTaskId = ''

      store.startPolling()

      await vi.advanceTimersByTimeAsync(1000)

      expect(request.get).not.toHaveBeenCalled()

      store.stopPolling()
    })

    it('新增消息应该使用绿色标记', async () => {
      const callback = vi.fn()
      const store = useSyncStore()
      store.currentTaskId = 'sync-123'
      store.setLogCallback(callback)

      mockAllRequestMethods({ status: 'syncing', progress: 0.1, message: '新增: file.txt' })
      store.startPolling()

      await vi.advanceTimersByTimeAsync(1000)

      expect(callback).toHaveBeenCalledWith(expect.stringContaining('\x1b[32m'))

      store.stopPolling()
    })

    it('修改消息应该使用黄色标记', async () => {
      const callback = vi.fn()
      const store = useSyncStore()
      store.currentTaskId = 'sync-123'
      store.setLogCallback(callback)

      mockAllRequestMethods({ status: 'syncing', progress: 0.5, message: '修改: config.js' })
      store.startPolling()

      await vi.advanceTimersByTimeAsync(1000)

      expect(callback).toHaveBeenCalledWith(expect.stringContaining('\x1b[33m'))

      store.stopPolling()
    })

    it('删除消息应该使用红色标记', async () => {
      const callback = vi.fn()
      const store = useSyncStore()
      store.currentTaskId = 'sync-123'
      store.setLogCallback(callback)

      mockAllRequestMethods({ status: 'syncing', progress: 0.8, message: '删除: old.txt' })
      store.startPolling()

      await vi.advanceTimersByTimeAsync(1000)

      expect(callback).toHaveBeenCalledWith(expect.stringContaining('\x1b[31m'))

      store.stopPolling()
    })
  })

  describe('stopPolling', () => {
    it('应该停止轮询', async () => {
      const store = useSyncStore()
      store.currentTaskId = 'sync-123'

      mockAllRequestMethods({ status: 'syncing', progress: 0.5 })
      store.startPolling()
      store.stopPolling()

      await vi.advanceTimersByTimeAsync(1000)
      expect(request.get).not.toHaveBeenCalled()
    })
  })

  describe('waitForCompletion', () => {
    it('syncStatus 为 completed 时应该返回 completed', async () => {
      const store = useSyncStore()
      store.syncStatus = 'completed'

      const result = await store.waitForCompletion()
      expect(result).toBe('completed')
    })

    it('syncStatus 为 failed 时应该返回 failed', async () => {
      const store = useSyncStore()
      store.syncStatus = 'failed'

      const result = await store.waitForCompletion()
      expect(result).toBe('failed')
    })

    it('syncStatus 为 error 时应该返回 failed', async () => {
      const store = useSyncStore()
      store.syncStatus = 'error'

      const result = await store.waitForCompletion()
      expect(result).toBe('failed')
    })

    it('syncStatus 为 stopped 时应该返回 stopped', async () => {
      const store = useSyncStore()
      store.syncStatus = 'stopped'

      const result = await store.waitForCompletion()
      expect(result).toBe('stopped')
    })
  })

  describe('resetStatus', () => {
    it('应该重置所有状态', () => {
      const store = useSyncStore()
      store.syncStatus = 'syncing'
      store.currentTaskId = 'sync-123'
      store.progress = {
        total: 50,
        transferred: 25,
        current_file: 'file.txt',
        bytes_transferred: 1024,
        speed: '1MB/s',
      }
      store.syncLogs = ['log1']

      store.resetStatus()

      expect(store.syncStatus).toBe('idle')
      expect(store.currentTaskId).toBe('')
      expect(store.progress.total).toBe(0)
      expect(store.progress.transferred).toBe(0)
      expect(store.progress.current_file).toBe('')
      expect(store.syncLogs).toEqual([])
    })

    it('应该停止轮询', async () => {
      const store = useSyncStore()
      store.currentTaskId = 'sync-123'

      mockAllRequestMethods({ status: 'syncing', progress: 0.5 })
      store.startPolling()
      store.resetStatus()

      await vi.advanceTimersByTimeAsync(1000)
      expect(request.get).not.toHaveBeenCalled()
    })
  })
})
