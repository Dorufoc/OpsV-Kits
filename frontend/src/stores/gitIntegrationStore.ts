import { defineStore } from 'pinia'
import { ref } from 'vue'
import { request } from '@/api'

export interface GitRepoInfo {
  current_branch: string
  branch_count: number
  remotes: { name: string; url: string }[]
  repo_size: string
  last_commit: string
  is_dirty: boolean
}

export interface GitBranch {
  name: string
  is_current: boolean
  last_commit: string
  upstream: string
}

export interface GitCommit {
  short_hash: string
  hash: string
  message: string
  author: string
  date: string
  files_changed: string[]
  diff?: string
}

export interface WebhookConfig {
  id: string
  platform: string
  event: string
  branch_filter: string
  status: 'active' | 'inactive'
}

export interface DeployPipeline {
  id: string
  name: string
  trigger_branch: string
  stages: string[]
  yaml_content: string
}

export interface DeployHistory {
  id: string
  time: string
  trigger_type: string
  branch: string
  status: 'success' | 'failed' | 'running'
  duration: string
}

export interface SyncConfig {
  id: string
  repo_path: string
  interval: number
  mode: 'auto_pull' | 'notify_only' | 'manual'
  auto_deploy: boolean
  status: 'active' | 'paused'
  pending_updates: number
}

export interface SyncLog {
  time: string
  action: string
  result: 'success' | 'failed'
  summary: string
}

export interface SyncStatus {
  last_sync_time: string
  next_check_time: string
  diff_commits: number
}

export const useGitIntegrationStore = defineStore('gitIntegration', () => {
  const currentAlias = ref('')
  const repoPath = ref('')
  const loading = ref(false)

  const repoInfo = ref<GitRepoInfo>({
    current_branch: '',
    branch_count: 0,
    remotes: [],
    repo_size: '',
    last_commit: '',
    is_dirty: false,
  })

  const branches = ref<GitBranch[]>([])
  const commits = ref<GitCommit[]>([])
  const commitTotal = ref(0)
  const webhooks = ref<WebhookConfig[]>([])
  const pipelines = ref<DeployPipeline[]>([])
  const deployHistory = ref<DeployHistory[]>([])
  const syncConfigs = ref<SyncConfig[]>([])
  const syncLogs = ref<SyncLog[]>([])
  const syncStatus = ref<SyncStatus>({
    last_sync_time: '',
    next_check_time: '',
    diff_commits: 0,
  })

  function setAccountAlias(alias: string) {
    currentAlias.value = alias
  }

  function setRepoPath(path: string) {
    repoPath.value = path
  }

  function getParams() {
    return { account_alias: currentAlias.value, repo_path: repoPath.value }
  }

  async function fetchRepoInfo() {
    if (!currentAlias.value || !repoPath.value) return
    loading.value = true
    try {
      const res = await request.get<GitRepoInfo>('/git/repo-info', { params: getParams() })
      repoInfo.value = res
    } finally {
      loading.value = false
    }
  }

  async function initRepo(data: { path: string; gitignore_template?: string }) {
    return request.post('/git/init', { ...data, account_alias: currentAlias.value })
  }

  async function cloneRepo(data: { url: string; target_path: string; branch?: string; depth?: number }) {
    return request.post('/git/clone', { ...data, account_alias: currentAlias.value })
  }

  async function configRemote(data: { name: string; url: string }) {
    return request.post('/git/remote', { ...data, ...getParams() })
  }

  async function fetchBranches() {
    if (!currentAlias.value || !repoPath.value) return
    const res = await request.get<GitBranch[]>('/git/branches', { params: getParams() })
    branches.value = res
  }

  async function createBranch(name: string, base?: string) {
    return request.post('/git/branch/create', { name, base, ...getParams() })
  }

  async function switchBranch(name: string) {
    return request.post('/git/branch/switch', { name, ...getParams() })
  }

  async function mergeBranch(source: string, target: string) {
    return request.post('/git/branch/merge', { source, target, ...getParams() })
  }

  async function deleteBranch(name: string) {
    return request.post('/git/branch/delete', { name, ...getParams() })
  }

  async function compareBranches(source: string, target: string) {
    return request.get<{ files: string[] }>('/git/branch/compare', {
      params: { source, target, ...getParams() },
    })
  }

  async function fetchCommits(params: { author?: string; since?: string; until?: string; keyword?: string; page?: number; page_size?: number }) {
    if (!currentAlias.value || !repoPath.value) return
    const res = await request.get<{ items: GitCommit[]; total: number }>('/git/commits', {
      params: { ...params, ...getParams() },
    })
    commits.value = res.items
    commitTotal.value = res.total
  }

  async function fetchCommitDiff(hash: string) {
    return request.get<{ diff: string; files: string[] }>('/git/commit/diff', {
      params: { hash, ...getParams() },
    })
  }

  async function fetchWebhooks() {
    if (!currentAlias.value || !repoPath.value) return
    const res = await request.get<WebhookConfig[]>('/git/webhooks', { params: getParams() })
    webhooks.value = res
  }

  async function createWebhook(data: { platform: string; event: string; branch_filter?: string }) {
    return request.post('/git/webhooks', { ...data, ...getParams() })
  }

  async function deleteWebhook(id: string) {
    return request.delete(`/git/webhooks/${id}`, { params: getParams() })
  }

  async function toggleWebhook(id: string, status: 'active' | 'inactive') {
    return request.patch(`/git/webhooks/${id}`, { status, ...getParams() })
  }

  async function fetchPipelines() {
    if (!currentAlias.value || !repoPath.value) return
    const res = await request.get<DeployPipeline[]>('/git/pipelines', { params: getParams() })
    pipelines.value = res
  }

  async function createPipeline(data: { name: string; trigger_branch: string; stages?: string[]; yaml_content?: string }) {
    return request.post('/git/pipelines', { ...data, ...getParams() })
  }

  async function updatePipeline(id: string, data: { name?: string; trigger_branch?: string; stages?: string[]; yaml_content?: string }) {
    return request.put(`/git/pipelines/${id}`, { ...data, ...getParams() })
  }

  async function deletePipeline(id: string) {
    return request.delete(`/git/pipelines/${id}`, { params: getParams() })
  }

  async function fetchDeployHistory() {
    if (!currentAlias.value || !repoPath.value) return
    const res = await request.get<DeployHistory[]>('/git/deploy-history', { params: getParams() })
    deployHistory.value = res
  }

  async function rollback(historyId: string) {
    return request.post(`/git/deploy/rollback/${historyId}`, getParams())
  }

  async function fetchSyncConfigs() {
    if (!currentAlias.value) return
    const res = await request.get<SyncConfig[]>('/git/sync/configs', { params: { account_alias: currentAlias.value } })
    syncConfigs.value = res
  }

  async function createSyncConfig(data: { repo_path: string; interval: number; mode: string; auto_deploy: boolean }) {
    return request.post('/git/sync/configs', { ...data, account_alias: currentAlias.value })
  }

  async function updateSyncConfig(id: string, data: { interval?: number; mode?: string; auto_deploy?: boolean; status?: string }) {
    return request.put(`/git/sync/configs/${id}`, { ...data, account_alias: currentAlias.value })
  }

  async function deleteSyncConfig(id: string) {
    return request.delete(`/git/sync/configs/${id}`, { params: { account_alias: currentAlias.value } })
  }

  async function fetchSyncStatus(configId: string) {
    const res = await request.get<SyncStatus>(`/git/sync/status/${configId}`, {
      params: { account_alias: currentAlias.value },
    })
    syncStatus.value = res
  }

  async function manualPull(configId: string) {
    return request.post(`/git/sync/pull/${configId}`, { account_alias: currentAlias.value })
  }

  async function fetchSyncLogs(configId: string) {
    const res = await request.get<SyncLog[]>(`/git/sync/logs/${configId}`, {
      params: { account_alias: currentAlias.value },
    })
    syncLogs.value = res
  }

  return {
    currentAlias,
    repoPath,
    loading,
    repoInfo,
    branches,
    commits,
    commitTotal,
    webhooks,
    pipelines,
    deployHistory,
    syncConfigs,
    syncLogs,
    syncStatus,
    setAccountAlias,
    setRepoPath,
    fetchRepoInfo,
    initRepo,
    cloneRepo,
    configRemote,
    fetchBranches,
    createBranch,
    switchBranch,
    mergeBranch,
    deleteBranch,
    compareBranches,
    fetchCommits,
    fetchCommitDiff,
    fetchWebhooks,
    createWebhook,
    deleteWebhook,
    toggleWebhook,
    fetchPipelines,
    createPipeline,
    updatePipeline,
    deletePipeline,
    fetchDeployHistory,
    rollback,
    fetchSyncConfigs,
    createSyncConfig,
    updateSyncConfig,
    deleteSyncConfig,
    fetchSyncStatus,
    manualPull,
    fetchSyncLogs,
  }
})
