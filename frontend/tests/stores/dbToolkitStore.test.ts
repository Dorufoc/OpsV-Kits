import { describe, it, expect, vi, beforeEach } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useDbToolkitStore } from '@/stores/dbToolkitStore'
import * as api from '@/api'

describe('DbToolkit Store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    localStorage.clear()
  })

  describe('状态初始化', () => {
    it('应该正确初始化 mysqlConnection 为 null', () => {
      const store = useDbToolkitStore()
      expect(store.mysqlConnection).toBeNull()
    })

    it('应该正确初始化 redisConnection 为 null', () => {
      const store = useDbToolkitStore()
      expect(store.redisConnection).toBeNull()
    })

    it('应该正确初始化 mysqlDetectResult 为 null', () => {
      const store = useDbToolkitStore()
      expect(store.mysqlDetectResult).toBeNull()
    })

    it('应该正确初始化 redisDetectResult 为 null', () => {
      const store = useDbToolkitStore()
      expect(store.redisDetectResult).toBeNull()
    })

    it('应该正确初始化 mysqlQueryResult 为 null', () => {
      const store = useDbToolkitStore()
      expect(store.mysqlQueryResult).toBeNull()
    })

    it('应该正确初始化 mysqlQueryLoading 为 false', () => {
      const store = useDbToolkitStore()
      expect(store.mysqlQueryLoading).toBe(false)
    })

    it('应该正确初始化 mysqlTables 为空数组', () => {
      const store = useDbToolkitStore()
      expect(store.mysqlTables).toEqual([])
    })

    it('应该正确初始化 mysqlTableStructure 为 null', () => {
      const store = useDbToolkitStore()
      expect(store.mysqlTableStructure).toBeNull()
    })

    it('应该正确初始化 mysqlQueryHistory 为空数组', () => {
      const store = useDbToolkitStore()
      expect(store.mysqlQueryHistory).toEqual([])
    })

    it('应该正确初始化 redisScanResult 为 null', () => {
      const store = useDbToolkitStore()
      expect(store.redisScanResult).toBeNull()
    })

    it('应该正确初始化 redisKeyInfo 为 null', () => {
      const store = useDbToolkitStore()
      expect(store.redisKeyInfo).toBeNull()
    })

    it('应该正确初始化 redisDbStats 为 null', () => {
      const store = useDbToolkitStore()
      expect(store.redisDbStats).toBeNull()
    })

    it('应该正确初始化 redisScanLoading 为 false', () => {
      const store = useDbToolkitStore()
      expect(store.redisScanLoading).toBe(false)
    })

    it('应该正确初始化 savedConnections 为空数组', () => {
      const store = useDbToolkitStore()
      expect(store.savedConnections).toEqual([])
    })

    it('应该正确初始化 activeConnection 为 null', () => {
      const store = useDbToolkitStore()
      expect(store.activeConnection).toBeNull()
    })

    it('应该正确初始化 activeDeployMode 为 docker', () => {
      const store = useDbToolkitStore()
      expect(store.activeDeployMode).toBe('docker')
    })

    it('应该正确初始化 sidebarCollapsed 为 false', () => {
      const store = useDbToolkitStore()
      expect(store.sidebarCollapsed).toBe(false)
    })

    it('应该正确初始化 selectedTreeNode 为 null', () => {
      const store = useDbToolkitStore()
      expect(store.selectedTreeNode).toBeNull()
    })

    it('应该正确初始化 currentViewMode 为 welcome', () => {
      const store = useDbToolkitStore()
      expect(store.currentViewMode).toBe('welcome')
    })

    it('应该正确初始化 mysqlDatabases 为空数组', () => {
      const store = useDbToolkitStore()
      expect(store.mysqlDatabases).toEqual([])
    })
  })

  describe('连接管理 - localStorage', () => {
    it('loadConnections 应该从 localStorage 加载连接', () => {
      const savedData = [
        { id: 'c1', name: 'My MySQL', dbType: 'mysql', deployMode: 'docker', connection: {}, createdAt: 1000, updatedAt: 1000, favorite: false },
      ]
      localStorage.setItem('opsv-db-connections', JSON.stringify(savedData))

      const store = useDbToolkitStore()
      store.loadConnections()

      expect(store.savedConnections).toEqual(savedData)
    })

    it('loadConnections 在 localStorage 为空时应该保持空数组', () => {
      const store = useDbToolkitStore()
      store.loadConnections()

      expect(store.savedConnections).toEqual([])
    })

    it('loadConnections 在数据损坏时应该重置为空数组', () => {
      localStorage.setItem('opsv-db-connections', 'invalid-json')

      const store = useDbToolkitStore()
      store.loadConnections()

      expect(store.savedConnections).toEqual([])
    })

    it('saveConnections 应该持久化到 localStorage', () => {
      const store = useDbToolkitStore()
      store.addConnection({ name: 'Test', dbType: 'mysql', deployMode: 'docker', connection: {} })

      const stored = localStorage.getItem('opsv-db-connections')
      expect(stored).toBeTruthy()
      const parsed = JSON.parse(stored!)
      expect(parsed).toHaveLength(1)
      expect(parsed[0].name).toBe('Test')
    })
  })

  describe('addConnection', () => {
    it('应该添加新连接并生成 id 和时间戳', () => {
      const store = useDbToolkitStore()
      store.addConnection({ name: 'My DB', dbType: 'mysql', deployMode: 'docker', connection: {} })

      expect(store.savedConnections).toHaveLength(1)
      expect(store.savedConnections[0].name).toBe('My DB')
      expect(store.savedConnections[0].id).toBeTruthy()
      expect(store.savedConnections[0].createdAt).toBeGreaterThan(0)
      expect(store.savedConnections[0].updatedAt).toBeGreaterThan(0)
    })
  })

  describe('updateConnection', () => {
    it('应该更新指定连接', () => {
      vi.useFakeTimers()
      const store = useDbToolkitStore()
      store.addConnection({ name: 'Old Name', dbType: 'mysql', deployMode: 'docker', connection: {} })
      vi.advanceTimersByTime(1000)
      store.updateConnection(store.savedConnections[0].id, { name: 'New Name' })

      expect(store.savedConnections[0].name).toBe('New Name')
      expect(store.savedConnections[0].updatedAt).toBeGreaterThan(store.savedConnections[0].createdAt)
      vi.useRealTimers()
    })

    it('更新不存在的连接时应该不报错', () => {
      const store = useDbToolkitStore()
      store.updateConnection('nonexistent', { name: 'Test' })

      expect(store.savedConnections).toEqual([])
    })
  })

  describe('removeConnection', () => {
    it('应该删除指定连接', () => {
      const store = useDbToolkitStore()
      store.addConnection({ name: 'Conn1', dbType: 'mysql', deployMode: 'docker', connection: {} })
      store.addConnection({ name: 'Conn2', dbType: 'redis', deployMode: 'local', connection: {} })

      const connId = store.savedConnections[0].id
      store.removeConnection(connId)

      expect(store.savedConnections).toHaveLength(1)
      expect(store.savedConnections[0].name).toBe('Conn2')
    })
  })

  describe('toggleFavorite', () => {
    it('应该切换连接的收藏状态', () => {
      const store = useDbToolkitStore()
      store.addConnection({ name: 'Fav', dbType: 'mysql', deployMode: 'docker', connection: {} })

      const connId = store.savedConnections[0].id
      expect(store.savedConnections[0].favorite).toBeFalsy()

      store.toggleFavorite(connId)
      expect(store.savedConnections[0].favorite).toBe(true)

      store.toggleFavorite(connId)
      expect(store.savedConnections[0].favorite).toBe(false)
    })
  })

  describe('setActiveConnection', () => {
    it('应该设置活动连接并更新 deployMode', () => {
      const store = useDbToolkitStore()
      const conn = {
        id: 'c1', name: 'Active', dbType: 'mysql' as const, deployMode: 'local' as const,
        connection: { host: 'localhost', port: 3306, username: 'root', password: '', database: 'test' },
        createdAt: 1000, updatedAt: 1000, favorite: false,
      }
      store.setActiveConnection(conn)

      expect(store.activeConnection).toEqual(conn)
      expect(store.activeDeployMode).toBe('local')
      expect(store.mysqlConnection).toEqual(conn.connection)
    })

    it('设置 Redis 连接时应该更新 redisConnection', () => {
      const store = useDbToolkitStore()
      const conn = {
        id: 'c2', name: 'Redis', dbType: 'redis' as const, deployMode: 'docker' as const,
        connection: { host: 'localhost', port: 6379, password: '', db: 0 },
        createdAt: 1000, updatedAt: 1000, favorite: false,
      }
      store.setActiveConnection(conn)

      expect(store.redisConnection).toEqual(conn.connection)
    })

    it('传入 null 时应该清空活动连接', () => {
      const store = useDbToolkitStore()
      store.setActiveConnection(null)

      expect(store.activeConnection).toBeNull()
    })
  })

  describe('setViewMode', () => {
    it('应该更新 currentViewMode', () => {
      const store = useDbToolkitStore()
      store.setViewMode('data')

      expect(store.currentViewMode).toBe('data')
    })
  })

  describe('toggleSidebar', () => {
    it('应该切换侧边栏折叠状态', () => {
      const store = useDbToolkitStore()
      expect(store.sidebarCollapsed).toBe(false)

      store.toggleSidebar()
      expect(store.sidebarCollapsed).toBe(true)

      store.toggleSidebar()
      expect(store.sidebarCollapsed).toBe(false)
    })
  })

  describe('selectTreeNode', () => {
    it('选择 database 节点时应该切换到 data 视图', () => {
      const store = useDbToolkitStore()
      store.selectTreeNode({ id: 'db1', label: 'mydb', type: 'database', children: [] } as any)

      expect(store.selectedTreeNode?.type).toBe('database')
      expect(store.currentViewMode).toBe('data')
    })

    it('选择 table 节点时应该切换到 structure 视图', () => {
      const store = useDbToolkitStore()
      store.selectTreeNode({ id: 't1', label: 'users', type: 'table' } as any)

      expect(store.currentViewMode).toBe('structure')
    })

    it('选择 redis-db 节点时应该切换到 redis-browse 视图', () => {
      const store = useDbToolkitStore()
      store.selectTreeNode({ id: 'rd1', label: 'db0', type: 'redis-db' } as any)

      expect(store.currentViewMode).toBe('redis-browse')
    })

    it('传入 null 时应该清空选中节点', () => {
      const store = useDbToolkitStore()
      store.selectTreeNode({ id: 'db1', label: 'mydb', type: 'database', children: [] } as any)
      store.selectTreeNode(null)

      expect(store.selectedTreeNode).toBeNull()
    })
  })

  describe('detectClient', () => {
    it('应该检测 MySQL 客户端', async () => {
      const mockResult = { installed: true, client_name: 'mysql', version: '8.0' }
      vi.mocked(api.request.get).mockResolvedValue(mockResult as any)

      const store = useDbToolkitStore()
      const result = await store.detectClient('mysql', 'test-server')

      expect(store.mysqlDetectResult).toEqual(mockResult)
      expect(result).toEqual(mockResult)
    })

    it('应该检测 Redis 客户端', async () => {
      const mockResult = { installed: true, client_name: 'redis-cli', version: '7.0' }
      vi.mocked(api.request.get).mockResolvedValue(mockResult as any)

      const store = useDbToolkitStore()
      const result = await store.detectClient('redis', 'test-server')

      expect(store.redisDetectResult).toEqual(mockResult)
    })

    it('带 containerId 时应该传递参数', async () => {
      vi.mocked(api.request.get).mockResolvedValue({ installed: true } as any)

      const store = useDbToolkitStore()
      await store.detectClient('mysql', 'test-server', 'container-1')

      expect(api.request.get).toHaveBeenCalledWith('/db-toolkit/detect/mysql', {
        params: { account_alias: 'test-server', container_id: 'container-1' },
      })
    })
  })

  describe('connectMysql / disconnectMysql', () => {
    it('connectMysql 应该设置 mysqlConnection', () => {
      const store = useDbToolkitStore()
      const params = { host: 'localhost', port: 3306, username: 'root', password: 'pass', database: 'test' }
      store.connectMysql(params)

      expect(store.mysqlConnection).toEqual(params)
    })

    it('disconnectMysql 应该清空 MySQL 相关状态', () => {
      const store = useDbToolkitStore()
      store.connectMysql({ host: 'localhost', port: 3306, username: 'root', password: '', database: 'test' })

      store.disconnectMysql()

      expect(store.mysqlConnection).toBeNull()
      expect(store.mysqlQueryResult).toBeNull()
      expect(store.mysqlTables).toEqual([])
      expect(store.mysqlTableStructure).toBeNull()
    })
  })

  describe('connectRedis / disconnectRedis', () => {
    it('connectRedis 应该设置 redisConnection', () => {
      const store = useDbToolkitStore()
      const params = { host: 'localhost', port: 6379, password: '', db: 0 }
      store.connectRedis(params)

      expect(store.redisConnection).toEqual(params)
    })

    it('disconnectRedis 应该清空 Redis 相关状态', () => {
      const store = useDbToolkitStore()
      store.connectRedis({ host: 'localhost', port: 6379, password: '', db: 0 })

      store.disconnectRedis()

      expect(store.redisConnection).toBeNull()
      expect(store.redisScanResult).toBeNull()
      expect(store.redisKeyInfo).toBeNull()
      expect(store.redisDbStats).toBeNull()
    })
  })

  describe('checkDangerousSql', () => {
    it('应该检查危险 SQL', async () => {
      const mockResult = { dangerous: false, warnings: [] }
      vi.mocked(api.request.post).mockResolvedValue(mockResult as any)

      const store = useDbToolkitStore()
      const result = await store.checkDangerousSql('SELECT * FROM users')

      expect(result).toEqual(mockResult)
      expect(api.request.post).toHaveBeenCalledWith('/db-toolkit/check-dangerous-sql', { sql: 'SELECT * FROM users' })
    })
  })

  describe('checkDangerousRedisCommand', () => {
    it('应该检查危险 Redis 命令', async () => {
      const mockResult = { dangerous: true, warnings: ['FLUSHALL will delete all data'] }
      vi.mocked(api.request.post).mockResolvedValue(mockResult as any)

      const store = useDbToolkitStore()
      const result = await store.checkDangerousRedisCommand('FLUSHALL')

      expect(result).toEqual(mockResult)
      expect(api.request.post).toHaveBeenCalledWith('/db-toolkit/check-dangerous-redis', { command: 'FLUSHALL' })
    })
  })

  describe('executeMysqlQuery', () => {
    it('未连接时应该抛出错误', async () => {
      const store = useDbToolkitStore()
      await expect(store.executeMysqlQuery('test-server', undefined, 'SELECT 1'))
        .rejects.toThrow('MySQL 未连接')
    })

    it('应该执行查询并更新结果', async () => {
      const mockResult = { rows: [['1']], columns: ['1'], error: null }
      vi.mocked(api.request.post).mockResolvedValue(mockResult as any)

      const store = useDbToolkitStore()
      store.connectMysql({ host: 'localhost', port: 3306, username: 'root', password: '', database: 'test' })
      const result = await store.executeMysqlQuery('test-server', undefined, 'SELECT 1')

      expect(store.mysqlQueryResult).toEqual(mockResult)
      expect(store.mysqlQueryHistory).toContain('SELECT 1')
    })

    it('请求期间 mysqlQueryLoading 应该为 true', async () => {
      vi.mocked(api.request.post).mockImplementation(async () => {
        const store = useDbToolkitStore()
        expect(store.mysqlQueryLoading).toBe(true)
        return { rows: [], columns: [], error: null }
      })

      const store = useDbToolkitStore()
      store.connectMysql({ host: 'localhost', port: 3306, username: 'root', password: '', database: 'test' })
      await store.executeMysqlQuery('test-server', undefined, 'SELECT 1')
      expect(store.mysqlQueryLoading).toBe(false)
    })

    it('查询出错时不应添加到历史记录', async () => {
      vi.mocked(api.request.post).mockResolvedValue({ rows: [], columns: [], error: 'Syntax error' } as any)

      const store = useDbToolkitStore()
      store.connectMysql({ host: 'localhost', port: 3306, username: 'root', password: '', database: 'test' })
      await store.executeMysqlQuery('test-server', undefined, 'BAD SQL')

      expect(store.mysqlQueryHistory).not.toContain('BAD SQL')
    })

    it('重复 SQL 不应重复添加到历史记录', async () => {
      vi.mocked(api.request.post).mockResolvedValue({ rows: [], columns: [], error: null } as any)

      const store = useDbToolkitStore()
      store.connectMysql({ host: 'localhost', port: 3306, username: 'root', password: '', database: 'test' })
      await store.executeMysqlQuery('test-server', undefined, 'SELECT 1')
      await store.executeMysqlQuery('test-server', undefined, 'SELECT 1')

      expect(store.mysqlQueryHistory).toHaveLength(1)
    })

    it('历史记录不应超过 20 条', async () => {
      vi.mocked(api.request.post).mockImplementation(async (_, data) => {
        return { rows: [], columns: [], error: null }
      })

      const store = useDbToolkitStore()
      store.connectMysql({ host: 'localhost', port: 3306, username: 'root', password: '', database: 'test' })

      for (let i = 0; i < 25; i++) {
        await store.executeMysqlQuery('test-server', undefined, `SELECT ${i}`)
      }

      expect(store.mysqlQueryHistory).toHaveLength(20)
    })
  })

  describe('loadMysqlTables', () => {
    it('未连接时应该抛出错误', async () => {
      const store = useDbToolkitStore()
      await expect(store.loadMysqlTables('test-server'))
        .rejects.toThrow('MySQL 未连接')
    })

    it('应该加载表列表', async () => {
      const mockTables = ['users', 'orders', 'products']
      vi.mocked(api.request.post).mockResolvedValue(mockTables as any)

      const store = useDbToolkitStore()
      store.connectMysql({ host: 'localhost', port: 3306, username: 'root', password: '', database: 'test' })
      const result = await store.loadMysqlTables('test-server')

      expect(store.mysqlTables).toEqual(mockTables)
      expect(result).toEqual(mockTables)
    })
  })

  describe('loadMysqlTableStructure', () => {
    it('未连接时应该抛出错误', async () => {
      const store = useDbToolkitStore()
      await expect(store.loadMysqlTableStructure('test-server', undefined, 'users'))
        .rejects.toThrow('MySQL 未连接')
    })

    it('应该加载表结构', async () => {
      const mockStructure = { name: 'users', columns: [{ name: 'id', type: 'int' }] }
      vi.mocked(api.request.post).mockResolvedValue(mockStructure as any)

      const store = useDbToolkitStore()
      store.connectMysql({ host: 'localhost', port: 3306, username: 'root', password: '', database: 'test' })
      const result = await store.loadMysqlTableStructure('test-server', undefined, 'users')

      expect(store.mysqlTableStructure).toEqual(mockStructure)
    })
  })

  describe('scanRedisKeys', () => {
    it('未连接时应该抛出错误', async () => {
      const store = useDbToolkitStore()
      await expect(store.scanRedisKeys('test-server', undefined))
        .rejects.toThrow('Redis 未连接')
    })

    it('首次扫描应该替换 scanResult', async () => {
      const mockResult = { keys: ['key1', 'key2'], next_cursor: 10, has_more: true }
      vi.mocked(api.request.post).mockResolvedValue(mockResult as any)

      const store = useDbToolkitStore()
      store.connectRedis({ host: 'localhost', port: 6379, password: '', db: 0 })
      const result = await store.scanRedisKeys('test-server', undefined, '*', 0, 100)

      expect(store.redisScanResult).toEqual(mockResult)
    })

    it('续扫描应该追加 keys', async () => {
      const firstResult = { keys: ['key1'], next_cursor: 10, has_more: true }
      const secondResult = { keys: ['key2'], next_cursor: 0, has_more: false }
      vi.mocked(api.request.post)
        .mockResolvedValueOnce(firstResult as any)
        .mockResolvedValueOnce(secondResult as any)

      const store = useDbToolkitStore()
      store.connectRedis({ host: 'localhost', port: 6379, password: '', db: 0 })
      await store.scanRedisKeys('test-server', undefined, '*', 0, 100)
      await store.scanRedisKeys('test-server', undefined, '*', 10, 100)

      expect(store.redisScanResult?.keys).toEqual(['key1', 'key2'])
      expect(store.redisScanResult?.next_cursor).toBe(0)
    })

    it('请求期间 redisScanLoading 应该为 true', async () => {
      vi.mocked(api.request.post).mockImplementation(async () => {
        const store = useDbToolkitStore()
        expect(store.redisScanLoading).toBe(true)
        return { keys: [], next_cursor: 0, has_more: false }
      })

      const store = useDbToolkitStore()
      store.connectRedis({ host: 'localhost', port: 6379, password: '', db: 0 })
      await store.scanRedisKeys('test-server', undefined)
      expect(store.redisScanLoading).toBe(false)
    })
  })

  describe('loadRedisKeyDetail', () => {
    it('未连接时应该抛出错误', async () => {
      const store = useDbToolkitStore()
      await expect(store.loadRedisKeyDetail('test-server', undefined, 'mykey'))
        .rejects.toThrow('Redis 未连接')
    })

    it('应该加载键详情', async () => {
      const mockInfo = { key: 'mykey', type: 'string', value: 'hello', ttl: -1 }
      vi.mocked(api.request.post).mockResolvedValue(mockInfo as any)

      const store = useDbToolkitStore()
      store.connectRedis({ host: 'localhost', port: 6379, password: '', db: 0 })
      const result = await store.loadRedisKeyDetail('test-server', undefined, 'mykey')

      expect(store.redisKeyInfo).toEqual(mockInfo)
    })
  })

  describe('loadRedisDbStats', () => {
    it('未连接时应该抛出错误', async () => {
      const store = useDbToolkitStore()
      await expect(store.loadRedisDbStats('test-server', undefined))
        .rejects.toThrow('Redis 未连接')
    })

    it('应该加载数据库统计', async () => {
      const mockStats = { db: 'db0', keys: 100, expires: 50, avg_ttl: 3600 }
      vi.mocked(api.request.post).mockResolvedValue(mockStats as any)

      const store = useDbToolkitStore()
      store.connectRedis({ host: 'localhost', port: 6379, password: '', db: 0 })
      const result = await store.loadRedisDbStats('test-server', undefined)

      expect(store.redisDbStats).toEqual(mockStats)
    })
  })

  describe('deleteRedisKey', () => {
    it('未连接时应该抛出错误', async () => {
      const store = useDbToolkitStore()
      await expect(store.deleteRedisKey('test-server', undefined, 'mykey'))
        .rejects.toThrow('Redis 未连接')
    })

    it('应该删除键并返回结果', async () => {
      vi.mocked(api.request.delete).mockResolvedValue({ success: true } as any)

      const store = useDbToolkitStore()
      store.connectRedis({ host: 'localhost', port: 6379, password: 'pass', db: 0 })
      const result = await store.deleteRedisKey('test-server', undefined, 'mykey')

      expect(result).toBe(true)
    })
  })

  describe('loadMysqlDatabases', () => {
    it('未连接时应该抛出错误', async () => {
      const store = useDbToolkitStore()
      await expect(store.loadMysqlDatabases('test-server'))
        .rejects.toThrow('MySQL 未连接')
    })

    it('应该加载数据库列表', async () => {
      const mockQueryResult = { rows: [['information_schema'], ['mysql'], ['test_db']], columns: ['Database'], error: null }
      vi.mocked(api.request.post).mockResolvedValue(mockQueryResult as any)

      const store = useDbToolkitStore()
      store.connectMysql({ host: 'localhost', port: 3306, username: 'root', password: '', database: 'test' })
      const result = await store.loadMysqlDatabases('test-server')

      expect(store.mysqlDatabases).toEqual(['information_schema', 'mysql', 'test_db'])
      expect(result).toEqual(['information_schema', 'mysql', 'test_db'])
    })
  })

  describe('switchMysqlDatabase', () => {
    it('应该切换数据库并清空相关状态', () => {
      const store = useDbToolkitStore()
      store.connectMysql({ host: 'localhost', port: 3306, username: 'root', password: '', database: 'old_db' })
      store.mysqlTables = ['table1']
      store.mysqlTableStructure = { name: 'table1', columns: [] } as any
      store.mysqlQueryResult = { rows: [], columns: [], error: null } as any

      store.switchMysqlDatabase('new_db')

      expect(store.mysqlConnection?.database).toBe('new_db')
      expect(store.mysqlTables).toEqual([])
      expect(store.mysqlTableStructure).toBeNull()
      expect(store.mysqlQueryResult).toBeNull()
    })

    it('未连接时应该直接返回', () => {
      const store = useDbToolkitStore()
      store.switchMysqlDatabase('new_db')

      expect(store.mysqlConnection).toBeNull()
    })
  })
})
