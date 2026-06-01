import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useBuildStore } from '@/stores/buildStore'
import { request } from '@/api'

vi.mock('@/api')

function mockRequestResolved(value: any) {
  vi.mocked(request.get).mockResolvedValue(value)
  vi.mocked(request.post).mockResolvedValue(value)
  vi.mocked(request.put).mockResolvedValue(value)
  vi.mocked(request.delete).mockResolvedValue(value)
}

function mockRequestRejected(error: Error) {
  vi.mocked(request.get).mockRejectedValue(error)
  vi.mocked(request.post).mockRejectedValue(error)
  vi.mocked(request.put).mockRejectedValue(error)
  vi.mocked(request.delete).mockRejectedValue(error)
}

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
      expect(() => store.setLogCallback(callback)).not.toThrow()
    })
  })

  describe('startBuild', () => {
    it('应该设置 buildStatus 为 building', async () => {
      mockRequestResolved({ task_id: 'task-123' } as any)

      const store = useBuildStore()
      await store.startBuild({ remote_path: '/path', account_alias: 'test' })

      expect(store.buildStatus).toBe('building')
    })

    it('应该清空 rawLog', async () => {
      const store = useBuildStore()
      store.rawLog = 'old logs'
      mockRequestResolved({ task_id: 'task-123' } as any)

      await store.startBuild({ remote_path: '/path', account_alias: 'test' })

      expect(store.rawLog).toBe('')
    })

    it('应该设置 currentTaskId', async () => {
      mockRequestResolved({ task_id: 'task-123' } as any)

      const store = useBuildStore()
      await store.startBuild({ remote_path: '/path', account_alias: 'test' })

      expect(store.currentTaskId).toBe('task-123')
    })

    it('应该支持 taskId 字段', async () => {
      mockRequestResolved({ taskId: 'task-456' } as any)

      const store = useBuildStore()
      await store.startBuild({ remote_path: '/path', account_alias: 'test' })

      expect(store.currentTaskId).toBe('task-456')
    })

    it('失败时应该设置 buildStatus 为 failed', async () => {
      mockRequestRejected(new Error('Build start failed'))

      const store = useBuildStore()
      await expect(store.startBuild({ remote_path: '/path', account_alias: 'test' })).rejects.toThrow()

      expect(store.buildStatus).toBe('failed')
    })

    it('应该停止之前的轮询', async () => {
      mockRequestResolved({ task_id: 'task-123' } as any)

      const store = useBuildStore()
      store.currentTaskId = 'old-task'
      await store.startBuild({ remote_path: '/path', account_alias: 'test' })

      expect(store.currentTaskId).toBe('task-123')
    })

    it('失败时应该通过回调输出错误日志', async () => {
      mockRequestRejected(new Error('Build start failed'))

      const store = useBuildStore()
      const callback = vi.fn()
      store.setLogCallback(callback)

      await expect(store.startBuild({ remote_path: '/path', account_alias: 'test' })).rejects.toThrow()

      expect(callback).toHaveBeenCalled()
      expect(callback.mock.calls[0][0]).toContain('启动编译失败')
    })

    it('应该传递可选参数到 API', async () => {
      mockRequestResolved({ task_id: 'task-123' } as any)

      const store = useBuildStore()
      await store.startBuild({
        remote_path: '/path',
        account_alias: 'test',
        local_path: '/local',
        command: 'npm run build',
        jdk_version: '17',
      })

      expect(request.post).toHaveBeenCalledWith('/build/compile', expect.objectContaining({
        project_path: '/path',
        account_alias: 'test',
        local_path: '/local',
        command: 'npm run build',
        jdk_version: '17',
      }))
    })
  })

  describe('startTest', () => {
    it('应该设置 buildStatus 为 building', async () => {
      mockRequestResolved({ task_id: 'task-test' } as any)

      const store = useBuildStore()
      await store.startTest({ remote_path: '/path', account_alias: 'test' })

      expect(store.buildStatus).toBe('building')
    })

    it('应该调用 /build/test 接口', async () => {
      mockRequestResolved({ task_id: 'task-test' } as any)

      const store = useBuildStore()
      await store.startTest({ remote_path: '/path', account_alias: 'test' })

      expect(request.post).toHaveBeenCalledWith('/build/test', expect.objectContaining({
        project_path: '/path',
        account_alias: 'test',
      }))
    })

    it('失败时应该设置 buildStatus 为 failed 并调用回调', async () => {
      mockRequestRejected(new Error('Test start failed'))

      const store = useBuildStore()
      const callback = vi.fn()
      store.setLogCallback(callback)

      await expect(store.startTest({ remote_path: '/path', account_alias: 'test' })).rejects.toThrow()

      expect(store.buildStatus).toBe('failed')
      expect(callback).toHaveBeenCalled()
      expect(callback.mock.calls[0][0]).toContain('启动测试失败')
    })

    it('应该传递可选参数到 API', async () => {
      mockRequestResolved({ task_id: 'task-test' } as any)

      const store = useBuildStore()
      await store.startTest({
        remote_path: '/path',
        account_alias: 'test',
        local_path: '/local',
        command: 'npm test',
        jdk_version: '11',
      })

      expect(request.post).toHaveBeenCalledWith('/build/test', expect.objectContaining({
        local_path: '/local',
        command: 'npm test',
        jdk_version: '11',
      }))
    })
  })

  describe('startRun', () => {
    it('应该设置 runStatus 为 running', async () => {
      mockRequestResolved({ task_id: 'task-run' } as any)

      const store = useBuildStore()
      await store.startRun({ remote_path: '/path', account_alias: 'test' })

      expect(store.runStatus).toBe('running')
    })

    it('应该调用 /build/run 接口', async () => {
      mockRequestResolved({ task_id: 'task-run' } as any)

      const store = useBuildStore()
      await store.startRun({ remote_path: '/path', account_alias: 'test' })

      expect(request.post).toHaveBeenCalledWith('/build/run', expect.objectContaining({
        project_path: '/path',
        account_alias: 'test',
      }))
    })

    it('失败时应该设置 runStatus 为 stopped', async () => {
      mockRequestRejected(new Error('Run start failed'))

      const store = useBuildStore()
      await expect(store.startRun({ remote_path: '/path', account_alias: 'test' })).rejects.toThrow()

      expect(store.runStatus).toBe('stopped')
    })

    it('失败时应该通过回调输出错误日志', async () => {
      mockRequestRejected(new Error('Run start failed'))

      const store = useBuildStore()
      const callback = vi.fn()
      store.setLogCallback(callback)

      await expect(store.startRun({ remote_path: '/path', account_alias: 'test' })).rejects.toThrow()

      expect(callback).toHaveBeenCalled()
      expect(callback.mock.calls[0][0]).toContain('启动失败')
    })

    it('应该传递可选参数到 API', async () => {
      mockRequestResolved({ task_id: 'task-run' } as any)

      const store = useBuildStore()
      await store.startRun({
        remote_path: '/path',
        account_alias: 'test',
        local_path: '/local',
        jar_path: '/app.jar',
        run_mode: 'jar',
        jdk_version: '17',
      })

      expect(request.post).toHaveBeenCalledWith('/build/run', expect.objectContaining({
        local_path: '/local',
        jar_path: '/app.jar',
        run_mode: 'jar',
        jdk_version: '17',
      }))
    })

    it('run_mode 默认应为 spring-boot', async () => {
      mockRequestResolved({ task_id: 'task-run' } as any)

      const store = useBuildStore()
      await store.startRun({ remote_path: '/path', account_alias: 'test' })

      expect(request.post).toHaveBeenCalledWith('/build/run', expect.objectContaining({
        run_mode: 'spring-boot',
      }))
    })
  })

  describe('轮询逻辑', () => {
    it('startBuild 后应该开始轮询任务状态', async () => {
      vi.mocked(request.post).mockResolvedValue({ task_id: 'task-123' })
      vi.mocked(request.get).mockResolvedValue({ status: 'running', action: 'build', log: '' })

      const store = useBuildStore()
      await store.startBuild({ remote_path: '/path', account_alias: 'test' })

      vi.advanceTimersByTime(500)
      await vi.runOnlyPendingTimersAsync()

      expect(request.get).toHaveBeenCalledWith('/build/status/task-123')
    })

    it('轮询时 build action running 状态应设置 buildStatus 为 building', async () => {
      vi.mocked(request.post).mockResolvedValue({ task_id: 'task-123' })
      vi.mocked(request.get).mockResolvedValue({ status: 'running', action: 'build', log: '' })

      const store = useBuildStore()
      await store.startBuild({ remote_path: '/path', account_alias: 'test' })

      vi.advanceTimersByTime(500)
      await vi.runOnlyPendingTimersAsync()

      expect(store.buildStatus).toBe('building')
    })

    it('轮询时 build action completed 状态应设置 buildStatus 为 success 并停止轮询', async () => {
      vi.mocked(request.post).mockResolvedValue({ task_id: 'task-123' })
      vi.mocked(request.get).mockResolvedValue({ status: 'completed', action: 'build', log: '' })

      const store = useBuildStore()
      await store.startBuild({ remote_path: '/path', account_alias: 'test' })

      vi.advanceTimersByTime(500)
      await vi.runOnlyPendingTimersAsync()

      expect(store.buildStatus).toBe('success')

      vi.advanceTimersByTime(1000)
      const callCount = vi.mocked(request.get).mock.calls.length
      vi.advanceTimersByTime(500)
      await vi.runOnlyPendingTimersAsync()
      expect(vi.mocked(request.get).mock.calls.length).toBe(callCount)
    })

    it('轮询时 run action running 状态应设置 runStatus 为 running', async () => {
      vi.mocked(request.post).mockResolvedValue({ task_id: 'task-123' })
      vi.mocked(request.get).mockResolvedValue({ status: 'running', action: 'run', log: '' })

      const store = useBuildStore()
      await store.startRun({ remote_path: '/path', account_alias: 'test' })

      vi.advanceTimersByTime(500)
      await vi.runOnlyPendingTimersAsync()

      expect(store.runStatus).toBe('running')
    })

    it('轮询时 run action completed 状态应保持 runStatus 为 running', async () => {
      vi.mocked(request.post).mockResolvedValue({ task_id: 'task-123' })
      vi.mocked(request.get).mockResolvedValue({ status: 'completed', action: 'run', log: '' })

      const store = useBuildStore()
      await store.startRun({ remote_path: '/path', account_alias: 'test' })

      vi.advanceTimersByTime(500)
      await vi.runOnlyPendingTimersAsync()

      expect(store.runStatus).toBe('running')
    })

    it('轮询时 build action failed 状态应设置 buildStatus 为 failed 并停止轮询', async () => {
      vi.mocked(request.post).mockResolvedValue({ task_id: 'task-123' })
      vi.mocked(request.get).mockResolvedValue({ status: 'failed', action: 'build', log: '' })

      const store = useBuildStore()
      await store.startBuild({ remote_path: '/path', account_alias: 'test' })

      vi.advanceTimersByTime(500)
      await vi.runOnlyPendingTimersAsync()

      expect(store.buildStatus).toBe('failed')
    })

    it('轮询时 run action failed 状态应设置 runStatus 为 stopped', async () => {
      vi.mocked(request.post).mockResolvedValue({ task_id: 'task-123' })
      vi.mocked(request.get).mockResolvedValue({ status: 'failed', action: 'run', log: '' })

      const store = useBuildStore()
      await store.startRun({ remote_path: '/path', account_alias: 'test' })

      vi.advanceTimersByTime(500)
      await vi.runOnlyPendingTimersAsync()

      expect(store.runStatus).toBe('stopped')
    })

    it('轮询时 build action stopped 状态应设置 buildStatus 为 idle', async () => {
      vi.mocked(request.post).mockResolvedValue({ task_id: 'task-123' })
      vi.mocked(request.get).mockResolvedValue({ status: 'stopped', action: 'build', log: '' })

      const store = useBuildStore()
      await store.startBuild({ remote_path: '/path', account_alias: 'test' })

      vi.advanceTimersByTime(500)
      await vi.runOnlyPendingTimersAsync()

      expect(store.buildStatus).toBe('idle')
    })

    it('轮询时 run action stopped 状态应设置 runStatus 为 stopped', async () => {
      vi.mocked(request.post).mockResolvedValue({ task_id: 'task-123' })
      vi.mocked(request.get).mockResolvedValue({ status: 'stopped', action: 'run', log: '' })

      const store = useBuildStore()
      await store.startRun({ remote_path: '/path', account_alias: 'test' })

      vi.advanceTimersByTime(500)
      await vi.runOnlyPendingTimersAsync()

      expect(store.runStatus).toBe('stopped')
    })

    it('轮询时 pending 状态应保持 buildStatus 为 building', async () => {
      vi.mocked(request.post).mockResolvedValue({ task_id: 'task-123' })
      vi.mocked(request.get).mockResolvedValue({ status: 'pending', action: 'build', log: '' })

      const store = useBuildStore()
      await store.startBuild({ remote_path: '/path', account_alias: 'test' })

      vi.advanceTimersByTime(500)
      await vi.runOnlyPendingTimersAsync()

      expect(store.buildStatus).toBe('building')
    })

    it('轮询时新日志应该通过回调输出', async () => {
      vi.mocked(request.post).mockResolvedValue({ task_id: 'task-123' })
      vi.mocked(request.get).mockResolvedValue({ status: 'running', action: 'build', log: 'Hello World' })

      const store = useBuildStore()
      const callback = vi.fn()
      store.setLogCallback(callback)
      await store.startBuild({ remote_path: '/path', account_alias: 'test' })

      vi.advanceTimersByTime(500)
      await vi.runOnlyPendingTimersAsync()

      expect(store.rawLog).toBe('Hello World')
      expect(callback).toHaveBeenCalledWith('Hello World')
    })

    it('轮询时日志增量应该只输出新增部分', async () => {
      vi.mocked(request.post).mockResolvedValue({ task_id: 'task-123' })
      vi.mocked(request.get)
        .mockResolvedValueOnce({ status: 'running', action: 'build', log: 'Hello' })

      const store = useBuildStore()
      const callback = vi.fn()
      store.setLogCallback(callback)
      await store.startBuild({ remote_path: '/path', account_alias: 'test' })

      await vi.advanceTimersByTimeAsync(500)

      expect(store.rawLog).toBe('Hello')
      expect(callback).toHaveBeenLastCalledWith('Hello')

      vi.mocked(request.get).mockResolvedValueOnce({ status: 'running', action: 'build', log: 'Hello World' })

      await vi.advanceTimersByTimeAsync(500)

      expect(store.rawLog).toBe('Hello World')
      expect(callback).toHaveBeenLastCalledWith(' World')
    })

    it('轮询请求失败应设置 buildStatus 为 failed 并停止轮询', async () => {
      vi.mocked(request.post).mockResolvedValue({ task_id: 'task-123' })
      vi.mocked(request.get).mockRejectedValue(new Error('Network error'))

      const store = useBuildStore()
      await store.startBuild({ remote_path: '/path', account_alias: 'test' })

      vi.advanceTimersByTime(500)
      await vi.runOnlyPendingTimersAsync()

      expect(store.buildStatus).toBe('failed')
    })

    it('currentTaskId 为空时轮询应跳过请求', async () => {
      vi.mocked(request.get).mockResolvedValue({ status: 'running', action: 'build', log: '' })

      const store = useBuildStore()
      store.currentTaskId = ''

      store.resetStatus()
      await store.startBuild({ remote_path: '/path', account_alias: 'test' })
      store.currentTaskId = ''

      vi.advanceTimersByTime(500)
      await vi.runOnlyPendingTimersAsync()

      const statusCalls = vi.mocked(request.get).mock.calls.filter(
        (call: any[]) => call[0]?.includes('/build/status/')
      )
      expect(statusCalls.length).toBe(0)
    })
  })

  describe('stopTask', () => {
    it('应该调用停止 API', async () => {
      mockRequestResolved({} as any)

      const store = useBuildStore()
      store.currentTaskId = 'task-123'
      await store.stopTask()

      expect(request.post).toHaveBeenCalledWith('/build/stop', { task_id: 'task-123' })
    })

    it('停止编译任务时应该设置 buildStatus 为 idle', async () => {
      mockRequestResolved({} as any)

      const store = useBuildStore()
      store.buildStatus = 'building'
      store.currentTaskId = 'task-123'
      await store.stopTask()

      expect(store.buildStatus).toBe('idle')
    })

    it('停止运行任务时应该设置 runStatus 为 stopped', async () => {
      mockRequestResolved({} as any)

      const store = useBuildStore()
      store.runStatus = 'running'
      store.currentTaskId = 'task-123'
      await store.stopTask()

      expect(store.runStatus).toBe('stopped')
    })

    it('应该清空 currentTaskId', async () => {
      mockRequestResolved({} as any)

      const store = useBuildStore()
      store.currentTaskId = 'task-123'
      await store.stopTask()

      expect(store.currentTaskId).toBe('')
    })

    it('API 失败时不应该抛出异常', async () => {
      mockRequestRejected(new Error('Stop failed'))

      const store = useBuildStore()
      store.currentTaskId = 'task-123'
      await expect(store.stopTask()).resolves.toBeUndefined()
    })

    it('停止编译任务时应该通过回调输出停止消息', async () => {
      mockRequestResolved({} as any)

      const store = useBuildStore()
      const callback = vi.fn()
      store.setLogCallback(callback)
      store.buildStatus = 'building'
      store.currentTaskId = 'task-123'
      await store.stopTask()

      expect(callback).toHaveBeenCalled()
    })

    it('API 失败时应该通过回调输出错误', async () => {
      mockRequestRejected(new Error('Stop failed'))

      const store = useBuildStore()
      const callback = vi.fn()
      store.setLogCallback(callback)
      store.currentTaskId = 'task-123'
      await store.stopTask()

      expect(callback).toHaveBeenCalled()
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
  })
})
