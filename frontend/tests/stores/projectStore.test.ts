/**
 * Project Store 单元测试
 * 测试 CRUD 操作和加载状态管理
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useProjectStore } from '@/stores/projectStore'
import * as api from '@/api'

// 辅助函数：mock request 的所有方法返回相同值
function mockAllRequestMethods(value: any) {
  vi.mocked(api.request.get).mockResolvedValue(value)
  vi.mocked(api.request.post).mockResolvedValue(value)
  vi.mocked(api.request.put).mockResolvedValue(value)
  vi.mocked(api.request.delete).mockResolvedValue(value)
}

// 辅助函数：mock request 的所有方法为拒绝
function mockAllRequestReject(error: Error) {
  vi.mocked(api.request.get).mockRejectedValue(error)
  vi.mocked(api.request.post).mockRejectedValue(error)
  vi.mocked(api.request.put).mockRejectedValue(error)
  vi.mocked(api.request.delete).mockRejectedValue(error)
}

// 辅助函数：mock request 的所有方法为自定义实现
function mockAllRequestImplementation(fn: (...args: any[]) => Promise<any>) {
  vi.mocked(api.request.get).mockImplementation(fn)
  vi.mocked(api.request.post).mockImplementation(fn)
  vi.mocked(api.request.put).mockImplementation(fn)
  vi.mocked(api.request.delete).mockImplementation(fn)
}

describe('Project Store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  describe('状态初始化', () => {
    it('应该正确初始化 projects 为空数组', () => {
      const store = useProjectStore()
      expect(store.projects).toEqual([])
    })

    it('应该正确初始化 loading 为 false', () => {
      const store = useProjectStore()
      expect(store.loading).toBe(false)
    })
  })

  describe('fetchProjects', () => {
    it('应该获取项目列表', async () => {
      const mockProjects = [
        { alias: 'project1', local_path: '/local/p1', remote_path: '/remote/p1', ssh_alias: 'server1' },
        { alias: 'project2', local_path: '/local/p2', remote_path: '/remote/p2', ssh_alias: 'server2' },
      ]
      mockAllRequestMethods(mockProjects)

      const store = useProjectStore()
      await store.fetchProjects()

      expect(store.projects).toEqual(mockProjects)
    })

    it('请求期间 loading 应该为 true', async () => {
      mockAllRequestImplementation(async () => {
        const store = useProjectStore()
        expect(store.loading).toBe(true)
        return []
      })

      await useProjectStore().fetchProjects()
      expect(useProjectStore().loading).toBe(false)
    })

    it('请求失败时 loading 应该恢复为 false', async () => {
      mockAllRequestReject(new Error('Network error'))

      const store = useProjectStore()
      await expect(store.fetchProjects()).rejects.toThrow()
      expect(store.loading).toBe(false)
    })
  })

  describe('createProject', () => {
    it('应该创建新项目并添加到列表', async () => {
      const newProject = {
        alias: 'new-project',
        local_path: '/local/np',
        remote_path: '/remote/np',
        ssh_alias: 'server1',
        project_type: 'vite',
      }
      mockAllRequestMethods(newProject)

      const store = useProjectStore()
      const result = await store.createProject(newProject)

      expect(result).toEqual(newProject)
      expect(store.projects).toContainEqual(newProject)
    })

    it('应该支持创建带 jdk_version 的 Java 项目', async () => {
      const newProject = {
        alias: 'java-project',
        remote_path: '/remote/jp',
        ssh_alias: 'server1',
        jdk_version: '17',
      }
      mockAllRequestMethods(newProject)

      const store = useProjectStore()
      const result = await store.createProject(newProject)

      expect(result.jdk_version).toBe('17')
    })
  })

  describe('updateProject', () => {
    it('应该更新现有项目', async () => {
      const store = useProjectStore()
      store.projects.push({
        alias: 'project1',
        local_path: '/local/p1',
        remote_path: '/remote/p1',
        ssh_alias: 'server1',
      })

      const updatedProject = { alias: 'project1', local_path: '/local/p1', remote_path: '/remote/p1-updated', ssh_alias: 'server1' }
      mockAllRequestMethods(updatedProject)

      const result = await store.updateProject('project1', { remote_path: '/remote/p1-updated' })

      expect(result).toEqual(updatedProject)
      expect(store.projects[0].remote_path).toBe('/remote/p1-updated')
    })

    it('当项目不存在时应该只返回更新结果', async () => {
      const updatedProject = { alias: 'nonexistent', remote_path: '/remote/np' }
      mockAllRequestMethods(updatedProject)

      const store = useProjectStore()
      const result = await store.updateProject('nonexistent', { remote_path: '/remote/np' })

      expect(result).toEqual(updatedProject)
      expect(store.projects).toEqual([])
    })
  })

  describe('deleteProject', () => {
    it('应该从列表中删除项目', async () => {
      const store = useProjectStore()
      store.projects.push({ alias: 'p1', local_path: '/local/p1', remote_path: '/remote/p1', ssh_alias: 's1' })
      store.projects.push({ alias: 'p2', local_path: '/local/p2', remote_path: '/remote/p2', ssh_alias: 's2' })

      mockAllRequestMethods({})

      await store.deleteProject('p1')

      expect(store.projects.length).toBe(1)
      expect(store.projects[0].alias).toBe('p2')
    })

    it('应该调用正确的 DELETE API', async () => {
      mockAllRequestMethods({})

      const store = useProjectStore()
      await store.deleteProject('project1')

      expect(api.request.delete).toHaveBeenCalledWith('/projects/project1')
    })
  })
})
