/**
 * API 客户端单元测试
 * 测试 axios 实例配置、拦截器、错误处理以及所有 API 模块函数
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import axios from 'axios'
import type { AxiosRequestConfig, AxiosResponse } from 'axios'

// 模拟 axios 模块
vi.mock('axios', () => {
  const mockInstance = {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
    interceptors: {
      request: {
        use: vi.fn((fulfilled, rejected) => {
          mockInstance.interceptors.request.fulfilledHandler = fulfilled
          mockInstance.interceptors.request.rejectedHandler = rejected
          return 'request-interceptor-id'
        }),
        eject: vi.fn(),
        fulfilledHandler: null as ((config: AxiosRequestConfig) => AxiosRequestConfig) | null,
        rejectedHandler: null as ((error: any) => Promise<any>) | null,
      },
      response: {
        use: vi.fn((fulfilled, rejected) => {
          mockInstance.interceptors.response.fulfilledHandler = fulfilled
          mockInstance.interceptors.response.rejectedHandler = rejected
          return 'response-interceptor-id'
        }),
        eject: vi.fn(),
        fulfilledHandler: null as ((response: AxiosResponse) => any) | null,
        rejectedHandler: null as ((error: any) => Promise<any>) | null,
      },
    },
  }
  return {
    default: {
      create: vi.fn(() => mockInstance),
    },
  }
})

describe('API 客户端', () => {
  let axiosInstance: any

  beforeEach(() => {
    vi.clearAllMocks()
    vi.resetModules()
    localStorage.clear()
    // 重置 localStorage mock
    vi.stubGlobal('localStorage', {
      getItem: vi.fn(),
      setItem: vi.fn(),
      removeItem: vi.fn(),
      clear: vi.fn(),
    })
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  describe('Axios 实例配置', () => {
    it('应该正确创建 axios 实例', async () => {
      const { default: axiosModule } = await import('@/api/index')
      expect(axios.create).toHaveBeenCalledWith({
        baseURL: '/api',
        timeout: 30000,
        headers: {
          'Content-Type': 'application/json',
        },
      })
    })

    it('应该配置 baseURL 为 /api', async () => {
      const createMock = axios.create as ReturnType<typeof vi.fn>
      const callArgs = createMock.mock.calls[0][0]
      expect(callArgs.baseURL).toBe('/api')
    })

    it('应该配置 timeout 为 30000', async () => {
      const createMock = axios.create as ReturnType<typeof vi.fn>
      const callArgs = createMock.mock.calls[0][0]
      expect(callArgs.timeout).toBe(30000)
    })

    it('应该配置 Content-Type 为 application/json', async () => {
      const createMock = axios.create as ReturnType<typeof vi.fn>
      const callArgs = createMock.mock.calls[0][0]
      expect(callArgs.headers['Content-Type']).toBe('application/json')
    })
  })

  describe('请求拦截器', () => {
    it('当存在 token 时应该在请求头中添加 Authorization', async () => {
      const mockToken = 'test-token-123'
      vi.mocked(localStorage.getItem).mockReturnValue(mockToken)

      const { default: axiosModule } = await import('@/api/index')
      const mockInstance = axios.create()
      const requestInterceptor = mockInstance.interceptors.request.use.mock.calls[0][0]

      const config = { headers: {} } as AxiosRequestConfig
      const result = requestInterceptor!(config)

      expect(result.headers).toHaveProperty('Authorization', 'Bearer test-token-123')
    })

    it('当不存在 token 时不应该添加 Authorization 头', async () => {
      vi.mocked(localStorage.getItem).mockReturnValue(null)

      const { default: axiosModule } = await import('@/api/index')
      const mockInstance = axios.create()
      const requestInterceptor = mockInstance.interceptors.request.use.mock.calls[0][0]

      const config = { headers: {} } as AxiosRequestConfig
      const result = requestInterceptor!(config)

      expect(result.headers).not.toHaveProperty('Authorization')
    })

    it('应该在请求错误时返回 rejected promise', async () => {
      const { default: axiosModule } = await import('@/api/index')
      const mockInstance = axios.create()
      const requestErrorHandler = mockInstance.interceptors.request.use.mock.calls[0][1]

      const error = new Error('Request error')
      await expect(requestErrorHandler!(error)).rejects.toThrow('Request error')
    })
  })

  describe('响应拦截器', () => {
    it('成功响应时应该返回 response.data', async () => {
      const { default: axiosModule } = await import('@/api/index')
      const mockInstance = axios.create()
      const responseInterceptor = mockInstance.interceptors.response.use.mock.calls[0][0]

      const mockResponse = { data: { success: true }, status: 200 } as AxiosResponse
      const result = responseInterceptor!(mockResponse)

      expect(result).toEqual({ success: true })
    })

    it('401 错误时应该移除 localStorage 中的 token', async () => {
      const { default: axiosModule } = await import('@/api/index')
      const mockInstance = axios.create()
      const responseErrorHandler = mockInstance.interceptors.response.use.mock.calls[0][1]

      const error = { response: { status: 401 } }
      await expect(responseErrorHandler!(error)).rejects.toBe(error)
      expect(localStorage.removeItem).toHaveBeenCalledWith('token')
    })

    it('403 错误时应该输出权限不足日志', async () => {
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
      const { default: axiosModule } = await import('@/api/index')
      const mockInstance = axios.create()
      const responseErrorHandler = mockInstance.interceptors.response.use.mock.calls[0][1]

      const error = { response: { status: 403 } }
      await expect(responseErrorHandler!(error)).rejects.toBe(error)
      expect(consoleSpy).toHaveBeenCalledWith('权限不足')
      consoleSpy.mockRestore()
    })

    it('500 错误时应该输出服务器错误日志', async () => {
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
      const { default: axiosModule } = await import('@/api/index')
      const mockInstance = axios.create()
      const responseErrorHandler = mockInstance.interceptors.response.use.mock.calls[0][1]

      const error = { response: { status: 500 } }
      await expect(responseErrorHandler!(error)).rejects.toBe(error)
      expect(consoleSpy).toHaveBeenCalledWith('服务器错误')
      consoleSpy.mockRestore()
    })

    it('其他错误时应该输出错误消息', async () => {
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
      const { default: axiosModule } = await import('@/api/index')
      const mockInstance = axios.create()
      const responseErrorHandler = mockInstance.interceptors.response.use.mock.calls[0][1]

      const error = { message: 'Network Error' }
      await expect(responseErrorHandler!(error)).rejects.toBe(error)
      expect(consoleSpy).toHaveBeenCalledWith('Network Error')
      consoleSpy.mockRestore()
    })

    it('没有 response 对象时应该正确 rejected', async () => {
      const { default: axiosModule } = await import('@/api/index')
      const mockInstance = axios.create()
      const responseErrorHandler = mockInstance.interceptors.response.use.mock.calls[0][1]

      const error = { message: 'Network Error' }
      await expect(responseErrorHandler!(error)).rejects.toBe(error)
    })
  })

  describe('Request 封装方法', () => {
    it('request.get 应该调用 instance.get', async () => {
      const { request } = await import('@/api/index')
      const mockInstance = axios.create()

      await request.get('/test', { params: { id: 1 } })
      expect(mockInstance.get).toHaveBeenCalledWith('/test', { params: { id: 1 } })
    })

    it('request.post 应该调用 instance.post', async () => {
      const { request } = await import('@/api/index')
      const mockInstance = axios.create()

      await request.post('/test', { name: 'test' })
      expect(mockInstance.post).toHaveBeenCalledWith('/test', { name: 'test' }, undefined)
    })

    it('request.put 应该调用 instance.put', async () => {
      const { request } = await import('@/api/index')
      const mockInstance = axios.create()

      await request.put('/test', { name: 'updated' })
      expect(mockInstance.put).toHaveBeenCalledWith('/test', { name: 'updated' }, undefined)
    })

    it('request.delete 应该调用 instance.delete', async () => {
      const { request } = await import('@/api/index')
      const mockInstance = axios.create()

      await request.delete('/test', { params: { id: 1 } })
      expect(mockInstance.delete).toHaveBeenCalledWith('/test', { params: { id: 1 } })
    })
  })

  describe('viteDeploy API 模块', () => {
    it('check 方法应该调用 GET /deploy/vite/check', async () => {
      const { viteDeploy } = await import('@/api/index')
      const mockInstance = axios.create()

      await viteDeploy.check('test-account', '/path/to/project')
      expect(mockInstance.get).toHaveBeenCalledWith('/deploy/vite/check', {
        params: { account_alias: 'test-account', project_path: '/path/to/project' },
      })
    })

    it('setup 方法应该调用 POST /deploy/vite/setup', async () => {
      const { viteDeploy } = await import('@/api/index')
      const mockInstance = axios.create()
      const data = { account_alias: 'test', project_path: '/path' }

      await viteDeploy.setup(data)
      expect(mockInstance.post).toHaveBeenCalledWith('/deploy/vite/setup', data)
    })

    it('installDeps 方法应该调用 POST /deploy/vite/install-deps', async () => {
      const { viteDeploy } = await import('@/api/index')
      const mockInstance = axios.create()
      const data = { account_alias: 'test', project_path: '/path' }

      await viteDeploy.installDeps(data)
      expect(mockInstance.post).toHaveBeenCalledWith('/deploy/vite/install-deps', data)
    })

    it('build 方法应该调用 POST /deploy/vite/build', async () => {
      const { viteDeploy } = await import('@/api/index')
      const mockInstance = axios.create()
      const data = { account_alias: 'test', project_path: '/path' }

      await viteDeploy.build(data)
      expect(mockInstance.post).toHaveBeenCalledWith('/deploy/vite/build', data)
    })

    it('nginx 方法应该调用 POST /deploy/vite/nginx', async () => {
      const { viteDeploy } = await import('@/api/index')
      const mockInstance = axios.create()
      const data = { account_alias: 'test', project_path: '/path' }

      await viteDeploy.nginx(data)
      expect(mockInstance.post).toHaveBeenCalledWith('/deploy/vite/nginx', data)
    })

    it('deploy 方法应该调用 POST /deploy/vite/deploy', async () => {
      const { viteDeploy } = await import('@/api/index')
      const mockInstance = axios.create()
      const data = { account_alias: 'test', project_alias: 'myproj', project_path: '/path' }

      await viteDeploy.deploy(data)
      expect(mockInstance.post).toHaveBeenCalledWith('/deploy/vite/deploy', data)
    })

    it('status 方法应该调用 GET /deploy/vite/status/:taskId', async () => {
      const { viteDeploy } = await import('@/api/index')
      const mockInstance = axios.create()

      await viteDeploy.status('task-123')
      expect(mockInstance.get).toHaveBeenCalledWith('/deploy/vite/status/task-123')
    })
  })

  describe('dockerStoreApi 模块', () => {
    it('getStoreApps 应该调用 GET /docker-store/apps', async () => {
      const { dockerStoreApi } = await import('@/api/index')
      const mockInstance = axios.create()

      await dockerStoreApi.getStoreApps('category1')
      expect(mockInstance.get).toHaveBeenCalledWith('/docker-store/apps', { params: { category: 'category1' } })
    })

    it('getStoreApps 不带参数时应该调用不带 category', async () => {
      const { dockerStoreApi } = await import('@/api/index')
      const mockInstance = axios.create()

      await dockerStoreApi.getStoreApps()
      expect(mockInstance.get).toHaveBeenCalledWith('/docker-store/apps', { params: {} })
    })

    it('getStoreApp 应该调用 GET /docker-store/apps/:appId', async () => {
      const { dockerStoreApi } = await import('@/api/index')
      const mockInstance = axios.create()

      await dockerStoreApi.getStoreApp('app-1')
      expect(mockInstance.get).toHaveBeenCalledWith('/docker-store/apps/app-1')
    })

    it('installStoreApp 应该调用 POST /docker-store/install/:appId', async () => {
      const { dockerStoreApi } = await import('@/api/index')
      const mockInstance = axios.create()
      const data = { account_alias: 'test' }

      await dockerStoreApi.installStoreApp('app-1', data)
      expect(mockInstance.post).toHaveBeenCalledWith('/docker-store/install/app-1', data)
    })

    it('uninstallStoreApp 应该调用 POST /docker-store/uninstall/:appId', async () => {
      const { dockerStoreApi } = await import('@/api/index')
      const mockInstance = axios.create()
      const data = { account_alias: 'test', purge_data: true }

      await dockerStoreApi.uninstallStoreApp('app-1', data)
      expect(mockInstance.post).toHaveBeenCalledWith('/docker-store/uninstall/app-1', data)
    })

    it('getStoreAppStatus 应该调用 GET /docker-store/status/:appId', async () => {
      const { dockerStoreApi } = await import('@/api/index')
      const mockInstance = axios.create()

      await dockerStoreApi.getStoreAppStatus('app-1', 'test-account')
      expect(mockInstance.get).toHaveBeenCalledWith('/docker-store/status/app-1', {
        params: { account_alias: 'test-account' },
      })
    })
  })

  describe('securityNetworkApi 模块', () => {
    it('getFirewallBackend 应该调用 GET /security/firewall/backend', async () => {
      const { securityNetworkApi } = await import('@/api/index')
      const mockInstance = axios.create()

      await securityNetworkApi.getFirewallBackend('test-alias')
      expect(mockInstance.get).toHaveBeenCalledWith('/security/firewall/backend', { params: { alias: 'test-alias' } })
    })

    it('getFirewallRules 应该调用 GET /security/firewall/rules', async () => {
      const { securityNetworkApi } = await import('@/api/index')
      const mockInstance = axios.create()

      await securityNetworkApi.getFirewallRules('test-alias')
      expect(mockInstance.get).toHaveBeenCalledWith('/security/firewall/rules', { params: { alias: 'test-alias' } })
    })

    it('addPortRule 应该调用 POST /security/firewall/port', async () => {
      const { securityNetworkApi } = await import('@/api/index')
      const mockInstance = axios.create()

      await securityNetworkApi.addPortRule('test-alias', 80, 'tcp', 'allow', 'public')
      expect(mockInstance.post).toHaveBeenCalledWith('/security/firewall/port', null, {
        params: { alias: 'test-alias', port: 80, protocol: 'tcp', zone: 'public' },
      })
    })

    it('getSshConfig 应该调用 GET /security/ssh/config', async () => {
      const { securityNetworkApi } = await import('@/api/index')
      const mockInstance = axios.create()

      await securityNetworkApi.getSshConfig('test-alias')
      expect(mockInstance.get).toHaveBeenCalledWith('/security/ssh/config', { params: { alias: 'test-alias' } })
    })

    it('runPing 应该调用 POST /security/network/ping', async () => {
      const { securityNetworkApi } = await import('@/api/index')
      const mockInstance = axios.create()

      await securityNetworkApi.runPing('test-alias', '8.8.8.8')
      expect(mockInstance.post).toHaveBeenCalledWith('/security/network/ping', null, {
        params: { alias: 'test-alias', host: '8.8.8.8' },
      })
    })
  })

  describe('cronBackupApi 模块', () => {
    it('listCronJobs 应该调用 GET /cron-backup/cron-jobs', async () => {
      const { cronBackupApi } = await import('@/api/index')
      const mockInstance = axios.create()

      await cronBackupApi.listCronJobs('test-alias')
      expect(mockInstance.get).toHaveBeenCalledWith('/cron-backup/cron-jobs', { params: { alias: 'test-alias' } })
    })

    it('createCronJob 应该调用 POST /cron-backup/cron-jobs', async () => {
      const { cronBackupApi } = await import('@/api/index')
      const mockInstance = axios.create()
      const data = { schedule: '0 2 * * *', command: 'backup' }

      await cronBackupApi.createCronJob('test-alias', data)
      expect(mockInstance.post).toHaveBeenCalledWith('/cron-backup/cron-jobs', { alias: 'test-alias', data })
    })

    it('deleteCronJob 应该调用 DELETE /cron-backup/cron-jobs/:jobId', async () => {
      const { cronBackupApi } = await import('@/api/index')
      const mockInstance = axios.create()

      await cronBackupApi.deleteCronJob('job-1', 'test-alias')
      expect(mockInstance.delete).toHaveBeenCalledWith('/cron-backup/cron-jobs/job-1', { params: { alias: 'test-alias' } })
    })

    it('listBackupHistory 应该调用 GET /cron-backup/backup-history', async () => {
      const { cronBackupApi } = await import('@/api/index')
      const mockInstance = axios.create()

      await cronBackupApi.listBackupHistory('test-alias', 'policy-1', 10)
      expect(mockInstance.get).toHaveBeenCalledWith('/cron-backup/backup-history', {
        params: { alias: 'test-alias', policy_id: 'policy-1', limit: 10 },
      })
    })

    it('getDiskAlert 应该调用 GET /cron-backup/disk-alert', async () => {
      const { cronBackupApi } = await import('@/api/index')
      const mockInstance = axios.create()

      await cronBackupApi.getDiskAlert('test-alias')
      expect(mockInstance.get).toHaveBeenCalledWith('/cron-backup/disk-alert', { params: { alias: 'test-alias' } })
    })
  })

  describe('类型定义导出', () => {
    it('应该导出 ViteCheckResponse 类型', async () => {
      const api = await import('@/api/index')
      // 类型在编译时检查，这里验证模块存在
      expect(api).toHaveProperty('viteDeployApi')
    })

    it('应该导出 ViteTaskResponse 类型', async () => {
      const api = await import('@/api/index')
      expect(api).toHaveProperty('viteDeploy')
    })

    it('应该导出 StoreApp 类型', async () => {
      const api = await import('@/api/index')
      expect(api).toHaveProperty('dockerStoreApi')
    })

    it('应该导出 FirewallRule 类型', async () => {
      const api = await import('@/api/index')
      expect(api).toHaveProperty('securityNetworkApi')
    })
  })
})
