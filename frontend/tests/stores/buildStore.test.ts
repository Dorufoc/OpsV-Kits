/**
 * Build Store 单元测试
 * 测试构建生命周期：开始、状态轮询、取消、任务完成等待
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useBuildStore } from '@/stores/buildStore'
import * as api from '@/api'

describe('Build Store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  describe('状态初始化', () => {
    it('应该正确初始化 buildStatus 为 idle', () => {
      const store = useBuildStore()
      expect(store.buildStatus).toBe('idle')
    })

    it('应该正确初始化 runStatus 为 idle', () => {
      const store = useBuildStore()
      expect(store.runStatus).toBe('idle')
    })

    it('应该正确初始化 currentTaskId 为空字符串', () => {
      const store = useBuildStore()
      expect(store.currentTaskId).toBe('')
    })

    it('应该正确初始化 rawLog 为空字符串', () => {
      const store = useBuildStore()
      expect(store.rawLog).toBe('')
    })
  })

  describe('setLogCallback', () => {
    it('应该设置日志回调函数', () => {
      const store = useBuildStore()
      const callback = vi.fn()
      store.setLogCallback(callback)

      expect((store as any).logCallback).toBe(callback)
    })
  })

  describe('pipeToTerminal', () => {
    it('有回调时应该调用日志回调', () => {
      const store = useBuildStore()
      const callback = vi.fn()
      store.setLogCallback(callback)

      store.pipeToTerminal('test log')

      expect(callback).toHaveBeenCalledWith('test log')
    })

    it('没有回调时不应该报错', () => {
      const store = useBuildStore()
      expect(() => store.pipeToTerminal('test log')).not.toThrow()
    })
  })

  describe('startBuild', () => {
    it('应该设置 buildStatus 为 building', async () => {
      vi.spyOn(api, 'request').mockResolvedValue({ task_id: 'task-123' } as any)

      const store = useBuildStore()
      await store.startBuild({ remote_path: '/path', account_alias: 'test' })

      expect(store.buildStatus).toBe('building')
    })

    it('应该清空 rawLog', async () => {
      const store = useBuildStore()
      store.rawLog = 'old logs'
      vi.spyOn(api, 'request').mockResolvedValue({ task_id: 'task-123' } as any)

      await store.startBuild({ remote_path: '/path', account_alias: 'test' })

      expect(store.rawLog).toBe('')
    })

    it('应该设置 currentTaskId', async () => {
      vi.spyOn(api, 'request').mockResolvedValue({ task_id: 'task-123' } as any)

      const store = useBuildStore()
      await store.startBuild({ remote_path: '/path', account_alias: 'test' })

      expect(store.currentTaskId).toBe('task-123')
    })

    it('应该支持 taskId 字段', async () => {
      vi.spyOn(api, 'request').mockResolvedValue({ taskId: 'task-456' } as any)

      const store = useBuildStore()
      await store.startBuild({ remote_path: '/path', account_alias: 'test' })

      expect(store.currentTaskId).toBe('task-456')
    })

    it('失败时应该设置 buildStatus 为 failed', async () => {
      vi.spyOn(api, 'request').mockRejectedValue(new Error('Build start failed'))

      const store = useBuildStore()
      await expect(store.startBuild({ remote_path: '/path', account_alias: 'test' })).rejects.toThrow()

      expect(store.buildStatus).toBe('failed')
    })

    it('应该停止之前的轮询', async () => {
      vi.spyOn(api, 'request').mockResolvedValue({ task_id: 'task-123' } as any)

      const store = useBuildStore()
      store.currentTaskId = 'old-task'
      await store.startBuild({ remote_path: '/path', account_alias: 'test' })

      // 验证旧 task ID 被替换
      expect(store.currentTaskId).toBe('task-123')
    })
  })

  describe('startTest', () => {
    it('应该设置 buildStatus 为 building', async () => {
      vi.spyOn(api, 'request').mockResolvedValue({ task_id: 'task-test' } as any)

      const store = useBuildStore()
      await store.startTest({ remote_path: '/path', account_alias: 'test' })

      expect(store.buildStatus).toBe('building')
    })

    it('应该调用 /build/test 接口', async () => {
      vi.spyOn(api, 'request').mockResolvedValue({ task_id: 'task-test' } as any)

      const store = useBuildStore()
      await store.startTest({ remote_path: '/path', account_alias: 'test' })

      expect(api.request.post).toHaveBeenCalledWith('/build/test', expect.objectContaining({
        project_path: '/path',
        account_alias: 'test',
      }))
    })
  })

  describe('startRun', () => {
    it('应该设置 runStatus 为 running', async () => {
      vi.spyOn(api, 'request').mockResolvedValue({ task_id: 'task-run' } as any)

      const store = useBuildStore()
      await store.startRun({ remote_path: '/path', account_alias: 'test' })

      expect(store.runStatus).toBe('running')
    })

    it('应该调用 /build/run 接口', async () => {
      vi.spyOn(api, 'request').mockResolvedValue({ task_id: 'task-run' } as any)

      const store = useBuildStore()
      await store.startRun({ remote_path: '/path', account_alias: 'test' })

      expect(api.request.post).toHaveBeenCalledWith('/build/run', expect.objectContaining({
        project_path: '/path',
        account_alias: 'test',
      }))
    })

    it('失败时应该设置 runStatus 为 stopped', async () => {
      vi.spyOn(api, 'request').mockRejectedValue(new Error('Run start failed'))

      const store = useBuildStore()
      await expect(store.startRun({ remote_path: '/path', account_alias: 'test' })).rejects.toThrow()

      expect(store.runStatus).toBe('stopped')
    })
  })

  describe('stopTask', () => {
    it('应该调用停止 API', async () => {
      vi.spyOn(api, 'request').mockResolvedValue({} as any)

      const store = useBuildStore()
      store.currentTaskId = 'task-123'
      await store.stopTask()

      expect(api.request.post).toHaveBeenCalledWith('/build/stop', { task_id: 'task-123' })
    })

    it('停止编译任务时应该设置 buildStatus 为 idle', async () => {
      vi.spyOn(api, 'request').mockResolvedValue({} as any)

      const store = useBuildStore()
      store.buildStatus = 'building'
      store.currentTaskId = 'task-123'
      await store.stopTask()

      expect(store.buildStatus).toBe('idle')
    })

    it('停止运行任务时应该设置 runStatus 为 stopped', async () => {
      vi.spyOn(api, 'request').mockResolvedValue({} as any)

      const store = useBuildStore()
      store.runStatus = 'running'
      store.currentTaskId = 'task-123'
      await store.stopTask()

      expect(store.runStatus).toBe('stopped')
    })

    it('应该清空 currentTaskId', async () => {
      vi.spyOn(api, 'request').mockResolvedValue({} as any)

      const store = useBuildStore()
      store.currentTaskId = 'task-123'
      await store.stopTask()

      expect(store.currentTaskId).toBe('')
    })

    it('API 失败时不应该抛出异常', async () => {
      vi.spyOn(api, 'request').mockRejectedValue(new Error('Stop failed'))

      const store = useBuildStore()
      store.currentTaskId = 'task-123'
      await expect(store.stopTask()).resolves.toBeUndefined()
    })
  })

  describe('startPolling', () => {
    it('轮询应该定期获取状态', async () => {
      const store = useBuildStore()
      store.currentTaskId = 'task-123'

      const statusResponses = [
        { status: 'running', log: 'log1' },
        { status: 'running', log: 'log1log2' },
        { status: 'completed', log: 'log1log2log3' },
      ]
      let callIndex = 0
      vi.spyOn(api, 'request').mockImplementation(async () => {
        const res = statusResponses[callIndex++] || statusResponses[statusResponses.length - 1]
        return res
      })

      ;(store as any).startPolling()

      // 触发第一次轮询
      vi.advanceTimersByTime(500)
      expect(api.request.get).toHaveBeenCalledWith('/build/status/task-123')
      expect(store.buildStatus).toBe('building')

      // 触发第二次轮询
      vi.advanceTimersByTime(500)

      // 触发第三次轮询 (completed 应该停止)
      vi.advanceTimersByTime(500)
      expect(store.buildStatus).toBe('success')

      ;(store as any).stopPolling()
    })

    it('状态为 failed 时应该停止轮询并设置 failed', async () => {
      const store = useBuildStore()
      store.currentTaskId = 'task-123'

      vi.spyOn(api, 'request').mockResolvedValue({ status: 'failed', log: '' })
      ;(store as any).startPolling()

      vi.advanceTimersByTime(500)

      expect(store.buildStatus).toBe('failed')

      ;(store as any).stopPolling()
    })

    it('状态为 stopped 时应该停止轮询', async () => {
      const store = useBuildStore()
      store.currentTaskId = 'task-123'

      vi.spyOn(api, 'request').mockResolvedValue({ status: 'stopped', log: '' })
      ;(store as any).startPolling()

      vi.advanceTimersByTime(500)

      expect(store.buildStatus).toBe('idle')

      ;(store as any).stopPolling()
    })

    it('运行任务 completed 时 runStatus 应该保持 running', async () => {
      const store = useBuildStore()
      store.currentTaskId = 'task-123'
      ;(store as any).logCallback = null

      vi.spyOn(api, 'request').mockResolvedValue({ status: 'completed', log: '', action: 'run' })
      ;(store as any).startPolling()

      vi.advanceTimersByTime(500)

      expect(store.runStatus).toBe('running')

      ;(store as any).stopPolling()
    })

    it('轮询失败时应该停止轮询并设置 failed', async () => {
      const store = useBuildStore()
      store.currentTaskId = 'task-123'

      vi.spyOn(api, 'request').mockRejectedValue(new Error('Poll error'))
      ;(store as any).startPolling()

      vi.advanceTimersByTime(500)

      expect(store.buildStatus).toBe('failed')

      ;(store as any).stopPolling()
    })

    it('应该更新 rawLog 并调用 pipeToTerminal', async () => {
      const callback = vi.fn()
      const store = useBuildStore()
      store.currentTaskId = 'task-123'
      store.setLogCallback(callback)

      vi.spyOn(api, 'request').mockResolvedValue({ status: 'running', log: 'new log chunk' })
      ;(store as any).startPolling()

      vi.advanceTimersByTime(500)

      expect(store.rawLog).toBe('new log chunk')
      expect(callback).toHaveBeenCalledWith('new log chunk')

      ;(store as any).stopPolling()
    })

    it('没有 currentTaskId 时应该不请求', async () => {
      const store = useBuildStore()
      store.currentTaskId = ''

      ;(store as any).startPolling()

      vi.advanceTimersByTime(500)

      expect(api.request.get).not.toHaveBeenCalled()

      ;(store as any).stopPolling()
    })
  })

  describe('stopPolling', () => {
    it('应该停止轮询', () => {
      const store = useBuildStore()
      ;(store as any).startPolling()
      ;(store as any).stopPolling()

      vi.advanceTimersByTime(500)
      expect(api.request.get).not.toHaveBeenCalled()
    })
  })

  describe('waitForCompletion', () => {
    it('buildStatus 为 success 时应该返回 success', async () => {
      const store = useBuildStore()
      store.buildStatus = 'success'

      const result = await store.waitForCompletion()
      expect(result).toBe('success')
    })

    it('buildStatus 为 failed 时应该返回 failed', async () => {
      const store = useBuildStore()
      store.buildStatus = 'failed'

      const result = await store.waitForCompletion()
      expect(result).toBe('failed')
    })

    it('runStatus 为 stopped 时应该返回 stopped', async () => {
      const store = useBuildStore()
      store.runStatus = 'stopped'

      const result = await store.waitForCompletion()
      expect(result).toBe('stopped')
    })

    it('应该等待直到状态变化', async () => {
      const store = useBuildStore()
      store.buildStatus = 'building'

      const completionPromise = store.waitForCompletion()

      // 延迟更新状态
      setTimeout(() => {
        store.buildStatus = 'success'
      }, 100)

      vi.advanceTimersByTime(200)

      const result = await completionPromise
      expect(result).toBe('success')
    })
  })

  describe('resetStatus', () => {
    it('应该重置所有状态', () => {
      const store = useBuildStore()
      store.buildStatus = 'building'
      store.runStatus = 'running'
      store.rawLog = 'some logs'
      store.currentTaskId = 'task-123'

      store.resetStatus()

      expect(store.buildStatus).toBe('idle')
      expect(store.runStatus).toBe('idle')
      expect(store.rawLog).toBe('')
      expect(store.currentTaskId).toBe('')
    })

    it('应该停止轮询', () => {
      const store = useBuildStore()
      ;(store as any).startPolling()
      store.resetStatus()

      vi.advanceTimersByTime(500)
      expect(api.request.get).not.toHaveBeenCalled()
    })
  })
})
