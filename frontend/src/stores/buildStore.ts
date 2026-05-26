import { defineStore } from 'pinia'
import { ref } from 'vue'
import { request } from '@/api'

export type BuildStatus = 'idle' | 'building' | 'success' | 'failed'
export type RunStatus = 'idle' | 'running' | 'stopped'

export const useBuildStore = defineStore('build', () => {
  const buildStatus = ref<BuildStatus>('idle')
  const runStatus = ref<RunStatus>('idle')
  const currentTaskId = ref('')
  const rawLog = ref('')
  let pollTimer: ReturnType<typeof setInterval> | null = null
  let logCallback: ((text: string) => void) | null = null

  function setLogCallback(cb: (text: string) => void) {
    logCallback = cb
  }

  function pipeToTerminal(text: string) {
    if (logCallback) {
      logCallback(text)
    }
  }

  function startPolling() {
    stopPolling()
    pollTimer = setInterval(async () => {
      if (!currentTaskId.value) return
      try {
        const res: any = await request.get(`/build/status/${currentTaskId.value}`)

        if (res.status === 'running' || res.status === 'pending') {
          buildStatus.value = 'building'
        } else if (res.status === 'completed') {
          buildStatus.value = 'success'
          stopPolling()
        } else if (res.status === 'failed') {
          buildStatus.value = 'failed'
          stopPolling()
        } else if (res.status === 'stopped') {
          buildStatus.value = 'idle'
          stopPolling()
        }

        if (res.log && res.log.length > rawLog.value.length) {
          const newChunk = res.log.substring(rawLog.value.length)
          rawLog.value = res.log
          pipeToTerminal(newChunk)
        }
      } catch {
        stopPolling()
      }
    }, 500)
  }

  function stopPolling() {
    if (pollTimer !== null) {
      clearInterval(pollTimer)
      pollTimer = null
    }
  }

  async function startBuild(params: { remote_path: string; account_alias: string; local_path?: string; command?: string; jdk_version?: string }) {
    buildStatus.value = 'building'
    rawLog.value = ''
    stopPolling()
    try {
      const res: any = await request.post('/build/compile', {
        project_path: params.remote_path,
        account_alias: params.account_alias,
        local_path: params.local_path || undefined,
        command: params.command || undefined,
        jdk_version: params.jdk_version || undefined,
      })
      currentTaskId.value = res.task_id || res.taskId
      startPolling()
      return res
    } catch (e) {
      buildStatus.value = 'failed'
      pipeToTerminal(`\r\n\x1b[31m启动编译失败: ${e}\x1b[0m\r\n`)
      throw e
    }
  }

  async function startRun(params: { remote_path: string; account_alias: string; jar_path?: string }) {
    runStatus.value = 'running'
    try {
      const res: any = await request.post('/build/run', {
        project_path: params.remote_path,
        account_alias: params.account_alias,
        jar_path: params.jar_path || undefined,
      })
      currentTaskId.value = res.task_id || res.taskId
      return res
    } catch (e) {
      runStatus.value = 'stopped'
      throw e
    }
  }

  async function stopTask() {
    await request.post('/build/stop', { task_id: currentTaskId.value })
    stopPolling()
    if (buildStatus.value === 'building') {
      buildStatus.value = 'idle'
      pipeToTerminal('\r\n\x1b[33m编译已停止\x1b[0m\r\n')
    }
    if (runStatus.value === 'running') {
      runStatus.value = 'stopped'
    }
    currentTaskId.value = ''
  }

  function resetStatus() {
    stopPolling()
    buildStatus.value = 'idle'
    runStatus.value = 'idle'
    rawLog.value = ''
    currentTaskId.value = ''
  }

  return {
    buildStatus,
    runStatus,
    rawLog,
    currentTaskId,
    setLogCallback,
    startBuild,
    startRun,
    stopTask,
    resetStatus,
  }
})
