/**
 * SSH Account Store 单元测试
 * 测试 CRUD 操作、连接测试、状态管理和群组管理
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useSshAccountStore } from '@/stores/sshAccountStore'
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

describe('SSH Account Store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  describe('状态初始化', () => {
    it('应该正确初始化 accounts 为空数组', () => {
      const store = useSshAccountStore()
      expect(store.accounts).toEqual([])
    })

    it('应该正确初始化 groups 为空数组', () => {
      const store = useSshAccountStore()
      expect(store.groups).toEqual([])
    })

    it('应该正确初始化 defaultAlias 为空字符串', () => {
      const store = useSshAccountStore()
      expect(store.defaultAlias).toBe('')
    })

    it('应该正确初始化 loading 为 false', () => {
      const store = useSshAccountStore()
      expect(store.loading).toBe(false)
    })
  })

  describe('fetchAccounts', () => {
    it('应该获取账户列表', async () => {
      const mockAccounts = [
        { alias: 'server1', host: '192.168.1.1', port: 22, username: 'root', auth_type: 'password' as const },
        { alias: 'server2', host: '192.168.1.2', port: 22, username: 'admin', auth_type: 'key' as const, default: true },
      ]
      mockAllRequestMethods(mockAccounts)

      const store = useSshAccountStore()
      await store.fetchAccounts()

      expect(store.accounts).toEqual(mockAccounts)
    })

    it('应该自动设置默认账户', async () => {
      const mockAccounts = [
        { alias: 'server1', host: '192.168.1.1', port: 22, username: 'root', auth_type: 'password' as const },
        { alias: 'server2', host: '192.168.1.2', port: 22, username: 'admin', auth_type: 'key' as const, default: true },
      ]
      mockAllRequestMethods(mockAccounts)

      const store = useSshAccountStore()
      await store.fetchAccounts()

      expect(store.defaultAlias).toBe('server2')
    })

    it('请求期间 loading 应该为 true', async () => {
      mockAllRequestImplementation(async () => {
        const store = useSshAccountStore()
        expect(store.loading).toBe(true)
        return []
      })

      await useSshAccountStore().fetchAccounts()
      expect(useSshAccountStore().loading).toBe(false)
    })

    it('请求失败时 loading 应该恢复为 false', async () => {
      mockAllRequestReject(new Error('Network error'))

      const store = useSshAccountStore()
      await expect(store.fetchAccounts()).rejects.toThrow()
      expect(store.loading).toBe(false)
    })
  })

  describe('createAccount', () => {
    it('应该创建新账户并添加到列表', async () => {
      const newAccount = {
        alias: 'new-server',
        host: '10.0.0.1',
        port: 22,
        username: 'deploy',
        auth_type: 'key' as const,
        private_key: 'ssh-rsa ...',
      }
      mockAllRequestMethods(newAccount)

      const store = useSshAccountStore()
      const result = await store.createAccount(newAccount)

      expect(result).toEqual(newAccount)
      expect(store.accounts).toContainEqual(newAccount)
    })

    it('应该返回创建的账户数据', async () => {
      const newAccount = { alias: 'test', host: '1.2.3.4', port: 22, username: 'root', auth_type: 'password' as const }
      mockAllRequestMethods(newAccount)

      const store = useSshAccountStore()
      const result = await store.createAccount(newAccount)

      expect(result.alias).toBe('test')
    })
  })

  describe('updateAccount', () => {
    it('应该更新现有账户', async () => {
      const store = useSshAccountStore()
      store.accounts.push({
        alias: 'server1',
        host: '192.168.1.1',
        port: 22,
        username: 'root',
        auth_type: 'password' as const,
      })

      const updatedData = { host: '10.0.0.1', port: 2222 }
      const updatedAccount = { ...store.accounts[0], ...updatedData }
      mockAllRequestMethods(updatedAccount)

      const result = await store.updateAccount('server1', updatedData)

      expect(result).toEqual(updatedAccount)
      expect(store.accounts[0]).toEqual(updatedAccount)
    })

    it('当账户不存在时应该只返回更新结果', async () => {
      const updatedAccount = { alias: 'nonexistent', host: '10.0.0.1', port: 22, username: 'root', auth_type: 'password' as const }
      mockAllRequestMethods(updatedAccount)

      const store = useSshAccountStore()
      const result = await store.updateAccount('nonexistent', { host: '10.0.0.1' })

      expect(result).toEqual(updatedAccount)
      expect(store.accounts).toEqual([])
    })
  })

  describe('deleteAccount', () => {
    it('应该从列表中删除账户', async () => {
      const store = useSshAccountStore()
      store.accounts.push({ alias: 'server1', host: '1.2.3.4', port: 22, username: 'root', auth_type: 'password' as const })
      store.accounts.push({ alias: 'server2', host: '5.6.7.8', port: 22, username: 'admin', auth_type: 'key' as const })

      mockAllRequestMethods({})

      await store.deleteAccount('server1')

      expect(store.accounts.length).toBe(1)
      expect(store.accounts[0].alias).toBe('server2')
    })

    it('删除默认账户时应该清空 defaultAlias', async () => {
      const store = useSshAccountStore()
      store.accounts.push({ alias: 'server1', host: '1.2.3.4', port: 22, username: 'root', auth_type: 'password' as const, default: true })
      store.defaultAlias = 'server1'

      mockAllRequestMethods({})

      await store.deleteAccount('server1')

      expect(store.defaultAlias).toBe('')
    })

    it('应该调用正确的 DELETE API', async () => {
      mockAllRequestMethods({})

      const store = useSshAccountStore()
      await store.deleteAccount('server1')

      expect(api.request.delete).toHaveBeenCalledWith('/accounts/server1')
    })
  })

  describe('testConnection', () => {
    it('连接成功时应该设置状态为 online', async () => {
      const store = useSshAccountStore()
      store.accounts.push({ alias: 'server1', host: '1.2.3.4', port: 22, username: 'root', auth_type: 'password' as const, status: 'unknown' })

      mockAllRequestMethods({ success: true, message: 'Connected' })

      const result = await store.testConnection('server1')

      expect(result.success).toBe(true)
      expect(store.accounts[0].status).toBe('online')
    })

    it('连接失败时应该设置状态为 offline', async () => {
      const store = useSshAccountStore()
      store.accounts.push({ alias: 'server1', host: '1.2.3.4', port: 22, username: 'root', auth_type: 'password' as const, status: 'unknown' })

      mockAllRequestMethods({ success: false, message: 'Connection refused' })

      const result = await store.testConnection('server1')

      expect(result.success).toBe(false)
      expect(store.accounts[0].status).toBe('offline')
    })

    it('当账户不存在时应该只返回结果', async () => {
      mockAllRequestMethods({ success: true, message: 'OK' })

      const store = useSshAccountStore()
      const result = await store.testConnection('nonexistent')

      expect(result.success).toBe(true)
    })
  })

  describe('setDefault', () => {
    it('应该设置默认账户', async () => {
      const store = useSshAccountStore()
      store.accounts.push(
        { alias: 'server1', host: '1.2.3.4', port: 22, username: 'root', auth_type: 'password' as const },
        { alias: 'server2', host: '5.6.7.8', port: 22, username: 'admin', auth_type: 'key' as const }
      )

      mockAllRequestMethods({})

      await store.setDefault('server2')

      expect(store.defaultAlias).toBe('server2')
      expect(store.accounts[0].default).toBe(false)
      expect(store.accounts[1].default).toBe(true)
    })

    it('应该调用正确的 API', async () => {
      mockAllRequestMethods({})

      const store = useSshAccountStore()
      await store.setDefault('server1')

      expect(api.request.post).toHaveBeenCalledWith('/accounts/server1/default')
    })
  })

  describe('fetchGroups', () => {
    it('应该获取群组列表', async () => {
      const mockGroups = [
        { name: 'production', accounts: ['server1', 'server2'] },
        { name: 'staging', accounts: ['server3'] },
      ]
      mockAllRequestMethods(mockGroups)

      const store = useSshAccountStore()
      await store.fetchGroups()

      expect(store.groups).toEqual(mockGroups)
    })
  })

  describe('createGroup', () => {
    it('应该创建新群组并添加到列表', async () => {
      const newGroup = { name: 'production', accounts: ['server1', 'server2'] }
      mockAllRequestMethods(newGroup)

      const store = useSshAccountStore()
      const result = await store.createGroup('production', ['server1', 'server2'])

      expect(result).toEqual(newGroup)
      expect(store.groups).toContainEqual(newGroup)
    })

    it('应该支持不带 accounts 创建群组', async () => {
      const newGroup = { name: 'empty-group', accounts: [] }
      mockAllRequestMethods(newGroup)

      const store = useSshAccountStore()
      await store.createGroup('empty-group')

      expect(api.request.post).toHaveBeenCalledWith('/accounts/groups', { name: 'empty-group', accounts: [] })
    })
  })

  describe('updateGroup', () => {
    it('应该更新现有群组', async () => {
      const store = useSshAccountStore()
      store.groups.push({ name: 'production', accounts: ['server1'] })

      const updatedGroup = { name: 'production-updated', accounts: ['server1', 'server2'] }
      mockAllRequestMethods(updatedGroup)

      const result = await store.updateGroup('production', { new_name: 'production-updated', accounts: ['server1', 'server2'] })

      expect(result).toEqual(updatedGroup)
      expect(store.groups[0]).toEqual(updatedGroup)
    })

    it('群组改名时应该同步更新账户的 group 字段', async () => {
      const store = useSshAccountStore()
      store.groups.push({ name: 'old-name', accounts: ['server1'] })
      store.accounts.push({ alias: 'server1', host: '1.2.3.4', port: 22, username: 'root', auth_type: 'password' as const, group: 'old-name' })

      mockAllRequestMethods({ name: 'new-name', accounts: ['server1'] })

      await store.updateGroup('old-name', { new_name: 'new-name' })

      expect(store.accounts[0].group).toBe('new-name')
    })
  })

  describe('deleteGroup', () => {
    it('应该从列表中删除群组', async () => {
      const store = useSshAccountStore()
      store.groups.push({ name: 'production', accounts: ['server1'] })
      store.groups.push({ name: 'staging', accounts: ['server2'] })

      mockAllRequestMethods({})

      await store.deleteGroup('production')

      expect(store.groups.length).toBe(1)
      expect(store.groups[0].name).toBe('staging')
    })

    it('删除群组时应该清空相关账户的 group 字段', async () => {
      const store = useSshAccountStore()
      store.accounts.push({ alias: 'server1', host: '1.2.3.4', port: 22, username: 'root', auth_type: 'password' as const, group: 'production' })

      mockAllRequestMethods({})

      await store.deleteGroup('production')

      expect(store.accounts[0].group).toBeUndefined()
    })
  })
})
