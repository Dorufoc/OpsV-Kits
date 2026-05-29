export interface MySqlConnectionParams {
  host: string
  port: number
  user: string
  password: string
  database: string
}

export interface RedisConnectionParams {
  host: string
  port: number
  password: string
  db: number
}

export interface DetectResult {
  installed: boolean
  path: string
  client_version: string
  error: string
}

export interface MysqlColumnDef {
  field: string
  type: string
  null: string
  key: string
  default: string | null
  extra: string
}

export interface MysqlIndexDef {
  name: string
  column: string
  unique: boolean
}

export interface MysqlTableStructure {
  table_name: string
  columns: MysqlColumnDef[]
  indexes: MysqlIndexDef[]
  row_count: number
  create_ddl: string
}

export interface MysqlQueryResult {
  columns: string[]
  rows: string[][]
  total_count: number
  truncated: boolean
  error: string
}

export interface RedisScanResult {
  keys: string[]
  next_cursor: number
  has_more: boolean
}

export interface RedisKeyInfo {
  key: string
  type: string
  ttl: number
  ttl_display: string
  value: unknown
  size_bytes: number
  truncated: boolean
}

export interface RedisDbStats {
  key_count: number
  used_memory_human: string
  used_memory_bytes: number
}

export interface DangerousCheckResult {
  is_dangerous: boolean
  reason: string
  level: 'critical' | 'warning'
}
