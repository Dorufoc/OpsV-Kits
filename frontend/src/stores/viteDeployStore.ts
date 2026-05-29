import { defineStore } from 'pinia'
import { ref } from 'vue'
import { request } from '@/api'

export type DeployStatus = 'idle' | 'running' | 'completed' | 'failed' | 'stopped'

export interface NodeStatus {
  installed: boolean
  version: string
}

export interface NginxStatus {
  installed: boolean
  running: boolean
}

export interface EnvironmentCheckResult {
  account_alias: string
  project_path: string
  node: NodeStatus & Record<string, any>
  nginx: NginxStatus & Record<string, any>
  vite: Record<string, any>
  framework: Record<string, any>
  all_ready: boolean
}

export interface TaskStatus {
  task_id: string
  status: string
  progress: number
  message: string
  step: string
  log: string
  url?: string
}

export interface DeployParams {
  account_alias: string
  project_alias: string
  project_path: string
  node_version?: string
  nginx_port?: number
  build_command?: string
  force?: boolean
}

export interface StepParams {
  account_alias: string
  project_path: string
  node_version?: string
  build_command?: string
  force?: boolean
  project_alias?: string
  port?: number
}

export const useViteDeployStore = defineStore('viteDeploy', () => {
  const deployStatus = ref<DeployStatus>('idle')
  const currentTaskId = ref<string | null>(null)
  const currentStep = ref<string>('')
  const progress = ref<number>(0)
  const log = ref<string>('')
  const nginxUrl = ref<string | null>(null)
  const nodeStatus = ref<NodeStatus | null>(null)
  const nginxStatus = ref<NginxStatus | null>(null)

  let ws: WebSocket | null = null
  let logCallback: ((text: string) => void) | null = null
  let pingTimer: ReturnType<typeof setInterval> | null = null

  function setLogCallback(cb: (text: string) => void) {
    logCallback = cb
  }

  function pipeToTerminal(text: string) {
    if (logCallback) {
      logCallback(text)
    }
  }

  async function checkEnvironment(account_alias: string, project_path: string): Promise<EnvironmentCheckResult> {
    const res = await request.get<EnvironmentCheckResult>('/deploy/vite/check', {
      params: { account_alias, project_path },
    })
    nodeStatus.value = res.node || null
    nginxStatus.value = res.nginx || null
    return res
  }

  async function startDeploy(data: DeployParams): Promise<TaskStatus> {
    deployStatus.value = 'running'
    log.value = ''
    currentStep.value = ''
    progress.value = 0
    nginxUrl.value = null
    disconnectWebSocket()

    try {
      const res = await request.post<TaskStatus>('/deploy/vite/deploy', {
        account_alias: data.account_alias,
        project_alias: data.project_alias,
        project_path: data.project_path,
        node_version: data.node_version || '20',
        nginx_port: data.nginx_port || 8080,
        build_command: data.build_command || 'npm run build',
        force: data.force || false,
      })
      currentTaskId.value = res.task_id
      connectWebSocket(res.task_id)
      return res
    } catch (e) {
      deployStatus.value = 'failed'
      pipeToTerminal(`\r\n\x1b[31m启动部署失败: ${e}\x1b[0m\r\n`)
      throw e
    }
  }

  async function startStep(step: 'setup' | 'install-deps' | 'build' | 'nginx', data: StepParams): Promise<TaskStatus> {
    deployStatus.value = 'running'
    log.value = ''
    currentStep.value = step
    progress.value = 0
    disconnectWebSocket()

    const endpointMap = {
      setup: '/deploy/vite/setup',
      'install-deps': '/deploy/vite/install-deps',
      build: '/deploy/vite/build',
      nginx: '/deploy/vite/nginx',
    }

    try {
      const payload: Record<string, any> = {
        account_alias: data.account_alias,
        project_path: data.project_path,
      }
      if (step === 'setup' && data.node_version) payload.node_version = data.node_version
      if (step === 'install-deps') payload.force = data.force || false
      if (step === 'build' && data.build_command) payload.build_command = data.build_command
      if (step === 'nginx') {
        payload.project_alias = data.project_alias
        payload.port = data.port || 8080
      }

      const res = await request.post<TaskStatus>(endpointMap[step], payload)
      currentTaskId.value = res.task_id
      connectWebSocket(res.task_id)
      return res
    } catch (e) {
      deployStatus.value = 'failed'
      pipeToTerminal(`\r\n\x1b[31m启动步骤 ${step} 失败: ${e}\x1b[0m\r\n`)
      throw e
    }
  }

  async function stopDeploy() {
    if (currentTaskId.value) {
      try {
        await request.post('/deploy/vite/stop', { task_id: currentTaskId.value })
      } catch (e) {
        pipeToTerminal(`\r\n\x1b[33m停止请求发送失败: ${e}\x1b[0m\r\n`)
      }
    }
    disconnectWebSocket()
    deployStatus.value = 'stopped'
    currentTaskId.value = null
    currentStep.value = ''
    progress.value = 0
    pipeToTerminal('\r\n\x1b[33m部署已停止\x1b[0m\r\n')
  }

  function connectWebSocket(taskId: string) {
    disconnectWebSocket()
    const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:'
    const url = `${protocol}//${location.host}/api/deploy/vite/ws/logs/${encodeURIComponent(taskId)}`
    ws = new WebSocket(url)

    ws.onopen = () => {
      pingTimer = setInterval(() => {
        if (ws && ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ type: 'ping' }))
        }
      }, 30000)
    }

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data)
        if (msg.type === 'pong') return
        if (msg.type === 'error') {
          pipeToTerminal(`\r\n\x1b[31mWebSocket 错误: ${msg.message}\x1b[0m\r\n`)
          return
        }
        if (msg.type === 'task_info') {
          const data = msg.data as TaskStatus
          currentTaskId.value = data.task_id
          currentStep.value = data.step
          progress.value = Math.round(data.progress * 100)
          log.value = data.log
          if (data.url) nginxUrl.value = data.url
          return
        }
        if (msg.type === 'log_update') {
          const data = msg.data as TaskStatus
          currentStep.value = data.step
          progress.value = Math.round(data.progress * 100)
          if (data.log && data.log.length > log.value.length) {
            const newChunk = data.log.substring(log.value.length)
            log.value = data.log
            pipeToTerminal(newChunk)
          }
          if (data.url) nginxUrl.value = data.url

          if (data.status === 'completed') {
            deployStatus.value = 'completed'
            disconnectWebSocket()
            pipeToTerminal(`\r\n\x1b[32m部署完成${data.url ? `，访问地址: ${data.url}` : ''}\x1b[0m\r\n`)
          } else if (data.status === 'failed') {
            deployStatus.value = 'failed'
            disconnectWebSocket()
            pipeToTerminal(`\r\n\x1b[31m部署失败: ${data.message || ''}\x1b[0m\r\n`)
          } else if (data.status === 'stopped') {
            deployStatus.value = 'stopped'
            disconnectWebSocket()
            pipeToTerminal('\r\n\x1b[33m部署已停止\x1b[0m\r\n')
          }
        }
      } catch {
        // Ignore parse errors
      }
    }

    ws.onclose = () => {
      if (pingTimer) {
        clearInterval(pingTimer)
        pingTimer = null
      }
      ws = null
    }

    ws.onerror = () => {
      pipeToTerminal('\r\n\x1b[31mWebSocket 连接错误\x1b[0m\r\n')
      if (pingTimer) {
        clearInterval(pingTimer)
        pingTimer = null
      }
      ws = null
    }
  }

  function disconnectWebSocket() {
    if (pingTimer) {
      clearInterval(pingTimer)
      pingTimer = null
    }
    if (ws) {
      ws.close()
      ws = null
    }
  }

  async function fetchStatus(taskId?: string): Promise<TaskStatus | null> {
    const id = taskId || currentTaskId.value
    if (!id) return null
    try {
      const res = await request.get<TaskStatus>(`/deploy/vite/status/${id}`)
      currentStep.value = res.step
      progress.value = Math.round(res.progress * 100)
      if (res.log && res.log.length > log.value.length) {
        const newChunk = res.log.substring(log.value.length)
        log.value = res.log
        pipeToTerminal(newChunk)
      }
      if (res.url) nginxUrl.value = res.url
      return res
    } catch (e) {
      console.error('Failed to fetch task status:', e)
      return null
    }
  }

  function waitForCompletion(): Promise<'completed' | 'failed' | 'stopped'> {
    return new Promise((resolve) => {
      const check = () => {
        const s = deployStatus.value
        if (s === 'completed') return resolve('completed')
        if (s === 'failed') return resolve('failed')
        if (s === 'stopped') return resolve('stopped')
        setTimeout(check, 200)
      }
      check()
    })
  }

  function reset() {
    disconnectWebSocket()
    deployStatus.value = 'idle'
    currentTaskId.value = null
    currentStep.value = ''
    progress.value = 0
    log.value = ''
    nginxUrl.value = null
    nodeStatus.value = null
    nginxStatus.value = null
    logCallback = null
  }

  return {
    deployStatus,
    currentTaskId,
    currentStep,
    progress,
    log,
    nginxUrl,
    nodeStatus,
    nginxStatus,
    setLogCallback,
    pipeToTerminal,
    checkEnvironment,
    startDeploy,
    startStep,
    stopDeploy,
    connectWebSocket,
    disconnectWebSocket,
    fetchStatus,
    waitForCompletion,
    reset,
  }
})
