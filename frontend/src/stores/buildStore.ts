import { defineStore } from 'pinia'
import { ref } from 'vue'
import { request } from '@/api'

export type BuildStatus = 'idle' | 'building' | 'success' | 'failed'
export type RunStatus = 'idle' | 'running' | 'stopped'

export interface BuildLog {
  timestamp: string
  level: 'INFO' | 'WARN' | 'ERROR'
  message: string
}

export interface TaskHistory {
  id: string
  type: 'build' | 'run'
  status: string
  started_at: string
  duration: number
  log_summary: string
}

export const useBuildStore = defineStore('build', () => {
  const buildStatus = ref<BuildStatus>('idle')
  const runStatus = ref<RunStatus>('idle')
  const logs = ref<BuildLog[]>([])
  const taskHistory = ref<TaskHistory[]>([])
  const currentTaskId = ref('')

  async function startBuild(params: { remote_path: string; ssh_alias: string; command?: string }) {
    buildStatus.value = 'building'
    logs.value = []
    try {
      const res = await request.post<{ task_id: string }>('/build/start', params)
      currentTaskId.value = res.task_id
      return res
    } catch (e) {
      buildStatus.value = 'failed'
      throw e
    }
  }

  async function startRun(params: { remote_path: string; ssh_alias: string; mode?: string; jar_path?: string; main_class?: string }) {
    runStatus.value = 'running'
    try {
      const res = await request.post<{ task_id: string }>('/build/run', params)
      currentTaskId.value = res.task_id
      return res
    } catch (e) {
      runStatus.value = 'stopped'
      throw e
    }
  }

  async function stopTask() {
    await request.post('/build/stop', { task_id: currentTaskId.value })
    if (buildStatus.value === 'building') {
      buildStatus.value = 'idle'
    }
    if (runStatus.value === 'running') {
      runStatus.value = 'stopped'
    }
    currentTaskId.value = ''
  }

  async function getHistory() {
    const res = await request.get<TaskHistory[]>('/build/history')
    taskHistory.value = res
    return res
  }

  async function getTaskStatus() {
    const res = await request.get<{ build_status: BuildStatus; run_status: RunStatus; logs: BuildLog[] }>(
      `/build/status/${currentTaskId.value}`
    )
    buildStatus.value = res.build_status
    runStatus.value = res.run_status
    if (res.logs) {
      logs.value = res.logs
    }
    return res
  }

  function addLog(entry: BuildLog) {
    logs.value.push(entry)
  }

  function resetStatus() {
    buildStatus.value = 'idle'
    runStatus.value = 'idle'
    logs.value = []
    currentTaskId.value = ''
  }

  return {
    buildStatus,
    runStatus,
    logs,
    taskHistory,
    currentTaskId,
    startBuild,
    startRun,
    stopTask,
    getHistory,
    getTaskStatus,
    addLog,
    resetStatus,
  }
})
