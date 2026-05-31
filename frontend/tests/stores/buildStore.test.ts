/**
 * Build Store 单元测试
 * 测试构建生命周期：开始、状态轮询、取消、任务完成等待
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
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

      // 验证旧 task ID 被替换
      expect(store.currentTaskId).toBe('task-123')
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
  })
})
