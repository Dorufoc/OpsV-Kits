import { describe, it, expect, vi, beforeEach } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useSchedulerStore } from '@/stores/schedulerStore'
import * as api from '@/api'

describe('SchedulerStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  describe('状态初始化', () => {
    it('应该正确初始化 tasks 为空数组', () => {
      const store = useSchedulerStore()
      expect(store.tasks).toEqual([])
    })

    it('应该正确初始化 executions 为空数组', () => {
      const store = useSchedulerStore()
      expect(store.executions).toEqual([])
    })

    it('应该正确初始化 currentExecution 为 null', () => {
      const store = useSchedulerStore()
      expect(store.currentExecution).toBeNull()
    })

    it('应该正确初始化 schedulerStatus 为 null', () => {
      const store = useSchedulerStore()
      expect(store.schedulerStatus).toBeNull()
    })

    it('应该正确初始化 loading 为 false', () => {
      const store = useSchedulerStore()
      expect(store.loading).toBe(false)
    })
  })

  describe('计算属性', () => {
    it('enabledTaskCount 应该返回 status 为 enabled 的任务数', () => {
      const store = useSchedulerStore()
      store.tasks = [
        { id: '1', status: 'enabled' } as any,
        { id: '2', status: 'disabled' } as any,
        { id: '3', status: 'enabled' } as any,
      ]
      expect(store.enabledTaskCount).toBe(2)
    })

    it('enabledTaskCount 在没有 enabled 任务时应该返回 0', () => {
      const store = useSchedulerStore()
      store.tasks = [
        { id: '1', status: 'disabled' } as any,
      ]
      expect(store.enabledTaskCount).toBe(0)
    })

    it('todaySuccessCount 应该返回今天成功的执行数', () => {
      const store = useSchedulerStore()
      const today = new Date().toISOString().slice(0, 10)
      store.executions = [
        { id: '1', started_at: `${today}T10:00:00Z`, status: 'success' } as any,
        { id: '2', started_at: `${today}T11:00:00Z`, status: 'failed' } as any,
        { id: '3', started_at: `${today}T12:00:00Z`, status: 'success' } as any,
        { id: '4', started_at: '2000-01-01T10:00:00Z', status: 'success' } as any,
      ]
      expect(store.todaySuccessCount).toBe(2)
    })

    it('todayFailedCount 应该返回今天失败的执行数', () => {
      const store = useSchedulerStore()
      const today = new Date().toISOString().slice(0, 10)
      store.executions = [
        { id: '1', started_at: `${today}T10:00:00Z`, status: 'failed' } as any,
        { id: '2', started_at: `${today}T11:00:00Z`, status: 'success' } as any,
        { id: '3', started_at: '2000-01-01T10:00:00Z', status: 'failed' } as any,
      ]
      expect(store.todayFailedCount).toBe(1)
    })

    it('todaySuccessCount 在没有执行记录时应该返回 0', () => {
      const store = useSchedulerStore()
      expect(store.todaySuccessCount).toBe(0)
    })

    it('todayFailedCount 在没有执行记录时应该返回 0', () => {
      const store = useSchedulerStore()
      expect(store.todayFailedCount).toBe(0)
    })
  })

  describe('fetchTasks', () => {
    it('应该调用 schedulerApi.listTasks', async () => {
      const store = useSchedulerStore()
      await store.fetchTasks()
      expect(api.schedulerApi.listTasks).toHaveBeenCalled()
    })

    it('应该将返回数据设置到 tasks', async () => {
      const mockTasks = [{ id: '1', name: 'task1' }]
      vi.mocked(api.schedulerApi.listTasks).mockResolvedValue({ items: mockTasks })
      const store = useSchedulerStore()
      await store.fetchTasks()
      expect(store.tasks).toEqual(mockTasks)
    })

    it('返回数据没有 items 时应该设置为空数组', async () => {
      vi.mocked(api.schedulerApi.listTasks).mockResolvedValue({})
      const store = useSchedulerStore()
      await store.fetchTasks()
      expect(store.tasks).toEqual([])
    })

    it('请求期间 loading 应该为 true', async () => {
      let resolveFn: (v: any) => void
      const promise = new Promise(resolve => { resolveFn = resolve })
      vi.mocked(api.schedulerApi.listTasks).mockReturnValue(promise as any)
      const store = useSchedulerStore()
      const fetchPromise = store.fetchTasks()
      expect(store.loading).toBe(true)
      resolveFn!({ items: [] })
      await fetchPromise
      expect(store.loading).toBe(false)
    })

    it('请求失败后 loading 也应该恢复为 false', async () => {
      vi.mocked(api.schedulerApi.listTasks).mockRejectedValueOnce(new Error('fail'))
      const store = useSchedulerStore()
      await expect(store.fetchTasks()).rejects.toThrow('fail')
      expect(store.loading).toBe(false)
    })
  })

  describe('createTask', () => {
    it('应该调用 schedulerApi.createTask', async () => {
      const data = { name: 'new task' }
      vi.mocked(api.schedulerApi.createTask).mockResolvedValue({ id: '1', ...data })
      const store = useSchedulerStore()
      await store.createTask(data)
      expect(api.schedulerApi.createTask).toHaveBeenCalledWith(data)
    })

    it('应该将新任务添加到 tasks', async () => {
      const newTask = { id: '1', name: 'new task' }
      vi.mocked(api.schedulerApi.createTask).mockResolvedValue(newTask)
      const store = useSchedulerStore()
      await store.createTask({ name: 'new task' })
      expect(store.tasks).toContainEqual(newTask)
    })

    it('应该返回创建的任务', async () => {
      const newTask = { id: '1', name: 'new task' }
      vi.mocked(api.schedulerApi.createTask).mockResolvedValue(newTask)
      const store = useSchedulerStore()
      const result = await store.createTask({ name: 'new task' })
      expect(result).toEqual(newTask)
    })
  })

  describe('updateTask', () => {
    it('应该调用 schedulerApi.updateTask', async () => {
      const updated = { id: '1', name: 'updated' }
      vi.mocked(api.schedulerApi.updateTask).mockResolvedValue(updated)
      const store = useSchedulerStore()
      store.tasks = [{ id: '1', name: 'old' } as any]
      await store.updateTask('1', { name: 'updated' })
      expect(api.schedulerApi.updateTask).toHaveBeenCalledWith('1', { name: 'updated' })
    })

    it('应该更新 tasks 中对应 id 的任务', async () => {
      const updated = { id: '1', name: 'updated' }
      vi.mocked(api.schedulerApi.updateTask).mockResolvedValue(updated)
      const store = useSchedulerStore()
      store.tasks = [{ id: '1', name: 'old' } as any]
      await store.updateTask('1', { name: 'updated' })
      expect(store.tasks[0]).toEqual(updated)
    })

    it('应该返回更新后的任务', async () => {
      const updated = { id: '1', name: 'updated' }
      vi.mocked(api.schedulerApi.updateTask).mockResolvedValue(updated)
      const store = useSchedulerStore()
      const result = await store.updateTask('1', { name: 'updated' })
      expect(result).toEqual(updated)
    })
  })

  describe('deleteTask', () => {
    it('应该调用 schedulerApi.deleteTask', async () => {
      vi.mocked(api.schedulerApi.deleteTask).mockResolvedValue({})
      const store = useSchedulerStore()
      store.tasks = [{ id: '1', name: 'task1' } as any]
      await store.deleteTask('1')
      expect(api.schedulerApi.deleteTask).toHaveBeenCalledWith('1')
    })

    it('应该从 tasks 中移除对应 id 的任务', async () => {
      vi.mocked(api.schedulerApi.deleteTask).mockResolvedValue({})
      const store = useSchedulerStore()
      store.tasks = [{ id: '1', name: 'task1' } as any, { id: '2', name: 'task2' } as any]
      await store.deleteTask('1')
      expect(store.tasks).toHaveLength(1)
      expect(store.tasks[0].id).toBe('2')
    })
  })

  describe('toggleTask', () => {
    it('应该调用 schedulerApi.toggleTask', async () => {
      const updated = { id: '1', status: 'enabled' }
      vi.mocked(api.schedulerApi.toggleTask).mockResolvedValue(updated)
      const store = useSchedulerStore()
      store.tasks = [{ id: '1', status: 'disabled' } as any]
      await store.toggleTask('1', true)
      expect(api.schedulerApi.toggleTask).toHaveBeenCalledWith('1', true)
    })

    it('应该更新 tasks 中对应任务', async () => {
      const updated = { id: '1', status: 'enabled' }
      vi.mocked(api.schedulerApi.toggleTask).mockResolvedValue(updated)
      const store = useSchedulerStore()
      store.tasks = [{ id: '1', status: 'disabled' } as any]
      await store.toggleTask('1', true)
      expect(store.tasks[0]).toEqual(updated)
    })

    it('应该返回更新后的任务', async () => {
      const updated = { id: '1', status: 'enabled' }
      vi.mocked(api.schedulerApi.toggleTask).mockResolvedValue(updated)
      const store = useSchedulerStore()
      const result = await store.toggleTask('1', true)
      expect(result).toEqual(updated)
    })
  })

  describe('runTaskNow', () => {
    it('应该调用 schedulerApi.runTask', async () => {
      const response = { execution_id: 'e1' }
      vi.mocked(api.schedulerApi.runTask).mockResolvedValue(response)
      const store = useSchedulerStore()
      await store.runTaskNow('1')
      expect(api.schedulerApi.runTask).toHaveBeenCalledWith('1')
    })

    it('应该返回执行结果', async () => {
      const response = { execution_id: 'e1' }
      vi.mocked(api.schedulerApi.runTask).mockResolvedValue(response)
      const store = useSchedulerStore()
      const result = await store.runTaskNow('1')
      expect(result).toEqual(response)
    })
  })

  describe('fetchExecutions', () => {
    it('应该调用 schedulerApi.listExecutions', async () => {
      vi.mocked(api.schedulerApi.listExecutions).mockResolvedValue({ items: [] })
      const store = useSchedulerStore()
      await store.fetchExecutions()
      expect(api.schedulerApi.listExecutions).toHaveBeenCalledWith(undefined, undefined)
    })

    it('应该传递 taskId 和 status 参数', async () => {
      vi.mocked(api.schedulerApi.listExecutions).mockResolvedValue({ items: [] })
      const store = useSchedulerStore()
      await store.fetchExecutions('task1', 'failed')
      expect(api.schedulerApi.listExecutions).toHaveBeenCalledWith('task1', 'failed')
    })

    it('应该将返回数据设置到 executions', async () => {
      const mockExecutions = [{ id: 'e1', task_id: '1' }]
      vi.mocked(api.schedulerApi.listExecutions).mockResolvedValue({ items: mockExecutions })
      const store = useSchedulerStore()
      await store.fetchExecutions()
      expect(store.executions).toEqual(mockExecutions)
    })

    it('返回数据没有 items 时应该设置为空数组', async () => {
      vi.mocked(api.schedulerApi.listExecutions).mockResolvedValue({})
      const store = useSchedulerStore()
      await store.fetchExecutions()
      expect(store.executions).toEqual([])
    })
  })

  describe('fetchExecution', () => {
    it('应该调用 schedulerApi.getExecution', async () => {
      const mockExec = { id: 'e1', status: 'success' }
      vi.mocked(api.schedulerApi.getExecution).mockResolvedValue(mockExec)
      const store = useSchedulerStore()
      await store.fetchExecution('e1')
      expect(api.schedulerApi.getExecution).toHaveBeenCalledWith('e1')
    })

    it('应该将返回数据设置到 currentExecution', async () => {
      const mockExec = { id: 'e1', status: 'success' }
      vi.mocked(api.schedulerApi.getExecution).mockResolvedValue(mockExec)
      const store = useSchedulerStore()
      await store.fetchExecution('e1')
      expect(store.currentExecution).toEqual(mockExec)
    })
  })

  describe('retryExecution', () => {
    it('应该调用 schedulerApi.retryExecution', async () => {
      const response = { execution_id: 'e2' }
      vi.mocked(api.schedulerApi.retryExecution).mockResolvedValue(response)
      const store = useSchedulerStore()
      await store.retryExecution('e1')
      expect(api.schedulerApi.retryExecution).toHaveBeenCalledWith('e1')
    })

    it('应该返回重试结果', async () => {
      const response = { execution_id: 'e2' }
      vi.mocked(api.schedulerApi.retryExecution).mockResolvedValue(response)
      const store = useSchedulerStore()
      const result = await store.retryExecution('e1')
      expect(result).toEqual(response)
    })
  })

  describe('fetchSchedulerStatus', () => {
    it('应该调用 schedulerApi.getStatus', async () => {
      const mockStatus = { running: true, job_count: 5 }
      vi.mocked(api.schedulerApi.getStatus).mockResolvedValue(mockStatus)
      const store = useSchedulerStore()
      await store.fetchSchedulerStatus()
      expect(api.schedulerApi.getStatus).toHaveBeenCalled()
    })

    it('应该将返回数据设置到 schedulerStatus', async () => {
      const mockStatus = { running: true, job_count: 5 }
      vi.mocked(api.schedulerApi.getStatus).mockResolvedValue(mockStatus)
      const store = useSchedulerStore()
      await store.fetchSchedulerStatus()
      expect(store.schedulerStatus).toEqual(mockStatus)
    })
  })
})
