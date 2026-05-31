/**
 * Docker Store 单元测试
 * 测试状态初始化、actions、计算属性、错误处理和加载状态
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useDockerStore } from '@/stores/dockerStore'
import * as api from '@/api'

describe('Docker Store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  describe('状态初始化', () => {
    it('应该正确初始化 currentAlias 为空字符串', () => {
      const store = useDockerStore()
      expect(store.currentAlias).toBe('')
    })

    it('应该正确初始化 dockerInfo 默认值', () => {
      const store = useDockerStore()
      expect(store.dockerInfo.version).toBe('')
      expect(store.dockerInfo.daemon_status).toBe('stopped')
      expect(store.dockerInfo.user_permission).toBe('')
      expect(store.dockerInfo.docker_group).toBe(false)
    })

    it('应该正确初始化 containers 为空数组', () => {
      const store = useDockerStore()
      expect(store.containers).toEqual([])
    })

    it('应该正确初始化 images 为空数组', () => {
      const store = useDockerStore()
      expect(store.images).toEqual([])
    })

    it('应该正确初始化 networks 为空数组', () => {
      const store = useDockerStore()
      expect(store.networks).toEqual([])
    })

    it('应该正确初始化 volumes 为空数组', () => {
      const store = useDockerStore()
      expect(store.volumes).toEqual([])
    })

    it('应该正确初始化 composeProjects 为空数组', () => {
      const store = useDockerStore()
      expect(store.composeProjects).toEqual([])
    })

    it('应该正确初始化 loading 为 false', () => {
      const store = useDockerStore()
      expect(store.loading).toBe(false)
    })
  })

  describe('setAccountAlias', () => {
    it('应该更新 currentAlias', () => {
      const store = useDockerStore()
      store.setAccountAlias('test-server')
      expect(store.currentAlias).toBe('test-server')
    })
  })

  describe('fetchInfo', () => {
    it('应该从 API 获取 docker 信息', async () => {
      const mockResponse = {
        version: '24.0.5',
        running: true,
        installed: true,
        permissions: { in_docker_group: true },
      }
      vi.mocked(api.request.get).mockResolvedValue(mockResponse as any)

      const store = useDockerStore()
      store.setAccountAlias('test-server')
      await store.fetchInfo()

      expect(store.dockerInfo.version).toBe('24.0.5')
      expect(store.dockerInfo.daemon_status).toBe('running')
      expect(store.dockerInfo.docker_group).toBe(true)
    })

    it('当没有 alias 时应该直接返回', async () => {
      const store = useDockerStore()
      const result = await store.fetchInfo()
      expect(result).toBeUndefined()
    })

    it('应该处理 daemon 停止状态', async () => {
      vi.mocked(api.request.get).mockResolvedValue({
        version: '24.0.5',
        running: false,
        installed: false,
      } as any)

      const store = useDockerStore()
      store.setAccountAlias('test-server')
      await store.fetchInfo()

      expect(store.dockerInfo.daemon_status).toBe('stopped')
    })

    it('应该支持传入 alias 参数', async () => {
      vi.mocked(api.request.get).mockResolvedValue({
        version: '25.0.0',
        running: true,
        installed: true,
      } as any)

      const store = useDockerStore()
      await store.fetchInfo('direct-alias')

      expect(api.request.get).toHaveBeenCalledWith('/docker/info', {
        params: { account_alias: 'direct-alias' },
      })
    })
  })

  describe('fetchContainers', () => {
    it('应该获取容器列表并更新 loading 状态', async () => {
      const mockContainers = [
        { id: 'c1', name: 'nginx', status: 'running', state: 'running', ports: '80:80', created: '2024-01-01' },
      ]
      vi.mocked(api.request.get).mockResolvedValue(mockContainers as any)

      const store = useDockerStore()
      store.setAccountAlias('test-server')
      await store.fetchContainers()

      expect(store.containers).toEqual(mockContainers)
    })

    it('请求期间 loading 应该为 true', async () => {
      vi.mocked(api.request.get).mockImplementation(async () => {
        const store = useDockerStore()
        expect(store.loading).toBe(true)
        return []
      })

      const store = useDockerStore()
      store.setAccountAlias('test-server')
      await store.fetchContainers()
      expect(store.loading).toBe(false)
    })

    it('请求失败时 loading 应该恢复为 false', async () => {
      vi.mocked(api.request.get).mockRejectedValue(new Error('Network error'))

      const store = useDockerStore()
      store.setAccountAlias('test-server')
      await expect(store.fetchContainers()).rejects.toThrow()
      expect(store.loading).toBe(false)
    })

    it('当没有 alias 时应该直接返回', async () => {
      const store = useDockerStore()
      const result = await store.fetchContainers()
      expect(result).toBeUndefined()
    })
  })

  describe('fetchImages', () => {
    it('应该获取镜像列表', async () => {
      const mockImages = [
        { id: 'img1', repository: 'nginx', tag: 'latest', size: '200MB', created: '2024-01-01', in_use: true },
      ]
      vi.mocked(api.request.get).mockResolvedValue(mockImages as any)

      const store = useDockerStore()
      store.setAccountAlias('test-server')
      const result = await store.fetchImages()

      expect(store.images).toEqual(mockImages)
      expect(result).toEqual(mockImages)
    })

    it('当没有 alias 时应该直接返回', async () => {
      const store = useDockerStore()
      const result = await store.fetchImages()
      expect(result).toBeUndefined()
    })
  })

  describe('fetchNetworks', () => {
    it('应该获取网络列表', async () => {
      const mockNetworks = [
        { id: 'net1', name: 'bridge', driver: 'bridge', scope: 'local', containers: 3 },
      ]
      vi.mocked(api.request.get).mockResolvedValue(mockNetworks as any)

      const store = useDockerStore()
      store.setAccountAlias('test-server')
      const result = await store.fetchNetworks()

      expect(store.networks).toEqual(mockNetworks)
      expect(result).toEqual(mockNetworks)
    })
  })

  describe('fetchVolumes', () => {
    it('应该获取数据卷列表', async () => {
      const mockVolumes = [
        { name: 'vol1', driver: 'local', mountpoint: '/data', size: '1GB', in_use: true },
      ]
      vi.mocked(api.request.get).mockResolvedValue(mockVolumes as any)

      const store = useDockerStore()
      store.setAccountAlias('test-server')
      const result = await store.fetchVolumes()

      expect(store.volumes).toEqual(mockVolumes)
      expect(result).toEqual(mockVolumes)
    })
  })

  describe('容器操作', () => {
    beforeEach(() => {
      vi.mocked(api.request.post).mockResolvedValue({} as any)
      vi.mocked(api.request.get).mockResolvedValue({} as any)
      vi.mocked(api.request.delete).mockResolvedValue({} as any)
    })

    it('startContainer 应该启动容器并刷新列表', async () => {
      vi.useFakeTimers()
      const mockContainers = [
        { id: 'c1', name: 'nginx', status: 'running', state: 'running', ports: '80:80', created: '2024-01-01' },
      ]

      vi.mocked(api.request.get).mockResolvedValueOnce([] as any) // first fetchContainers
      vi.mocked(api.request.get).mockResolvedValueOnce(mockContainers as any) // second fetchContainers after delay

      const store = useDockerStore()
      store.setAccountAlias('test-server')
      const promise = store.startContainer('c1')
      await vi.advanceTimersByTimeAsync(10000)
      const result = await promise

      expect(result.success).toBe(true)
      vi.useRealTimers()
    })

    it('stopContainer 应该停止容器并刷新列表', async () => {
      const store = useDockerStore()
      store.setAccountAlias('test-server')
      await store.stopContainer('c1')

      expect(api.request.post).toHaveBeenCalledWith('/docker/containers/c1/stop', { account_alias: 'test-server' })
    })

    it('restartContainer 应该重启容器并刷新列表', async () => {
      const store = useDockerStore()
      store.setAccountAlias('test-server')
      await store.restartContainer('c1')

      expect(api.request.post).toHaveBeenCalledWith('/docker/containers/c1/restart', null, { params: { account_alias: 'test-server' } })
    })

    it('killContainer 应该强制终止容器', async () => {
      const store = useDockerStore()
      store.setAccountAlias('test-server')
      await store.killContainer('c1')

      expect(api.request.post).toHaveBeenCalledWith('/docker/containers/c1/kill', null, { params: { account_alias: 'test-server' } })
    })

    it('deleteContainer 应该删除容器并刷新列表', async () => {
      const store = useDockerStore()
      store.setAccountAlias('test-server')
      await store.deleteContainer('c1')

      expect(api.request.delete).toHaveBeenCalledWith('/docker/containers/c1', { params: { account_alias: 'test-server' } })
    })

    it('pauseContainer 应该暂停容器', async () => {
      const store = useDockerStore()
      store.setAccountAlias('test-server')
      await store.pauseContainer('c1')

      expect(api.request.post).toHaveBeenCalledWith('/docker/containers/c1/pause', null, { params: { account_alias: 'test-server' } })
    })

    it('unpauseContainer 应该恢复暂停的容器', async () => {
      const store = useDockerStore()
      store.setAccountAlias('test-server')
      await store.unpauseContainer('c1')

      expect(api.request.post).toHaveBeenCalledWith('/docker/containers/c1/unpause', null, { params: { account_alias: 'test-server' } })
    })

    it('容器操作当没有 alias 时应该返回', async () => {
      const store = useDockerStore()
      expect(await store.startContainer('c1')).toEqual({ success: false })
      expect(await store.stopContainer('c1')).toBeUndefined()
      expect(await store.restartContainer('c1')).toBeUndefined()
      expect(await store.killContainer('c1')).toBeUndefined()
      expect(await store.deleteContainer('c1')).toBeUndefined()
    })
  })

  describe('镜像操作', () => {
    it('deleteImage 应该删除镜像并刷新列表', async () => {
      vi.mocked(api.request.delete).mockResolvedValue({} as any)

      const store = useDockerStore()
      store.setAccountAlias('test-server')
      await store.deleteImage('img1')

      expect(api.request.delete).toHaveBeenCalledWith('/docker/images/img1', { params: { account_alias: 'test-server' } })
    })

    it('pullImage 应该拉取新镜像并刷新列表', async () => {
      vi.mocked(api.request.post).mockResolvedValue({} as any)

      const store = useDockerStore()
      store.setAccountAlias('test-server')
      await store.pullImage({ repository: 'nginx', tag: 'latest' })

      expect(api.request.post).toHaveBeenCalledWith('/docker/images/pull', {
        account_alias: 'test-server',
        image_name: 'nginx:latest',
      })
    })

    it('pullImage 不带 tag 时应该只用 repository', async () => {
      vi.mocked(api.request.post).mockResolvedValue({} as any)

      const store = useDockerStore()
      store.setAccountAlias('test-server')
      await store.pullImage({ repository: 'nginx' })

      expect(api.request.post).toHaveBeenCalledWith('/docker/images/pull', {
        account_alias: 'test-server',
        image_name: 'nginx',
      })
    })

    it('buildImage 应该构建新镜像', async () => {
      vi.mocked(api.request.post).mockResolvedValue({} as any)

      const store = useDockerStore()
      store.setAccountAlias('test-server')
      await store.buildImage({ dockerfile_path: '/path/Dockerfile', tag: 'myimage:v1' })

      expect(api.request.post).toHaveBeenCalledWith('/docker/images/build', {
        account_alias: 'test-server',
        tag: 'myimage:v1',
        dockerfile_path: '/path/Dockerfile',
        context_path: '/path',
      })
    })

    it('pruneImages 应该清理未使用的镜像', async () => {
      vi.mocked(api.request.post).mockResolvedValue({} as any)

      const store = useDockerStore()
      store.setAccountAlias('test-server')
      await store.pruneImages()

      expect(api.request.post).toHaveBeenCalledWith('/docker/images/prune', null, { params: { account_alias: 'test-server' } })
    })
  })

  describe('网络操作', () => {
    it('createNetwork 应该创建新网络', async () => {
      vi.mocked(api.request.post).mockResolvedValue({} as any)

      const store = useDockerStore()
      store.setAccountAlias('test-server')
      await store.createNetwork({ name: 'mynet', driver: 'overlay' })

      expect(api.request.post).toHaveBeenCalledWith('/docker/networks', {
        account_alias: 'test-server',
        name: 'mynet',
        driver: 'overlay',
      })
    })

    it('deleteNetwork 应该删除网络', async () => {
      vi.mocked(api.request.delete).mockResolvedValue({} as any)

      const store = useDockerStore()
      store.setAccountAlias('test-server')
      await store.deleteNetwork('net1')

      expect(api.request.delete).toHaveBeenCalledWith('/docker/networks/net1', { params: { account_alias: 'test-server' } })
    })
  })

  describe('数据卷操作', () => {
    it('createVolume 应该创建新数据卷', async () => {
      vi.mocked(api.request.post).mockResolvedValue({} as any)

      const store = useDockerStore()
      store.setAccountAlias('test-server')
      await store.createVolume({ name: 'myvol' })

      expect(api.request.post).toHaveBeenCalledWith('/docker/volumes', {
        account_alias: 'test-server',
        name: 'myvol',
      })
    })

    it('deleteVolume 应该删除数据卷', async () => {
      vi.mocked(api.request.delete).mockResolvedValue({} as any)

      const store = useDockerStore()
      store.setAccountAlias('test-server')
      await store.deleteVolume('myvol')

      expect(api.request.delete).toHaveBeenCalledWith('/docker/volumes/myvol', { params: { account_alias: 'test-server' } })
    })
  })

  describe('Compose 操作', () => {
    it('fetchComposeProjects 应该获取 compose 项目列表', async () => {
      const mockProjects = [{ name: 'myproject', path: '/path', status: 'running', services: ['web', 'db'] }]
      vi.mocked(api.request.get).mockResolvedValue(mockProjects as any)

      const store = useDockerStore()
      store.setAccountAlias('test-server')
      await store.fetchComposeProjects()

      expect(store.composeProjects).toEqual(mockProjects)
    })

    it('composeUp 应该启动 compose 项目', async () => {
      vi.mocked(api.request.post).mockResolvedValue({} as any)

      const store = useDockerStore()
      store.setAccountAlias('test-server')
      await store.composeUp({ path: '/path/to/compose', detached: true })

      expect(api.request.post).toHaveBeenCalledWith('/docker/compose/up', {
        account_alias: 'test-server',
        project_path: '/path/to/compose',
        detach: true,
      })
    })

    it('composeDown 应该停止 compose 项目', async () => {
      vi.mocked(api.request.post).mockResolvedValue({} as any)

      const store = useDockerStore()
      store.setAccountAlias('test-server')
      await store.composeDown({ path: '/path/to/compose' })

      expect(api.request.post).toHaveBeenCalledWith('/docker/compose/down', {
        account_alias: 'test-server',
        project_path: '/path/to/compose',
      })
    })
  })

  describe('容器辅助功能', () => {
    it('getContainerLogs 应该获取容器日志', async () => {
      vi.mocked(api.request.get).mockResolvedValue(['log1', 'log2'] as any)

      const store = useDockerStore()
      store.setAccountAlias('test-server')
      const result = await store.getContainerLogs('c1', 50)

      expect(api.request.get).toHaveBeenCalledWith('/docker/containers/c1/logs', {
        params: { account_alias: 'test-server', tail: 50 },
      })
      expect(result).toEqual(['log1', 'log2'])
    })

    it('getContainerStats 应该获取容器统计信息', async () => {
      vi.mocked(api.request.get).mockResolvedValue({ cpu: 10, memory: 50 } as any)

      const store = useDockerStore()
      store.setAccountAlias('test-server')
      const result = await store.getContainerStats('c1')

      expect(result).toEqual({ cpu: 10, memory: 50 })
    })

    it('getContainerStats 失败时应该返回 null', async () => {
      vi.mocked(api.request.get).mockRejectedValue(new Error('Error'))

      const store = useDockerStore()
      store.setAccountAlias('test-server')
      const result = await store.getContainerStats('c1')

      expect(result).toBeNull()
    })

    it('execInContainer 应该在容器中执行命令', async () => {
      vi.mocked(api.request.post).mockResolvedValue({ output: 'hello' } as any)

      const store = useDockerStore()
      store.setAccountAlias('test-server')
      const result = await store.execInContainer('c1', 'ls -la')

      expect(api.request.post).toHaveBeenCalledWith('/docker/containers/c1/exec', {
        account_alias: 'test-server',
        command: 'ls -la',
      })
    })
  })

  describe('installDocker', () => {
    it('应该安装 Docker', async () => {
      vi.mocked(api.request.post).mockResolvedValue({} as any)

      const store = useDockerStore()
      store.setAccountAlias('test-server')
      await store.installDocker()

      expect(api.request.post).toHaveBeenCalledWith('/docker/install', { account_alias: 'test-server' })
    })
  })
})
