import { describe, it, expect, vi, beforeEach } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useWebsshStore } from '@/stores/websshStore'
import { mockGet, mockPost } from '../setup'

describe('WebSSH Store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  describe('状态初始化', () => {
    it('应该正确初始化 sessions 为空数组', () => {
      const store = useWebsshStore()
      expect(store.sessions).toEqual([])
    })

    it('应该正确初始化 historyRecords 为空数组', () => {
      const store = useWebsshStore()
      expect(store.historyRecords).toEqual([])
    })

    it('应该正确初始化 activeSessionId 为空字符串', () => {
      const store = useWebsshStore()
      expect(store.activeSessionId).toBe('')
    })

    it('应该正确初始化 loading 为 false', () => {
      const store = useWebsshStore()
      expect(store.loading).toBe(false)
    })
  })

  describe('listSessions', () => {
    it('应该获取会话列表', async () => {
      const mockSessions = [
        { session_id: 's1', account_alias: 'server1', host: '192.168.1.1', port: 22, username: 'root', status: 'connected', connected_at: '2024-01-01' },
      ]
      mockGet.mockResolvedValue({ sessions: mockSessions })

      const store = useWebsshStore()
      const result = await store.listSessions()

      expect(store.sessions).toHaveLength(1)
      expect(store.sessions[0].id).toBe('s1')
      expect(store.sessions[0].alias).toBe('server1')
      expect(store.sessions[0].status).toBe('online')
    })

    it('应该正确映射 status 字段', async () => {
      const mockSessions = [
        { session_id: 's1', host: '192.168.1.1', port: 22, username: 'root', status: 'connected' },
        { session_id: 's2', host: '192.168.1.2', port: 22, username: 'root', status: 'disconnected' },
        { session_id: 's3', host: '192.168.1.3', port: 22, username: 'root', status: 'connecting' },
      ]
      mockGet.mockResolvedValue({ sessions: mockSessions })

      const store = useWebsshStore()
      await store.listSessions()

      expect(store.sessions[0].status).toBe('online')
      expect(store.sessions[1].status).toBe('offline')
      expect(store.sessions[2].status).toBe('connecting')
    })

    it('应该支持 id 字段映射', async () => {
      const mockSessions = [
        { id: 's1', alias: 'server1', host: '192.168.1.1', port: 22, username: 'root', status: 'connected', created_at: '2024-01-01' },
      ]
      mockGet.mockResolvedValue({ sessions: mockSessions })

      const store = useWebsshStore()
      await store.listSessions()

      expect(store.sessions[0].id).toBe('s1')
      expect(store.sessions[0].alias).toBe('server1')
      expect(store.sessions[0].connected_at).toBe('2024-01-01')
    })

    it('API 返回数组格式时应该正确处理', async () => {
      const mockSessions = [
        { session_id: 's1', host: '192.168.1.1', port: 22, username: 'root', status: 'connected' },
      ]
      mockGet.mockResolvedValue(mockSessions)

      const store = useWebsshStore()
      await store.listSessions()

      expect(store.sessions).toHaveLength(1)
    })

    it('请求期间 loading 应该为 true', async () => {
      mockGet.mockImplementation(async () => {
        const store = useWebsshStore()
        expect(store.loading).toBe(true)
        return { sessions: [] }
      })

      const store = useWebsshStore()
      await store.listSessions()
      expect(store.loading).toBe(false)
    })

    it('请求失败时 loading 应该恢复为 false', async () => {
      mockGet.mockRejectedValue(new Error('Network error'))

      const store = useWebsshStore()
      await expect(store.listSessions()).rejects.toThrow()
      expect(store.loading).toBe(false)
    })
  })

  describe('fetchHistory', () => {
    it('应该获取历史记录', async () => {
      const mockHistory = [
        { session_id: 's1', account_alias: 'server1', host: '192.168.1.1', port: 22, username: 'root', disconnected_at: '2024-01-01' },
      ]
      mockGet.mockResolvedValue({ sessions: mockHistory })

      const store = useWebsshStore()
      await store.fetchHistory()

      expect(store.historyRecords).toHaveLength(1)
      expect(store.historyRecords[0].session_id).toBe('s1')
    })

    it('请求失败时应该静默处理', async () => {
      mockGet.mockRejectedValue(new Error('Network error'))

      const store = useWebsshStore()
      await store.fetchHistory()

      expect(store.historyRecords).toEqual([])
    })
  })

  describe('connect', () => {
    it('应该创建新会话', async () => {
      const mockResponse = {
        session: { session_id: 's1', account_alias: 'server1', host: '192.168.1.1', port: 22, username: 'root' },
      }
      mockPost.mockResolvedValue(mockResponse)

      const store = useWebsshStore()
      const result = await store.connect({ host: '192.168.1.1', port: 22, username: 'root', auth_type: 'password', password: 'secret' })

      expect(store.sessions).toHaveLength(1)
      expect(store.sessions[0].id).toBe('s1')
      expect(store.sessions[0].status).toBe('online')
      expect(store.activeSessionId).toBe('s1')
      expect(result.id).toBe('s1')
    })

    it('应该支持 id 字段映射', async () => {
      const mockResponse = {
        session: { id: 's1', alias: 'server1', host: '192.168.1.1', port: 22, username: 'root' },
      }
      mockPost.mockResolvedValue(mockResponse)

      const store = useWebsshStore()
      const result = await store.connect({ host: '192.168.1.1', port: 22, username: 'root' })

      expect(result.id).toBe('s1')
      expect(result.alias).toBe('server1')
    })

    it('应该支持无 session 包装的响应', async () => {
      const mockResponse = { session_id: 's1', account_alias: 'server1', host: '192.168.1.1', port: 22, username: 'root' }
      mockPost.mockResolvedValue(mockResponse)

      const store = useWebsshStore()
      const result = await store.connect({ host: '192.168.1.1', port: 22, username: 'root' })

      expect(result.id).toBe('s1')
    })
  })

  describe('disconnect', () => {
    it('应该断开会话并从列表中移除', async () => {
      mockPost.mockResolvedValue({})
      mockGet.mockResolvedValue({ sessions: [] })

      const store = useWebsshStore()
      store.sessions = [
        { id: 's1', alias: 'server1', host: '192.168.1.1', port: 22, username: 'root', status: 'online' },
        { id: 's2', alias: 'server2', host: '192.168.1.2', port: 22, username: 'root', status: 'online' },
      ] as any
      store.activeSessionId = 's1'

      await store.disconnect('s1')

      expect(store.sessions).toHaveLength(1)
      expect(store.sessions[0].id).toBe('s2')
    })

    it('断开当前活动会话时应该切换到第一个剩余会话', async () => {
      mockPost.mockResolvedValue({})
      mockGet.mockResolvedValue({ sessions: [] })

      const store = useWebsshStore()
      store.sessions = [
        { id: 's1', alias: 'server1', host: '192.168.1.1', port: 22, username: 'root', status: 'online' },
        { id: 's2', alias: 'server2', host: '192.168.1.2', port: 22, username: 'root', status: 'online' },
      ] as any
      store.activeSessionId = 's1'

      await store.disconnect()

      expect(store.activeSessionId).toBe('s2')
    })

    it('断开最后一个会话时应该清空 activeSessionId', async () => {
      mockPost.mockResolvedValue({})
      mockGet.mockResolvedValue({ sessions: [] })

      const store = useWebsshStore()
      store.sessions = [
        { id: 's1', alias: 'server1', host: '192.168.1.1', port: 22, username: 'root', status: 'online' },
      ] as any
      store.activeSessionId = 's1'

      await store.disconnect('s1')

      expect(store.sessions).toHaveLength(0)
      expect(store.activeSessionId).toBe('')
    })

    it('断开后应该刷新历史记录', async () => {
      mockPost.mockResolvedValue({})
      mockGet.mockResolvedValue({ sessions: [] })

      const store = useWebsshStore()
      store.sessions = [
        { id: 's1', alias: 'server1', host: '192.168.1.1', port: 22, username: 'root', status: 'online' },
      ] as any
      store.activeSessionId = 's1'

      await store.disconnect('s1')

      expect(mockGet).toHaveBeenCalledWith('/webssh/sessions/history')
    })

    it('不传参数时应该断开当前活动会话', async () => {
      mockPost.mockResolvedValue({})
      mockGet.mockResolvedValue({ sessions: [] })

      const store = useWebsshStore()
      store.sessions = [
        { id: 's1', alias: 'server1', host: '192.168.1.1', port: 22, username: 'root', status: 'online' },
      ] as any
      store.activeSessionId = 's1'

      await store.disconnect()

      expect(mockPost).toHaveBeenCalledWith('/webssh/disconnect', { session_id: 's1' })
    })
  })

  describe('setActiveSession', () => {
    it('应该设置活动会话 ID', () => {
      const store = useWebsshStore()
      store.setActiveSession('s1')

      expect(store.activeSessionId).toBe('s1')
    })
  })

  describe('resizeTerminal', () => {
    it('应该调整终端大小', async () => {
      mockPost.mockResolvedValue({})

      const store = useWebsshStore()
      await store.resizeTerminal('s1', 120, 40)

      expect(mockPost).toHaveBeenCalledWith('/webssh/resize', { session_id: 's1', width: 120, height: 40 })
    })
  })

  describe('sendCommand', () => {
    it('应该发送命令', async () => {
      mockPost.mockResolvedValue({})

      const store = useWebsshStore()
      await store.sendCommand('s1', 'ls -la')

      expect(mockPost).toHaveBeenCalledWith('/webssh/command', { session_id: 's1', command: 'ls -la' })
    })
  })

  describe('getHistory', () => {
    it('应该获取会话命令历史', async () => {
      const mockHistory = ['ls -la', 'cd /home', 'pwd']
      mockGet.mockResolvedValue(mockHistory)

      const store = useWebsshStore()
      const result = await store.getHistory('s1')

      expect(result).toEqual(mockHistory)
      expect(mockGet).toHaveBeenCalledWith('/webssh/history/s1')
    })
  })
})
