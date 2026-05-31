import axios from 'axios'
import type { AxiosInstance, AxiosRequestConfig, AxiosResponse } from 'axios'

const instance: AxiosInstance = axios.create({
  baseURL: '/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

instance.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

instance.interceptors.response.use(
  (response: AxiosResponse) => {
    return response.data
  },
  (error) => {
    if (error.response) {
      switch (error.response.status) {
        case 401:
          localStorage.removeItem('token')
          break
        case 403:
          console.error('权限不足')
          break
        case 500:
          console.error('服务器错误')
          break
        default:
          console.error(error.message)
      }
    }
    return Promise.reject(error)
  }
)

export const request = {
  get<T = any>(url: string, config?: AxiosRequestConfig): Promise<T> {
    return instance.get(url, config)
  },
  post<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> {
    return instance.post(url, data, config)
  },
  put<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> {
    return instance.put(url, data, config)
  },
  delete<T = any>(url: string, config?: AxiosRequestConfig): Promise<T> {
    return instance.delete(url, config)
  },
  patch<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> {
    return instance.patch(url, data, config)
  },
}

export interface ViteCheckResponse {
  account_alias: string
  project_path: string
  node: Record<string, any>
  nginx: Record<string, any>
  vite: Record<string, any>
  framework: Record<string, any>
  all_ready: boolean
}

export interface ViteTaskResponse {
  task_id: string
  status: string
  progress: number
  message: string
  step: string
  log: string
  url?: string
}

export interface ViteDeployPayload {
  account_alias: string
  project_alias: string
  project_path: string
  node_version?: string
  nginx_port?: number
  build_command?: string
  force?: boolean
}

export interface ViteStepPayload {
  account_alias: string
  project_path: string
  node_version?: string
  force?: boolean
  build_command?: string
  project_alias?: string
  port?: number
}

export const viteDeploy = {
  check(account_alias: string, project_path: string): Promise<ViteCheckResponse> {
    return request.get<ViteCheckResponse>('/deploy/vite/check', {
      params: { account_alias, project_path },
    })
  },
  setup(data: ViteStepPayload): Promise<ViteTaskResponse> {
    return request.post<ViteTaskResponse>('/deploy/vite/setup', data)
  },
  installDeps(data: ViteStepPayload): Promise<ViteTaskResponse> {
    return request.post<ViteTaskResponse>('/deploy/vite/install-deps', data)
  },
  build(data: ViteStepPayload): Promise<ViteTaskResponse> {
    return request.post<ViteTaskResponse>('/deploy/vite/build', data)
  },
  nginx(data: ViteStepPayload): Promise<ViteTaskResponse> {
    return request.post<ViteTaskResponse>('/deploy/vite/nginx', data)
  },
  deploy(data: ViteDeployPayload): Promise<ViteTaskResponse> {
    return request.post<ViteTaskResponse>('/deploy/vite/deploy', data)
  },
  status(task_id: string): Promise<ViteTaskResponse> {
    return request.get<ViteTaskResponse>(`/deploy/vite/status/${task_id}`)
  },
}

export interface StoreApp {
  id: string
  name: string
  description: string
  category: string
  version: string
  icon?: string
  author?: string
  tags?: string[]
  compose_file?: string
  env_schema?: Record<string, {
    type: string
    default?: any
    required?: boolean
    description?: string
  }>
}

export interface StoreAppStatus {
  app_id: string
  installed: boolean
  running: boolean
  version?: string
  containers?: string[]
}

export interface InstallStoreAppPayload {
  account_alias: string
  [key: string]: any
}

export interface UninstallStoreAppPayload {
  account_alias: string
  purge_data?: boolean
}

export interface ConfigureRegistryMirrorPayload {
  account_alias: string
  mirror_url: string
}

export const dockerStoreApi = {
  getStoreApps(category?: string): Promise<StoreApp[]> {
    const params: Record<string, any> = {}
    if (category) {
      params.category = category
    }
    return request.get<StoreApp[]>('/docker-store/apps', { params })
  },
  getStoreApp(appId: string): Promise<StoreApp> {
    return request.get<StoreApp>(`/docker-store/apps/${appId}`)
  },
  installStoreApp(appId: string, data: InstallStoreAppPayload): Promise<any> {
    return request.post(`/docker-store/install/${appId}`, data)
  },
  uninstallStoreApp(appId: string, data: UninstallStoreAppPayload): Promise<any> {
    return request.post(`/docker-store/uninstall/${appId}`, data)
  },
  getStoreAppStatus(appId: string, account_alias: string): Promise<StoreAppStatus> {
    return request.get<StoreAppStatus>(`/docker-store/status/${appId}`, {
      params: { account_alias },
    })
  },
  getRegistryMirrors(account_alias: string): Promise<string[]> {
    return request.get<string[]>('/docker-store/registry-mirrors', {
      params: { account_alias },
    })
  },
  configureRegistryMirror(data: ConfigureRegistryMirrorPayload): Promise<any> {
    return request.post('/docker-store/registry-mirrors', data)
  },
}

export interface FirewallBackend {
  backend: 'firewalld' | 'ufw' | 'iptables'
  running: boolean
}

export interface FirewallRule {
  id?: string
  port?: number
  protocol?: 'tcp' | 'udp' | 'tcp/udp'
  action: 'allow' | 'deny' | 'reject'
  zone?: string
  source?: string
  permanent?: boolean
  remark?: string
}

export interface SshConfig {
  port: number
  password_auth: boolean
  root_login: boolean
  pubkey_auth: boolean
}

export interface SshKey {
  fingerprint: string
  comment: string
  type: string
  bits: number
}

export interface LoginLogEntry {
  time: string
  user: string
  ip: string
  status: 'success' | 'failed'
  method: string
}

export interface Fail2banStatus {
  running: boolean
  jails: string[]
  banned_ips: Record<string, string[]>
}

export interface OpsAuditLogEntry {
  id: string
  time: string
  user: string
  action: string
  target: string
  detail?: string
  ip?: string
}

export interface NetworkOutput {
  output: string
  error?: string
  exit_code: number
}

export const securityNetworkApi = {
  getFirewallBackend(alias: string): Promise<FirewallBackend> {
    return request.get<FirewallBackend>('/security/firewall/backend', {
      params: { alias },
    })
  },
  getFirewallRules(alias: string): Promise<FirewallRule[]> {
    return request.get<FirewallRule[]>('/security/firewall/rules', {
      params: { alias },
    })
  },
  addPortRule(
    alias: string,
    port: number,
    protocol: string,
    action: string,
    zone?: string,
    permanent?: boolean
  ): Promise<any> {
    const params: Record<string, any> = {
      alias,
      port,
      protocol,
    }
    if (zone !== undefined) params.zone = zone
    return request.post('/security/firewall/port', null, { params })
  },
  removePortRule(
    alias: string,
    port: number,
    protocol: string,
    action: string,
    zone?: string
  ): Promise<any> {
    const params: Record<string, any> = {
      alias,
      port,
      protocol,
    }
    if (zone !== undefined) params.zone = zone
    return request.delete('/security/firewall/port', { params })
  },
  addIpRule(
    alias: string,
    ip: string,
    action: string,
    remark?: string
  ): Promise<any> {
    const params: Record<string, any> = {
      alias,
      ip,
      action,
    }
    if (remark !== undefined) params.remark = remark
    return request.post('/security/firewall/ip', null, { params })
  },
  removeIpRule(alias: string, ip: string, action: string): Promise<any> {
    return request.delete('/security/firewall/ip', {
      params: { alias, ip },
    })
  },
  getSshConfig(alias: string): Promise<SshConfig> {
    return request.get<SshConfig>('/security/ssh/config', {
      params: { alias },
    })
  },
  changeSshPort(alias: string, port: number): Promise<any> {
    return request.post('/security/ssh/port', null, { params: { alias, port } })
  },
  togglePasswordAuth(alias: string, enabled: boolean): Promise<any> {
    return request.post('/security/ssh/password-auth', null, {
      params: { alias, enabled },
    })
  },
  getSshKeys(alias: string): Promise<SshKey[]> {
    return request.get<SshKey[]>('/security/ssh/keys', {
      params: { alias },
    })
  },
  addSshKey(alias: string, publicKey: string): Promise<any> {
    return request.post('/security/ssh/keys', null, {
      params: { alias, public_key: publicKey },
    })
  },
  removeSshKey(alias: string, fingerprintOrComment: string): Promise<any> {
    return request.delete('/security/ssh/keys', {
      params: { alias, fingerprint: fingerprintOrComment },
    })
  },
  generateSshKey(
    alias: string,
    algorithm: string,
    bits?: number,
    comment?: string
  ): Promise<any> {
    const params: Record<string, any> = {
      alias,
      key_type: algorithm,
    }
    if (bits !== undefined) params.bits = bits
    if (comment !== undefined) params.comment = comment
    return request.post('/security/ssh/keys/generate', null, { params })
  },
  getLoginLogs(alias: string, filters?: Record<string, any>): Promise<LoginLogEntry[]> {
    const params: Record<string, any> = { alias }
    if (filters) {
      Object.assign(params, filters)
    }
    return request.get<LoginLogEntry[]>('/security/audit/login-logs', { params })
  },
  getFail2banStatus(alias: string): Promise<Fail2banStatus> {
    return request.get<Fail2banStatus>('/security/audit/fail2ban', {
      params: { alias },
    })
  },
  unbanIp(alias: string, ip: string, jail?: string): Promise<any> {
    const params: Record<string, any> = { alias, ip }
    if (jail !== undefined) params.jail = jail
    return request.post('/security/audit/fail2ban/unban', null, { params })
  },
  getOpsAuditLogs(filters?: Record<string, any>): Promise<OpsAuditLogEntry[]> {
    const params: Record<string, any> = {}
    if (filters) {
      Object.assign(params, filters)
    }
    return request.get<OpsAuditLogEntry[]>('/security/audit/ops-logs', { params })
  },
  runPing(alias: string, target: string): Promise<NetworkOutput> {
    return request.post<NetworkOutput>('/security/network/ping', null, {
      params: { alias, host: target },
    })
  },
  runTraceroute(alias: string, target: string): Promise<NetworkOutput> {
    return request.post<NetworkOutput>('/security/network/traceroute', null, {
      params: { alias, host: target },
    })
  },
  runPortScan(alias: string, target: string, portRange: string): Promise<NetworkOutput> {
    return request.post<NetworkOutput>('/security/network/portscan', null, {
      params: { alias, host: target, ports: portRange },
    })
  },
}

// ── Cron Backup API ─────────────────────────────────────────────

export const cronBackupApi = {
  // Cron Jobs
  listCronJobs(alias: string): Promise<{ items: any[] }> {
    return request.get('/cron-backup/cron-jobs', { params: { alias } })
  },
  createCronJob(alias: string, data: any): Promise<any> {
    return request.post('/cron-backup/cron-jobs', { alias, data })
  },
  updateCronJob(jobId: string, alias: string, data: any): Promise<any> {
    return request.put(`/cron-backup/cron-jobs/${jobId}`, { alias, data })
  },
  deleteCronJob(jobId: string, alias: string): Promise<any> {
    return request.delete(`/cron-backup/cron-jobs/${jobId}`, { params: { alias } })
  },
  getCronJobLogs(jobId: string, alias: string, limit?: number): Promise<{ items: any[] }> {
    return request.get(`/cron-backup/cron-jobs/${jobId}/logs`, { params: { alias, limit } })
  },

  // Backup Policies
  listBackupPolicies(alias: string): Promise<{ items: any[] }> {
    return request.get('/cron-backup/backup-policies', { params: { alias } })
  },
  createBackupPolicy(alias: string, data: any): Promise<any> {
    return request.post('/cron-backup/backup-policies', { alias, data })
  },
  updateBackupPolicy(policyId: string, alias: string, data: any): Promise<any> {
    return request.put(`/cron-backup/backup-policies/${policyId}`, { alias, data })
  },
  deleteBackupPolicy(policyId: string, alias: string): Promise<any> {
    return request.delete(`/cron-backup/backup-policies/${policyId}`, { params: { alias } })
  },
  runBackupNow(policyId: string, alias: string): Promise<any> {
    return request.post(`/cron-backup/backup-policies/${policyId}/run`, null, { params: { alias } })
  },
  listBackupHistory(alias: string, policyId?: string, limit?: number): Promise<{ items: any[] }> {
    const params: Record<string, any> = { alias }
    if (policyId) params.policy_id = policyId
    if (limit) params.limit = limit
    return request.get('/cron-backup/backup-history', { params })
  },
  downloadBackupFile(historyId: string, alias: string, filePath: string): Promise<Blob> {
    return request.get(`/cron-backup/backup-history/${historyId}/download`, {
      params: { alias, file_path: filePath },
      responseType: 'blob',
    })
  },

  // Log Retention Policies
  listLogPolicies(alias: string): Promise<{ items: any[] }> {
    return request.get('/cron-backup/log-policies', { params: { alias } })
  },
  createLogPolicy(alias: string, data: any): Promise<any> {
    return request.post('/cron-backup/log-policies', { alias, data })
  },
  updateLogPolicy(policyId: string, alias: string, data: any): Promise<any> {
    return request.put(`/cron-backup/log-policies/${policyId}`, { alias, data })
  },
  deleteLogPolicy(policyId: string, alias: string): Promise<any> {
    return request.delete(`/cron-backup/log-policies/${policyId}`, { params: { alias } })
  },
  previewLogCleanup(policyId: string, alias: string): Promise<{ items: any[] }> {
    return request.post(`/cron-backup/log-policies/${policyId}/preview`, null, { params: { alias } })
  },
  runLogCleanupNow(policyId: string, alias: string): Promise<any> {
    return request.post(`/cron-backup/log-policies/${policyId}/run`, null, { params: { alias } })
  },

  // Disk Alert
  getDiskAlert(alias: string): Promise<any> {
    return request.get('/cron-backup/disk-alert', { params: { alias } })
  },
}

export interface GitRepoInfo {
  account_alias: string
  repo_path: string
  current_branch: string
  branches: string[]
  remotes: Record<string, string>
  repo_size: string
  last_commit_hash: string
  last_commit_message: string
  last_commit_author: string
  last_commit_time: string
  is_bare: boolean
  has_uncommitted_changes: boolean
}

export interface GitBranchInfo {
  name: string
  is_current: boolean
  is_remote: boolean
  last_commit_hash: string
  last_commit_message: string
  last_commit_time: string
  upstream?: string
}

export interface GitCommitInfo {
  hash: string
  short_hash: string
  author: string
  author_email: string
  date: string
  message: string
  parent_hashes: string[]
  changed_files: string[]
}

export interface GitDiffInfo {
  file_path: string
  change_type: string
  old_path?: string
  additions: number
  deletions: number
  diff_content: string
}

export interface WebhookConfigInfo {
  hook_id: string
  account_alias: string
  repo_path: string
  platform: string
  secret: string
  events: string[]
  branch_filter: string
  deploy_pipeline_id?: string
  enabled: boolean
  created_at: string
  updated_at: string
}

export interface DeployStageInfo {
  name: string
  commands: string[]
  work_dir: string
  env_vars: Record<string, string>
  timeout: number
  continue_on_error: boolean
}

export interface DeployPipelineInfo {
  pipeline_id: string
  name: string
  account_alias: string
  repo_path: string
  trigger_branches: string[]
  trigger_tags: string
  stages: DeployStageInfo[]
  auto_deploy_on_sync: boolean
  created_at: string
  updated_at: string
}

export interface DeployRecordInfo {
  record_id: string
  pipeline_id: string
  account_alias: string
  repo_path: string
  trigger_type: string
  trigger_info: string
  branch: string
  commit_hash: string
  status: string
  started_at?: string
  completed_at?: string
  log: string
  stages_result: Record<string, any>[]
}

export interface GitSyncConfigInfo {
  config_id: string
  account_alias: string
  repo_path: string
  enabled: boolean
  check_interval: number
  sync_mode: string
  auto_deploy: boolean
  deploy_pipeline_id?: string
  branch: string
  ff_only: boolean
  last_check_time?: string
  last_sync_time?: string
  last_sync_result?: string
  pending_updates: number
  error_count: number
  status: string
  created_at: string
  updated_at: string
}

export interface GitSyncLogInfo {
  log_id: string
  config_id: string
  account_alias: string
  repo_path: string
  action: string
  result: string
  message: string
  commits_behind: number
  commits_ahead: number
  changed_files: string[]
  timestamp: string
}

export const gitApi = {
  initRepo(data: { account_alias: string; repo_path: string; gitignore_template?: string }): Promise<any> {
    return request.post('/git/repo/init', data)
  },
  cloneRepo(data: { account_alias: string; repo_url: string; target_path: string; branch?: string; depth?: number }): Promise<any> {
    return request.post('/git/repo/clone', data)
  },
  configRemote(data: { account_alias: string; repo_path: string; remote_name?: string; remote_url: string }): Promise<any> {
    return request.post('/git/repo/remote', data)
  },
  getRepoInfo(account_alias: string, repo_path: string, force_refresh?: boolean): Promise<GitRepoInfo> {
    return request.get('/git/repo/info', { params: { account_alias, repo_path, force_refresh: force_refresh || false } })
  },

  createBranch(data: { account_alias: string; repo_path: string; branch_name: string; base_ref?: string; checkout?: boolean }): Promise<any> {
    return request.post('/git/branch/create', data)
  },
  switchBranch(data: { account_alias: string; repo_path: string; branch_name: string; stash_if_dirty?: boolean }): Promise<any> {
    return request.post('/git/branch/switch', data)
  },
  mergeBranch(data: { account_alias: string; repo_path: string; source_branch: string; target_branch?: string }): Promise<any> {
    return request.post('/git/branch/merge', data)
  },
  deleteBranch(data: { account_alias: string; repo_path: string; branch_name: string; force?: boolean }): Promise<any> {
    return request.post('/git/branch/delete', data)
  },
  compareBranches(data: { account_alias: string; repo_path: string; source: string; target: string }): Promise<any> {
    return request.post('/git/branch/compare', data)
  },

  getCommitLog(params: { account_alias: string; repo_path: string; author?: string; since?: string; until?: string; keyword?: string; page?: number; page_size?: number }): Promise<any> {
    return request.get('/git/commit/log', { params })
  },
  getCommitDetail(account_alias: string, repo_path: string, commit_hash: string): Promise<GitCommitInfo> {
    return request.get('/git/commit/detail', { params: { account_alias, repo_path, commit_hash } })
  },
  getDiff(account_alias: string, repo_path: string, from_ref: string, to_ref: string, file_path?: string): Promise<{ diff: string }> {
    return request.get('/git/commit/diff', { params: { account_alias, repo_path, from_ref, to_ref, file_path } })
  },

  createWebhookConfig(data: { account_alias: string; repo_path: string; platform: string; events?: string[]; branch_filter?: string; deploy_pipeline_id?: string }): Promise<WebhookConfigInfo> {
    return request.post('/git/webhook/config', data)
  },
  listWebhookConfigs(account_alias?: string): Promise<{ items: WebhookConfigInfo[] }> {
    return request.get('/git/webhook/config', { params: account_alias ? { account_alias } : {} })
  },
  getWebhookConfig(hook_id: string): Promise<WebhookConfigInfo> {
    return request.get(`/git/webhook/config/${hook_id}`)
  },
  updateWebhookConfig(hook_id: string, data: Partial<WebhookConfigInfo>): Promise<WebhookConfigInfo> {
    return request.put(`/git/webhook/config/${hook_id}`, data)
  },
  deleteWebhookConfig(hook_id: string): Promise<any> {
    return request.delete(`/git/webhook/config/${hook_id}`)
  },

  createDeployPipeline(data: { name: string; account_alias: string; repo_path: string; trigger_branches?: string[]; trigger_tags?: string; stages?: any[]; auto_deploy_on_sync?: boolean }): Promise<DeployPipelineInfo> {
    return request.post('/git/pipeline', data)
  },
  listDeployPipelines(account_alias?: string): Promise<{ items: DeployPipelineInfo[] }> {
    return request.get('/git/pipeline', { params: account_alias ? { account_alias } : {} })
  },
  getDeployPipeline(pipeline_id: string): Promise<DeployPipelineInfo> {
    return request.get(`/git/pipeline/${pipeline_id}`)
  },
  updateDeployPipeline(pipeline_id: string, data: Partial<DeployPipelineInfo>): Promise<DeployPipelineInfo> {
    return request.put(`/git/pipeline/${pipeline_id}`, data)
  },
  deleteDeployPipeline(pipeline_id: string): Promise<any> {
    return request.delete(`/git/pipeline/${pipeline_id}`)
  },
  executeDeployPipeline(pipeline_id: string): Promise<DeployRecordInfo> {
    return request.post(`/git/pipeline/${pipeline_id}/execute`)
  },

  listDeployHistory(params?: { account_alias?: string; pipeline_id?: string; limit?: number }): Promise<{ items: DeployRecordInfo[] }> {
    return request.get('/git/deploy/history', { params: params || {} })
  },
  getDeployRecord(record_id: string): Promise<DeployRecordInfo> {
    return request.get(`/git/deploy/history/${record_id}`)
  },
  rollbackDeploy(record_id: string): Promise<DeployRecordInfo> {
    return request.post(`/git/deploy/history/${record_id}/rollback`)
  },

  createSyncConfig(data: { account_alias: string; repo_path: string; enabled?: boolean; check_interval?: number; sync_mode?: string; auto_deploy?: boolean; deploy_pipeline_id?: string; branch?: string; ff_only?: boolean }): Promise<GitSyncConfigInfo> {
    return request.post('/git/sync/config', data)
  },
  listSyncConfigs(account_alias?: string): Promise<{ items: GitSyncConfigInfo[] }> {
    return request.get('/git/sync/config', { params: account_alias ? { account_alias } : {} })
  },
  getSyncConfig(config_id: string): Promise<GitSyncConfigInfo> {
    return request.get(`/git/sync/config/${config_id}`)
  },
  updateSyncConfig(config_id: string, data: Partial<GitSyncConfigInfo>): Promise<GitSyncConfigInfo> {
    return request.put(`/git/sync/config/${config_id}`, data)
  },
  deleteSyncConfig(config_id: string): Promise<any> {
    return request.delete(`/git/sync/config/${config_id}`)
  },
  manualPull(config_id: string): Promise<any> {
    return request.post(`/git/sync/manual-pull/${config_id}`)
  },
  getSyncStatus(config_id: string): Promise<any> {
    return request.get(`/git/sync/status/${config_id}`)
  },
  getSyncLogs(config_id: string, limit?: number): Promise<{ items: GitSyncLogInfo[] }> {
    return request.get(`/git/sync/logs/${config_id}`, { params: { limit: limit || 50 } })
  },
}

export interface AuditLogEntry {
  id: string
  user_id: string
  username: string
  timestamp: string
  ip_address: string
  action_type: string
  module: string
  detail: Record<string, any> | null
  status: string
  client_info: string
  request_path: string
  request_method: string
  response_code: number
  duration_ms: number
  hash: string
  sensitive: boolean
}

export interface AuditLogQueryParams {
  user_id?: string
  username?: string
  time_start?: string
  time_end?: string
  action_types?: string[]
  modules?: string[]
  status?: string
  request_path?: string
  keyword?: string
  page: number
  page_size: number
  order_by?: string
  order_dir?: string
}

export interface AuditLogPageResult {
  total: number
  page: number
  page_size: number
  total_pages: number
  items: AuditLogEntry[]
}

export interface AuditLogStatistics {
  trend: Array<{ bucket: string; count: number }>
  module_distribution: Array<{ module: string; count: number }>
  action_distribution: Array<{ action_type: string; count: number }>
  user_ranking: Array<{ username: string; count: number }>
  anomalies: Array<Record<string, any>>
}

export interface AuditArchiveInfo {
  filename: string
  size_bytes: number
  record_count: number
  period_start: string
  period_end: string
}

export const auditLogApi = {
  queryLogs(params: AuditLogQueryParams): Promise<AuditLogPageResult> {
    return request.post<AuditLogPageResult>('/audit-log/query', params)
  },
  getLogDetail(logId: string): Promise<AuditLogEntry> {
    return request.get<AuditLogEntry>(`/audit-log/${logId}`)
  },
  getStatistics(timeStart?: string, timeEnd?: string, granularity?: string): Promise<AuditLogStatistics> {
    const params: Record<string, any> = {}
    if (timeStart) params.time_start = timeStart
    if (timeEnd) params.time_end = timeEnd
    if (granularity) params.granularity = granularity
    return request.get<AuditLogStatistics>('/audit-log/statistics', { params })
  },
  exportLogs(params: AuditLogQueryParams, format: string): Promise<any> {
    return request.post('/audit-log/export', { query: params, format })
  },
  downloadExport(taskId: string, format: string): string {
    return `/api/audit-log/export/${taskId}/download?format=${format}`
  },
  verifyIntegrity(logId?: string): Promise<{ total: number; passed: number; failed: number; failed_ids: string[] }> {
    return request.post('/audit-log/verify', logId ? { log_id: logId } : {})
  },
  getArchives(): Promise<AuditArchiveInfo[]> {
    return request.get<AuditArchiveInfo[]>('/audit-log/archives')
  },
  getRecentLogs(limit?: number): Promise<AuditLogEntry[]> {
    return request.get<AuditLogEntry[]>('/audit-log/recent', { params: { limit: limit || 5 } })
  },
}

export const workflowApi = {
  list: () => request.get('/workflow/'),
  get: (id: string) => request.get(`/workflow/${id}`),
  create: (data: any) => request.post('/workflow/', data),
  update: (id: string, data: any) => request.put(`/workflow/${id}`, data),
  delete: (id: string) => request.delete(`/workflow/${id}`),
  validate: (nodes: any[], edges: any[]) => request.post('/workflow/validate', { nodes, edges }),
  saveVersion: (id: string, changeNote?: string) => request.post(`/workflow/${id}/save-version`, { change_note: changeNote }),
  listVersions: (id: string) => request.get(`/workflow/${id}/versions`),
  rollback: (id: string, version: number) => request.post(`/workflow/${id}/rollback`, { version }),
  exportWorkflow: (id: string) => request.get(`/workflow/${id}/export`),
  importWorkflow: (data: any) => request.post('/workflow/import', data),
  listTemplates: () => request.get('/workflow/templates'),
  createFromTemplate: (templateId: string, name: string) => request.post(`/workflow/templates/${templateId}/create`, { name }),
  execute: (id: string, triggerType: string, triggerSource?: string) => request.post(`/workflow/${id}/execute`, { trigger_type: triggerType, trigger_source: triggerSource }),
  pauseExecution: (executionId: string) => request.post(`/workflow/executions/${executionId}/pause`),
  resumeExecution: (executionId: string) => request.post(`/workflow/executions/${executionId}/resume`),
  cancelExecution: (executionId: string) => request.post(`/workflow/executions/${executionId}/cancel`),
  listExecutions: (workflowId: string, limit = 50) => request.get(`/workflow/${workflowId}/executions`, { params: { limit } }),
  getExecution: (executionId: string) => request.get(`/workflow/executions/${executionId}`),
  listNodeExecutions: (executionId: string) => request.get(`/workflow/executions/${executionId}/nodes`),
}

export const schedulerApi = {
  listTasks: () => request.get('/scheduler/tasks'),
  getTask: (id: string) => request.get(`/scheduler/tasks/${id}`),
  createTask: (data: any) => request.post('/scheduler/tasks', data),
  updateTask: (id: string, data: any) => request.put(`/scheduler/tasks/${id}`, data),
  deleteTask: (id: string) => request.delete(`/scheduler/tasks/${id}`),
  toggleTask: (id: string, enabled: boolean) => request.post(`/scheduler/tasks/${id}/toggle`, { enabled }),
  runTask: (id: string) => request.post(`/scheduler/tasks/${id}/run`),
  listExecutions: (taskId?: string, status?: string, limit = 50, offset = 0) => request.get('/scheduler/executions', { params: { task_id: taskId, status, limit, offset } }),
  getExecution: (id: string) => request.get(`/scheduler/executions/${id}`),
  retryExecution: (id: string) => request.post(`/scheduler/executions/${id}/retry`),
  getStatus: () => request.get('/scheduler/status'),
}

export const eventTriggerApi = {
  listSources: () => request.get('/event-trigger/sources'),
  getSource: (id: string) => request.get(`/event-trigger/sources/${id}`),
  createSource: (data: any) => request.post('/event-trigger/sources', data),
  updateSource: (id: string, data: any) => request.put(`/event-trigger/sources/${id}`, data),
  deleteSource: (id: string) => request.delete(`/event-trigger/sources/${id}`),
  listRoutes: (sourceId?: string) => request.get('/event-trigger/routes', { params: { source_id: sourceId } }),
  createRoute: (data: any) => request.post('/event-trigger/routes', data),
  updateRoute: (id: string, data: any) => request.put(`/event-trigger/routes/${id}`, data),
  deleteRoute: (id: string) => request.delete(`/event-trigger/routes/${id}`),
  listLogs: (sourceId?: string, eventType?: string, status?: string, limit = 50, offset = 0) => request.get('/event-trigger/logs', { params: { source_id: sourceId, event_type: eventType, status, limit, offset } }),
  replayEvent: (logId: string) => request.post(`/event-trigger/logs/${logId}/replay`),
}

export interface ProbeTarget {
  id: string
  name: string
  probe_type: 'http' | 'tcp' | 'icmp'
  target: string
  interval_seconds: number
  timeout_seconds: number
  enabled: boolean
  failure_threshold: number
  recovery_threshold: number
  http_config?: {
    expected_status_codes: number[]
    content_match?: string
    method: string
    headers?: Record<string, string>
    follow_redirects: boolean
  }
  tags: string[]
  current_status: 'available' | 'unavailable' | 'unknown'
  consecutive_failures: number
  consecutive_successes: number
  last_probe_time?: string
  last_success_time?: string
  last_failure_time?: string
  created_at: string
  updated_at: string
}

export interface ProbeTargetCreate {
  name: string
  probe_type: 'http' | 'tcp' | 'icmp'
  target: string
  interval_seconds?: number
  timeout_seconds?: number
  enabled?: boolean
  failure_threshold?: number
  recovery_threshold?: number
  http_config?: {
    expected_status_codes?: number[]
    content_match?: string
    method?: string
    headers?: Record<string, string>
    follow_redirects?: boolean
  }
  tags?: string[]
}

export interface ProbeTargetUpdate {
  name?: string
  probe_type?: 'http' | 'tcp' | 'icmp'
  target?: string
  interval_seconds?: number
  timeout_seconds?: number
  enabled?: boolean
  failure_threshold?: number
  recovery_threshold?: number
  http_config?: {
    expected_status_codes?: number[]
    content_match?: string
    method?: string
    headers?: Record<string, string>
    follow_redirects?: boolean
  }
  tags?: string[]
}

export interface ProbeResult {
  id: string
  target_id: string
  timestamp: string
  probe_type: 'http' | 'tcp' | 'icmp'
  target: string
  success: boolean
  response_time_ms?: number
  status_code?: number
  error_message?: string
  content_matched?: boolean
}

export interface ProbeStatistics {
  target_id: string
  uptime_percent: number
  avg_response_time_ms?: number
  max_response_time_ms?: number
  min_response_time_ms?: number
  total_probes: number
  success_count: number
  failure_count: number
  current_status: 'available' | 'unavailable' | 'unknown'
  last_probe_time?: string
  last_success_time?: string
  last_failure_time?: string
}

export interface ProbeOverview {
  total_targets: number
  available_count: number
  unavailable_count: number
  unknown_count: number
  targets: ProbeTarget[]
}

export interface ProbeLogQueryResult {
  items: ProbeResult[]
  total: number
  limit: number
  offset: number
}

export const healthProbeApi = {
  listTargets: (tag?: string, probeType?: string): Promise<ProbeTarget[]> => {
    const params: Record<string, any> = {}
    if (tag) params.tag = tag
    if (probeType) params.probe_type = probeType
    return request.get<ProbeTarget[]>('/health-probe/targets', { params })
  },
  getTarget: (id: string): Promise<ProbeTarget> => {
    return request.get<ProbeTarget>(`/health-probe/targets/${id}`)
  },
  createTarget: (data: ProbeTargetCreate): Promise<ProbeTarget> => {
    return request.post<ProbeTarget>('/health-probe/targets', data)
  },
  updateTarget: (id: string, data: ProbeTargetUpdate): Promise<ProbeTarget> => {
    return request.put<ProbeTarget>(`/health-probe/targets/${id}`, data)
  },
  deleteTarget: (id: string): Promise<any> => {
    return request.delete(`/health-probe/targets/${id}`)
  },
  probeNow: (id: string): Promise<ProbeResult> => {
    return request.post<ProbeResult>(`/health-probe/targets/${id}/probe`)
  },
  getLogs: (id: string, params?: { limit?: number; offset?: number; time_start?: string; time_end?: string; success?: boolean }): Promise<ProbeLogQueryResult> => {
    return request.get<ProbeLogQueryResult>(`/health-probe/targets/${id}/logs`, { params })
  },
  getStatistics: (id: string, hours?: number): Promise<ProbeStatistics> => {
    return request.get<ProbeStatistics>(`/health-probe/targets/${id}/statistics`, { params: { hours: hours || 24 } })
  },
  getOverview: (): Promise<ProbeOverview> => {
    return request.get<ProbeOverview>('/health-probe/overview')
  },
}

export default instance
