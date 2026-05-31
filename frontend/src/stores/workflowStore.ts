import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { workflowApi } from '@/api'

export interface WorkflowNode {
  id: string
  workflow_id: string
  node_type: string
  name: string
  config: Record<string, any>
  position_x: number
  position_y: number
  description?: string
  created_at: string
  updated_at: string
}

export interface WorkflowEdge {
  id: string
  workflow_id: string
  source_node_id: string
  target_node_id: string
  source_port?: string
  target_port?: string
  label?: string
  created_at: string
}

export interface Workflow {
  id: string
  name: string
  description?: string
  status: string
  nodes: WorkflowNode[]
  edges: WorkflowEdge[]
  version: number
  created_at: string
  updated_at: string
}

export interface WorkflowVersion {
  id: string
  workflow_id: string
  version: number
  snapshot: Record<string, any>
  change_note?: string
  created_at: string
}

export interface WorkflowExecution {
  id: string
  workflow_id: string
  workflow_name: string
  version: number
  status: string
  trigger_type: string
  trigger_source?: string
  started_at: string
  completed_at?: string
  duration_seconds?: number
  total_nodes: number
  success_nodes: number
  failed_nodes: number
  error_message?: string
}

export interface NodeExecution {
  id: string
  execution_id: string
  node_id: string
  node_name: string
  node_type: string
  status: string
  input_data?: Record<string, any>
  output_data?: Record<string, any>
  error_message?: string
  started_at: string
  completed_at?: string
  duration_seconds?: number
}

export interface WorkflowTemplate {
  id: string
  name: string
  description?: string
  category: string
  nodes: Record<string, any>[]
  edges: Record<string, any>[]
  icon?: string
}

export const useWorkflowStore = defineStore('workflow', () => {
  const workflows = ref<Workflow[]>([])
  const currentWorkflow = ref<Workflow | null>(null)
  const versions = ref<WorkflowVersion[]>([])
  const executions = ref<WorkflowExecution[]>([])
  const currentExecution = ref<WorkflowExecution | null>(null)
  const nodeExecutions = ref<NodeExecution[]>([])
  const templates = ref<WorkflowTemplate[]>([])
  const loading = ref(false)

  const activeWorkflowCount = computed(() => workflows.value.filter(w => w.status === 'active').length)
  const runningExecutionCount = computed(() => executions.value.filter(e => e.status === 'running').length)

  async function fetchWorkflows() {
    loading.value = true
    try {
      const res: any = await workflowApi.list()
      workflows.value = res.items || []
    } finally {
      loading.value = false
    }
  }

  async function fetchWorkflow(id: string) {
    loading.value = true
    try {
      const res: any = await workflowApi.get(id)
      currentWorkflow.value = res
    } finally {
      loading.value = false
    }
  }

  async function createWorkflow(data: any) {
    const res: any = await workflowApi.create(data)
    workflows.value.push(res)
    return res
  }

  async function updateWorkflow(id: string, data: any) {
    const res: any = await workflowApi.update(id, data)
    const idx = workflows.value.findIndex(w => w.id === id)
    if (idx >= 0) workflows.value[idx] = res
    if (currentWorkflow.value?.id === id) currentWorkflow.value = res
    return res
  }

  async function deleteWorkflow(id: string) {
    await workflowApi.delete(id)
    workflows.value = workflows.value.filter(w => w.id !== id)
    if (currentWorkflow.value?.id === id) currentWorkflow.value = null
  }

  async function validateDag(nodes: any[], edges: any[]) {
    return await workflowApi.validate(nodes, edges)
  }

  async function saveVersion(id: string, changeNote?: string) {
    const res: any = await workflowApi.saveVersion(id, changeNote)
    return res
  }

  async function fetchVersions(id: string) {
    const res: any = await workflowApi.listVersions(id)
    versions.value = res.items || []
  }

  async function rollback(id: string, version: number) {
    const res: any = await workflowApi.rollback(id, version)
    if (currentWorkflow.value?.id === id) currentWorkflow.value = res
    return res
  }

  async function exportWorkflow(id: string) {
    return await workflowApi.exportWorkflow(id)
  }

  async function importWorkflow(data: any) {
    const res: any = await workflowApi.importWorkflow(data)
    workflows.value.push(res)
    return res
  }

  async function fetchTemplates() {
    const res: any = await workflowApi.listTemplates()
    templates.value = res.items || []
  }

  async function createFromTemplate(templateId: string, name: string) {
    const res: any = await workflowApi.createFromTemplate(templateId, name)
    workflows.value.push(res)
    return res
  }

  async function executeWorkflow(id: string, triggerType: string = 'cron', triggerSource?: string) {
    const res: any = await workflowApi.execute(id, triggerType, triggerSource)
    return res
  }

  async function pauseExecution(executionId: string) {
    await workflowApi.pauseExecution(executionId)
  }

  async function resumeExecution(executionId: string) {
    await workflowApi.resumeExecution(executionId)
  }

  async function cancelExecution(executionId: string) {
    await workflowApi.cancelExecution(executionId)
  }

  async function fetchExecutions(workflowId: string) {
    const res: any = await workflowApi.listExecutions(workflowId)
    executions.value = res.items || []
  }

  async function fetchExecution(executionId: string) {
    const res: any = await workflowApi.getExecution(executionId)
    currentExecution.value = res
  }

  async function fetchNodeExecutions(executionId: string) {
    const res: any = await workflowApi.listNodeExecutions(executionId)
    nodeExecutions.value = res.items || []
  }

  return {
    workflows, currentWorkflow, versions, executions, currentExecution,
    nodeExecutions, templates, loading, activeWorkflowCount, runningExecutionCount,
    fetchWorkflows, fetchWorkflow, createWorkflow, updateWorkflow, deleteWorkflow,
    validateDag, saveVersion, fetchVersions, rollback, exportWorkflow, importWorkflow,
    fetchTemplates, createFromTemplate, executeWorkflow, pauseExecution, resumeExecution,
    cancelExecution, fetchExecutions, fetchExecution, fetchNodeExecutions,
  }
})
