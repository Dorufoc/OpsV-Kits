/**
 * Vite Deploy Store 单元测试
 * 测试部署步骤、WebSocket 连接、任务状态跟踪
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useViteDeployStore } from '@/stores/viteDeployStore'
import { request } from '@/api'

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

describe('Vite Deploy Store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  describe('状态初始化', () => {
    it('应该正确初始化 deployStatus 为 idle', () => {
      const store = useViteDeployStore()
      expect(store.deployStatus).toBe('idle')
    })

    it('应该正确初始化 currentTaskId 为 null', () => {
      const store = useViteDeployStore()
      expect(store.currentTaskId).toBeNull()
    })

    it('应该正确初始化 currentStep 为空字符串', () => {
      const store = useViteDeployStore()
      expect(store.currentStep).toBe('')
    })

    it('应该正确初始化 progress 为 0', () => {
      const store = useViteDeployStore()
      expect(store.progress).toBe(0)
    })

    it('应该正确初始化 log 为空字符串', () => {
      const store = useViteDeployStore()
      expect(store.log).toBe('')
    })

    it('应该正确初始化 nginxUrl 为 null', () => {
      const store = useViteDeployStore()
      expect(store.nginxUrl).toBeNull()
    })

    it('应该正确初始化 nodeStatus 为 null', () => {
      const store = useViteDeployStore()
      expect(store.nodeStatus).toBeNull()
    })

    it('应该正确初始化 nginxStatus 为 null', () => {
      const store = useViteDeployStore()
      expect(store.nginxStatus).toBeNull()
    })
  })

  describe('setLogCallback', () => {
    it('应该设置日志回调函数', () => {
      const store = useViteDeployStore()
      const callback = vi.fn()
      store.setLogCallback(callback)

      store.pipeToTerminal('test log')
      expect(callback).toHaveBeenCalledWith('test log')
    })
  })

  describe('pipeToTerminal', () => {
    it('有回调时应该调用日志回调', () => {
      const store = useViteDeployStore()
      const callback = vi.fn()
      store.setLogCallback(callback)

      store.pipeToTerminal('deploy log')

      expect(callback).toHaveBeenCalledWith('deploy log')
    })

    it('没有回调时不应该报错', () => {
      const store = useViteDeployStore()
      expect(() => store.pipeToTerminal('deploy log')).not.toThrow()
    })
  })

  describe('checkEnvironment', () => {
    it('应该获取环境检查结果', async () => {
      const mockResult = {
        account_alias: 'test',
        project_path: '/path',
        node: { installed: true, version: '20.10.0' },
        nginx: { installed: true, running: true },
        vite: { installed: true },
        framework: { type: 'vue' },
        all_ready: true,
      }
      mockRequestResolved(mockResult)

      const store = useViteDeployStore()
      const result = await store.checkEnvironment('test', '/path')

      expect(result).toEqual(mockResult)
      expect(store.nodeStatus).toEqual({ installed: true, version: '20.10.0' })
      expect(store.nginxStatus).toEqual({ installed: true, running: true })
    })

    it('应该调用正确的 API 端点', async () => {
      mockRequestResolved({})

      const store = useViteDeployStore()
      await store.checkEnvironment('myaccount', '/my/path')

      expect(request.get).toHaveBeenCalledWith('/deploy/vite/check', {
        params: { account_alias: 'myaccount', project_path: '/my/path' },
      })
    })

    it('node 为 null 时应该设置 nodeStatus 为 null', async () => {
      mockRequestResolved({ node: null, nginx: null })

      const store = useViteDeployStore()
      await store.checkEnvironment('test', '/path')

      expect(store.nodeStatus).toBeNull()
      expect(store.nginxStatus).toBeNull()
    })
  })

  describe('startDeploy', () => {
    it('应该设置 deployStatus 为 running', async () => {
      mockRequestResolved({ task_id: 'task-123' })

      const store = useViteDeployStore()
      await store.startDeploy({
        account_alias: 'test',
        project_alias: 'myproj',
        project_path: '/path',
      })

      expect(store.deployStatus).toBe('running')
    })

    it('应该清空日志和进度', async () => {
      const store = useViteDeployStore()
      store.log = 'old logs'
      store.progress = 50
      store.currentStep = 'build'

      mockRequestResolved({ task_id: 'task-123' })
      await store.startDeploy({
        account_alias: 'test',
        project_alias: 'myproj',
        project_path: '/path',
      })

      expect(store.log).toBe('')
      expect(store.progress).toBe(0)
      expect(store.currentStep).toBe('')
      expect(store.nginxUrl).toBeNull()
    })

    it('应该设置 currentTaskId', async () => {
      mockRequestResolved({ task_id: 'task-123' })

      const store = useViteDeployStore()
      await store.startDeploy({
        account_alias: 'test',
        project_alias: 'myproj',
        project_path: '/path',
      })

      expect(store.currentTaskId).toBe('task-123')
    })

    it('应该使用默认值', async () => {
      mockRequestResolved({ task_id: 'task-123' })

      const store = useViteDeployStore()
      await store.startDeploy({
        account_alias: 'test',
        project_alias: 'myproj',
        project_path: '/path',
      })

      expect(request.post).toHaveBeenCalledWith('/deploy/vite/deploy', {
        account_alias: 'test',
        project_alias: 'myproj',
        project_path: '/path',
        node_version: '20',
        nginx_port: 8080,
        build_command: 'npm run build',
        force: false,
      })
    })

    it('失败时应该设置 deployStatus 为 failed', async () => {
      mockRequestRejected(new Error('Deploy failed'))

      const store = useViteDeployStore()
      await expect(store.startDeploy({
        account_alias: 'test',
        project_alias: 'myproj',
        project_path: '/path',
      })).rejects.toThrow()

      expect(store.deployStatus).toBe('failed')
    })
  })

  describe('startStep', () => {
    it('setup 步骤应该调用 /deploy/vite/setup', async () => {
      mockRequestResolved({ task_id: 'task-123' })

      const store = useViteDeployStore()
      await store.startStep('setup', {
        account_alias: 'test',
        project_path: '/path',
        node_version: '20',
      })

      expect(request.post).toHaveBeenCalledWith('/deploy/vite/setup', {
        account_alias: 'test',
        project_path: '/path',
        node_version: '20',
      })
    })

    it('install-deps 步骤应该调用 /deploy/vite/install-deps', async () => {
      mockRequestResolved({ task_id: 'task-123' })

      const store = useViteDeployStore()
      await store.startStep('install-deps', {
        account_alias: 'test',
        project_path: '/path',
        force: true,
      })

      expect(request.post).toHaveBeenCalledWith('/deploy/vite/install-deps', {
        account_alias: 'test',
        project_path: '/path',
        force: true,
      })
    })

    it('build 步骤应该调用 /deploy/vite/build', async () => {
      mockRequestResolved({ task_id: 'task-123' })

      const store = useViteDeployStore()
      await store.startStep('build', {
        account_alias: 'test',
        project_path: '/path',
        build_command: 'npm run build',
      })

      expect(request.post).toHaveBeenCalledWith('/deploy/vite/build', {
        account_alias: 'test',
        project_path: '/path',
        build_command: 'npm run build',
      })
    })

    it('nginx 步骤应该调用 /deploy/vite/nginx', async () => {
      mockRequestResolved({ task_id: 'task-123' })

      const store = useViteDeployStore()
      await store.startStep('nginx', {
        account_alias: 'test',
        project_path: '/path',
        project_alias: 'myproj',
        port: 8080,
      })

      expect(request.post).toHaveBeenCalledWith('/deploy/vite/nginx', {
        account_alias: 'test',
        project_path: '/path',
        project_alias: 'myproj',
        port: 8080,
      })
    })

    it('应该设置 currentStep', async () => {
      mockRequestResolved({ task_id: 'task-123' })

      const store = useViteDeployStore()
      await store.startStep('build', {
        account_alias: 'test',
        project_path: '/path',
      })

      expect(store.currentStep).toBe('build')
    })

    it('失败时应该设置 deployStatus 为 failed', async () => {
      mockRequestRejected(new Error('Step failed'))

      const store = useViteDeployStore()
      await expect(store.startStep('build', {
        account_alias: 'test',
        project_path: '/path',
      })).rejects.toThrow()

      expect(store.deployStatus).toBe('failed')
    })
  })

  describe('stopDeploy', () => {
    it('应该调用停止 API', async () => {
      mockRequestResolved({})

      const store = useViteDeployStore()
      store.currentTaskId = 'task-123'
      await store.stopDeploy()

      expect(request.post).toHaveBeenCalledWith('/deploy/vite/stop', { task_id: 'task-123' })
    })

    it('应该设置 deployStatus 为 stopped', async () => {
      mockRequestResolved({})

      const store = useViteDeployStore()
      store.deployStatus = 'running'
      store.currentTaskId = 'task-123'
      await store.stopDeploy()

      expect(store.deployStatus).toBe('stopped')
    })

    it('应该清空状态', async () => {
      mockRequestResolved({})

      const store = useViteDeployStore()
      store.currentTaskId = 'task-123'
      store.currentStep = 'build'
      store.progress = 50
      await store.stopDeploy()

      expect(store.currentTaskId).toBeNull()
      expect(store.currentStep).toBe('')
      expect(store.progress).toBe(0)
    })

    it('API 失败时不应该抛出异常', async () => {
      mockRequestRejected(new Error('Stop failed'))

      const store = useViteDeployStore()
      store.currentTaskId = 'task-123'
      await expect(store.stopDeploy()).resolves.toBeUndefined()
    })

    it('没有 currentTaskId 时应该只更新状态', async () => {
      const store = useViteDeployStore()
      store.deployStatus = 'running'
      await store.stopDeploy()

      expect(store.deployStatus).toBe('stopped')
      expect(request.post).not.toHaveBeenCalled()
    })
  })

  describe('connectWebSocket', () => {
    let mockWebSocket: any

    beforeEach(() => {
      mockWebSocket = {
        onopen: null,
        onmessage: null,
        onclose: null,
        onerror: null,
        close: vi.fn(),
        send: vi.fn(),
        readyState: 1,
      }
      const MockWebSocket = vi.fn(() => mockWebSocket)
      ;(MockWebSocket as any).CONNECTING = 0
      ;(MockWebSocket as any).OPEN = 1
      ;(MockWebSocket as any).CLOSING = 2
      ;(MockWebSocket as any).CLOSED = 3
      vi.stubGlobal('WebSocket', MockWebSocket)
    })

    afterEach(() => {
      vi.unstubAllGlobals()
    })

    it('应该创建 WebSocket 连接', () => {
      const store = useViteDeployStore()
      store.connectWebSocket('task-123')

      const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:'
      expect(WebSocket).toHaveBeenCalledWith(
        `${protocol}//${location.host}/api/deploy/vite/ws/logs/task-123`
      )
    })

    it('收到 task_info 时应该更新状态', () => {
      const store = useViteDeployStore()
      store.connectWebSocket('task-123')

      const msg = {
        type: 'task_info',
        data: {
          task_id: 'task-123',
          step: 'build',
          progress: 0.75,
          log: 'building...',
          url: 'http://localhost:8080',
        },
      }
      mockWebSocket.onmessage({ data: JSON.stringify(msg) })

      expect(store.currentStep).toBe('build')
      expect(store.progress).toBe(75)
      expect(store.log).toBe('building...')
      expect(store.nginxUrl).toBe('http://localhost:8080')
    })

    it('收到 log_update 且 status 为 completed 时应该更新状态并断开连接', () => {
      const store = useViteDeployStore()
      store.connectWebSocket('task-123')

      const msg = {
        type: 'log_update',
        data: {
          step: 'deploy',
          progress: 1.0,
          log: 'done',
          status: 'completed',
        },
      }
      mockWebSocket.onmessage({ data: JSON.stringify(msg) })

      expect(store.deployStatus).toBe('completed')
    })

    it('收到 log_update 且 status 为 failed 时应该设置失败状态', () => {
      const store = useViteDeployStore()
      store.connectWebSocket('task-123')

      const msg = {
        type: 'log_update',
        data: {
          step: 'build',
          progress: 0.5,
          log: 'error',
          status: 'failed',
          message: 'Build failed',
        },
      }
      mockWebSocket.onmessage({ data: JSON.stringify(msg) })

      expect(store.deployStatus).toBe('failed')
    })

    it('收到 log_update 且 status 为 stopped 时应该设置停止状态', () => {
      const store = useViteDeployStore()
      store.connectWebSocket('task-123')

      const msg = {
        type: 'log_update',
        data: {
          step: 'build',
          progress: 0.3,
          log: '',
          status: 'stopped',
        },
      }
      mockWebSocket.onmessage({ data: JSON.stringify(msg) })

      expect(store.deployStatus).toBe('stopped')
    })

    it('收到 pong 消息时应该忽略', () => {
      const store = useViteDeployStore()
      store.connectWebSocket('task-123')
      store.progress = 50

      mockWebSocket.onmessage({ data: JSON.stringify({ type: 'pong' }) })

      expect(store.progress).toBe(50)
    })

    it('收到 error 消息时不应该更新状态', () => {
      const store = useViteDeployStore()
      store.connectWebSocket('task-123')
      store.deployStatus = 'running'

      mockWebSocket.onmessage({ data: JSON.stringify({ type: 'error', message: 'err' }) })

      expect(store.deployStatus).toBe('running')
    })

    it('已有连接时应该先断开', () => {
      const store = useViteDeployStore()
      const closeSpy = vi.fn()
      mockWebSocket.close = closeSpy

      store.connectWebSocket('task-1')
      store.connectWebSocket('task-2')

      expect(closeSpy).toHaveBeenCalled()
    })
  })

  describe('fetchStatus', () => {
    it('应该获取任务状态', async () => {
      const mockStatus = {
        task_id: 'task-123',
        step: 'build',
        progress: 0.5,
        log: 'building...',
        status: 'running',
      }
      mockRequestResolved(mockStatus)

      const store = useViteDeployStore()
      const result = await store.fetchStatus('task-123')

      expect(result).toEqual(mockStatus)
      expect(store.currentStep).toBe('build')
      expect(store.progress).toBe(50)
    })

    it('没有 taskId 时应该返回 null', async () => {
      const store = useViteDeployStore()
      const result = await store.fetchStatus()
      expect(result).toBeNull()
    })

    it('请求失败时应该返回 null', async () => {
      mockRequestRejected(new Error('Not found'))

      const store = useViteDeployStore()
      const result = await store.fetchStatus('nonexistent')

      expect(result).toBeNull()
    })
  })

  describe('waitForCompletion', () => {
    it('deployStatus 为 completed 时应该返回 completed', async () => {
      const store = useViteDeployStore()
      store.deployStatus = 'completed'

      const result = await store.waitForCompletion()
      expect(result).toBe('completed')
    })

    it('deployStatus 为 failed 时应该返回 failed', async () => {
      const store = useViteDeployStore()
      store.deployStatus = 'failed'

      const result = await store.waitForCompletion()
      expect(result).toBe('failed')
    })

    it('deployStatus 为 stopped 时应该返回 stopped', async () => {
      const store = useViteDeployStore()
      store.deployStatus = 'stopped'

      const result = await store.waitForCompletion()
      expect(result).toBe('stopped')
    })
  })

  describe('reset', () => {
    it('应该重置所有状态', () => {
      const store = useViteDeployStore()
      store.deployStatus = 'running'
      store.currentTaskId = 'task-123'
      store.currentStep = 'build'
      store.progress = 50
      store.log = 'logs'
      store.nginxUrl = 'http://localhost'
      store.nodeStatus = { installed: true, version: '20' }
      store.nginxStatus = { installed: true, running: true }

      store.reset()

      expect(store.deployStatus).toBe('idle')
      expect(store.currentTaskId).toBeNull()
      expect(store.currentStep).toBe('')
      expect(store.progress).toBe(0)
      expect(store.log).toBe('')
      expect(store.nginxUrl).toBeNull()
      expect(store.nodeStatus).toBeNull()
      expect(store.nginxStatus).toBeNull()
    })
  })
})
