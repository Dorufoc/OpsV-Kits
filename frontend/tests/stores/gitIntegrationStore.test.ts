import { describe, it, expect, vi, beforeEach } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useGitIntegrationStore } from '@/stores/gitIntegrationStore'
import { mockGet, mockPost, mockPut, mockDelete, mockPatch } from '../setup'

describe('GitIntegration Store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  describe('状态初始化', () => {
    it('应该正确初始化 currentAlias 为空字符串', () => {
      const store = useGitIntegrationStore()
      expect(store.currentAlias).toBe('')
    })

    it('应该正确初始化 repoPath 为空字符串', () => {
      const store = useGitIntegrationStore()
      expect(store.repoPath).toBe('')
    })

    it('应该正确初始化 loading 为 false', () => {
      const store = useGitIntegrationStore()
      expect(store.loading).toBe(false)
    })

    it('应该正确初始化 repoInfo', () => {
      const store = useGitIntegrationStore()
      expect(store.repoInfo).toEqual({
        current_branch: '',
        branch_count: 0,
        remotes: [],
        repo_size: '',
        last_commit: '',
        is_dirty: false,
      })
    })

    it('应该正确初始化 branches 为空数组', () => {
      const store = useGitIntegrationStore()
      expect(store.branches).toEqual([])
    })

    it('应该正确初始化 commits 为空数组', () => {
      const store = useGitIntegrationStore()
      expect(store.commits).toEqual([])
    })

    it('应该正确初始化 commitTotal 为 0', () => {
      const store = useGitIntegrationStore()
      expect(store.commitTotal).toBe(0)
    })

    it('应该正确初始化 webhooks 为空数组', () => {
      const store = useGitIntegrationStore()
      expect(store.webhooks).toEqual([])
    })

    it('应该正确初始化 pipelines 为空数组', () => {
      const store = useGitIntegrationStore()
      expect(store.pipelines).toEqual([])
    })

    it('应该正确初始化 deployHistory 为空数组', () => {
      const store = useGitIntegrationStore()
      expect(store.deployHistory).toEqual([])
    })

    it('应该正确初始化 syncConfigs 为空数组', () => {
      const store = useGitIntegrationStore()
      expect(store.syncConfigs).toEqual([])
    })

    it('应该正确初始化 syncLogs 为空数组', () => {
      const store = useGitIntegrationStore()
      expect(store.syncLogs).toEqual([])
    })

    it('应该正确初始化 syncStatus', () => {
      const store = useGitIntegrationStore()
      expect(store.syncStatus).toEqual({
        last_sync_time: '',
        next_check_time: '',
        diff_commits: 0,
      })
    })
  })

  describe('setAccountAlias / setRepoPath', () => {
    it('应该设置 currentAlias', () => {
      const store = useGitIntegrationStore()
      store.setAccountAlias('test-server')
      expect(store.currentAlias).toBe('test-server')
    })

    it('应该设置 repoPath', () => {
      const store = useGitIntegrationStore()
      store.setRepoPath('/home/user/repo')
      expect(store.repoPath).toBe('/home/user/repo')
    })
  })

  describe('fetchRepoInfo', () => {
    it('应该获取仓库信息', async () => {
      const mockRepoInfo = { current_branch: 'main', branch_count: 3, remotes: [], repo_size: '10MB', last_commit: 'abc123', is_dirty: false }
      mockGet.mockResolvedValue(mockRepoInfo)

      const store = useGitIntegrationStore()
      store.setAccountAlias('test-server')
      store.setRepoPath('/repo')
      await store.fetchRepoInfo()

      expect(store.repoInfo).toEqual(mockRepoInfo)
    })

    it('请求期间 loading 应该为 true', async () => {
      mockGet.mockImplementation(async () => {
        const store = useGitIntegrationStore()
        expect(store.loading).toBe(true)
        return {}
      })

      const store = useGitIntegrationStore()
      store.setAccountAlias('test-server')
      store.setRepoPath('/repo')
      await store.fetchRepoInfo()
      expect(store.loading).toBe(false)
    })

    it('请求失败时 loading 应该恢复为 false', async () => {
      mockGet.mockRejectedValue(new Error('Network error'))

      const store = useGitIntegrationStore()
      store.setAccountAlias('test-server')
      store.setRepoPath('/repo')
      await expect(store.fetchRepoInfo()).rejects.toThrow()
      expect(store.loading).toBe(false)
    })

    it('当没有 alias 时应该直接返回', async () => {
      const store = useGitIntegrationStore()
      await store.fetchRepoInfo()
      expect(mockGet).not.toHaveBeenCalled()
    })

    it('当没有 repoPath 时应该直接返回', async () => {
      const store = useGitIntegrationStore()
      store.setAccountAlias('test-server')
      await store.fetchRepoInfo()
      expect(mockGet).not.toHaveBeenCalled()
    })
  })

  describe('initRepo', () => {
    it('应该初始化仓库', async () => {
      mockPost.mockResolvedValue({ success: true })

      const store = useGitIntegrationStore()
      store.setAccountAlias('test-server')
      const result = await store.initRepo({ path: '/new-repo' })

      expect(mockPost).toHaveBeenCalledWith('/git/init', { path: '/new-repo', account_alias: 'test-server' })
    })
  })

  describe('cloneRepo', () => {
    it('应该克隆仓库', async () => {
      mockPost.mockResolvedValue({ success: true })

      const store = useGitIntegrationStore()
      store.setAccountAlias('test-server')
      await store.cloneRepo({ url: 'https://github.com/test/repo.git', target_path: '/repo' })

      expect(mockPost).toHaveBeenCalledWith('/git/clone', { url: 'https://github.com/test/repo.git', target_path: '/repo', account_alias: 'test-server' })
    })
  })

  describe('configRemote', () => {
    it('应该配置远程仓库', async () => {
      mockPost.mockResolvedValue({ success: true })

      const store = useGitIntegrationStore()
      store.setAccountAlias('test-server')
      store.setRepoPath('/repo')
      await store.configRemote({ name: 'origin', url: 'https://github.com/test/repo.git' })

      expect(mockPost).toHaveBeenCalledWith('/git/remote', { name: 'origin', url: 'https://github.com/test/repo.git', account_alias: 'test-server', repo_path: '/repo' })
    })
  })

  describe('fetchBranches', () => {
    it('应该获取分支列表', async () => {
      const mockBranches = [{ name: 'main', is_current: true, last_commit: 'abc', upstream: '' }]
      mockGet.mockResolvedValue(mockBranches)

      const store = useGitIntegrationStore()
      store.setAccountAlias('test-server')
      store.setRepoPath('/repo')
      await store.fetchBranches()

      expect(store.branches).toEqual(mockBranches)
    })

    it('当没有 alias 时应该直接返回', async () => {
      const store = useGitIntegrationStore()
      await store.fetchBranches()
      expect(mockGet).not.toHaveBeenCalled()
    })
  })

  describe('createBranch', () => {
    it('应该创建分支', async () => {
      mockPost.mockResolvedValue({ success: true })

      const store = useGitIntegrationStore()
      store.setAccountAlias('test-server')
      store.setRepoPath('/repo')
      await store.createBranch('feature', 'main')

      expect(mockPost).toHaveBeenCalledWith('/git/branch/create', { name: 'feature', base: 'main', account_alias: 'test-server', repo_path: '/repo' })
    })
  })

  describe('switchBranch', () => {
    it('应该切换分支', async () => {
      mockPost.mockResolvedValue({ success: true })

      const store = useGitIntegrationStore()
      store.setAccountAlias('test-server')
      store.setRepoPath('/repo')
      await store.switchBranch('develop')

      expect(mockPost).toHaveBeenCalledWith('/git/branch/switch', { name: 'develop', account_alias: 'test-server', repo_path: '/repo' })
    })
  })

  describe('mergeBranch', () => {
    it('应该合并分支', async () => {
      mockPost.mockResolvedValue({ success: true })

      const store = useGitIntegrationStore()
      store.setAccountAlias('test-server')
      store.setRepoPath('/repo')
      await store.mergeBranch('feature', 'main')

      expect(mockPost).toHaveBeenCalledWith('/git/branch/merge', { source: 'feature', target: 'main', account_alias: 'test-server', repo_path: '/repo' })
    })
  })

  describe('deleteBranch', () => {
    it('应该删除分支', async () => {
      mockPost.mockResolvedValue({ success: true })

      const store = useGitIntegrationStore()
      store.setAccountAlias('test-server')
      store.setRepoPath('/repo')
      await store.deleteBranch('feature')

      expect(mockPost).toHaveBeenCalledWith('/git/branch/delete', { name: 'feature', account_alias: 'test-server', repo_path: '/repo' })
    })
  })

  describe('compareBranches', () => {
    it('应该比较分支', async () => {
      const mockResult = { files: ['src/main.ts', 'src/utils.ts'] }
      mockGet.mockResolvedValue(mockResult)

      const store = useGitIntegrationStore()
      store.setAccountAlias('test-server')
      store.setRepoPath('/repo')
      const result = await store.compareBranches('feature', 'main')

      expect(result).toEqual(mockResult)
    })
  })

  describe('fetchCommits', () => {
    it('应该获取提交记录', async () => {
      const mockCommits = [{ short_hash: 'abc1234', hash: 'abc1234def', message: 'fix: bug', author: 'dev', date: '', files_changed: [] }]
      mockGet.mockResolvedValue({ items: mockCommits, total: 1 })

      const store = useGitIntegrationStore()
      store.setAccountAlias('test-server')
      store.setRepoPath('/repo')
      await store.fetchCommits({})

      expect(store.commits).toEqual(mockCommits)
      expect(store.commitTotal).toBe(1)
    })

    it('当没有 alias 时应该直接返回', async () => {
      const store = useGitIntegrationStore()
      await store.fetchCommits({})
      expect(mockGet).not.toHaveBeenCalled()
    })
  })

  describe('fetchCommitDiff', () => {
    it('应该获取提交差异', async () => {
      const mockDiff = { diff: '--- a/file\n+++ b/file', files: ['file.ts'] }
      mockGet.mockResolvedValue(mockDiff)

      const store = useGitIntegrationStore()
      store.setAccountAlias('test-server')
      store.setRepoPath('/repo')
      const result = await store.fetchCommitDiff('abc123')

      expect(result).toEqual(mockDiff)
    })
  })

  describe('fetchWebhooks', () => {
    it('应该获取 Webhook 列表', async () => {
      const mockWebhooks = [{ id: 'wh1', platform: 'github', event: 'push', branch_filter: 'main', status: 'active' }]
      mockGet.mockResolvedValue(mockWebhooks)

      const store = useGitIntegrationStore()
      store.setAccountAlias('test-server')
      store.setRepoPath('/repo')
      await store.fetchWebhooks()

      expect(store.webhooks).toEqual(mockWebhooks)
    })

    it('当没有 alias 时应该直接返回', async () => {
      const store = useGitIntegrationStore()
      await store.fetchWebhooks()
      expect(mockGet).not.toHaveBeenCalled()
    })
  })

  describe('createWebhook', () => {
    it('应该创建 Webhook', async () => {
      mockPost.mockResolvedValue({ id: 'wh2' })

      const store = useGitIntegrationStore()
      store.setAccountAlias('test-server')
      store.setRepoPath('/repo')
      await store.createWebhook({ platform: 'github', event: 'push' })

      expect(mockPost).toHaveBeenCalledWith('/git/webhooks', { platform: 'github', event: 'push', account_alias: 'test-server', repo_path: '/repo' })
    })
  })

  describe('deleteWebhook', () => {
    it('应该删除 Webhook', async () => {
      mockDelete.mockResolvedValue({})

      const store = useGitIntegrationStore()
      store.setAccountAlias('test-server')
      store.setRepoPath('/repo')
      await store.deleteWebhook('wh1')

      expect(mockDelete).toHaveBeenCalledWith('/git/webhooks/wh1', expect.objectContaining({ params: expect.any(Object) }))
    })
  })

  describe('toggleWebhook', () => {
    it('应该切换 Webhook 状态', async () => {
      mockPatch.mockResolvedValue({})

      const store = useGitIntegrationStore()
      store.setAccountAlias('test-server')
      store.setRepoPath('/repo')
      await store.toggleWebhook('wh1', 'inactive')

      expect(mockPatch).toHaveBeenCalledWith('/git/webhooks/wh1', { status: 'inactive', account_alias: 'test-server', repo_path: '/repo' })
    })
  })

  describe('fetchPipelines', () => {
    it('应该获取部署流水线列表', async () => {
      const mockPipelines = [{ id: 'p1', name: 'Deploy', trigger_branch: 'main', stages: ['build', 'deploy'], yaml_content: '' }]
      mockGet.mockResolvedValue(mockPipelines)

      const store = useGitIntegrationStore()
      store.setAccountAlias('test-server')
      store.setRepoPath('/repo')
      await store.fetchPipelines()

      expect(store.pipelines).toEqual(mockPipelines)
    })
  })

  describe('createPipeline', () => {
    it('应该创建部署流水线', async () => {
      mockPost.mockResolvedValue({ id: 'p2' })

      const store = useGitIntegrationStore()
      store.setAccountAlias('test-server')
      store.setRepoPath('/repo')
      await store.createPipeline({ name: 'CI', trigger_branch: 'develop' })

      expect(mockPost).toHaveBeenCalledWith('/git/pipelines', { name: 'CI', trigger_branch: 'develop', account_alias: 'test-server', repo_path: '/repo' })
    })
  })

  describe('updatePipeline', () => {
    it('应该更新部署流水线', async () => {
      mockPut.mockResolvedValue({})

      const store = useGitIntegrationStore()
      store.setAccountAlias('test-server')
      store.setRepoPath('/repo')
      await store.updatePipeline('p1', { name: 'Updated CI' })

      expect(mockPut).toHaveBeenCalledWith('/git/pipelines/p1', { name: 'Updated CI', account_alias: 'test-server', repo_path: '/repo' })
    })
  })

  describe('deletePipeline', () => {
    it('应该删除部署流水线', async () => {
      mockDelete.mockResolvedValue({})

      const store = useGitIntegrationStore()
      store.setAccountAlias('test-server')
      store.setRepoPath('/repo')
      await store.deletePipeline('p1')

      expect(mockDelete).toHaveBeenCalledWith('/git/pipelines/p1', expect.objectContaining({ params: expect.any(Object) }))
    })
  })

  describe('fetchDeployHistory', () => {
    it('应该获取部署历史', async () => {
      const mockHistory = [{ id: 'd1', time: '', trigger_type: 'manual', branch: 'main', status: 'success' as const, duration: '30s' }]
      mockGet.mockResolvedValue(mockHistory)

      const store = useGitIntegrationStore()
      store.setAccountAlias('test-server')
      store.setRepoPath('/repo')
      await store.fetchDeployHistory()

      expect(store.deployHistory).toEqual(mockHistory)
    })
  })

  describe('rollback', () => {
    it('应该回滚部署', async () => {
      mockPost.mockResolvedValue({ success: true })

      const store = useGitIntegrationStore()
      store.setAccountAlias('test-server')
      store.setRepoPath('/repo')
      await store.rollback('d1')

      expect(mockPost).toHaveBeenCalledWith('/git/deploy/rollback/d1', { account_alias: 'test-server', repo_path: '/repo' })
    })
  })

  describe('fetchSyncConfigs', () => {
    it('应该获取同步配置列表', async () => {
      const mockConfigs = [{ id: 'sc1', repo_path: '/repo', interval: 300, mode: 'auto_pull' as const, auto_deploy: false, status: 'active' as const, pending_updates: 0 }]
      mockGet.mockResolvedValue(mockConfigs)

      const store = useGitIntegrationStore()
      store.setAccountAlias('test-server')
      await store.fetchSyncConfigs()

      expect(store.syncConfigs).toEqual(mockConfigs)
    })

    it('当没有 alias 时应该直接返回', async () => {
      const store = useGitIntegrationStore()
      await store.fetchSyncConfigs()
      expect(mockGet).not.toHaveBeenCalled()
    })
  })

  describe('createSyncConfig', () => {
    it('应该创建同步配置', async () => {
      mockPost.mockResolvedValue({ id: 'sc2' })

      const store = useGitIntegrationStore()
      store.setAccountAlias('test-server')
      await store.createSyncConfig({ repo_path: '/repo', interval: 300, mode: 'auto_pull', auto_deploy: false })

      expect(mockPost).toHaveBeenCalledWith('/git/sync/configs', { repo_path: '/repo', interval: 300, mode: 'auto_pull', auto_deploy: false, account_alias: 'test-server' })
    })
  })

  describe('updateSyncConfig', () => {
    it('应该更新同步配置', async () => {
      mockPut.mockResolvedValue({})

      const store = useGitIntegrationStore()
      store.setAccountAlias('test-server')
      await store.updateSyncConfig('sc1', { interval: 600 })

      expect(mockPut).toHaveBeenCalledWith('/git/sync/configs/sc1', { interval: 600, account_alias: 'test-server' })
    })
  })

  describe('deleteSyncConfig', () => {
    it('应该删除同步配置', async () => {
      mockDelete.mockResolvedValue({})

      const store = useGitIntegrationStore()
      store.setAccountAlias('test-server')
      await store.deleteSyncConfig('sc1')

      expect(mockDelete).toHaveBeenCalledWith('/git/sync/configs/sc1', expect.objectContaining({ params: expect.any(Object) }))
    })
  })

  describe('fetchSyncStatus', () => {
    it('应该获取同步状态', async () => {
      const mockStatus = { last_sync_time: '2024-01-01', next_check_time: '2024-01-02', diff_commits: 2 }
      mockGet.mockResolvedValue(mockStatus)

      const store = useGitIntegrationStore()
      store.setAccountAlias('test-server')
      await store.fetchSyncStatus('sc1')

      expect(store.syncStatus).toEqual(mockStatus)
    })
  })

  describe('manualPull', () => {
    it('应该手动拉取', async () => {
      mockPost.mockResolvedValue({ success: true })

      const store = useGitIntegrationStore()
      store.setAccountAlias('test-server')
      await store.manualPull('sc1')

      expect(mockPost).toHaveBeenCalledWith('/git/sync/pull/sc1', { account_alias: 'test-server' })
    })
  })

  describe('fetchSyncLogs', () => {
    it('应该获取同步日志', async () => {
      const mockLogs = [{ time: '2024-01-01', action: 'pull', result: 'success' as const, summary: 'Updated 2 commits' }]
      mockGet.mockResolvedValue(mockLogs)

      const store = useGitIntegrationStore()
      store.setAccountAlias('test-server')
      await store.fetchSyncLogs('sc1')

      expect(store.syncLogs).toEqual(mockLogs)
    })
  })
})
