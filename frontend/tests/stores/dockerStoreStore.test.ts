import { describe, it, expect, vi, beforeEach } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useDockerStoreStore } from '@/stores/dockerStoreStore'
import { useDockerStore } from '@/stores/dockerStore'
import * as api from '@/api'

const wsInstances: any[] = []

function createMockWebSocket() {
  return vi.fn().mockImplementation(function(this: any, url: string) {
    this.onopen = null
    this.onmessage = null
    this.onclose = null
    this.onerror = null
    this.close = vi.fn()
    this.send = vi.fn()
    this.readyState = 1
    this.url = url
    const self = this
    wsInstances.push(this)
    Promise.resolve().then(() => {
      if (self.onopen) self.onopen()
    })
  })
}

describe('DockerStore Store', () => {
  let dockerStore: ReturnType<typeof useDockerStore>

  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    wsInstances.length = 0
    vi.stubGlobal('WebSocket', createMockWebSocket())
    dockerStore = useDockerStore()
    dockerStore.setAccountAlias('test-server')
  })

  describe('状态初始化', () => {
    it('应该正确初始化 apps 为空数组', () => {
      const store = useDockerStoreStore()
      expect(store.apps).toEqual([])
    })

    it('应该正确初始化 currentApp 为 null', () => {
      const store = useDockerStoreStore()
      expect(store.currentApp).toBeNull()
    })

    it('应该正确初始化 appStatuses 为空对象', () => {
      const store = useDockerStoreStore()
      expect(store.appStatuses).toEqual({})
    })

    it('应该正确初始化 appSizes 为空对象', () => {
      const store = useDockerStoreStore()
      expect(store.appSizes).toEqual({})
    })

    it('应该正确初始化 imageVersionSizes 为空对象', () => {
      const store = useDockerStoreStore()
      expect(store.imageVersionSizes).toEqual({})
    })

    it('应该正确初始化 registryMirror', () => {
      const store = useDockerStoreStore()
      expect(store.registryMirror).toEqual({ enabled: false, urls: [] })
    })

    it('应该正确初始化 loading 为 false', () => {
      const store = useDockerStoreStore()
      expect(store.loading).toBe(false)
    })

    it('应该正确初始化 installing 为 false', () => {
      const store = useDockerStoreStore()
      expect(store.installing).toBe(false)
    })

    it('应该正确初始化 uninstalling 为 false', () => {
      const store = useDockerStoreStore()
      expect(store.uninstalling).toBe(false)
    })

    it('应该正确初始化 sizeLoading 为空对象', () => {
      const store = useDockerStoreStore()
      expect(store.sizeLoading).toEqual({})
    })

    it('应该正确初始化 versionSizeLoading 为空对象', () => {
      const store = useDockerStoreStore()
      expect(store.versionSizeLoading).toEqual({})
    })

    it('应该正确初始化 installProgress 为空对象', () => {
      const store = useDockerStoreStore()
      expect(store.installProgress).toEqual({})
    })

    it('应该正确初始化 installProgressPercent 为空对象', () => {
      const store = useDockerStoreStore()
      expect(store.installProgressPercent).toEqual({})
    })

    it('应该正确初始化 installProgressMessage 为空对象', () => {
      const store = useDockerStoreStore()
      expect(store.installProgressMessage).toEqual({})
    })
  })

  describe('fetchApps', () => {
    it('应该获取应用列表', async () => {
      const mockApps = [
        { id: 'app1', name: 'WordPress', icon: '', description: '', category: 'cms', require_memory: 512, versions: [], features: [], recommended_for: [], env_config: [] },
      ]
      vi.mocked(api.request.get).mockResolvedValue(mockApps as any)

      const store = useDockerStoreStore()
      const result = await store.fetchApps()

      expect(store.apps).toEqual(mockApps)
    })

    it('应该支持按分类筛选', async () => {
      vi.mocked(api.request.get).mockResolvedValue([] as any)

      const store = useDockerStoreStore()
      await store.fetchApps('cms')

      expect(api.request.get).toHaveBeenCalledWith('/docker-store/apps', {
        params: { account_alias: 'test-server', category: 'cms' },
      })
    })

    it('请求期间 loading 应该为 true', async () => {
      vi.mocked(api.request.get).mockImplementation(async () => {
        const store = useDockerStoreStore()
        expect(store.loading).toBe(true)
        return []
      })

      const store = useDockerStoreStore()
      await store.fetchApps()
      expect(store.loading).toBe(false)
    })

    it('请求失败时应该清空 apps 并恢复 loading', async () => {
      vi.mocked(api.request.get).mockRejectedValue(new Error('Network error'))

      const store = useDockerStoreStore()
      await store.fetchApps()

      expect(store.apps).toEqual([])
      expect(store.loading).toBe(false)
    })

    it('当没有 alias 时应该直接返回', async () => {
      dockerStore.setAccountAlias('')
      const store = useDockerStoreStore()
      const result = await store.fetchApps()
      expect(result).toBeUndefined()
    })
  })

  describe('getApp', () => {
    it('应该获取单个应用详情', async () => {
      const mockApp = { id: 'app1', name: 'WordPress', icon: '', description: '', category: 'cms', require_memory: 512, versions: [], features: [], recommended_for: [], env_config: [] }
      vi.mocked(api.request.get).mockResolvedValue(mockApp as any)

      const store = useDockerStoreStore()
      const result = await store.getApp('app1')

      expect(store.currentApp).toEqual(mockApp)
    })

    it('请求期间 loading 应该为 true', async () => {
      vi.mocked(api.request.get).mockImplementation(async () => {
        const store = useDockerStoreStore()
        expect(store.loading).toBe(true)
        return {}
      })

      const store = useDockerStoreStore()
      await store.getApp('app1')
      expect(store.loading).toBe(false)
    })

    it('当没有 alias 时应该直接返回', async () => {
      dockerStore.setAccountAlias('')
      const store = useDockerStoreStore()
      const result = await store.getApp('app1')
      expect(result).toBeUndefined()
    })
  })

  describe('installApp', () => {
    it('应该安装应用并刷新状态', async () => {
      vi.mocked(api.request.post).mockResolvedValue({ success: true } as any)
      vi.mocked(api.request.get).mockResolvedValue([] as any)

      const store = useDockerStoreStore()
      const formData = { port: 8080 }
      const result = await store.installApp('app1', formData)

      expect(api.request.post).toHaveBeenCalledWith('/docker-store/install/app1', {
        account_alias: 'test-server',
        port: 8080,
      })
    })

    it('安装期间 installing 应该为 true', async () => {
      vi.mocked(api.request.post).mockImplementation(async () => {
        const store = useDockerStoreStore()
        expect(store.installing).toBe(true)
        return { success: true }
      })
      vi.mocked(api.request.get).mockResolvedValue([] as any)

      const store = useDockerStoreStore()
      await store.installApp('app1', {})
      expect(store.installing).toBe(false)
    })

    it('安装失败时 installing 应该恢复为 false', async () => {
      vi.mocked(api.request.post).mockRejectedValue(new Error('Install failed'))

      const store = useDockerStoreStore()
      await expect(store.installApp('app1', {})).rejects.toThrow()
      expect(store.installing).toBe(false)
    })

    it('当没有 alias 时应该直接返回', async () => {
      dockerStore.setAccountAlias('')
      const store = useDockerStoreStore()
      const result = await store.installApp('app1', {})
      expect(result).toBeUndefined()
    })
  })

  describe('uninstallApp', () => {
    it('应该卸载应用并删除状态', async () => {
      vi.mocked(api.request.post).mockResolvedValue({ success: true } as any)

      const store = useDockerStoreStore()
      store.appStatuses = { app1: { app_id: 'app1', state: 'running' } as any }
      await store.uninstallApp('app1')

      expect(store.appStatuses.app1).toBeUndefined()
    })

    it('卸载期间 uninstalling 应该为 true', async () => {
      vi.mocked(api.request.post).mockImplementation(async () => {
        const store = useDockerStoreStore()
        expect(store.uninstalling).toBe(true)
        return {}
      })

      const store = useDockerStoreStore()
      await store.uninstallApp('app1')
      expect(store.uninstalling).toBe(false)
    })

    it('应该支持 purgeData 参数', async () => {
      vi.mocked(api.request.post).mockResolvedValue({} as any)

      const store = useDockerStoreStore()
      await store.uninstallApp('app1', true)

      expect(api.request.post).toHaveBeenCalledWith('/docker-store/uninstall/app1', {
        account_alias: 'test-server',
        purge_data: true,
      })
    })

    it('当没有 alias 时应该直接返回', async () => {
      dockerStore.setAccountAlias('')
      const store = useDockerStoreStore()
      const result = await store.uninstallApp('app1')
      expect(result).toBeUndefined()
    })
  })

  describe('fetchAppStatus', () => {
    it('应该获取单个应用状态', async () => {
      const mockStatus = { app_id: 'app1', state: 'running' as const }
      vi.mocked(api.request.get).mockResolvedValue(mockStatus as any)

      const store = useDockerStoreStore()
      const result = await store.fetchAppStatus('app1')

      expect(store.appStatuses['app1']).toEqual(mockStatus)
    })

    it('当没有 alias 时应该直接返回', async () => {
      dockerStore.setAccountAlias('')
      const store = useDockerStoreStore()
      const result = await store.fetchAppStatus('app1')
      expect(result).toBeUndefined()
    })
  })

  describe('fetchAppStatuses', () => {
    it('应该获取所有应用状态', async () => {
      const mockStatuses = [
        { app_id: 'app1', state: 'running' as const },
        { app_id: 'app2', state: 'stopped' as const },
      ]
      vi.mocked(api.request.get).mockResolvedValue(mockStatuses as any)

      const store = useDockerStoreStore()
      const result = await store.fetchAppStatuses()

      expect(store.appStatuses['app1'].state).toBe('running')
      expect(store.appStatuses['app2'].state).toBe('stopped')
    })

    it('请求失败时应该返回空数组', async () => {
      vi.mocked(api.request.get).mockRejectedValue(new Error('Network error'))

      const store = useDockerStoreStore()
      const result = await store.fetchAppStatuses()

      expect(result).toEqual([])
    })

    it('当没有 alias 时应该直接返回', async () => {
      dockerStore.setAccountAlias('')
      const store = useDockerStoreStore()
      const result = await store.fetchAppStatuses()
      expect(result).toBeUndefined()
    })
  })

  describe('fetchAppSize', () => {
    it('应该获取应用大小信息', async () => {
      const mockSize = {
        app_id: 'app1', image_size: 100, image_size_human: '100MB',
        container_size: 10, container_size_human: '10MB',
        volume_size: 50, volume_size_human: '50MB',
        data_dir_size: 20, data_dir_size_human: '20MB',
        total_size: 180, total_size_human: '180MB',
        components: [],
      }
      vi.mocked(api.request.get).mockResolvedValue(mockSize as any)

      const store = useDockerStoreStore()
      const result = await store.fetchAppSize('app1')

      expect(store.appSizes['app1']).toEqual(mockSize)
    })

    it('请求期间 sizeLoading 应该为 true', async () => {
      vi.mocked(api.request.get).mockImplementation(async () => {
        const store = useDockerStoreStore()
        expect(store.sizeLoading['app1']).toBe(true)
        return {}
      })

      const store = useDockerStoreStore()
      await store.fetchAppSize('app1')
      expect(store.sizeLoading['app1']).toBe(false)
    })

    it('请求失败时 sizeLoading 应该恢复为 false', async () => {
      vi.mocked(api.request.get).mockRejectedValue(new Error('Error'))

      const store = useDockerStoreStore()
      await store.fetchAppSize('app1')
      expect(store.sizeLoading['app1']).toBe(false)
    })

    it('当没有 alias 时应该直接返回', async () => {
      dockerStore.setAccountAlias('')
      const store = useDockerStoreStore()
      const result = await store.fetchAppSize('app1')
      expect(result).toBeUndefined()
    })
  })

  describe('fetchImageVersionSizes', () => {
    it('应该获取镜像版本大小信息', async () => {
      const mockVersionSizes = {
        app_id: 'app1', image_name: 'wordpress', versions: [], total_versions: 0,
      }
      vi.mocked(api.request.get).mockResolvedValue(mockVersionSizes as any)

      const store = useDockerStoreStore()
      const result = await store.fetchImageVersionSizes('app1')

      expect(store.imageVersionSizes['app1']).toEqual(mockVersionSizes)
    })

    it('请求期间 versionSizeLoading 应该为 true', async () => {
      vi.mocked(api.request.get).mockImplementation(async () => {
        const store = useDockerStoreStore()
        expect(store.versionSizeLoading['app1']).toBe(true)
        return {}
      })

      const store = useDockerStoreStore()
      await store.fetchImageVersionSizes('app1')
      expect(store.versionSizeLoading['app1']).toBe(false)
    })

    it('请求失败时 versionSizeLoading 应该恢复为 false', async () => {
      vi.mocked(api.request.get).mockRejectedValue(new Error('Error'))

      const store = useDockerStoreStore()
      await store.fetchImageVersionSizes('app1')
      expect(store.versionSizeLoading['app1']).toBe(false)
    })
  })

  describe('fetchRegistryMirrors', () => {
    it('应该获取镜像加速器配置', async () => {
      vi.mocked(api.request.get).mockResolvedValue({ mirrors: ['https://mirror1.com', 'https://mirror2.com'] } as any)

      const store = useDockerStoreStore()
      const result = await store.fetchRegistryMirrors()

      expect(store.registryMirror.enabled).toBe(true)
      expect(store.registryMirror.urls).toEqual(['https://mirror1.com', 'https://mirror2.com'])
    })

    it('没有镜像时应该设置 enabled 为 false', async () => {
      vi.mocked(api.request.get).mockResolvedValue({ mirrors: [] } as any)

      const store = useDockerStoreStore()
      await store.fetchRegistryMirrors()

      expect(store.registryMirror.enabled).toBe(false)
      expect(store.registryMirror.urls).toEqual([])
    })

    it('请求失败时应该重置为默认值', async () => {
      vi.mocked(api.request.get).mockRejectedValue(new Error('Error'))

      const store = useDockerStoreStore()
      await store.fetchRegistryMirrors()

      expect(store.registryMirror).toEqual({ enabled: false, urls: [] })
    })

    it('当没有 alias 时应该直接返回', async () => {
      dockerStore.setAccountAlias('')
      const store = useDockerStoreStore()
      const result = await store.fetchRegistryMirrors()
      expect(result).toBeUndefined()
    })
  })

  describe('configureRegistryMirror', () => {
    it('应该配置镜像加速器并刷新', async () => {
      vi.mocked(api.request.post).mockResolvedValue({ success: true } as any)
      vi.mocked(api.request.get).mockResolvedValue({ mirrors: ['https://new-mirror.com'] } as any)

      const store = useDockerStoreStore()
      await store.configureRegistryMirror('https://new-mirror.com')

      expect(api.request.post).toHaveBeenCalledWith('/docker-store/registry-mirrors', {
        account_alias: 'test-server',
        mirror_url: 'https://new-mirror.com',
      })
      expect(api.request.get).toHaveBeenCalled()
    })

    it('当没有 alias 时应该直接返回', async () => {
      dockerStore.setAccountAlias('')
      const store = useDockerStoreStore()
      const result = await store.configureRegistryMirror('https://mirror.com')
      expect(result).toBeUndefined()
    })
  })

  describe('installAppWithProgress', () => {
    function getLastWs(): any {
      return wsInstances.length > 0 ? wsInstances[wsInstances.length - 1] : null
    }

    it('当没有 alias 时应该 reject', async () => {
      dockerStore.setAccountAlias('')
      const store = useDockerStoreStore()
      await expect(store.installAppWithProgress('app1', {})).rejects.toThrow('未选择 SSH 服务器')
    })

    it('应该设置 installing 为 true 并初始化进度', async () => {
      const store = useDockerStoreStore()
      const promise = store.installAppWithProgress('app1', { port: 8080 })

      expect(store.installing).toBe(true)
      expect(store.installProgress['app1']).toBeDefined()
      expect(store.installProgressPercent['app1']).toBe(0)
      expect(store.appStatuses['app1'].state).toBe('installing')

      await new Promise(r => setTimeout(r, 20))
      const ws = getLastWs()
      if (ws?.onmessage) {
        ws.onmessage({ data: JSON.stringify({ type: 'complete', message: '安装完成', success: true }) })
      }
      try { await promise } catch {}
    })

    it('WebSocket onopen 应该发送安装参数', async () => {
      const store = useDockerStoreStore()
      const promise = store.installAppWithProgress('app1', { port: 8080 })

      await new Promise(r => setTimeout(r, 20))
      const ws = getLastWs()
      expect(ws).not.toBeNull()
      expect(ws.send).toHaveBeenCalled()
      const sentData = JSON.parse(ws.send.mock.calls[0][0])
      expect(sentData.account_alias).toBe('test-server')
      expect(sentData.user_config).toEqual({ port: 8080 })

      if (ws?.onmessage) {
        ws.onmessage({ data: JSON.stringify({ type: 'complete', message: '安装完成', success: true }) })
      }
      try { await promise } catch {}
    })

    it('stage prepare 消息应设置进度为 5%', async () => {
      const store = useDockerStoreStore()
      const promise = store.installAppWithProgress('app1', {})

      await new Promise(r => setTimeout(r, 20))
      const ws = getLastWs()
      ws.onmessage({ data: JSON.stringify({ type: 'stage', stage: 'prepare', message: '准备中...' }) })

      expect(store.installProgressPercent['app1']).toBe(5)
      expect(store.installProgressMessage['app1']).toBe('准备中...')

      ws.onmessage({ data: JSON.stringify({ type: 'complete', message: '安装完成', success: true }) })
      try { await promise } catch {}
    })

    it('stage download 消息应设置进度为 10%', async () => {
      const store = useDockerStoreStore()
      const promise = store.installAppWithProgress('app1', {})

      await new Promise(r => setTimeout(r, 20))
      const ws = getLastWs()
      ws.onmessage({ data: JSON.stringify({ type: 'stage', stage: 'download', message: '下载中...' }) })

      expect(store.installProgressPercent['app1']).toBe(10)

      ws.onmessage({ data: JSON.stringify({ type: 'complete', message: '安装完成', success: true }) })
      try { await promise } catch {}
    })

    it('stage start 消息应设置进度为 90%', async () => {
      const store = useDockerStoreStore()
      const promise = store.installAppWithProgress('app1', {})

      await new Promise(r => setTimeout(r, 20))
      const ws = getLastWs()
      ws.onmessage({ data: JSON.stringify({ type: 'stage', stage: 'start', message: '启动中...' }) })

      expect(store.installProgressPercent['app1']).toBe(90)

      ws.onmessage({ data: JSON.stringify({ type: 'complete', message: '安装完成', success: true }) })
      try { await promise } catch {}
    })

    it('pull_progress 消息应更新下载进度', async () => {
      const store = useDockerStoreStore()
      const promise = store.installAppWithProgress('app1', {})

      await new Promise(r => setTimeout(r, 20))
      const ws = getLastWs()
      ws.onmessage({ data: JSON.stringify({ type: 'pull_progress', progress_percent: 50, message: '下载镜像中...' }) })

      expect(store.installProgressPercent['app1']).toBeGreaterThan(10)
      expect(store.installProgressMessage['app1']).toBe('下载镜像中...')

      ws.onmessage({ data: JSON.stringify({ type: 'complete', message: '安装完成', success: true }) })
      try { await promise } catch {}
    })

    it('pull_complete 消息应设置进度为 80%', async () => {
      const store = useDockerStoreStore()
      const promise = store.installAppWithProgress('app1', {})

      await new Promise(r => setTimeout(r, 20))
      const ws = getLastWs()
      ws.onmessage({ data: JSON.stringify({ type: 'pull_complete', message: '镜像下载完成' }) })

      expect(store.installProgressPercent['app1']).toBe(80)
      expect(store.installProgressMessage['app1']).toBe('镜像下载完成')

      ws.onmessage({ data: JSON.stringify({ type: 'complete', message: '安装完成', success: true }) })
      try { await promise } catch {}
    })

    it('complete 消息应 resolve 并设置状态为 running', async () => {
      const store = useDockerStoreStore()
      const promise = store.installAppWithProgress('app1', {})

      await new Promise(r => setTimeout(r, 20))
      const ws = getLastWs()
      ws.onmessage({ data: JSON.stringify({ type: 'complete', message: '安装完成', success: true }) })

      const result = await promise
      expect(result.success).toBe(true)
      expect(store.appStatuses['app1'].state).toBe('running')
      expect(store.installProgressPercent['app1']).toBe(100)
      expect(store.installing).toBe(false)
    })

    it('error 消息应 reject 并设置状态为 not_installed', async () => {
      const store = useDockerStoreStore()
      const promise = store.installAppWithProgress('app1', {})

      await new Promise(r => setTimeout(r, 20))
      const ws = getLastWs()
      ws.onmessage({ data: JSON.stringify({ type: 'error', message: '安装出错' }) })

      await expect(promise).rejects.toThrow('安装出错')
      expect(store.appStatuses['app1'].state).toBe('not_installed')
      expect(store.installing).toBe(false)
    })

    it('WebSocket onerror 应 reject', async () => {
      const store = useDockerStoreStore()
      const promise = store.installAppWithProgress('app1', {})

      await new Promise(r => setTimeout(r, 20))
      const ws = getLastWs()
      ws.onerror(new Event('error'))

      await expect(promise).rejects.toThrow('WebSocket 连接失败')
      expect(store.installing).toBe(false)
    })

    it('非 JSON 消息应被忽略', async () => {
      const store = useDockerStoreStore()
      const promise = store.installAppWithProgress('app1', {})

      await new Promise(r => setTimeout(r, 20))
      const ws = getLastWs()
      ws.onmessage({ data: 'not json' })

      expect(store.installing).toBe(true)

      ws.onmessage({ data: JSON.stringify({ type: 'complete', message: '安装完成', success: true }) })

      await promise
    })
  })
})
