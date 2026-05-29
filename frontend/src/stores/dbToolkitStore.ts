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

  async function detectClient(
    dbType: 'mysql' | 'redis',
    accountAlias: string,
    containerId: string
  ): Promise<DetectResult> {
    const endpoint = dbType === 'mysql' ? '/db-toolkit/detect/mysql' : '/db-toolkit/detect/redis'
    const result = await api.get(endpoint, {
      params: { account_alias: accountAlias, container_id: containerId },
    }) as DetectResult
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
    containerId: string,
    sql: string
  ): Promise<MysqlQueryResult> {
    if (!mysqlConnection.value) throw new Error('MySQL 未连接')
    mysqlQueryLoading.value = true
    try {
      const result = await api.post('/db-toolkit/mysql/query', {
        account_alias: accountAlias,
        container_id: containerId,
        connection: mysqlConnection.value,
        sql,
      }) as MysqlQueryResult
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
    containerId: string
  ): Promise<string[]> {
    if (!mysqlConnection.value) throw new Error('MySQL 未连接')
    const result = await api.post('/db-toolkit/mysql/tables', {
      account_alias: accountAlias,
      container_id: containerId,
      connection: mysqlConnection.value,
    }) as string[]
    mysqlTables.value = result
    return result
  }

  async function loadMysqlTableStructure(
    accountAlias: string,
    containerId: string,
    tableName: string
  ): Promise<MysqlTableStructure> {
    if (!mysqlConnection.value) throw new Error('MySQL 未连接')
    const result = await api.post('/db-toolkit/mysql/table-structure', {
      account_alias: accountAlias,
      container_id: containerId,
      connection: mysqlConnection.value,
      table_name: tableName,
    }) as MysqlTableStructure
    mysqlTableStructure.value = result
    return result
  }

  async function scanRedisKeys(
    accountAlias: string,
    containerId: string,
    pattern: string = '*',
    cursor: number = 0,
    count: number = 100
  ): Promise<RedisScanResult> {
    if (!redisConnection.value) throw new Error('Redis 未连接')
    redisScanLoading.value = true
    try {
      const result = await api.post('/db-toolkit/redis/scan', {
        account_alias: accountAlias,
        container_id: containerId,
        connection: redisConnection.value,
        pattern,
        count,
        cursor,
      }) as RedisScanResult
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
    containerId: string,
    key: string
  ): Promise<RedisKeyInfo> {
    if (!redisConnection.value) throw new Error('Redis 未连接')
    const result = await api.post('/db-toolkit/redis/key-info', {
      account_alias: accountAlias,
      container_id: containerId,
      connection: redisConnection.value,
      key,
    }) as RedisKeyInfo
    redisKeyInfo.value = result
    return result
  }

  async function loadRedisDbStats(
    accountAlias: string,
    containerId: string
  ): Promise<RedisDbStats> {
    if (!redisConnection.value) throw new Error('Redis 未连接')
    const result = await api.post('/db-toolkit/redis/db-stats', {
      account_alias: accountAlias,
      container_id: containerId,
      connection: redisConnection.value,
    }) as RedisDbStats
    redisDbStats.value = result
    return result
  }

  async function deleteRedisKey(
    accountAlias: string,
    containerId: string,
    key: string
  ): Promise<boolean> {
    if (!redisConnection.value) throw new Error('Redis 未连接')
    const result = await api.delete('/db-toolkit/redis/key', {
      params: {
        account_alias: accountAlias,
        container_id: containerId,
        key,
        host: redisConnection.value.host,
        port: redisConnection.value.port,
        password: redisConnection.value.password,
        db: redisConnection.value.db,
      },
    }) as { success: boolean }
    return result.success
  }

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
  }
})
