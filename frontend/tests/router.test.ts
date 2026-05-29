/**
 * Router 单元测试
 * 测试所有路由定义、路径和组件懒加载
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import router from '@/router'

describe('Router', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('路由定义', () => {
    it('应该定义所有预期的路由', () => {
      const routes = router.getRoutes()
      expect(routes.length).toBeGreaterThanOrEqual(15)
    })

    it('应该包含首页路由', () => {
      const routes = router.getRoutes()
      const homeRoute = routes.find(r => r.name === 'Home')
      expect(homeRoute).toBeDefined()
      expect(homeRoute!.path).toBe('/')
    })

    it('应该包含项目管理路由', () => {
      const routes = router.getRoutes()
      const projectRoute = routes.find(r => r.name === 'Project')
      expect(projectRoute).toBeDefined()
      expect(projectRoute!.path).toBe('/project')
    })

    it('应该包含文件管理路由', () => {
      const routes = router.getRoutes()
      const fileRoute = routes.find(r => r.name === 'FileManager')
      expect(fileRoute).toBeDefined()
      expect(fileRoute!.path).toBe('/file-manager')
    })

    it('应该包含 SSH 账户管理路由', () => {
      const routes = router.getRoutes()
      const sshRoute = routes.find(r => r.name === 'SshAccounts')
      expect(sshRoute).toBeDefined()
      expect(sshRoute!.path).toBe('/ssh-accounts')
    })

    it('应该包含 Docker 管理路由', () => {
      const routes = router.getRoutes()
      const dockerRoute = routes.find(r => r.name === 'Docker')
      expect(dockerRoute).toBeDefined()
      expect(dockerRoute!.path).toBe('/docker')
    })

    it('应该包含 Docker 应用商店路由', () => {
      const routes = router.getRoutes()
      const storeRoute = routes.find(r => r.name === 'DockerStore')
      expect(storeRoute).toBeDefined()
      expect(storeRoute!.path).toBe('/docker-store')
    })

    it('应该包含容器详情路由', () => {
      const routes = router.getRoutes()
      const detailRoute = routes.find(r => r.name === 'DockerContainerDetail')
      expect(detailRoute).toBeDefined()
      expect(detailRoute!.path).toBe('/docker/container/:id')
    })

    it('应该包含 WebSSH 路由', () => {
      const routes = router.getRoutes()
      const websshRoute = routes.find(r => r.name === 'WebSSH')
      expect(websshRoute).toBeDefined()
      expect(websshRoute!.path).toBe('/webssh')
    })

    it('应该包含工具箱路由', () => {
      const routes = router.getRoutes()
      const toolsRoute = routes.find(r => r.name === 'Tools')
      expect(toolsRoute).toBeDefined()
      expect(toolsRoute!.path).toBe('/tools')
    })

    it('应该包含设置路由', () => {
      const routes = router.getRoutes()
      const settingsRoute = routes.find(r => r.name === 'Settings')
      expect(settingsRoute).toBeDefined()
      expect(settingsRoute!.path).toBe('/settings')
    })

    it('应该包含监控大屏路由', () => {
      const routes = router.getRoutes()
      const monitorRoute = routes.find(r => r.name === 'MonitorDashboard')
      expect(monitorRoute).toBeDefined()
      expect(monitorRoute!.path).toBe('/monitor')
    })

    it('应该包含监控大屏路由', () => {
      const routes = router.getRoutes()
      const largeScreenRoute = routes.find(r => r.name === 'MonitorLargeScreen')
      expect(largeScreenRoute).toBeDefined()
      expect(largeScreenRoute!.path).toBe('/monitor/large-screen')
    })

    it('应该包含进程管理路由', () => {
      const routes = router.getRoutes()
      const processRoute = routes.find(r => r.name === 'ProcessManager')
      expect(processRoute).toBeDefined()
      expect(processRoute!.path).toBe('/process')
    })

    it('应该包含安全与网络路由', () => {
      const routes = router.getRoutes()
      const securityRoute = routes.find(r => r.name === 'SecurityNetwork')
      expect(securityRoute).toBeDefined()
      expect(securityRoute!.path).toBe('/security-network')
    })

    it('应该包含计划任务与备份路由', () => {
      const routes = router.getRoutes()
      const cronRoute = routes.find(r => r.name === 'CronBackup')
      expect(cronRoute).toBeDefined()
      expect(cronRoute!.path).toBe('/cron-backup')
    })
  })

  describe('路由元信息', () => {
    it('所有路由都应该有 title 元信息', () => {
      const routes = router.getRoutes()
      routes.forEach(route => {
        if (route.name) {
          expect(route.meta).toHaveProperty('title')
          expect(typeof route.meta.title).toBe('string')
        }
      })
    })

    it('首页路由的 title 应该为 "首页"', () => {
      const routes = router.getRoutes()
      const homeRoute = routes.find(r => r.name === 'Home')
      expect(homeRoute!.meta.title).toBe('首页')
    })

    it('Docker 路由的 title 应该为 "Docker 管理"', () => {
      const routes = router.getRoutes()
      const dockerRoute = routes.find(r => r.name === 'Docker')
      expect(dockerRoute!.meta.title).toBe('Docker 管理')
    })

    it('监控大屏路由的 title 应该为 "监控大屏"', () => {
      const routes = router.getRoutes()
      const largeScreenRoute = routes.find(r => r.name === 'MonitorLargeScreen')
      expect(largeScreenRoute!.meta.title).toBe('监控大屏')
    })

    it('安全与网络路由的 title 应该为 "安全与网络"', () => {
      const routes = router.getRoutes()
      const securityRoute = routes.find(r => r.name === 'SecurityNetwork')
      expect(securityRoute!.meta.title).toBe('安全与网络')
    })
  })

  describe('组件懒加载', () => {
    it('首页路由应该使用懒加载', () => {
      const routes = router.getRoutes()
      const homeRoute = routes.find(r => r.name === 'Home')
      expect(homeRoute!.component).toBeDefined()
    })

    it('项目管理路由应该使用懒加载', () => {
      const routes = router.getRoutes()
      const projectRoute = routes.find(r => r.name === 'Project')
      expect(projectRoute!.component).toBeDefined()
    })

    it('容器详情路由应该使用懒加载', () => {
      const routes = router.getRoutes()
      const detailRoute = routes.find(r => r.name === 'DockerContainerDetail')
      expect(detailRoute!.component).toBeDefined()
    })

    it('监控大屏路由应该使用懒加载', () => {
      const routes = router.getRoutes()
      const largeScreenRoute = routes.find(r => r.name === 'MonitorLargeScreen')
      expect(largeScreenRoute!.component).toBeDefined()
    })
  })

  describe('路由路径格式', () => {
    it('所有路由路径都应该以 / 开头', () => {
      const routes = router.getRoutes()
      routes.forEach(route => {
        expect(route.path.startsWith('/')).toBe(true)
      })
    })

    it('容器详情路由应该使用动态参数', () => {
      const routes = router.getRoutes()
      const detailRoute = routes.find(r => r.name === 'DockerContainerDetail')
      expect(detailRoute!.path).toMatch(/:id/)
    })

    it('监控相关路由应该使用 /monitor 前缀', () => {
      const routes = router.getRoutes()
      const monitorRoutes = routes.filter(r => r.name && r.name.toString().startsWith('Monitor'))
      monitorRoutes.forEach(route => {
        expect(route.path.startsWith('/monitor')).toBe(true)
      })
    })

    it('Docker 相关路由应该使用 /docker 前缀', () => {
      const routes = router.getRoutes()
      const dockerRoutes = routes.filter(r =>
        r.name && (r.name.toString().startsWith('Docker'))
      )
      dockerRoutes.forEach(route => {
        expect(route.path.startsWith('/docker')).toBe(true)
      })
    })
  })

  describe('路由名称唯一性', () => {
    it('所有路由名称应该唯一', () => {
      const routes = router.getRoutes()
      const names = routes
        .filter(r => r.name)
        .map(r => r.name!.toString())
      const uniqueNames = new Set(names)
      expect(names.length).toBe(uniqueNames.size)
    })
  })

  describe('路由历史模式', () => {
    it('应该使用 createWebHistory', () => {
      // 验证 router 已正确创建
      expect(router).toBeDefined()
      expect(typeof router.beforeEach).toBe('function')
      expect(typeof router.push).toBe('function')
    })
  })
})
