import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { cronBackupApi } from '@/api'

export interface CronJob {
  id: string
  name: string
  cron_expression: string
  task_type: 'shell' | 'url'
  command: string
  http_method?: string
  http_headers?: Record<string, string>
  http_body?: string
  status: 'enabled' | 'disabled'
  account_alias: string
  description?: string
  created_at: string
  updated_at: string
  last_run_at?: string
  last_run_status?: string
}

export interface BackupPolicy {
  id: string
  name: string
  backup_type: 'website' | 'mysql' | 'postgresql' | 'custom'
  source_path?: string
  db_name?: string
  db_host?: string
  db_port?: number
  db_username?: string
  storage_type: 'local' | 'aliyun_oss' | 'tencent_cos' | 'aws_s3' | 'ftp' | 'sftp'
  storage_config: Record<string, any>
  cron_expression: string
  retention_count: number
  compression: 'tar.gz' | 'zip' | 'none'
  status: 'enabled' | 'disabled'
  account_alias: string
  description?: string
  created_at: string
  updated_at: string
  last_backup_at?: string
  last_backup_status?: string
}

export interface BackupHistory {
  id: string
  policy_id: string
  policy_name: string
  backup_type: string
  file_path?: string
  file_size?: number
  storage_type: string
  storage_path?: string
  status: 'success' | 'failed' | 'running'
  error_message?: string
  started_at: string
  completed_at?: string
  account_alias: string
}

export interface LogRetentionPolicy {
  id: string
  name: string
  log_path_pattern: string
  retention_days: number
  cleanup_action: 'delete' | 'compress' | 'move'
  archive_path?: string
  cron_expression: string
  status: 'enabled' | 'disabled'
  account_alias: string
  description?: string
  created_at: string
  updated_at: string
  last_run_at?: string
  last_run_status?: string
}

export interface ExecutionLog {
  id: string
  task_id: string
  task_type: string
  task_name: string
  status: string
  exit_code?: number
  output?: string
  error?: string
  started_at: string
  completed_at?: string
  duration_seconds?: number
  account_alias: string
}

export interface DiskAlert {
  has_alert: boolean
  alerts: Array<{
    filesystem: string
    size: string
    used: string
    available: string
    use_percent: number
    mount_point: string
  }>
  disk_usage: Array<{
    filesystem: string
    size: string
    used: string
    available: string
    use_percent: number
    mount_point: string
  }>
  log_sizes: Array<{ size: string; path: string }>
}

export interface FileInfo {
  path: string
  size: number
  modified_at: string
}

export const useCronBackupStore = defineStore('cronBackup', () => {
  const currentAlias = ref('')
  const cronJobs = ref<CronJob[]>([])
  const backupPolicies = ref<BackupPolicy[]>([])
  const backupHistory = ref<BackupHistory[]>([])
  const logPolicies = ref<LogRetentionPolicy[]>([])
  const executionLogs = ref<ExecutionLog[]>([])
  const diskAlert = ref<DiskAlert | null>(null)
  const loading = ref(false)
  const runningBackup = ref<string | null>(null)
  const runningLogCleanup = ref<string | null>(null)

  function setAccountAlias(alias: string) {
    currentAlias.value = alias
  }

  // ── Cron Jobs ────────────────────────────────────────────────

  async function fetchCronJobs(alias?: string) {
    const a = alias || currentAlias.value
    if (!a) return
    loading.value = true
    try {
      const res = await cronBackupApi.listCronJobs(a)
      cronJobs.value = res.items || []
      return res
    } finally {
      loading.value = false
    }
  }

  async function createCronJob(data: any, alias?: string) {
    const a = alias || currentAlias.value
    if (!a) return
    const res = await cronBackupApi.createCronJob(a, data)
    await fetchCronJobs(a)
    return res
  }

  async function updateCronJob(jobId: string, data: any, alias?: string) {
    const a = alias || currentAlias.value
    if (!a) return
    const res = await cronBackupApi.updateCronJob(jobId, a, data)
    await fetchCronJobs(a)
    return res
  }

  async function deleteCronJob(jobId: string, alias?: string) {
    const a = alias || currentAlias.value
    if (!a) return
    await cronBackupApi.deleteCronJob(jobId, a)
    await fetchCronJobs(a)
  }

  async function fetchExecutionLogs(jobId: string, alias?: string, limit?: number) {
    const a = alias || currentAlias.value
    if (!a) return
    const res = await cronBackupApi.getCronJobLogs(jobId, a, limit)
    executionLogs.value = res.items || []
    return res
  }

  // ── Backup Policies ──────────────────────────────────────────

  async function fetchBackupPolicies(alias?: string) {
    const a = alias || currentAlias.value
    if (!a) return
    loading.value = true
    try {
      const res = await cronBackupApi.listBackupPolicies(a)
      backupPolicies.value = res.items || []
      return res
    } finally {
      loading.value = false
    }
  }

  async function createBackupPolicy(data: any, alias?: string) {
    const a = alias || currentAlias.value
    if (!a) return
    const res = await cronBackupApi.createBackupPolicy(a, data)
    await fetchBackupPolicies(a)
    return res
  }

  async function updateBackupPolicy(policyId: string, data: any, alias?: string) {
    const a = alias || currentAlias.value
    if (!a) return
    const res = await cronBackupApi.updateBackupPolicy(policyId, a, data)
    await fetchBackupPolicies(a)
    return res
  }

  async function deleteBackupPolicy(policyId: string, alias?: string) {
    const a = alias || currentAlias.value
    if (!a) return
    await cronBackupApi.deleteBackupPolicy(policyId, a)
    await fetchBackupPolicies(a)
  }

  async function runBackupNow(policyId: string, alias?: string) {
    const a = alias || currentAlias.value
    if (!a) return
    runningBackup.value = policyId
    try {
      const res = await cronBackupApi.runBackupNow(policyId, a)
      await fetchBackupHistory(policyId, a)
      await fetchBackupPolicies(a)
      return res
    } finally {
      runningBackup.value = null
    }
  }

  async function fetchBackupHistory(policyId?: string, alias?: string, limit?: number) {
    const a = alias || currentAlias.value
    if (!a) return
    const res = await cronBackupApi.listBackupHistory(a, policyId, limit)
    backupHistory.value = res.items || []
    return res
  }

  // ── Log Retention Policies ───────────────────────────────────

  async function fetchLogPolicies(alias?: string) {
    const a = alias || currentAlias.value
    if (!a) return
    loading.value = true
    try {
      const res = await cronBackupApi.listLogPolicies(a)
      logPolicies.value = res.items || []
      return res
    } finally {
      loading.value = false
    }
  }

  async function createLogPolicy(data: any, alias?: string) {
    const a = alias || currentAlias.value
    if (!a) return
    const res = await cronBackupApi.createLogPolicy(a, data)
    await fetchLogPolicies(a)
    return res
  }

  async function updateLogPolicy(policyId: string, data: any, alias?: string) {
    const a = alias || currentAlias.value
    if (!a) return
    const res = await cronBackupApi.updateLogPolicy(policyId, a, data)
    await fetchLogPolicies(a)
    return res
  }

  async function deleteLogPolicy(policyId: string, alias?: string) {
    const a = alias || currentAlias.value
    if (!a) return
    await cronBackupApi.deleteLogPolicy(policyId, a)
    await fetchLogPolicies(a)
  }

  async function previewLogCleanup(policyId: string, alias?: string) {
    const a = alias || currentAlias.value
    if (!a) return
    return cronBackupApi.previewLogCleanup(policyId, a)
  }

  async function runLogCleanupNow(policyId: string, alias?: string) {
    const a = alias || currentAlias.value
    if (!a) return
    runningLogCleanup.value = policyId
    try {
      const res = await cronBackupApi.runLogCleanupNow(policyId, a)
      await fetchLogPolicies(a)
      return res
    } finally {
      runningLogCleanup.value = null
    }
  }

  async function fetchDiskAlert(alias?: string) {
    const a = alias || currentAlias.value
    if (!a) return
    const res = await cronBackupApi.getDiskAlert(a)
    diskAlert.value = res
    return res
  }

  return {
    currentAlias,
    cronJobs,
    backupPolicies,
    backupHistory,
    logPolicies,
    executionLogs,
    diskAlert,
    loading,
    runningBackup,
    runningLogCleanup,
    setAccountAlias,
    fetchCronJobs,
    createCronJob,
    updateCronJob,
    deleteCronJob,
    fetchExecutionLogs,
    fetchBackupPolicies,
    createBackupPolicy,
    updateBackupPolicy,
    deleteBackupPolicy,
    runBackupNow,
    fetchBackupHistory,
    fetchLogPolicies,
    createLogPolicy,
    updateLogPolicy,
    deleteLogPolicy,
    previewLogCleanup,
    runLogCleanupNow,
    fetchDiskAlert,
  }
})
