import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '@/api'
import type {
  MySqlConnectionParams,
  RedisConnectionParams,
  DetectResult,
  MysqlQueryResult,
  MysqlTableStructure,
  RedisScanResult,
  RedisKeyInfo,
  RedisDbStats,
  DangerousCheckResult,
  DeployMode,
  DbType,
  SavedConnection,
  DatabaseTreeNode,
  DbViewMode,
} from '@/types/db-toolkit'

export const useDbToolkitStore = defineStore('dbToolkit', () => {
  const mysqlConnection = ref<MySqlConnectionParams | null>(null)
  const redisConnection = ref<RedisConnectionParams | null>(null)
  const mysqlDetectResult = ref<DetectResult | null>(null)
  const redisDetectResult = ref<DetectResult | null>(null)

  const mysqlQueryResult = ref<MysqlQueryResult | null>(null)
  const mysqlQueryLoading = ref(false)
  const mysqlTables = ref<string[]>([])
  const mysqlTableStructure = ref<MysqlTableStructure | null>(null)
  const mysqlQueryHistory = ref<string[]>([])

  const redisScanResult = ref<RedisScanResult | null>(null)
  const redisKeyInfo = ref<RedisKeyInfo | null>(null)
  const redisDbStats = ref<RedisDbStats | null>(null)
  const redisScanLoading = ref(false)

  const savedConnections = ref<SavedConnection[]>([])
  const activeConnection = ref<SavedConnection | null>(null)
  const activeDeployMode = ref<DeployMode>('docker')
  const sidebarCollapsed = ref(false)
  const selectedTreeNode = ref<DatabaseTreeNode | null>(null)
  const currentViewMode = ref<DbViewMode>('welcome')
  const mysqlDatabases = ref<string[]>([])

  function loadConnections() {
    try {
      const raw = localStorage.getItem('opsv-db-connections')
      if (raw) {
        savedConnections.value = JSON.parse(raw)
      }
    } catch {
      savedConnections.value = []
    }
  }

  function saveConnections() {
    localStorage.setItem('opsv-db-connections', JSON.stringify(savedConnections.value))
  }

  function addConnection(conn: Omit<SavedConnection, 'id' | 'createdAt' | 'updatedAt'>) {
    const now = Date.now()
    const id = Date.now().toString(36) + Math.random().toString(36).slice(2)
    savedConnections.value.push({
      ...conn,
      id,
      createdAt: now,
      updatedAt: now,
    })
    saveConnections()
  }

  function updateConnection(id: string, updates: Partial<SavedConnection>) {
    const idx = savedConnections.value.findIndex((c) => c.id === id)
    if (idx !== -1) {
      savedConnections.value[idx] = {
        ...savedConnections.value[idx],
        ...updates,
        updatedAt: Date.now(),
      }
      saveConnections()
    }
  }

  function removeConnection(id: string) {
    savedConnections.value = savedConnections.value.filter((c) => c.id !== id)
    saveConnections()
  }

  function toggleFavorite(id: string) {
    const conn = savedConnections.value.find((c) => c.id === id)
    if (conn) {
      conn.favorite = !conn.favorite
      saveConnections()
    }
  }

  function setActiveConnection(conn: SavedConnection | null) {
    activeConnection.value = conn
    if (conn) {
      activeDeployMode.value = conn.deployMode
      if (conn.dbType === 'mysql') {
        mysqlConnection.value = conn.connection as MySqlConnectionParams
      } else {
        redisConnection.value = conn.connection as RedisConnectionParams
      }
    }
  }

  function setViewMode(mode: DbViewMode) {
    currentViewMode.value = mode
  }

  function toggleSidebar() {
    sidebarCollapsed.value = !sidebarCollapsed.value
  }

  function selectTreeNode(node: DatabaseTreeNode | null) {
    selectedTreeNode.value = node
    if (!node) return
    if (node.type === 'database') {
      currentViewMode.value = 'data'
    } else if (node.type === 'table') {
      currentViewMode.value = 'structure'
    } else if (node.type === 'redis-db') {
      currentViewMode.value = 'redis-browse'
    }
  }

  async function detectClient(
    dbType: 'mysql' | 'redis',
    accountAlias: string,
    containerId?: string
  ): Promise<DetectResult> {
    const endpoint = dbType === 'mysql' ? '/db-toolkit/detect/mysql' : '/db-toolkit/detect/redis'
    const params: Record<string, string> = { account_alias: accountAlias }
    if (containerId !== undefined) {
      params.container_id = containerId
    }
    const result = await api.get(endpoint, { params }) as DetectResult
    if (dbType === 'mysql') {
      mysqlDetectResult.value = result
    } else {
      redisDetectResult.value = result
    }
    return result
  }

  function connectMysql(params: MySqlConnectionParams) {
    mysqlConnection.value = { ...params }
  }

  function disconnectMysql() {
    mysqlConnection.value = null
    mysqlQueryResult.value = null
    mysqlTables.value = []
    mysqlTableStructure.value = null
  }

  function connectRedis(params: RedisConnectionParams) {
    redisConnection.value = { ...params }
  }

  function disconnectRedis() {
    redisConnection.value = null
    redisScanResult.value = null
    redisKeyInfo.value = null
    redisDbStats.value = null
  }

  async function checkDangerousSql(sql: string): Promise<DangerousCheckResult> {
    return await api.post('/db-toolkit/check-dangerous-sql', { sql }) as DangerousCheckResult
  }

  async function checkDangerousRedisCommand(command: string): Promise<DangerousCheckResult> {
    return await api.post('/db-toolkit/check-dangerous-redis', { command }) as DangerousCheckResult
  }

  async function executeMysqlQuery(
    accountAlias: string,
    containerId: string | undefined,
    sql: string
  ): Promise<MysqlQueryResult> {
    if (!mysqlConnection.value) throw new Error('MySQL 未连接')
    mysqlQueryLoading.value = true
    try {
      const body: Record<string, unknown> = {
        account_alias: accountAlias,
        connection: mysqlConnection.value,
        sql,
      }
      if (containerId !== undefined) {
        body.container_id = containerId
      }
      const result = await api.post('/db-toolkit/mysql/query', body) as MysqlQueryResult
      mysqlQueryResult.value = result
      if (!result.error && !mysqlQueryHistory.value.includes(sql)) {
        mysqlQueryHistory.value.unshift(sql)
        if (mysqlQueryHistory.value.length > 20) {
          mysqlQueryHistory.value = mysqlQueryHistory.value.slice(0, 20)
        }
      }
      return result
    } finally {
      mysqlQueryLoading.value = false
    }
  }

  async function loadMysqlTables(
    accountAlias: string,
    containerId?: string
  ): Promise<string[]> {
    if (!mysqlConnection.value) throw new Error('MySQL 未连接')
    const body: Record<string, unknown> = {
      account_alias: accountAlias,
      connection: mysqlConnection.value,
    }
    if (containerId !== undefined) {
      body.container_id = containerId
    }
    const result = await api.post('/db-toolkit/mysql/tables', body) as string[]
    mysqlTables.value = result
    return result
  }

  async function loadMysqlTableStructure(
    accountAlias: string,
    containerId: string | undefined,
    tableName: string
  ): Promise<MysqlTableStructure> {
    if (!mysqlConnection.value) throw new Error('MySQL 未连接')
    const body: Record<string, unknown> = {
      account_alias: accountAlias,
      connection: mysqlConnection.value,
      table_name: tableName,
    }
    if (containerId !== undefined) {
      body.container_id = containerId
    }
    const result = await api.post('/db-toolkit/mysql/table-structure', body) as MysqlTableStructure
    mysqlTableStructure.value = result
    return result
  }

  async function scanRedisKeys(
    accountAlias: string,
    containerId: string | undefined,
    pattern: string = '*',
    cursor: number = 0,
    count: number = 100
  ): Promise<RedisScanResult> {
    if (!redisConnection.value) throw new Error('Redis 未连接')
    redisScanLoading.value = true
    try {
      const body: Record<string, unknown> = {
        account_alias: accountAlias,
        connection: redisConnection.value,
        pattern,
        count,
        cursor,
      }
      if (containerId !== undefined) {
        body.container_id = containerId
      }
      const result = await api.post('/db-toolkit/redis/scan', body) as RedisScanResult
      if (cursor === 0) {
        redisScanResult.value = result
      } else if (redisScanResult.value) {
        redisScanResult.value = {
          keys: [...redisScanResult.value.keys, ...result.keys],
          next_cursor: result.next_cursor,
          has_more: result.has_more,
        }
      }
      return result
    } finally {
      redisScanLoading.value = false
    }
  }

  async function loadRedisKeyDetail(
    accountAlias: string,
    containerId: string | undefined,
    key: string
  ): Promise<RedisKeyInfo> {
    if (!redisConnection.value) throw new Error('Redis 未连接')
    const body: Record<string, unknown> = {
      account_alias: accountAlias,
      connection: redisConnection.value,
      key,
    }
    if (containerId !== undefined) {
      body.container_id = containerId
    }
    const result = await api.post('/db-toolkit/redis/key-info', body) as RedisKeyInfo
    redisKeyInfo.value = result
    return result
  }

  async function loadRedisDbStats(
    accountAlias: string,
    containerId: string | undefined
  ): Promise<RedisDbStats> {
    if (!redisConnection.value) throw new Error('Redis 未连接')
    const body: Record<string, unknown> = {
      account_alias: accountAlias,
      connection: redisConnection.value,
    }
    if (containerId !== undefined) {
      body.container_id = containerId
    }
    const result = await api.post('/db-toolkit/redis/db-stats', body) as RedisDbStats
    redisDbStats.value = result
    return result
  }

  async function deleteRedisKey(
    accountAlias: string,
    containerId: string | undefined,
    key: string
  ): Promise<boolean> {
    if (!redisConnection.value) throw new Error('Redis 未连接')
    const params: Record<string, unknown> = {
      account_alias: accountAlias,
      key,
      host: redisConnection.value.host,
      port: redisConnection.value.port,
      password: redisConnection.value.password,
      db: redisConnection.value.db,
    }
    if (containerId !== undefined) {
      params.container_id = containerId
    }
    const result = await api.delete('/db-toolkit/redis/key', { params }) as { success: boolean }
    return result.success
  }

  async function loadMysqlDatabases(accountAlias: string, containerId?: string): Promise<string[]> {
    if (!mysqlConnection.value) throw new Error('MySQL 未连接')
    const body: Record<string, unknown> = {
      account_alias: accountAlias,
      connection: mysqlConnection.value,
      sql: 'SHOW DATABASES',
    }
    if (containerId !== undefined) {
      body.container_id = containerId
    }
    const result = await api.post('/db-toolkit/mysql/query', body) as MysqlQueryResult
    const dbs = result.rows.map((row) => row[0])
    mysqlDatabases.value = dbs
    return dbs
  }

  async function switchMysqlDatabase(databaseName: string) {
    if (!mysqlConnection.value) return
    mysqlConnection.value = {
      ...mysqlConnection.value,
      database: databaseName,
    }
    if (activeConnection.value && activeConnection.value.dbType === 'mysql') {
      activeConnection.value = {
        ...activeConnection.value,
        connection: mysqlConnection.value,
      }
    }
    mysqlTables.value = []
    mysqlTableStructure.value = null
    mysqlQueryResult.value = null
  }

  loadConnections()

  return {
    mysqlConnection,
    redisConnection,
    mysqlDetectResult,
    redisDetectResult,
    mysqlQueryResult,
    mysqlQueryLoading,
    mysqlTables,
    mysqlTableStructure,
    mysqlQueryHistory,
    redisScanResult,
    redisKeyInfo,
    redisDbStats,
    redisScanLoading,
    savedConnections,
    activeConnection,
    activeDeployMode,
    sidebarCollapsed,
    selectedTreeNode,
    currentViewMode,
    mysqlDatabases,
    detectClient,
    connectMysql,
    disconnectMysql,
    connectRedis,
    disconnectRedis,
    checkDangerousSql,
    checkDangerousRedisCommand,
    executeMysqlQuery,
    loadMysqlTables,
    loadMysqlTableStructure,
    scanRedisKeys,
    loadRedisKeyDetail,
    loadRedisDbStats,
    deleteRedisKey,
    loadConnections,
    saveConnections,
    addConnection,
    updateConnection,
    removeConnection,
    toggleFavorite,
    setActiveConnection,
    setViewMode,
    toggleSidebar,
    selectTreeNode,
    loadMysqlDatabases,
    switchMysqlDatabase,
  }
})
