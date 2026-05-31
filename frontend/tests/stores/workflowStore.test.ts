import { describe, it, expect, vi, beforeEach } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useWorkflowStore } from '@/stores/workflowStore'
import * as api from '@/api'

describe('Workflow Store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  describe('状态初始化', () => {
    it('应该正确初始化 workflows 为空数组', () => {
      const store = useWorkflowStore()
      expect(store.workflows).toEqual([])
    })

    it('应该正确初始化 currentWorkflow 为 null', () => {
      const store = useWorkflowStore()
      expect(store.currentWorkflow).toBeNull()
    })

    it('应该正确初始化 versions 为空数组', () => {
      const store = useWorkflowStore()
      expect(store.versions).toEqual([])
    })

    it('应该正确初始化 executions 为空数组', () => {
      const store = useWorkflowStore()
      expect(store.executions).toEqual([])
    })

    it('应该正确初始化 currentExecution 为 null', () => {
      const store = useWorkflowStore()
      expect(store.currentExecution).toBeNull()
    })

    it('应该正确初始化 nodeExecutions 为空数组', () => {
      const store = useWorkflowStore()
      expect(store.nodeExecutions).toEqual([])
    })

    it('应该正确初始化 templates 为空数组', () => {
      const store = useWorkflowStore()
      expect(store.templates).toEqual([])
    })

    it('应该正确初始化 loading 为 false', () => {
      const store = useWorkflowStore()
      expect(store.loading).toBe(false)
    })
  })

  describe('计算属性', () => {
    it('activeWorkflowCount 应该返回 active 状态的工作流数量', () => {
      const store = useWorkflowStore()
      store.workflows = [
        { id: '1', name: 'w1', status: 'active', nodes: [], edges: [], version: 1, created_at: '', updated_at: '' },
        { id: '2', name: 'w2', status: 'draft', nodes: [], edges: [], version: 1, created_at: '', updated_at: '' },
        { id: '3', name: 'w3', status: 'active', nodes: [], edges: [], version: 1, created_at: '', updated_at: '' },
      ] as any

      expect(store.activeWorkflowCount).toBe(2)
    })

    it('activeWorkflowCount 在没有 active 工作流时应该返回 0', () => {
      const store = useWorkflowStore()
      expect(store.activeWorkflowCount).toBe(0)
    })

    it('runningExecutionCount 应该返回 running 状态的执行数量', () => {
      const store = useWorkflowStore()
      store.executions = [
        { id: 'e1', workflow_id: '1', workflow_name: 'w1', version: 1, status: 'running', trigger_type: 'manual', started_at: '', total_nodes: 3, success_nodes: 1, failed_nodes: 0 },
        { id: 'e2', workflow_id: '1', workflow_name: 'w1', version: 1, status: 'completed', trigger_type: 'cron', started_at: '', total_nodes: 3, success_nodes: 3, failed_nodes: 0 },
        { id: 'e3', workflow_id: '2', workflow_name: 'w2', version: 1, status: 'running', trigger_type: 'event', started_at: '', total_nodes: 2, success_nodes: 0, failed_nodes: 0 },
      ] as any

      expect(store.runningExecutionCount).toBe(2)
    })

    it('runningExecutionCount 在没有 running 执行时应该返回 0', () => {
      const store = useWorkflowStore()
      expect(store.runningExecutionCount).toBe(0)
    })
  })

  describe('fetchWorkflows', () => {
    it('应该获取工作流列表', async () => {
      const mockWorkflows = [
        { id: '1', name: 'Deploy', status: 'active', nodes: [], edges: [], version: 1, created_at: '', updated_at: '' },
      ]
      vi.mocked(api.workflowApi.list).mockResolvedValue({ items: mockWorkflows } as any)

      const store = useWorkflowStore()
      await store.fetchWorkflows()

      expect(store.workflows).toEqual(mockWorkflows)
    })

    it('API 返回无 items 时应该设为空数组', async () => {
      vi.mocked(api.workflowApi.list).mockResolvedValue({} as any)

      const store = useWorkflowStore()
      await store.fetchWorkflows()

      expect(store.workflows).toEqual([])
    })

    it('请求期间 loading 应该为 true', async () => {
      vi.mocked(api.workflowApi.list).mockImplementation(async () => {
        const store = useWorkflowStore()
        expect(store.loading).toBe(true)
        return { items: [] }
      })

      const store = useWorkflowStore()
      await store.fetchWorkflows()
      expect(store.loading).toBe(false)
    })

    it('请求失败时 loading 应该恢复为 false', async () => {
      vi.mocked(api.workflowApi.list).mockRejectedValue(new Error('Network error'))

      const store = useWorkflowStore()
      await expect(store.fetchWorkflows()).rejects.toThrow()
      expect(store.loading).toBe(false)
    })
  })

  describe('fetchWorkflow', () => {
    it('应该获取单个工作流详情', async () => {
      const mockWorkflow = { id: '1', name: 'Deploy', status: 'active', nodes: [], edges: [], version: 1, created_at: '', updated_at: '' }
      vi.mocked(api.workflowApi.get).mockResolvedValue(mockWorkflow as any)

      const store = useWorkflowStore()
      await store.fetchWorkflow('1')

      expect(store.currentWorkflow).toEqual(mockWorkflow)
    })

    it('请求期间 loading 应该为 true', async () => {
      vi.mocked(api.workflowApi.get).mockImplementation(async () => {
        const store = useWorkflowStore()
        expect(store.loading).toBe(true)
        return {}
      })

      const store = useWorkflowStore()
      await store.fetchWorkflow('1')
      expect(store.loading).toBe(false)
    })
  })

  describe('createWorkflow', () => {
    it('应该创建工作流并添加到列表', async () => {
      const newWorkflow = { id: '2', name: 'New Workflow', status: 'draft', nodes: [], edges: [], version: 1, created_at: '', updated_at: '' }
      vi.mocked(api.workflowApi.create).mockResolvedValue(newWorkflow as any)

      const store = useWorkflowStore()
      const result = await store.createWorkflow({ name: 'New Workflow' })

      expect(store.workflows).toContainEqual(newWorkflow)
      expect(result).toEqual(newWorkflow)
    })
  })

  describe('updateWorkflow', () => {
    it('应该更新工作流并同步列表和 currentWorkflow', async () => {
      const store = useWorkflowStore()
      store.workflows = [
        { id: '1', name: 'Old', status: 'draft', nodes: [], edges: [], version: 1, created_at: '', updated_at: '' },
      ] as any
      store.currentWorkflow = store.workflows[0]

      const updatedWorkflow = { id: '1', name: 'Updated', status: 'active', nodes: [], edges: [], version: 2, created_at: '', updated_at: '' }
      vi.mocked(api.workflowApi.update).mockResolvedValue(updatedWorkflow as any)

      const result = await store.updateWorkflow('1', { name: 'Updated' })

      expect(store.workflows[0]).toEqual(updatedWorkflow)
      expect(store.currentWorkflow).toEqual(updatedWorkflow)
    })

    it('更新非当前工作流时不应修改 currentWorkflow', async () => {
      const store = useWorkflowStore()
      store.workflows = [
        { id: '1', name: 'W1', status: 'active', nodes: [], edges: [], version: 1, created_at: '', updated_at: '' },
        { id: '2', name: 'W2', status: 'draft', nodes: [], edges: [], version: 1, created_at: '', updated_at: '' },
      ] as any
      store.currentWorkflow = store.workflows[0]

      const updatedWorkflow = { id: '2', name: 'W2-Updated', status: 'active', nodes: [], edges: [], version: 2, created_at: '', updated_at: '' }
      vi.mocked(api.workflowApi.update).mockResolvedValue(updatedWorkflow as any)

      await store.updateWorkflow('2', { name: 'W2-Updated' })

      expect(store.currentWorkflow?.id).toBe('1')
    })
  })

  describe('deleteWorkflow', () => {
    it('应该从列表中删除工作流', async () => {
      vi.mocked(api.workflowApi.delete).mockResolvedValue({} as any)

      const store = useWorkflowStore()
      store.workflows = [
        { id: '1', name: 'W1', status: 'active', nodes: [], edges: [], version: 1, created_at: '', updated_at: '' },
        { id: '2', name: 'W2', status: 'draft', nodes: [], edges: [], version: 1, created_at: '', updated_at: '' },
      ] as any

      await store.deleteWorkflow('1')

      expect(store.workflows).toHaveLength(1)
      expect(store.workflows[0].id).toBe('2')
    })

    it('删除当前工作流时应该清空 currentWorkflow', async () => {
      vi.mocked(api.workflowApi.delete).mockResolvedValue({} as any)

      const store = useWorkflowStore()
      store.workflows = [
        { id: '1', name: 'W1', status: 'active', nodes: [], edges: [], version: 1, created_at: '', updated_at: '' },
      ] as any
      store.currentWorkflow = store.workflows[0]

      await store.deleteWorkflow('1')

      expect(store.currentWorkflow).toBeNull()
    })

    it('删除非当前工作流时不应修改 currentWorkflow', async () => {
      vi.mocked(api.workflowApi.delete).mockResolvedValue({} as any)

      const store = useWorkflowStore()
      store.workflows = [
        { id: '1', name: 'W1', status: 'active', nodes: [], edges: [], version: 1, created_at: '', updated_at: '' },
        { id: '2', name: 'W2', status: 'draft', nodes: [], edges: [], version: 1, created_at: '', updated_at: '' },
      ] as any
      store.currentWorkflow = store.workflows[0]

      await store.deleteWorkflow('2')

      expect(store.currentWorkflow?.id).toBe('1')
    })
  })

  describe('validateDag', () => {
    it('应该验证 DAG 结构', async () => {
      const mockResult = { valid: true, errors: [] }
      vi.mocked(api.workflowApi.validate).mockResolvedValue(mockResult as any)

      const store = useWorkflowStore()
      const nodes = [{ id: 'n1' }]
      const edges = [{ source: 'n1', target: 'n2' }]
      const result = await store.validateDag(nodes, edges)

      expect(result).toEqual(mockResult)
      expect(api.workflowApi.validate).toHaveBeenCalledWith(nodes, edges)
    })
  })

  describe('saveVersion', () => {
    it('应该保存版本', async () => {
      const mockVersion = { id: 'v1', workflow_id: '1', version: 2, snapshot: {}, change_note: 'test' }
      vi.mocked(api.workflowApi.saveVersion).mockResolvedValue(mockVersion as any)

      const store = useWorkflowStore()
      const result = await store.saveVersion('1', 'test note')

      expect(result).toEqual(mockVersion)
      expect(api.workflowApi.saveVersion).toHaveBeenCalledWith('1', 'test note')
    })
  })

  describe('fetchVersions', () => {
    it('应该获取版本列表', async () => {
      const mockVersions = [
        { id: 'v1', workflow_id: '1', version: 1, snapshot: {}, created_at: '' },
      ]
      vi.mocked(api.workflowApi.listVersions).mockResolvedValue({ items: mockVersions } as any)

      const store = useWorkflowStore()
      await store.fetchVersions('1')

      expect(store.versions).toEqual(mockVersions)
    })

    it('API 返回无 items 时应该设为空数组', async () => {
      vi.mocked(api.workflowApi.listVersions).mockResolvedValue({} as any)

      const store = useWorkflowStore()
      await store.fetchVersions('1')

      expect(store.versions).toEqual([])
    })
  })

  describe('rollback', () => {
    it('应该回滚到指定版本并更新 currentWorkflow', async () => {
      const mockRollback = { id: '1', name: 'W1', status: 'active', nodes: [], edges: [], version: 1, created_at: '', updated_at: '' }
      vi.mocked(api.workflowApi.rollback).mockResolvedValue(mockRollback as any)

      const store = useWorkflowStore()
      store.currentWorkflow = { id: '1', name: 'W1', status: 'active', nodes: [], edges: [], version: 2, created_at: '', updated_at: '' } as any

      const result = await store.rollback('1', 1)

      expect(store.currentWorkflow).toEqual(mockRollback)
      expect(result).toEqual(mockRollback)
    })

    it('回滚非当前工作流时不应修改 currentWorkflow', async () => {
      const mockRollback = { id: '2', name: 'W2', status: 'active', nodes: [], edges: [], version: 1, created_at: '', updated_at: '' }
      vi.mocked(api.workflowApi.rollback).mockResolvedValue(mockRollback as any)

      const store = useWorkflowStore()
      store.currentWorkflow = { id: '1', name: 'W1', status: 'active', nodes: [], edges: [], version: 2, created_at: '', updated_at: '' } as any

      await store.rollback('2', 1)

      expect(store.currentWorkflow?.id).toBe('1')
    })
  })

  describe('exportWorkflow', () => {
    it('应该导出工作流', async () => {
      const mockExport = { name: 'W1', nodes: [], edges: [] }
      vi.mocked(api.workflowApi.exportWorkflow).mockResolvedValue(mockExport as any)

      const store = useWorkflowStore()
      const result = await store.exportWorkflow('1')

      expect(result).toEqual(mockExport)
      expect(api.workflowApi.exportWorkflow).toHaveBeenCalledWith('1')
    })
  })

  describe('importWorkflow', () => {
    it('应该导入工作流并添加到列表', async () => {
      const mockImported = { id: '3', name: 'Imported', status: 'draft', nodes: [], edges: [], version: 1, created_at: '', updated_at: '' }
      vi.mocked(api.workflowApi.importWorkflow).mockResolvedValue(mockImported as any)

      const store = useWorkflowStore()
      const result = await store.importWorkflow({ name: 'Imported' })

      expect(store.workflows).toContainEqual(mockImported)
      expect(result).toEqual(mockImported)
    })
  })

  describe('fetchTemplates', () => {
    it('应该获取模板列表', async () => {
      const mockTemplates = [
        { id: 't1', name: 'CI/CD', category: 'devops', nodes: [], edges: [] },
      ]
      vi.mocked(api.workflowApi.listTemplates).mockResolvedValue({ items: mockTemplates } as any)

      const store = useWorkflowStore()
      await store.fetchTemplates()

      expect(store.templates).toEqual(mockTemplates)
    })

    it('API 返回无 items 时应该设为空数组', async () => {
      vi.mocked(api.workflowApi.listTemplates).mockResolvedValue({} as any)

      const store = useWorkflowStore()
      await store.fetchTemplates()

      expect(store.templates).toEqual([])
    })
  })

  describe('createFromTemplate', () => {
    it('应该从模板创建工作流并添加到列表', async () => {
      const mockCreated = { id: '4', name: 'From Template', status: 'draft', nodes: [], edges: [], version: 1, created_at: '', updated_at: '' }
      vi.mocked(api.workflowApi.createFromTemplate).mockResolvedValue(mockCreated as any)

      const store = useWorkflowStore()
      const result = await store.createFromTemplate('t1', 'From Template')

      expect(store.workflows).toContainEqual(mockCreated)
      expect(api.workflowApi.createFromTemplate).toHaveBeenCalledWith('t1', 'From Template')
    })
  })

  describe('executeWorkflow', () => {
    it('应该执行工作流', async () => {
      const mockExecution = { id: 'e1', workflow_id: '1', status: 'running' }
      vi.mocked(api.workflowApi.execute).mockResolvedValue(mockExecution as any)

      const store = useWorkflowStore()
      const result = await store.executeWorkflow('1')

      expect(result).toEqual(mockExecution)
      expect(api.workflowApi.execute).toHaveBeenCalledWith('1', 'cron', undefined)
    })

    it('应该支持自定义触发类型和来源', async () => {
      vi.mocked(api.workflowApi.execute).mockResolvedValue({} as any)

      const store = useWorkflowStore()
      await store.executeWorkflow('1', 'webhook', 'source-1')

      expect(api.workflowApi.execute).toHaveBeenCalledWith('1', 'webhook', 'source-1')
    })
  })

  describe('pauseExecution', () => {
    it('应该暂停执行', async () => {
      vi.mocked(api.workflowApi.pauseExecution).mockResolvedValue({} as any)

      const store = useWorkflowStore()
      await store.pauseExecution('e1')

      expect(api.workflowApi.pauseExecution).toHaveBeenCalledWith('e1')
    })
  })

  describe('resumeExecution', () => {
    it('应该恢复执行', async () => {
      vi.mocked(api.workflowApi.resumeExecution).mockResolvedValue({} as any)

      const store = useWorkflowStore()
      await store.resumeExecution('e1')

      expect(api.workflowApi.resumeExecution).toHaveBeenCalledWith('e1')
    })
  })

  describe('cancelExecution', () => {
    it('应该取消执行', async () => {
      vi.mocked(api.workflowApi.cancelExecution).mockResolvedValue({} as any)

      const store = useWorkflowStore()
      await store.cancelExecution('e1')

      expect(api.workflowApi.cancelExecution).toHaveBeenCalledWith('e1')
    })
  })

  describe('fetchExecutions', () => {
    it('应该获取执行列表', async () => {
      const mockExecutions = [
        { id: 'e1', workflow_id: '1', workflow_name: 'W1', version: 1, status: 'completed', trigger_type: 'manual', started_at: '', total_nodes: 3, success_nodes: 3, failed_nodes: 0 },
      ]
      vi.mocked(api.workflowApi.listExecutions).mockResolvedValue({ items: mockExecutions } as any)

      const store = useWorkflowStore()
      await store.fetchExecutions('1')

      expect(store.executions).toEqual(mockExecutions)
    })

    it('API 返回无 items 时应该设为空数组', async () => {
      vi.mocked(api.workflowApi.listExecutions).mockResolvedValue({} as any)

      const store = useWorkflowStore()
      await store.fetchExecutions('1')

      expect(store.executions).toEqual([])
    })
  })

  describe('fetchExecution', () => {
    it('应该获取单个执行详情', async () => {
      const mockExecution = { id: 'e1', workflow_id: '1', workflow_name: 'W1', version: 1, status: 'running', trigger_type: 'manual', started_at: '', total_nodes: 3, success_nodes: 1, failed_nodes: 0 }
      vi.mocked(api.workflowApi.getExecution).mockResolvedValue(mockExecution as any)

      const store = useWorkflowStore()
      await store.fetchExecution('e1')

      expect(store.currentExecution).toEqual(mockExecution)
    })
  })

  describe('fetchNodeExecutions', () => {
    it('应该获取节点执行列表', async () => {
      const mockNodeExecutions = [
        { id: 'ne1', execution_id: 'e1', node_id: 'n1', node_name: 'Start', node_type: 'trigger', status: 'completed', started_at: '' },
      ]
      vi.mocked(api.workflowApi.listNodeExecutions).mockResolvedValue({ items: mockNodeExecutions } as any)

      const store = useWorkflowStore()
      await store.fetchNodeExecutions('e1')

      expect(store.nodeExecutions).toEqual(mockNodeExecutions)
    })

    it('API 返回无 items 时应该设为空数组', async () => {
      vi.mocked(api.workflowApi.listNodeExecutions).mockResolvedValue({} as any)

      const store = useWorkflowStore()
      await store.fetchNodeExecutions('e1')

      expect(store.nodeExecutions).toEqual([])
    })
  })
})
