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

export default instance
