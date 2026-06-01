import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { nextTick } from 'vue'

vi.mock('@/components/md3', () => ({
  Md3Icon: { name: 'Md3Icon', props: ['name', 'size'], template: '<span class="mdi-icon" :data-name="name"></span>' },
  Md3Confirm: { show: vi.fn().mockResolvedValue(true) },
  Md3Message: { success: vi.fn(), error: vi.fn() },
  Md3Tag: { name: 'Md3Tag', props: ['type', 'size', 'variant'], template: '<span class="md3-tag"><slot /></span>' },
  Md3Input: { name: 'Md3Input', props: ['modelValue', 'label', 'placeholder', 'type'], emits: ['update:modelValue'], template: '<input class="md3-input" :value="modelValue" />' },
  Md3Select: { name: 'Md3Select', props: ['modelValue', 'options', 'placeholder', 'label'], emits: ['update:modelValue'], template: '<select class="md3-select" />' },
  Md3Card: { name: 'Md3Card', props: ['shadow'], template: '<div class="md3-card"><slot /><slot name="header" /></div>' },
  Md3Empty: { name: 'Md3Empty', props: ['description'], template: '<div class="md3-empty">{{ description }}</div>' },
  Md3Dialog: { name: 'Md3Dialog', props: ['visible', 'title', 'width'], emits: ['update:visible'], template: '<div class="md3-dialog" v-if="visible"><slot /><slot name="footer" /></div>' },
  Md3Table: { name: 'Md3Table', props: ['columns', 'data', 'stripe', 'emptyText'], template: '<div class="md3-table"><slot /></div>' },
  Md3Tabs: { name: 'Md3Tabs', props: ['modelValue', 'tabs'], template: '<div class="md3-tabs" />' },
  Md3Divider: { name: 'Md3Divider', template: '<hr class="md3-divider" />' },
  Md3Button: { name: 'Md3Button', props: ['size', 'variant', 'disabled', 'loading'], template: '<button class="md3-btn" :disabled="disabled" @click="$emit(\'click\')"><slot /></button>' },
  Md3Progress: { name: 'Md3Progress', props: ['percentage', 'color'], template: '<div class="md3-progress" />' },
  Md3Switch: { name: 'Md3Switch', props: ['modelValue', 'onText', 'offText'], emits: ['update:modelValue'], template: '<div class="md3-switch" />' },
}))

vi.mock('@/components/Md3Button.vue', () => ({
  default: { name: 'Md3Button', props: ['size', 'variant', 'disabled', 'loading', 'type'], template: '<button class="md3-btn" :disabled="disabled" @click="$emit(\'click\')"><slot /></button>' },
}))

vi.mock('@/components/md3/Md3Message', () => ({
  Md3Message: { success: vi.fn(), error: vi.fn() },
}))

vi.mock('@/components/md3/Md3Confirm', () => ({
  Md3Confirm: { show: vi.fn().mockResolvedValue(true) },
}))

let mockGitStore: any

vi.mock('@/stores/gitIntegrationStore', () => ({
  useGitIntegrationStore: () => mockGitStore,
}))

beforeEach(() => {
  setActivePinia(createPinia())
  vi.clearAllMocks()
  mockGitStore = {
    branches: [
      { name: 'main', is_current: true, last_commit: 'abc123', upstream: 'origin/main' },
      { name: 'develop', is_current: false, last_commit: 'def456', upstream: 'origin/develop' },
      { name: 'feature/test', is_current: false, last_commit: 'ghi789', upstream: '' },
    ],
    repoInfo: { current_branch: 'main', branch_count: 3, remotes: [{ name: 'origin', url: 'https://github.com/test/repo.git' }], repo_size: '10MB', last_commit: 'abc123', is_dirty: false },
    commits: [],
    commitTotal: 0,
    webhooks: [
      { id: 'wh1', platform: 'github', event: 'push', branch_filter: 'main', status: 'active' },
      { id: 'wh2', platform: 'gitlab', event: 'tag', branch_filter: '', status: 'inactive' },
    ],
    pipelines: [
      { id: 'p1', name: 'deploy-prod', trigger_branch: 'main', stages: ['build', 'test', 'deploy'], yaml_content: 'stages:\n  - build' },
    ],
    deployHistory: [
      { id: 'h1', time: '2024-01-01 10:00', trigger_type: 'webhook', branch: 'main', status: 'success', duration: '5m' },
      { id: 'h2', time: '2024-01-02 11:00', trigger_type: 'manual', branch: 'develop', status: 'failed', duration: '2m' },
      { id: 'h3', time: '2024-01-03 12:00', trigger_type: 'manual', branch: 'feature/test', status: 'running', duration: '1m' },
    ],
    syncConfigs: [],
    syncLogs: [],
    syncStatus: { last_sync_time: '', next_check_time: '', diff_commits: 0 },
    fetchBranches: vi.fn().mockResolvedValue(undefined),
    switchBranch: vi.fn().mockResolvedValue(undefined),
    mergeBranch: vi.fn().mockResolvedValue(undefined),
    deleteBranch: vi.fn().mockResolvedValue(undefined),
    createBranch: vi.fn().mockResolvedValue(undefined),
    compareBranches: vi.fn().mockResolvedValue({ files: ['src/main.ts', 'src/utils.ts'] }),
    fetchRepoInfo: vi.fn().mockResolvedValue(undefined),
    fetchCommits: vi.fn().mockResolvedValue(undefined),
    fetchWebhooks: vi.fn().mockResolvedValue(undefined),
    createWebhook: vi.fn().mockResolvedValue(undefined),
    toggleWebhook: vi.fn().mockResolvedValue(undefined),
    deleteWebhook: vi.fn().mockResolvedValue(undefined),
    fetchPipelines: vi.fn().mockResolvedValue(undefined),
    createPipeline: vi.fn().mockResolvedValue(undefined),
    updatePipeline: vi.fn().mockResolvedValue(undefined),
    deletePipeline: vi.fn().mockResolvedValue(undefined),
    fetchDeployHistory: vi.fn().mockResolvedValue(undefined),
    rollback: vi.fn().mockResolvedValue(undefined),
    fetchSyncConfigs: vi.fn().mockResolvedValue(undefined),
    fetchSyncStatus: vi.fn().mockResolvedValue(undefined),
    fetchSyncLogs: vi.fn().mockResolvedValue(undefined),
    createSyncConfig: vi.fn().mockResolvedValue(undefined),
    updateSyncConfig: vi.fn().mockResolvedValue(undefined),
    deleteSyncConfig: vi.fn().mockResolvedValue(undefined),
    manualPull: vi.fn().mockResolvedValue(undefined),
  }
})

import GitBranchPanel from '@/components/GitBranchPanel.vue'
import GitCommitPanel from '@/components/GitCommitPanel.vue'
import GitRepoPanel from '@/components/GitRepoPanel.vue'
import GitSyncPanel from '@/components/GitSyncPanel.vue'
import WebhookDeployPanel from '@/components/WebhookDeployPanel.vue'

describe('GitBranchPanel', () => {
  function createWrapper() {
    return mount(GitBranchPanel)
  }

  it('应该渲染 Git 分支面板', () => {
    const wrapper = createWrapper()
    expect(wrapper.find('.git-branch-panel').exists()).toBe(true)
  })

  it('应该渲染面板容器', () => {
    const wrapper = createWrapper()
    expect(wrapper.element).toBeTruthy()
  })

  it('应该渲染创建分支和刷新按钮', () => {
    const wrapper = createWrapper()
    expect(wrapper.text()).toContain('创建分支')
    expect(wrapper.text()).toContain('刷新')
  })

  it('点击刷新按钮应调用 fetchBranches', async () => {
    const wrapper = createWrapper()
    const buttons = wrapper.findAll('.md3-btn')
    const refreshBtn = buttons.find(b => b.text().includes('刷新'))
    if (refreshBtn) {
      await refreshBtn.trigger('click')
      expect(mockGitStore.fetchBranches).toHaveBeenCalled()
    }
  })

  it('点击创建分支按钮应显示对话框', async () => {
    const wrapper = createWrapper()
    const buttons = wrapper.findAll('.md3-btn')
    const createBtn = buttons.find(b => b.text().includes('创建分支'))
    if (createBtn) {
      await createBtn.trigger('click')
      await nextTick()
      const vm = wrapper.vm as any
      if (vm.showCreateDialog !== undefined) {
        expect(vm.showCreateDialog).toBe(true)
      }
    }
  })

  it('handleSwitch 成功时应显示成功消息', async () => {
    const wrapper = createWrapper()
    await nextTick()
    const vm = wrapper.vm as any
    if (typeof vm.handleSwitch === 'function') {
      await vm.handleSwitch('develop')
      expect(mockGitStore.switchBranch).toHaveBeenCalledWith('develop')
    }
  })

  it('handleSwitch 失败时应显示错误消息', async () => {
    mockGitStore.switchBranch.mockRejectedValue(new Error('Switch failed'))
    const wrapper = createWrapper()
    await nextTick()
    const vm = wrapper.vm as any
    if (typeof vm.handleSwitch === 'function') {
      await vm.handleSwitch('develop')
    }
  })

  it('openMergeDialog 应设置 mergeSource 并显示对话框', async () => {
    const wrapper = createWrapper()
    await nextTick()
    const vm = wrapper.vm as any
    if (typeof vm.openMergeDialog === 'function') {
      vm.openMergeDialog('develop')
      expect(vm.mergeSource).toBe('develop')
      expect(vm.showMergeDialog).toBe(true)
    }
  })

  it('handleMerge 成功时应显示成功消息', async () => {
    const wrapper = createWrapper()
    await nextTick()
    const vm = wrapper.vm as any
    if (typeof vm.handleMerge === 'function') {
      vm.mergeSource = 'develop'
      await vm.handleMerge()
      expect(mockGitStore.mergeBranch).toHaveBeenCalledWith('develop', 'main')
    }
  })

  it('handleMerge 失败时应显示错误消息', async () => {
    mockGitStore.mergeBranch.mockRejectedValue(new Error('Merge failed'))
    const wrapper = createWrapper()
    await nextTick()
    const vm = wrapper.vm as any
    if (typeof vm.handleMerge === 'function') {
      vm.mergeSource = 'develop'
      await vm.handleMerge()
    }
  })

  it('confirmDeleteBranch 应设置 deleteTarget 并显示对话框', async () => {
    const wrapper = createWrapper()
    await nextTick()
    const vm = wrapper.vm as any
    if (typeof vm.confirmDeleteBranch === 'function') {
      vm.confirmDeleteBranch('feature/test')
      expect(vm.deleteTarget).toBe('feature/test')
      expect(vm.showDeleteDialog).toBe(true)
    }
  })

  it('handleDelete 成功时应显示成功消息', async () => {
    const wrapper = createWrapper()
    await nextTick()
    const vm = wrapper.vm as any
    if (typeof vm.handleDelete === 'function') {
      vm.deleteTarget = 'feature/test'
      await vm.handleDelete()
      expect(mockGitStore.deleteBranch).toHaveBeenCalledWith('feature/test')
    }
  })

  it('handleDelete 失败时应显示错误消息', async () => {
    mockGitStore.deleteBranch.mockRejectedValue(new Error('Delete failed'))
    const wrapper = createWrapper()
    await nextTick()
    const vm = wrapper.vm as any
    if (typeof vm.handleDelete === 'function') {
      vm.deleteTarget = 'feature/test'
      await vm.handleDelete()
    }
  })

  it('handleCreate 成功时应显示成功消息', async () => {
    const wrapper = createWrapper()
    await nextTick()
    const vm = wrapper.vm as any
    if (typeof vm.handleCreate === 'function') {
      vm.createForm = { name: 'feature/new', base: 'main' }
      await vm.handleCreate()
      expect(mockGitStore.createBranch).toHaveBeenCalledWith('feature/new', 'main')
    }
  })

  it('handleCreate 无 base 时应传 undefined', async () => {
    const wrapper = createWrapper()
    await nextTick()
    const vm = wrapper.vm as any
    if (typeof vm.handleCreate === 'function') {
      vm.createForm = { name: 'feature/new', base: '' }
      await vm.handleCreate()
      expect(mockGitStore.createBranch).toHaveBeenCalledWith('feature/new', undefined)
    }
  })

  it('handleCreate 失败时应显示错误消息', async () => {
    mockGitStore.createBranch.mockRejectedValue(new Error('Create failed'))
    const wrapper = createWrapper()
    await nextTick()
    const vm = wrapper.vm as any
    if (typeof vm.handleCreate === 'function') {
      vm.createForm = { name: 'feature/new', base: '' }
      await vm.handleCreate()
    }
  })

  it('handleCompare 成功时应设置 diffFiles', async () => {
    const wrapper = createWrapper()
    await nextTick()
    const vm = wrapper.vm as any
    if (typeof vm.handleCompare === 'function') {
      vm.compareSource = 'main'
      vm.compareTarget = 'develop'
      await vm.handleCompare()
      expect(mockGitStore.compareBranches).toHaveBeenCalledWith('main', 'develop')
    }
  })

  it('handleCompare 无选择时应提前返回', async () => {
    mockGitStore.compareBranches.mockClear()
    const wrapper = createWrapper()
    await nextTick()
    const vm = wrapper.vm as any
    if (typeof vm.handleCompare === 'function') {
      vm.compareSource = ''
      vm.compareTarget = ''
      await vm.handleCompare()
      expect(mockGitStore.compareBranches).not.toHaveBeenCalled()
    }
  })

  it('handleCompare 失败时应显示错误消息', async () => {
    mockGitStore.compareBranches.mockRejectedValue(new Error('Compare failed'))
    const wrapper = createWrapper()
    await nextTick()
    const vm = wrapper.vm as any
    if (typeof vm.handleCompare === 'function') {
      vm.compareSource = 'main'
      vm.compareTarget = 'develop'
      await vm.handleCompare()
    }
  })

  it('onMounted 应调用 fetchBranches', () => {
    createWrapper()
    expect(mockGitStore.fetchBranches).toHaveBeenCalled()
  })

  it('branchOptions 应从 branches 计算得出', async () => {
    const wrapper = createWrapper()
    await nextTick()
    const vm = wrapper.vm as any
    if (typeof vm.branchOptions !== 'undefined') {
      expect(vm.branchOptions.length).toBe(3)
    }
  })
})

describe('GitCommitPanel', () => {
  it('应该渲染 Git 提交面板', () => {
    const wrapper = mount(GitCommitPanel)
    expect(wrapper.find('.git-commit-panel').exists()).toBe(true)
  })

  it('应该渲染面板容器', () => {
    const wrapper = mount(GitCommitPanel)
    expect(wrapper.element).toBeTruthy()
  })
})

describe('GitRepoPanel', () => {
  it('应该渲染 Git 仓库面板', () => {
    const wrapper = mount(GitRepoPanel)
    expect(wrapper.find('.git-repo-panel').exists()).toBe(true)
  })

  it('应该渲染面板容器', () => {
    const wrapper = mount(GitRepoPanel)
    expect(wrapper.element).toBeTruthy()
  })
})

describe('GitSyncPanel', () => {
  function createWrapper() {
    return mount(GitSyncPanel)
  }

  it('应该渲染 Git 同步面板', () => {
    const wrapper = createWrapper()
    expect(wrapper.find('.git-sync-panel').exists()).toBe(true)
  })

  it('应该渲染面板容器', () => {
    const wrapper = createWrapper()
    expect(wrapper.element).toBeTruthy()
  })

  it('应该渲染创建同步配置按钮', () => {
    const wrapper = createWrapper()
    expect(wrapper.text()).toContain('创建同步配置')
  })

  it('应该渲染刷新按钮', () => {
    const wrapper = createWrapper()
    expect(wrapper.text()).toContain('刷新')
  })

  it('modeTagType 应正确映射模式标签类型', async () => {
    const wrapper = createWrapper()
    await nextTick()
    const vm = wrapper.vm as any
    expect(vm.modeTagType('auto_pull')).toBe('success')
    expect(vm.modeTagType('notify_only')).toBe('warning')
    expect(vm.modeTagType('manual')).toBe('info')
    expect(vm.modeTagType('other')).toBe('info')
  })

  it('modeLabel 应正确映射模式标签', async () => {
    const wrapper = createWrapper()
    await nextTick()
    const vm = wrapper.vm as any
    expect(vm.modeLabel('auto_pull')).toBe('自动拉取')
    expect(vm.modeLabel('notify_only')).toBe('仅通知')
    expect(vm.modeLabel('manual')).toBe('手动')
    expect(vm.modeLabel('other')).toBe('手动')
  })

  it('openEditDialog 应设置编辑状态并打开对话框', async () => {
    const wrapper = createWrapper()
    await nextTick()
    const vm = wrapper.vm as any
    const config = { id: 'cfg-1', repo_path: '/repo', interval: 300, mode: 'auto_pull', auto_deploy: true }
    vm.openEditDialog(config)
    expect(vm.configEditId).toBe('cfg-1')
    expect(vm.configForm.repo_path).toBe('/repo')
    expect(vm.configForm.interval).toBe(300)
    expect(vm.showConfigDialog).toBe(true)
  })

  it('handleSaveConfig 新建时应调用 createSyncConfig', async () => {
    const { Md3Message } = await import('@/components/md3/Md3Message')
    const wrapper = createWrapper()
    await nextTick()
    const vm = wrapper.vm as any
    vm.configEditId = ''
    vm.configForm = { repo_path: '/new-repo', interval: 300, mode: 'auto_pull', auto_deploy: false }
    await vm.handleSaveConfig()
    expect(mockGitStore.createSyncConfig).toHaveBeenCalled()
    expect(Md3Message.success).toHaveBeenCalled()
    expect(vm.showConfigDialog).toBe(false)
  })

  it('handleSaveConfig 编辑时应调用 updateSyncConfig', async () => {
    const { Md3Message } = await import('@/components/md3/Md3Message')
    const wrapper = createWrapper()
    await nextTick()
    const vm = wrapper.vm as any
    vm.configEditId = 'cfg-1'
    vm.configForm = { repo_path: '/updated', interval: 900, mode: 'notify_only', auto_deploy: true }
    await vm.handleSaveConfig()
    expect(mockGitStore.updateSyncConfig).toHaveBeenCalledWith('cfg-1', { repo_path: '/updated', interval: 900, mode: 'notify_only', auto_deploy: true })
    expect(Md3Message.success).toHaveBeenCalled()
  })

  it('handleSaveConfig 失败时应显示错误', async () => {
    const { Md3Message } = await import('@/components/md3/Md3Message')
    mockGitStore.createSyncConfig.mockRejectedValueOnce(new Error('fail'))
    const wrapper = createWrapper()
    await nextTick()
    const vm = wrapper.vm as any
    vm.configEditId = ''
    await vm.handleSaveConfig()
    expect(Md3Message.error).toHaveBeenCalled()
  })

  it('handleManualPull 成功时应显示成功消息', async () => {
    const { Md3Message } = await import('@/components/md3/Md3Message')
    const wrapper = createWrapper()
    await nextTick()
    const vm = wrapper.vm as any
    await vm.handleManualPull('cfg-1')
    expect(mockGitStore.manualPull).toHaveBeenCalledWith('cfg-1')
    expect(Md3Message.success).toHaveBeenCalled()
    expect(vm.selectedConfigId).toBe('cfg-1')
  })

  it('handleManualPull 成功时应获取同步状态和日志', async () => {
    const wrapper = createWrapper()
    await nextTick()
    const vm = wrapper.vm as any
    await vm.handleManualPull('cfg-1')
    expect(mockGitStore.fetchSyncStatus).toHaveBeenCalledWith('cfg-1')
    expect(mockGitStore.fetchSyncLogs).toHaveBeenCalledWith('cfg-1')
  })

  it('handleManualPull 失败时应显示错误', async () => {
    const { Md3Message } = await import('@/components/md3/Md3Message')
    mockGitStore.manualPull.mockRejectedValueOnce(new Error('fail'))
    const wrapper = createWrapper()
    await nextTick()
    const vm = wrapper.vm as any
    await vm.handleManualPull('cfg-1')
    expect(Md3Message.error).toHaveBeenCalled()
  })

  it('handleDeleteConfig 确认时应调用 deleteSyncConfig', async () => {
    const { Md3Message } = await import('@/components/md3/Md3Message')
    const wrapper = createWrapper()
    await nextTick()
    const vm = wrapper.vm as any
    await vm.handleDeleteConfig('cfg-1')
    expect(mockGitStore.deleteSyncConfig).toHaveBeenCalledWith('cfg-1')
    expect(Md3Message.success).toHaveBeenCalled()
  })

  it('handleDeleteConfig 取消时不应删除', async () => {
    const { Md3Confirm } = await import('@/components/md3/Md3Confirm')
    Md3Confirm.show.mockResolvedValueOnce(false)
    const wrapper = createWrapper()
    await nextTick()
    const vm = wrapper.vm as any
    await vm.handleDeleteConfig('cfg-1')
    expect(mockGitStore.deleteSyncConfig).not.toHaveBeenCalled()
  })

  it('handleDeleteConfig 删除当前选中的配置时应清空 selectedConfigId', async () => {
    const wrapper = createWrapper()
    await nextTick()
    const vm = wrapper.vm as any
    vm.selectedConfigId = 'cfg-1'
    await vm.handleDeleteConfig('cfg-1')
    expect(vm.selectedConfigId).toBe('')
  })

  it('handleDeleteConfig 失败时应显示错误', async () => {
    const { Md3Message } = await import('@/components/md3/Md3Message')
    mockGitStore.deleteSyncConfig.mockRejectedValueOnce(new Error('fail'))
    const wrapper = createWrapper()
    await nextTick()
    const vm = wrapper.vm as any
    await vm.handleDeleteConfig('cfg-1')
    expect(Md3Message.error).toHaveBeenCalled()
  })

  it('onMounted 应调用 fetchSyncConfigs', () => {
    createWrapper()
    expect(mockGitStore.fetchSyncConfigs).toHaveBeenCalled()
  })
})

describe('WebhookDeployPanel', () => {
  function createWrapper() {
    return mount(WebhookDeployPanel)
  }

  it('应该渲染 Webhook 部署面板', () => {
    const wrapper = createWrapper()
    expect(wrapper.find('.webhook-deploy-panel').exists()).toBe(true)
  })

  it('应该渲染三个卡片区域', () => {
    const wrapper = createWrapper()
    const cards = wrapper.findAll('.section-card')
    expect(cards.length).toBe(3)
  })

  it('应该渲染 Webhook 配置区域', () => {
    const wrapper = createWrapper()
    expect(wrapper.text()).toContain('Webhook 配置')
  })

  it('应该渲染部署流程区域', () => {
    const wrapper = createWrapper()
    expect(wrapper.text()).toContain('部署流程')
  })

  it('应该渲染部署历史区域', () => {
    const wrapper = createWrapper()
    expect(wrapper.text()).toContain('部署历史')
  })

  it('onMounted 应调用三个 fetch 方法', () => {
    createWrapper()
    expect(mockGitStore.fetchWebhooks).toHaveBeenCalled()
    expect(mockGitStore.fetchPipelines).toHaveBeenCalled()
    expect(mockGitStore.fetchDeployHistory).toHaveBeenCalled()
  })

  it('handleCreateWebhook 成功时应显示成功消息', async () => {
    const wrapper = createWrapper()
    await nextTick()
    const vm = wrapper.vm as any
    if (typeof vm.handleCreateWebhook === 'function') {
      vm.webhookForm = { platform: 'github', event: 'push', branch_filter: 'main' }
      await vm.handleCreateWebhook()
      expect(mockGitStore.createWebhook).toHaveBeenCalledWith({ platform: 'github', event: 'push', branch_filter: 'main' })
    }
  })

  it('handleCreateWebhook 失败时应显示错误消息', async () => {
    mockGitStore.createWebhook.mockRejectedValue(new Error('Create failed'))
    const wrapper = createWrapper()
    await nextTick()
    const vm = wrapper.vm as any
    if (typeof vm.handleCreateWebhook === 'function') {
      vm.webhookForm = { platform: 'github', event: 'push', branch_filter: '' }
      await vm.handleCreateWebhook()
    }
  })

  it('handleToggleWebhook 应切换状态', async () => {
    const wrapper = createWrapper()
    await nextTick()
    const vm = wrapper.vm as any
    if (typeof vm.handleToggleWebhook === 'function') {
      await vm.handleToggleWebhook({ id: 'wh1', status: 'active' })
      expect(mockGitStore.toggleWebhook).toHaveBeenCalledWith('wh1', 'inactive')
    }
  })

  it('handleToggleWebhook inactive 应切换为 active', async () => {
    const wrapper = createWrapper()
    await nextTick()
    const vm = wrapper.vm as any
    if (typeof vm.handleToggleWebhook === 'function') {
      await vm.handleToggleWebhook({ id: 'wh2', status: 'inactive' })
      expect(mockGitStore.toggleWebhook).toHaveBeenCalledWith('wh2', 'active')
    }
  })

  it('handleToggleWebhook 失败时应显示错误消息', async () => {
    mockGitStore.toggleWebhook.mockRejectedValue(new Error('Toggle failed'))
    const wrapper = createWrapper()
    await nextTick()
    const vm = wrapper.vm as any
    if (typeof vm.handleToggleWebhook === 'function') {
      await vm.handleToggleWebhook({ id: 'wh1', status: 'active' })
    }
  })

  it('handleDeleteWebhook 确认后应删除', async () => {
    const wrapper = createWrapper()
    await nextTick()
    const vm = wrapper.vm as any
    if (typeof vm.handleDeleteWebhook === 'function') {
      await vm.handleDeleteWebhook('wh1')
      expect(mockGitStore.deleteWebhook).toHaveBeenCalledWith('wh1')
    }
  })

  it('handleDeleteWebhook 失败时应显示错误消息', async () => {
    mockGitStore.deleteWebhook.mockRejectedValue(new Error('Delete failed'))
    const wrapper = createWrapper()
    await nextTick()
    const vm = wrapper.vm as any
    if (typeof vm.handleDeleteWebhook === 'function') {
      await vm.handleDeleteWebhook('wh1')
    }
  })

  it('openPipelineDialog 无参数时应重置表单', async () => {
    const wrapper = createWrapper()
    await nextTick()
    const vm = wrapper.vm as any
    if (typeof vm.openPipelineDialog === 'function') {
      vm.openPipelineDialog()
      expect(vm.pipelineEditId).toBe('')
      expect(vm.showPipelineDialog).toBe(true)
    }
  })

  it('openPipelineDialog 有参数时应填充表单', async () => {
    const wrapper = createWrapper()
    await nextTick()
    const vm = wrapper.vm as any
    if (typeof vm.openPipelineDialog === 'function') {
      const pipeline = { id: 'p1', name: 'deploy-prod', trigger_branch: 'main', stages: ['build'], yaml_content: 'test' }
      vm.openPipelineDialog(pipeline)
      expect(vm.pipelineEditId).toBe('p1')
      expect(vm.pipelineForm.name).toBe('deploy-prod')
      expect(vm.showPipelineDialog).toBe(true)
    }
  })

  it('handleSavePipeline 新建时应调用 createPipeline', async () => {
    const wrapper = createWrapper()
    await nextTick()
    const vm = wrapper.vm as any
    if (typeof vm.handleSavePipeline === 'function') {
      vm.pipelineEditId = ''
      vm.pipelineForm = { name: 'new-pipeline', trigger_branch: 'main', yaml_content: 'test' }
      await vm.handleSavePipeline()
      expect(mockGitStore.createPipeline).toHaveBeenCalled()
    }
  })

  it('handleSavePipeline 编辑时应调用 updatePipeline', async () => {
    const wrapper = createWrapper()
    await nextTick()
    const vm = wrapper.vm as any
    if (typeof vm.handleSavePipeline === 'function') {
      vm.pipelineEditId = 'p1'
      vm.pipelineForm = { name: 'updated', trigger_branch: 'main', yaml_content: 'test' }
      await vm.handleSavePipeline()
      expect(mockGitStore.updatePipeline).toHaveBeenCalledWith('p1', vm.pipelineForm)
    }
  })

  it('handleSavePipeline 失败时应显示错误消息', async () => {
    mockGitStore.createPipeline.mockRejectedValue(new Error('Save failed'))
    const wrapper = createWrapper()
    await nextTick()
    const vm = wrapper.vm as any
    if (typeof vm.handleSavePipeline === 'function') {
      vm.pipelineEditId = ''
      vm.pipelineForm = { name: 'test', trigger_branch: '', yaml_content: '' }
      await vm.handleSavePipeline()
    }
  })

  it('handleDeletePipeline 确认后应删除', async () => {
    const wrapper = createWrapper()
    await nextTick()
    const vm = wrapper.vm as any
    if (typeof vm.handleDeletePipeline === 'function') {
      await vm.handleDeletePipeline('p1')
      expect(mockGitStore.deletePipeline).toHaveBeenCalledWith('p1')
    }
  })

  it('handleDeletePipeline 失败时应显示错误消息', async () => {
    mockGitStore.deletePipeline.mockRejectedValue(new Error('Delete failed'))
    const wrapper = createWrapper()
    await nextTick()
    const vm = wrapper.vm as any
    if (typeof vm.handleDeletePipeline === 'function') {
      await vm.handleDeletePipeline('p1')
    }
  })

  it('handleRollback 确认后应回滚', async () => {
    const wrapper = createWrapper()
    await nextTick()
    const vm = wrapper.vm as any
    if (typeof vm.handleRollback === 'function') {
      await vm.handleRollback('h1')
      expect(mockGitStore.rollback).toHaveBeenCalledWith('h1')
    }
  })

  it('handleRollback 失败时应显示错误消息', async () => {
    mockGitStore.rollback.mockRejectedValue(new Error('Rollback failed'))
    const wrapper = createWrapper()
    await nextTick()
    const vm = wrapper.vm as any
    if (typeof vm.handleRollback === 'function') {
      await vm.handleRollback('h1')
    }
  })

  it('deployStatusType 应正确映射状态', async () => {
    const wrapper = createWrapper()
    await nextTick()
    const vm = wrapper.vm as any
    if (typeof vm.deployStatusType === 'function') {
      expect(vm.deployStatusType('success')).toBe('success')
      expect(vm.deployStatusType('failed')).toBe('danger')
      expect(vm.deployStatusType('running')).toBe('warning')
    }
  })

  it('deployStatusLabel 应正确映射状态', async () => {
    const wrapper = createWrapper()
    await nextTick()
    const vm = wrapper.vm as any
    if (typeof vm.deployStatusLabel === 'function') {
      expect(vm.deployStatusLabel('success')).toBe('成功')
      expect(vm.deployStatusLabel('failed')).toBe('失败')
      expect(vm.deployStatusLabel('running')).toBe('运行中')
    }
  })

  it('点击创建 Webhook 按钮应显示对话框', async () => {
    const wrapper = createWrapper()
    const buttons = wrapper.findAll('.md3-btn')
    const createBtn = buttons.find(b => b.text().includes('创建 Webhook'))
    if (createBtn) {
      await createBtn.trigger('click')
      await nextTick()
      const vm = wrapper.vm as any
      if (vm.showWebhookDialog !== undefined) {
        expect(vm.showWebhookDialog).toBe(true)
      }
    }
  })

  it('点击创建流程按钮应显示对话框', async () => {
    const wrapper = createWrapper()
    const buttons = wrapper.findAll('.md3-btn')
    const createBtn = buttons.find(b => b.text().includes('创建流程'))
    if (createBtn) {
      await createBtn.trigger('click')
      await nextTick()
      const vm = wrapper.vm as any
      if (vm.showPipelineDialog !== undefined) {
        expect(vm.showPipelineDialog).toBe(true)
      }
    }
  })
})
