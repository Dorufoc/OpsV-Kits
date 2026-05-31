import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { schedulerApi } from '@/api'

export interface RetryPolicy {
  max_retries: number
  strategy: string
  interval_seconds: number
  max_interval_seconds?: number
}

export interface AlertConfig {
  channel: string
  recipients: string[]
  template?: string
  enabled: boolean
}

export interface ScheduledTask {
  id: string
  name: string
  description?: string
  workflow_id?: string
  task_type: string
  command?: string
  cron_expression: string
  timezone: string
  priority: string
  max_concurrent: number
  timeout_seconds: number
  retry_policy: RetryPolicy
  alert_configs: AlertConfig[]
  status: string
  account_alias?: string
  last_run_at?: string
  last_run_status?: string
  next_run_at?: string
  created_at: string
  updated_at: string
}

export interface TaskExecution {
  id: string
  task_id: string
  task_name: string
  status: string
  trigger_mode: string
  retry_count: number
  exit_code?: number
  output?: string
  error?: string
  started_at: string
  completed_at?: string
  duration_seconds?: number
  account_alias?: string
}

export const useSchedulerStore = defineStore('scheduler', () => {
  const tasks = ref<ScheduledTask[]>([])
  const executions = ref<TaskExecution[]>([])
  const currentExecution = ref<TaskExecution | null>(null)
  const schedulerStatus = ref<{ running: boolean; job_count: number } | null>(null)
  const loading = ref(false)

  const enabledTaskCount = computed(() => tasks.value.filter(t => t.status === 'enabled').length)
  const todaySuccessCount = computed(() => {
    const today = new Date().toISOString().slice(0, 10)
    return executions.value.filter(e => e.started_at?.startsWith(today) && e.status === 'success').length
  })
  const todayFailedCount = computed(() => {
    const today = new Date().toISOString().slice(0, 10)
    return executions.value.filter(e => e.started_at?.startsWith(today) && e.status === 'failed').length
  })

  async function fetchTasks() {
    loading.value = true
    try {
      const res: any = await schedulerApi.listTasks()
      tasks.value = res.items || []
    } finally {
      loading.value = false
    }
  }

  async function createTask(data: any) {
    const res: any = await schedulerApi.createTask(data)
    tasks.value.push(res)
    return res
  }

  async function updateTask(id: string, data: any) {
    const res: any = await schedulerApi.updateTask(id, data)
    const idx = tasks.value.findIndex(t => t.id === id)
    if (idx >= 0) tasks.value[idx] = res
    return res
  }

  async function deleteTask(id: string) {
    await schedulerApi.deleteTask(id)
    tasks.value = tasks.value.filter(t => t.id !== id)
  }

  async function toggleTask(id: string, enabled: boolean) {
    const res: any = await schedulerApi.toggleTask(id, enabled)
    const idx = tasks.value.findIndex(t => t.id === id)
    if (idx >= 0) tasks.value[idx] = res
    return res
  }

  async function runTaskNow(id: string) {
    const res: any = await schedulerApi.runTask(id)
    return res
  }

  async function fetchExecutions(taskId?: string, status?: string) {
    const res: any = await schedulerApi.listExecutions(taskId, status)
    executions.value = res.items || []
  }

  async function fetchExecution(executionId: string) {
    const res: any = await schedulerApi.getExecution(executionId)
    currentExecution.value = res
  }

  async function retryExecution(executionId: string) {
    const res: any = await schedulerApi.retryExecution(executionId)
    return res
  }

  async function fetchSchedulerStatus() {
    const res: any = await schedulerApi.getStatus()
    schedulerStatus.value = res
  }

  return {
    tasks, executions, currentExecution, schedulerStatus, loading,
    enabledTaskCount, todaySuccessCount, todayFailedCount,
    fetchTasks, createTask, updateTask, deleteTask, toggleTask,
    runTaskNow, fetchExecutions, fetchExecution, retryExecution, fetchSchedulerStatus,
  }
})
