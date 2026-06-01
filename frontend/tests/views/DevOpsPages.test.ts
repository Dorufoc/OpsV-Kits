import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { nextTick } from 'vue'

vi.mock('@/components/md3', () => ({
  Md3Icon: { name: 'Md3Icon', props: ['name', 'size'], template: '<span class="mdi-icon" :data-name="name"></span>' },
  Md3Confirm: { show: vi.fn().mockResolvedValue(true) },
  Md3Message: { success: vi.fn(), error: vi.fn(), warning: vi.fn(), info: vi.fn() },
  Md3PageHeader: { name: 'Md3PageHeader', props: ['title', 'showBack', 'subtitle'], template: '<div class="md3-page-header">{{ title }}<slot name="subtitle" /><slot name="actions" /><slot name="content" /><slot name="extra" /></div>' },
  Md3Divider: { name: 'Md3Divider', template: '<hr class="md3-divider" />' },
  Md3Card: { name: 'Md3Card', props: ['shadow', 'hoverable'], template: '<div class="md3-card"><slot /><slot name="header" /></div>' },
  Md3Empty: { name: 'Md3Empty', props: ['description'], template: '<div class="md3-empty">{{ description }}</div>' },
  Md3Tag: { name: 'Md3Tag', props: ['type', 'size', 'variant'], template: '<span class="md3-tag"><slot /></span>' },
  Md3Table: { name: 'Md3Table', props: ['columns', 'data', 'stripe', 'emptyText', 'selection', 'maxHeight'], template: '<div class="md3-table"><slot /></div>' },
  Md3Tabs: { name: 'Md3Tabs', props: ['modelValue', 'tabs'], template: '<div class="md3-tabs" />' },
  Md3Dialog: { name: 'Md3Dialog', props: ['visible', 'title', 'width', 'closable'], emits: ['update:visible'], template: '<div class="md3-dialog" v-if="visible"><slot /><slot name="footer" /></div>' },
  Md3Input: { name: 'Md3Input', props: ['modelValue', 'label', 'placeholder', 'type', 'min', 'max'], emits: ['update:modelValue'], template: '<input class="md3-input" :value="modelValue" />' },
  Md3Select: { name: 'Md3Select', props: ['modelValue', 'options', 'placeholder', 'label', 'clearable', 'size'], emits: ['update:modelValue'], template: '<select class="md3-select" :data-placeholder="placeholder">{{ placeholder }}</select>' },
  Md3Alert: { name: 'Md3Alert', props: ['type', 'title', 'message'], template: '<div class="md3-alert"><slot name="title" /><slot name="message" /></div>' },
  Md3Switch: { name: 'Md3Switch', props: ['modelValue', 'onText', 'offText'], emits: ['update:modelValue'], template: '<div class="md3-switch" />' },
  Md3Progress: { name: 'Md3Progress', props: ['percentage', 'color'], template: '<div class="md3-progress" />' },
}))

vi.mock('@/components/Md3Button.vue', () => ({
  default: { name: 'Md3Button', props: ['size', 'variant', 'disabled', 'icon', 'loading', 'type'], template: '<button class="md3-btn" :disabled="disabled" @click="$emit(\'click\')"><slot /></button>' },
}))

vi.mock('@/components/md3/Md3Confirm', () => ({
  Md3Confirm: { show: vi.fn().mockResolvedValue(true) },
}))

vi.mock('@/components/GitBranchPanel.vue', () => ({
  default: { name: 'GitBranchPanel', template: '<div class="git-branch-panel" />' },
}))

vi.mock('@/components/GitCommitPanel.vue', () => ({
  default: { name: 'GitCommitPanel', template: '<div class="git-commit-panel" />' },
}))

vi.mock('@/components/GitRepoPanel.vue', () => ({
  default: { name: 'GitRepoPanel', template: '<div class="git-repo-panel" />' },
}))

vi.mock('@/components/GitSyncPanel.vue', () => ({
  default: { name: 'GitSyncPanel', template: '<div class="git-sync-panel" />' },
}))

vi.mock('@/components/WebhookDeployPanel.vue', () => ({
  default: { name: 'WebhookDeployPanel', template: '<div class="webhook-deploy-panel" />' },
}))

vi.mock('@/components/CronPicker.vue', () => ({
  default: { name: 'CronPicker', props: ['modelValue'], emits: ['update:modelValue'], template: '<div class="cron-picker" />' },
}))

vi.mock('@/components/BackupHistoryDrawer.vue', () => ({
  default: { name: 'BackupHistoryDrawer', props: ['visible'], emits: ['update:visible'], template: '<div class="backup-history-drawer" />' },
}))

vi.mock('@/components/workflow/WorkflowCanvas.vue', () => ({
  default: { name: 'WorkflowCanvas', props: ['nodes', 'edges', 'nodeExecutions'], emits: ['nodeClick', 'nodeDrag', 'nodeDragEnd', 'edgeClick', 'canvasClick', 'connect'], template: '<div class="workflow-canvas" />' },
}))

vi.mock('@/components/workflow/WorkflowNodePanel.vue', () => ({
  default: { name: 'WorkflowNodePanel', emits: ['dragStart'], template: '<div class="workflow-node-panel" />' },
}))

vi.mock('@/components/workflow/NodeConfigPanel.vue', () => ({
  default: { name: 'NodeConfigPanel', props: ['node', 'sshAccounts'], emits: ['update', 'close'], template: '<div class="node-config-panel" />' },
}))

vi.mock('@/components/workflow/WorkflowTemplateGallery.vue', () => ({
  default: { name: 'WorkflowTemplateGallery', template: '<div class="workflow-template-gallery" />' },
}))

const mockPush = vi.fn()
vi.mock('vue-router', () => ({
  useRouter: () => ({ push: mockPush }),
  useRoute: () => ({ params: { id: 'test-workflow-id' }, query: {} }),
}))

let sshStoreMock: any
let gitStoreMock: any
let workflowStoreMock: any
let cronBackupStoreMock: any

vi.mock('@/stores/sshAccountStore', () => ({
  useSshAccountStore: () => sshStoreMock,
}))

vi.mock('@/stores/gitIntegrationStore', () => ({
  useGitIntegrationStore: () => gitStoreMock,
}))

vi.mock('@/stores/workflowStore', () => ({
  useWorkflowStore: () => workflowStoreMock,
}))

vi.mock('@/stores/cronBackupStore', () => ({
  useCronBackupStore: () => cronBackupStoreMock,
}))

let schedulerStoreMock: any
let eventTriggerStoreMock: any

vi.mock('@/stores/schedulerStore', () => ({
  useSchedulerStore: () => schedulerStoreMock,
}))

vi.mock('@/stores/eventTriggerStore', () => ({
  useEventTriggerStore: () => eventTriggerStoreMock,
}))

beforeEach(() => {
  setActivePinia(createPinia())
  vi.clearAllMocks()
  sshStoreMock = {
    accounts: [{ alias: 'test-server', host: '192.168.1.1', default: true }],
    fetchAccounts: vi.fn().mockResolvedValue(undefined),
  }
  gitStoreMock = {
    currentAlias: '',
    repoPath: '',
    setAccountAlias: vi.fn(),
    setRepoPath: vi.fn(),
    fetchRepoInfo: vi.fn().mockResolvedValue(undefined),
  }
  workflowStoreMock = {
    workflows: [],
    versions: [],
    currentWorkflow: null,
    currentExecution: null,
    nodeExecutions: [],
    loading: false,
    activeWorkflowCount: 0,
    runningExecutionCount: 0,
    templates: [],
    fetchWorkflows: vi.fn().mockResolvedValue(undefined),
    fetchWorkflow: vi.fn().mockResolvedValue(undefined),
    fetchVersions: vi.fn().mockResolvedValue(undefined),
    fetchExecution: vi.fn().mockResolvedValue(undefined),
    fetchNodeExecutions: vi.fn().mockResolvedValue(undefined),
    fetchTemplates: vi.fn().mockResolvedValue(undefined),
    createWorkflow: vi.fn().mockResolvedValue({ id: '1', name: 'test' }),
    createFromTemplate: vi.fn().mockResolvedValue({ id: '2', name: 'from-template' }),
    updateWorkflow: vi.fn().mockResolvedValue(undefined),
    deleteWorkflow: vi.fn().mockResolvedValue(undefined),
    executeWorkflow: vi.fn().mockResolvedValue(undefined),
    getWorkflow: vi.fn().mockResolvedValue(null),
    saveVersion: vi.fn().mockResolvedValue(undefined),
    rollback: vi.fn().mockResolvedValue(undefined),
    exportWorkflow: vi.fn().mockResolvedValue(undefined),
    importWorkflow: vi.fn().mockResolvedValue(undefined),
    listTemplates: vi.fn().mockResolvedValue([]),
    pauseExecution: vi.fn().mockResolvedValue(undefined),
    resumeExecution: vi.fn().mockResolvedValue(undefined),
    cancelExecution: vi.fn().mockResolvedValue(undefined),
  }
  cronBackupStoreMock = {
    cronJobs: [],
    backupPolicies: [],
    backupHistory: [],
    logPolicies: [],
    executionLogs: [],
    diskAlert: null,
    loading: false,
    runningBackup: null,
    runningLogCleanup: null,
    fetchCronJobs: vi.fn().mockResolvedValue(undefined),
    createCronJob: vi.fn().mockResolvedValue(undefined),
    updateCronJob: vi.fn().mockResolvedValue(undefined),
    deleteCronJob: vi.fn().mockResolvedValue(undefined),
    fetchBackupPolicies: vi.fn().mockResolvedValue(undefined),
    createBackupPolicy: vi.fn().mockResolvedValue(undefined),
    updateBackupPolicy: vi.fn().mockResolvedValue(undefined),
    deleteBackupPolicy: vi.fn().mockResolvedValue(undefined),
    runBackupNow: vi.fn().mockResolvedValue(undefined),
    fetchBackupHistory: vi.fn().mockResolvedValue(undefined),
    fetchLogPolicies: vi.fn().mockResolvedValue(undefined),
    createLogPolicy: vi.fn().mockResolvedValue(undefined),
    updateLogPolicy: vi.fn().mockResolvedValue(undefined),
    deleteLogPolicy: vi.fn().mockResolvedValue(undefined),
    fetchDiskAlert: vi.fn().mockResolvedValue(undefined),
    fetchExecutionLogs: vi.fn().mockResolvedValue(undefined),
    previewLogCleanup: vi.fn().mockResolvedValue({ files: [], total_size: 0 }),
    runLogCleanupNow: vi.fn().mockResolvedValue(undefined),
    setAccountAlias: vi.fn(),
  }
  schedulerStoreMock = {
    tasks: [],
    enabledTaskCount: 0,
    runningExecutionCount: 0,
    todaySuccessCount: 0,
    todayFailedCount: 0,
    fetchTasks: vi.fn().mockResolvedValue(undefined),
    toggleTask: vi.fn().mockResolvedValue(undefined),
    runTaskNow: vi.fn().mockResolvedValue(undefined),
    createTask: vi.fn().mockResolvedValue(undefined),
    updateTask: vi.fn().mockResolvedValue(undefined),
    deleteTask: vi.fn().mockResolvedValue(undefined),
  }
  eventTriggerStoreMock = {
    sources: [],
    eventLogs: [],
    fetchSources: vi.fn().mockResolvedValue(undefined),
    fetchEventLogs: vi.fn().mockResolvedValue(undefined),
    createSource: vi.fn().mockResolvedValue(undefined),
    updateSource: vi.fn().mockResolvedValue(undefined),
    deleteSource: vi.fn().mockResolvedValue(undefined),
    replayEvent: vi.fn().mockResolvedValue(undefined),
  }
})

import GitIntegrationPage from '@/views/GitIntegrationPage.vue'
import WorkflowEditorPage from '@/views/WorkflowEditorPage.vue'
import AutomationPage from '@/views/AutomationPage.vue'
import CronBackupPage from '@/views/CronBackupPage.vue'

describe('GitIntegrationPage', () => {
  function createWrapper() {
    return mount(GitIntegrationPage, { global: { stubs: { Md3Icon: true } } })
  }

  it('应该渲染 Git 集成页面容器', () => {
    const wrapper = createWrapper()
    expect(wrapper.find('.git-integration-page').exists()).toBe(true)
  })

  it('应该渲染页面标题', () => {
    const wrapper = createWrapper()
    expect(wrapper.text()).toContain('Git 集成')
  })

  it('应该渲染工具栏', () => {
    const wrapper = createWrapper()
    expect(wrapper.find('.git-toolbar').exists()).toBe(true)
  })

  it('应该在无 currentAlias 时显示空状态', () => {
    const wrapper = createWrapper()
    expect(wrapper.text()).toContain('请先选择 SSH 账户并输入仓库路径')
  })

  it('应该渲染 SSH 账户选择器', () => {
    const wrapper = createWrapper()
    expect(wrapper.text()).toContain('SSH 账户')
  })

  it('应该渲染仓库路径输入框', () => {
    const wrapper = createWrapper()
    expect(wrapper.text()).toContain('仓库路径')
  })

  it('应该渲染加载按钮', () => {
    const wrapper = createWrapper()
    expect(wrapper.text()).toContain('加载')
  })

  it('有 currentAlias 和 repoPath 时应该渲染 Tabs 和面板', async () => {
    gitStoreMock.currentAlias = 'test-server'
    gitStoreMock.repoPath = '/var/repo'
    const wrapper = createWrapper()
    await nextTick()
    expect(wrapper.find('.git-tabs').exists() || wrapper.find('.md3-tabs').exists()).toBe(true)
    expect(wrapper.find('.git-content').exists()).toBe(true)
  })

  it('有 currentAlias 和 repoPath 时应该渲染 GitRepoPanel', async () => {
    gitStoreMock.currentAlias = 'test-server'
    gitStoreMock.repoPath = '/var/repo'
    const wrapper = createWrapper()
    await nextTick()
    expect(wrapper.find('.git-repo-panel').exists()).toBe(true)
  })

  it('activeTab 为 branch 时应该渲染 GitBranchPanel', async () => {
    gitStoreMock.currentAlias = 'test-server'
    gitStoreMock.repoPath = '/var/repo'
    const wrapper = createWrapper()
    wrapper.vm.activeTab = 'branch'
    await nextTick()
    expect(wrapper.find('.git-branch-panel').exists()).toBe(true)
  })

  it('activeTab 为 commit 时应该渲染 GitCommitPanel', async () => {
    gitStoreMock.currentAlias = 'test-server'
    gitStoreMock.repoPath = '/var/repo'
    const wrapper = createWrapper()
    wrapper.vm.activeTab = 'commit'
    await nextTick()
    expect(wrapper.find('.git-commit-panel').exists()).toBe(true)
  })

  it('activeTab 为 webhook 时应该渲染 WebhookDeployPanel', async () => {
    gitStoreMock.currentAlias = 'test-server'
    gitStoreMock.repoPath = '/var/repo'
    const wrapper = createWrapper()
    wrapper.vm.activeTab = 'webhook'
    await nextTick()
    expect(wrapper.find('.webhook-deploy-panel').exists()).toBe(true)
  })

  it('activeTab 为 sync 时应该渲染 GitSyncPanel', async () => {
    gitStoreMock.currentAlias = 'test-server'
    gitStoreMock.repoPath = '/var/repo'
    const wrapper = createWrapper()
    wrapper.vm.activeTab = 'sync'
    await nextTick()
    expect(wrapper.find('.git-sync-panel').exists()).toBe(true)
  })

  it('tabs 计算属性应该返回5个标签', () => {
    const wrapper = createWrapper()
    expect(wrapper.vm.tabs).toHaveLength(5)
    expect(wrapper.vm.tabs[0].value).toBe('repo')
    expect(wrapper.vm.tabs[1].value).toBe('branch')
    expect(wrapper.vm.tabs[2].value).toBe('commit')
    expect(wrapper.vm.tabs[3].value).toBe('webhook')
    expect(wrapper.vm.tabs[4].value).toBe('sync')
  })

  it('tabs 每个标签应该有 icon', () => {
    const wrapper = createWrapper()
    wrapper.vm.tabs.forEach(tab => {
      expect(tab.icon).toBeTruthy()
    })
  })

  it('onAccountChange 应该调用 gitStore.setAccountAlias', () => {
    const wrapper = createWrapper()
    wrapper.vm.onAccountChange('new-server')
    expect(gitStoreMock.setAccountAlias).toHaveBeenCalledWith('new-server')
  })

  it('onAccountChange 应该将值转为字符串', () => {
    const wrapper = createWrapper()
    wrapper.vm.onAccountChange(123)
    expect(gitStoreMock.setAccountAlias).toHaveBeenCalledWith('123')
  })

  it('loadRepoInfo 无账户和路径时不应调用 store', () => {
    const wrapper = createWrapper()
    wrapper.vm.accountAlias = ''
    wrapper.vm.repoPath = ''
    wrapper.vm.loadRepoInfo()
    expect(gitStoreMock.setAccountAlias).not.toHaveBeenCalled()
  })

  it('loadRepoInfo 无账户时不应调用 store', () => {
    const wrapper = createWrapper()
    wrapper.vm.accountAlias = ''
    wrapper.vm.repoPath = '/var/repo'
    wrapper.vm.loadRepoInfo()
    expect(gitStoreMock.setAccountAlias).not.toHaveBeenCalled()
  })

  it('loadRepoInfo 无路径时不应调用 store', () => {
    const wrapper = createWrapper()
    wrapper.vm.accountAlias = 'test-server'
    wrapper.vm.repoPath = ''
    wrapper.vm.loadRepoInfo()
    expect(gitStoreMock.setAccountAlias).not.toHaveBeenCalled()
  })

  it('loadRepoInfo 有账户和路径时应该调用 store', () => {
    const wrapper = createWrapper()
    wrapper.vm.accountAlias = 'test-server'
    wrapper.vm.repoPath = '/var/repo'
    wrapper.vm.loadRepoInfo()
    expect(gitStoreMock.setAccountAlias).toHaveBeenCalledWith('test-server')
    expect(gitStoreMock.setRepoPath).toHaveBeenCalledWith('/var/repo')
    expect(gitStoreMock.fetchRepoInfo).toHaveBeenCalled()
  })

  it('onMounted 应该加载 SSH 账户并设置默认账户', async () => {
    createWrapper()
    await nextTick()
    await nextTick()
    expect(sshStoreMock.fetchAccounts).toHaveBeenCalled()
  })

  it('onMounted 有默认账户时应该设置 accountAlias 和 gitStore', async () => {
    createWrapper()
    await nextTick()
    await nextTick()
    expect(gitStoreMock.setAccountAlias).toHaveBeenCalledWith('test-server')
  })

  it('accountOptions 应该返回正确的选项', () => {
    const wrapper = createWrapper()
    const options = wrapper.vm.accountOptions
    expect(options).toHaveLength(1)
    expect(options[0].value).toBe('test-server')
    expect(options[0].label).toContain('test-server')
  })

  it('onMounted 无默认账户但有第一个账户时应该使用第一个账户', async () => {
    sshStoreMock.accounts = [{ alias: 'first-server', host: '10.0.0.1', default: false }]
    createWrapper()
    await nextTick()
    await nextTick()
    expect(gitStoreMock.setAccountAlias).toHaveBeenCalledWith('first-server')
  })

  it('onMounted 无账户时不应设置 accountAlias', async () => {
    sshStoreMock.accounts = []
    const wrapper = createWrapper()
    await nextTick()
    await nextTick()
    expect(wrapper.vm.accountAlias).toBe('')
    expect(gitStoreMock.setAccountAlias).not.toHaveBeenCalled()
  })

  it('tabs 每个标签应该有正确的 label', () => {
    const wrapper = createWrapper()
    expect(wrapper.vm.tabs[0].label).toBe('仓库管理')
    expect(wrapper.vm.tabs[1].label).toBe('分支管理')
    expect(wrapper.vm.tabs[2].label).toBe('提交记录')
    expect(wrapper.vm.tabs[3].label).toBe('Webhook 部署')
    expect(wrapper.vm.tabs[4].label).toBe('同步管理')
  })
})

describe('WorkflowEditorPage', () => {
  function createWrapper() {
    return mount(WorkflowEditorPage, { global: { stubs: { Md3Icon: true } } })
  }

  it('应该渲染工作流编辑器页面容器', () => {
    const wrapper = createWrapper()
    expect(wrapper.find('.workflow-editor-page').exists()).toBe(true)
  })

  it('应该渲染工具栏', () => {
    const wrapper = createWrapper()
    expect(wrapper.find('.editor-toolbar').exists()).toBe(true)
  })

  it('应该渲染编辑器主体', () => {
    const wrapper = createWrapper()
    expect(wrapper.find('.editor-body').exists()).toBe(true)
  })

  it('应该渲染返回按钮', () => {
    const wrapper = createWrapper()
    expect(wrapper.text()).toContain('返回')
  })

  it('应该渲染执行按钮', () => {
    const wrapper = createWrapper()
    expect(wrapper.text()).toContain('执行')
  })

  it('应该渲染导出按钮', () => {
    const wrapper = createWrapper()
    expect(wrapper.text()).toContain('导出')
  })

  it('应该渲染导入按钮', () => {
    const wrapper = createWrapper()
    expect(wrapper.text()).toContain('导入')
  })

  it('goBack 应该导航回上一页', () => {
    const wrapper = createWrapper()
    wrapper.vm.goBack()
    expect(mockPush).toHaveBeenCalled()
  })

  it('getExecutionIcon 应该返回正确的图标', () => {
    const wrapper = createWrapper()
    expect(wrapper.vm.getExecutionIcon('running')).toBe('loading')
    expect(wrapper.vm.getExecutionIcon('success')).toBe('check-circle')
    expect(wrapper.vm.getExecutionIcon('failed')).toBe('alert-circle')
    expect(wrapper.vm.getExecutionIcon('paused')).toBe('pause-circle')
    expect(wrapper.vm.getExecutionIcon('cancelled')).toBe('close-circle')
    expect(wrapper.vm.getExecutionIcon('unknown')).toBe('help-circle')
  })

  it('getExecutionStatusLabel 应该返回正确的标签', () => {
    const wrapper = createWrapper()
    expect(wrapper.vm.getExecutionStatusLabel('running')).toBe('运行中')
    expect(wrapper.vm.getExecutionStatusLabel('success')).toBe('已完成')
    expect(wrapper.vm.getExecutionStatusLabel('failed')).toBe('失败')
    expect(wrapper.vm.getExecutionStatusLabel('paused')).toBe('已暂停')
    expect(wrapper.vm.getExecutionStatusLabel('cancelled')).toBe('已取消')
    expect(wrapper.vm.getExecutionStatusLabel('pending')).toBe('等待中')
    expect(wrapper.vm.getExecutionStatusLabel('other')).toBe('other')
  })

  it('executionProgress 无执行时应该为 0', () => {
    const wrapper = createWrapper()
    expect(wrapper.vm.executionProgress).toBe(0)
  })

  it('executionProgress 有执行时应该计算正确', () => {
    const wrapper = createWrapper()
    wrapper.vm.currentExecution = { total_nodes: 10, success_nodes: 5, failed_nodes: 2 }
    expect(wrapper.vm.executionProgress).toBe(70)
  })

  it('saveWorkflow 无工作流时应该返回', async () => {
    workflowStoreMock.currentWorkflow = null
    const wrapper = createWrapper()
    await wrapper.vm.saveWorkflow()
    expect(workflowStoreMock.updateWorkflow).not.toHaveBeenCalled()
  })

  it('saveWorkflow 有工作流时应该调用 updateWorkflow', async () => {
    workflowStoreMock.currentWorkflow = { id: 'test', name: 'Test', nodes: [], edges: [] }
    const wrapper = createWrapper()
    wrapper.vm.workflowName = 'Updated'
    await wrapper.vm.saveWorkflow()
    expect(workflowStoreMock.updateWorkflow).toHaveBeenCalled()
  })

  it('saveWorkflow 失败时应该显示错误', async () => {
    const { Md3Message } = await import('@/components/md3')
    workflowStoreMock.currentWorkflow = { id: 'test', name: 'Test', nodes: [], edges: [] }
    workflowStoreMock.updateWorkflow = vi.fn().mockRejectedValue(new Error('fail'))
    const wrapper = createWrapper()
    wrapper.vm.workflowName = 'Updated'
    await wrapper.vm.saveWorkflow()
    expect(Md3Message.error).toHaveBeenCalled()
  })

  it('exportWorkflow 无工作流时应该返回', async () => {
    workflowStoreMock.currentWorkflow = null
    const wrapper = createWrapper()
    await wrapper.vm.exportWorkflow()
    expect(workflowStoreMock.exportWorkflow).not.toHaveBeenCalled()
  })

  it('executeWorkflow 无工作流时应该返回', async () => {
    workflowStoreMock.currentWorkflow = null
    const wrapper = createWrapper()
    await wrapper.vm.executeWorkflow()
    expect(workflowStoreMock.executeWorkflow).not.toHaveBeenCalled()
  })

  it('executeWorkflow 有工作流时应该调用 store', async () => {
    const { Md3Message } = await import('@/components/md3')
    workflowStoreMock.currentWorkflow = { id: 'test', name: 'Test', nodes: [], edges: [] }
    workflowStoreMock.executeWorkflow = vi.fn().mockResolvedValue({ id: 'exec-1' })
    const wrapper = createWrapper()
    await wrapper.vm.executeWorkflow()
    expect(workflowStoreMock.executeWorkflow).toHaveBeenCalled()
    expect(wrapper.vm.isExecuting).toBe(true)
  })

  it('executeWorkflow 失败时应该显示错误', async () => {
    const { Md3Message } = await import('@/components/md3')
    workflowStoreMock.currentWorkflow = { id: 'test', name: 'Test', nodes: [], edges: [] }
    workflowStoreMock.executeWorkflow = vi.fn().mockRejectedValue(new Error('fail'))
    const wrapper = createWrapper()
    await wrapper.vm.executeWorkflow()
    expect(Md3Message.error).toHaveBeenCalled()
  })

  it('pauseExecution 无执行时应该返回', async () => {
    const wrapper = createWrapper()
    wrapper.vm.currentExecution = null
    await wrapper.vm.pauseExecution()
    expect(workflowStoreMock.pauseExecution).not.toHaveBeenCalled()
  })

  it('pauseExecution 有执行时应该调用 store', async () => {
    const { Md3Message } = await import('@/components/md3')
    const wrapper = createWrapper()
    wrapper.vm.currentExecution = { id: 'exec-1' }
    await wrapper.vm.pauseExecution()
    expect(workflowStoreMock.pauseExecution).toHaveBeenCalled()
  })

  it('cancelExecution 有执行时应该调用 store', async () => {
    const { Md3Message } = await import('@/components/md3')
    const wrapper = createWrapper()
    wrapper.vm.currentExecution = { id: 'exec-1' }
    await wrapper.vm.cancelExecution()
    expect(workflowStoreMock.cancelExecution).toHaveBeenCalled()
    expect(wrapper.vm.isExecuting).toBe(false)
  })

  it('rollbackToVersion 成功时应该显示成功消息', async () => {
    const { Md3Message } = await import('@/components/md3')
    workflowStoreMock.currentWorkflow = { id: 'test', name: 'Test', version: 2 }
    const wrapper = createWrapper()
    await wrapper.vm.rollbackToVersion(1)
    expect(workflowStoreMock.rollback).toHaveBeenCalled()
    expect(Md3Message.success).toHaveBeenCalled()
  })

  it('rollbackToVersion 失败时应该显示错误', async () => {
    const { Md3Message } = await import('@/components/md3')
    workflowStoreMock.rollback = vi.fn().mockRejectedValue(new Error('fail'))
    const wrapper = createWrapper()
    await wrapper.vm.rollbackToVersion(1)
    expect(Md3Message.error).toHaveBeenCalled()
  })

  it('onNodeClick 应该设置 selectedNode', () => {
    workflowStoreMock.currentWorkflow = {
      id: 'test', name: 'Test', nodes: [{ id: 'node-1', type: 'shell', config: {} }], edges: [],
    }
    const wrapper = createWrapper()
    wrapper.vm.onNodeClick('node-1')
    expect(wrapper.vm.selectedNode).toBeTruthy()
    expect(wrapper.vm.selectedNode.id).toBe('node-1')
  })

  it('onNodeClick 不存在的节点不应该设置 selectedNode', () => {
    workflowStoreMock.currentWorkflow = { id: 'test', name: 'Test', nodes: [], edges: [] }
    const wrapper = createWrapper()
    wrapper.vm.onNodeClick('nonexistent')
    expect(wrapper.vm.selectedNode).toBeNull()
  })

  it('onCanvasClick 应该清空 selectedNode', () => {
    const wrapper = createWrapper()
    wrapper.vm.selectedNode = { id: 'node-1' }
    wrapper.vm.onCanvasClick()
    expect(wrapper.vm.selectedNode).toBeNull()
  })

  it('onNodeDragEnd 应该调用 updateWorkflow', () => {
    workflowStoreMock.currentWorkflow = {
      id: 'test', name: 'Test',
      nodes: [{ id: 'node-1', type: 'shell', position_x: 0, position_y: 0, config: {} }],
      edges: [],
    }
    const wrapper = createWrapper()
    wrapper.vm.onNodeDragEnd('node-1', 100, 200)
    expect(workflowStoreMock.updateWorkflow).toHaveBeenCalled()
  })

  it('onConnect 应该调用 updateWorkflow', () => {
    workflowStoreMock.currentWorkflow = {
      id: 'test', name: 'Test', nodes: [], edges: [],
    }
    const wrapper = createWrapper()
    wrapper.vm.onConnect('node-1', 'node-2')
    expect(workflowStoreMock.updateWorkflow).toHaveBeenCalled()
  })

  it('onNodeUpdate 应该调用 updateWorkflow', () => {
    workflowStoreMock.currentWorkflow = {
      id: 'test', name: 'Test',
      nodes: [{ id: 'node-1', type: 'shell', config: {} }],
      edges: [],
    }
    const wrapper = createWrapper()
    wrapper.vm.onNodeUpdate('node-1', { command: 'ls' })
    expect(workflowStoreMock.updateWorkflow).toHaveBeenCalled()
  })

  it('sshAccounts 应该返回 store 数据', () => {
    const wrapper = createWrapper()
    expect(wrapper.vm.sshAccounts).toHaveLength(1)
  })

  it('versionColumns 应该包含正确的列', () => {
    const wrapper = createWrapper()
    expect(wrapper.vm.versionColumns).toHaveLength(4)
  })

  it('onMounted 应该调用 store 方法', async () => {
    createWrapper()
    await nextTick()
    await nextTick()
    await nextTick()
    expect(workflowStoreMock.fetchWorkflow).toHaveBeenCalled()
    expect(workflowStoreMock.fetchVersions).toHaveBeenCalled()
  })

  it('cancelExecution 失败时应该显示错误', async () => {
    const { Md3Message } = await import('@/components/md3')
    workflowStoreMock.cancelExecution = vi.fn().mockRejectedValue(new Error('fail'))
    const wrapper = createWrapper()
    wrapper.vm.currentExecution = { id: 'exec-1' }
    await wrapper.vm.cancelExecution()
    expect(Md3Message.error).toHaveBeenCalledWith('取消执行失败')
  })

  it('startPolling 应该设置定时器并轮询执行状态', async () => {
    vi.useFakeTimers()
    workflowStoreMock.currentExecution = { id: 'exec-1', status: 'running' }
    workflowStoreMock.nodeExecutions = []
    const wrapper = createWrapper()
    wrapper.vm.startPolling('exec-1')
    await vi.advanceTimersByTimeAsync(2000)
    expect(workflowStoreMock.fetchExecution).toHaveBeenCalledWith('exec-1')
    expect(workflowStoreMock.fetchNodeExecutions).toHaveBeenCalledWith('exec-1')
    vi.useRealTimers()
  })

  it('startPolling 执行完成时应该停止轮询', async () => {
    vi.useFakeTimers()
    workflowStoreMock.currentExecution = { id: 'exec-1', status: 'success' }
    workflowStoreMock.nodeExecutions = []
    const wrapper = createWrapper()
    wrapper.vm.isExecuting = true
    wrapper.vm.startPolling('exec-1')
    await vi.advanceTimersByTimeAsync(2000)
    expect(wrapper.vm.isExecuting).toBe(false)
    vi.useRealTimers()
  })

  it('startPolling 执行失败时应该停止轮询', async () => {
    vi.useFakeTimers()
    workflowStoreMock.currentExecution = { id: 'exec-1', status: 'failed' }
    workflowStoreMock.nodeExecutions = []
    const wrapper = createWrapper()
    wrapper.vm.isExecuting = true
    wrapper.vm.startPolling('exec-1')
    await vi.advanceTimersByTimeAsync(2000)
    expect(wrapper.vm.isExecuting).toBe(false)
    vi.useRealTimers()
  })

  it('startPolling 轮询异常时应该停止轮询', async () => {
    vi.useFakeTimers()
    workflowStoreMock.fetchExecution = vi.fn().mockRejectedValue(new Error('fail'))
    const wrapper = createWrapper()
    wrapper.vm.startPolling('exec-1')
    await vi.advanceTimersByTimeAsync(2000)
    vi.useRealTimers()
  })

  it('stopPolling 应该清除定时器', () => {
    vi.useFakeTimers()
    const wrapper = createWrapper()
    wrapper.vm.startPolling('exec-1')
    wrapper.vm.stopPolling()
    expect(workflowStoreMock.fetchExecution).not.toHaveBeenCalled()
    vi.useRealTimers()
  })

  it('onNodeDragStart 应该被调用不报错', () => {
    const wrapper = createWrapper()
    expect(() => wrapper.vm.onNodeDragStart('shell')).not.toThrow()
  })

  it('onNodeDrag 应该被调用不报错', () => {
    const wrapper = createWrapper()
    expect(() => wrapper.vm.onNodeDrag('node-1', 100, 200)).not.toThrow()
  })

  it('onEdgeClick 应该被调用不报错', () => {
    const wrapper = createWrapper()
    expect(() => wrapper.vm.onEdgeClick('edge-1')).not.toThrow()
  })

  it('onNodeUpdate 应该更新 selectedNode 的 config', () => {
    workflowStoreMock.currentWorkflow = {
      id: 'test', name: 'Test',
      nodes: [{ id: 'node-1', type: 'shell', config: { command: 'ls' } }],
      edges: [],
    }
    const wrapper = createWrapper()
    wrapper.vm.selectedNode = { id: 'node-1', type: 'shell', config: { command: 'ls' } }
    wrapper.vm.onNodeUpdate('node-1', { command: 'pwd' })
    expect(wrapper.vm.selectedNode.config).toEqual({ command: 'pwd' })
  })

  it('onNodeUpdate 非 selectedNode 不应更新 selectedNode', () => {
    workflowStoreMock.currentWorkflow = {
      id: 'test', name: 'Test',
      nodes: [{ id: 'node-1', type: 'shell', config: {} }, { id: 'node-2', type: 'shell', config: {} }],
      edges: [],
    }
    const wrapper = createWrapper()
    wrapper.vm.selectedNode = { id: 'node-1', type: 'shell', config: {} }
    wrapper.vm.onNodeUpdate('node-2', { command: 'pwd' })
    expect(wrapper.vm.selectedNode.id).toBe('node-1')
  })

  it('onUnmounted 应该停止轮询', () => {
    vi.useFakeTimers()
    const wrapper = createWrapper()
    wrapper.vm.startPolling('exec-1')
    wrapper.unmount()
    vi.useRealTimers()
  })

  it('saveWorkflow 失败时应该显示错误', async () => {
    const { Md3Message } = await import('@/components/md3')
    workflowStoreMock.updateWorkflow = vi.fn().mockRejectedValue(new Error('fail'))
    workflowStoreMock.currentWorkflow = { id: 'test', name: 'Test', nodes: [], edges: [] }
    const wrapper = createWrapper()
    await wrapper.vm.saveWorkflow()
    expect(Md3Message.error).toHaveBeenCalledWith('保存工作流失败')
  })

  it('saveWorkflow 无 workflow 时不应调用 store', async () => {
    workflowStoreMock.currentWorkflow = null
    const wrapper = createWrapper()
    await wrapper.vm.saveWorkflow()
    expect(workflowStoreMock.updateWorkflow).not.toHaveBeenCalled()
  })

  it('exportWorkflow 成功时应该下载文件', async () => {
    workflowStoreMock.exportWorkflow = vi.fn().mockResolvedValue({ name: 'test' })
    workflowStoreMock.currentWorkflow = { id: 'test', name: 'Test', nodes: [], edges: [] }
    const mockCreateObjectURL = vi.fn().mockReturnValue('blob:test')
    const mockRevokeObjectURL = vi.fn()
    globalThis.URL.createObjectURL = mockCreateObjectURL
    globalThis.URL.revokeObjectURL = mockRevokeObjectURL
    const wrapper = createWrapper()
    await wrapper.vm.exportWorkflow()
    expect(workflowStoreMock.exportWorkflow).toHaveBeenCalled()
    expect(mockCreateObjectURL).toHaveBeenCalled()
    expect(mockRevokeObjectURL).toHaveBeenCalled()
  })

  it('exportWorkflow 失败时应该显示错误', async () => {
    const { Md3Message } = await import('@/components/md3')
    workflowStoreMock.exportWorkflow = vi.fn().mockRejectedValue(new Error('fail'))
    workflowStoreMock.currentWorkflow = { id: 'test', name: 'Test', nodes: [], edges: [] }
    const wrapper = createWrapper()
    await wrapper.vm.exportWorkflow()
    expect(Md3Message.error).toHaveBeenCalledWith('导出失败')
  })

  it('exportWorkflow 无 workflow 时不应调用 store', async () => {
    workflowStoreMock.currentWorkflow = null
    const wrapper = createWrapper()
    await wrapper.vm.exportWorkflow()
    expect(workflowStoreMock.exportWorkflow).not.toHaveBeenCalled()
  })

  it('executeWorkflow 成功时应该开始轮询', async () => {
    const { Md3Message } = await import('@/components/md3')
    workflowStoreMock.executeWorkflow = vi.fn().mockResolvedValue({ id: 'exec-1', status: 'running' })
    workflowStoreMock.currentWorkflow = { id: 'test', name: 'Test', nodes: [], edges: [] }
    const wrapper = createWrapper()
    await wrapper.vm.executeWorkflow()
    expect(wrapper.vm.isExecuting).toBe(true)
    expect(wrapper.vm.currentExecution).toBeTruthy()
    expect(Md3Message.success).toHaveBeenCalledWith('工作流已开始执行')
  })

  it('executeWorkflow 失败时应该显示错误', async () => {
    const { Md3Message } = await import('@/components/md3')
    workflowStoreMock.executeWorkflow = vi.fn().mockRejectedValue(new Error('fail'))
    workflowStoreMock.currentWorkflow = { id: 'test', name: 'Test', nodes: [], edges: [] }
    const wrapper = createWrapper()
    await wrapper.vm.executeWorkflow()
    expect(Md3Message.error).toHaveBeenCalledWith('执行工作流失败')
  })

  it('executeWorkflow 无 workflow 时不应调用 store', async () => {
    workflowStoreMock.currentWorkflow = null
    const wrapper = createWrapper()
    await wrapper.vm.executeWorkflow()
    expect(workflowStoreMock.executeWorkflow).not.toHaveBeenCalled()
  })

  it('pauseExecution 成功时应该显示成功消息', async () => {
    const { Md3Message } = await import('@/components/md3')
    workflowStoreMock.pauseExecution = vi.fn().mockResolvedValue(undefined)
    const wrapper = createWrapper()
    wrapper.vm.currentExecution = { id: 'exec-1' }
    await wrapper.vm.pauseExecution()
    expect(Md3Message.success).toHaveBeenCalledWith('执行已暂停')
  })

  it('pauseExecution 失败时应该显示错误', async () => {
    const { Md3Message } = await import('@/components/md3')
    workflowStoreMock.pauseExecution = vi.fn().mockRejectedValue(new Error('fail'))
    const wrapper = createWrapper()
    wrapper.vm.currentExecution = { id: 'exec-1' }
    await wrapper.vm.pauseExecution()
    expect(Md3Message.error).toHaveBeenCalledWith('暂停执行失败')
  })

  it('pauseExecution 无 currentExecution 时不应调用 store', async () => {
    const wrapper = createWrapper()
    wrapper.vm.currentExecution = null
    await wrapper.vm.pauseExecution()
    expect(workflowStoreMock.pauseExecution).not.toHaveBeenCalled()
  })

  it('cancelExecution 成功时应该停止轮询', async () => {
    workflowStoreMock.cancelExecution = vi.fn().mockResolvedValue(undefined)
    const wrapper = createWrapper()
    wrapper.vm.currentExecution = { id: 'exec-1' }
    wrapper.vm.isExecuting = true
    await wrapper.vm.cancelExecution()
    expect(wrapper.vm.isExecuting).toBe(false)
  })

  it('cancelExecution 无 currentExecution 时不应调用 store', async () => {
    const wrapper = createWrapper()
    wrapper.vm.currentExecution = null
    await wrapper.vm.cancelExecution()
    expect(workflowStoreMock.cancelExecution).not.toHaveBeenCalled()
  })

  it('rollbackToVersion 成功时应该刷新工作流', async () => {
    const { Md3Message } = await import('@/components/md3')
    workflowStoreMock.rollback = vi.fn().mockResolvedValue(undefined)
    workflowStoreMock.currentWorkflow = { id: 'test', name: 'Test', nodes: [], edges: [] }
    const wrapper = createWrapper()
    await wrapper.vm.rollbackToVersion(2)
    expect(workflowStoreMock.rollback).toHaveBeenCalledWith('test-workflow-id', 2)
    expect(workflowStoreMock.fetchWorkflow).toHaveBeenCalled()
    expect(wrapper.vm.showVersions).toBe(false)
    expect(Md3Message.success).toHaveBeenCalled()
  })

  it('executionProgress 应该计算正确的进度', () => {
    const wrapper = createWrapper()
    wrapper.vm.currentExecution = { total_nodes: 10, success_nodes: 3, failed_nodes: 2 }
    expect(wrapper.vm.executionProgress).toBe(50)
  })

  it('executionProgress 无执行时应该返回 0', () => {
    const wrapper = createWrapper()
    expect(wrapper.vm.executionProgress).toBe(0)
  })

  it('executionProgress total_nodes 为 0 时应该返回 0', () => {
    const wrapper = createWrapper()
    wrapper.vm.currentExecution = { total_nodes: 0, success_nodes: 0, failed_nodes: 0 }
    expect(wrapper.vm.executionProgress).toBe(0)
  })

  it('getExecutionIcon 应该返回正确的图标名', () => {
    const wrapper = createWrapper()
    expect(wrapper.vm.getExecutionIcon('running')).toBe('loading')
    expect(wrapper.vm.getExecutionIcon('success')).toBe('check-circle')
    expect(wrapper.vm.getExecutionIcon('failed')).toBe('alert-circle')
    expect(wrapper.vm.getExecutionIcon('paused')).toBe('pause-circle')
    expect(wrapper.vm.getExecutionIcon('cancelled')).toBe('close-circle')
    expect(wrapper.vm.getExecutionIcon('unknown')).toBe('help-circle')
  })

  it('getExecutionStatusLabel 应该返回正确的状态标签', () => {
    const wrapper = createWrapper()
    expect(wrapper.vm.getExecutionStatusLabel('running')).toBe('运行中')
    expect(wrapper.vm.getExecutionStatusLabel('success')).toBe('已完成')
    expect(wrapper.vm.getExecutionStatusLabel('failed')).toBe('失败')
    expect(wrapper.vm.getExecutionStatusLabel('paused')).toBe('已暂停')
    expect(wrapper.vm.getExecutionStatusLabel('cancelled')).toBe('已取消')
    expect(wrapper.vm.getExecutionStatusLabel('pending')).toBe('等待中')
    expect(wrapper.vm.getExecutionStatusLabel('unknown')).toBe('unknown')
  })
})

describe('AutomationPage', () => {
  function createWrapper() {
    return mount(AutomationPage, { global: { stubs: { Md3Icon: true } } })
  }

  it('应该渲染自动化页面容器', () => {
    const wrapper = createWrapper()
    expect(wrapper.find('.automation-page').exists()).toBe(true)
  })

  it('应该渲染页面标题', () => {
    const wrapper = createWrapper()
    expect(wrapper.text()).toContain('任务调度与自动化')
  })

  it('应该渲染指标卡片行', () => {
    const wrapper = createWrapper()
    expect(wrapper.find('.metrics-row').exists()).toBe(true)
  })

  it('应该渲染 Tab 切换', () => {
    const wrapper = createWrapper()
    expect(wrapper.find('.page-tabs').exists() || wrapper.find('.md3-tabs').exists()).toBe(true)
  })

  it('应该渲染新建工作流按钮', () => {
    const wrapper = createWrapper()
    expect(wrapper.text()).toContain('新建工作流')
  })

  it('getSourceTypeTag 应该返回正确的标签类型', () => {
    const wrapper = createWrapper()
    expect(wrapper.vm.getSourceTypeTag('webhook')).toBe('primary')
    expect(wrapper.vm.getSourceTypeTag('file_watch')).toBe('success')
    expect(wrapper.vm.getSourceTypeTag('system_metric')).toBe('warning')
    expect(wrapper.vm.getSourceTypeTag('polling')).toBe('info')
    expect(wrapper.vm.getSourceTypeTag('unknown')).toBe('info')
  })

  it('getSourceTypeLabel 应该返回正确的标签', () => {
    const wrapper = createWrapper()
    expect(wrapper.vm.getSourceTypeLabel('webhook')).toBe('Webhook')
    expect(wrapper.vm.getSourceTypeLabel('file_watch')).toBe('文件监控')
    expect(wrapper.vm.getSourceTypeLabel('system_metric')).toBe('系统指标')
    expect(wrapper.vm.getSourceTypeLabel('polling')).toBe('定时轮询')
    expect(wrapper.vm.getSourceTypeLabel('other')).toBe('other')
  })

  it('getEventStatusTag 应该返回正确的标签类型', () => {
    const wrapper = createWrapper()
    expect(wrapper.vm.getEventStatusTag('processed')).toBe('success')
    expect(wrapper.vm.getEventStatusTag('failed')).toBe('danger')
    expect(wrapper.vm.getEventStatusTag('filtered')).toBe('warning')
    expect(wrapper.vm.getEventStatusTag('pending')).toBe('info')
    expect(wrapper.vm.getEventStatusTag('other')).toBe('info')
  })

  it('filteredWorkflows 无搜索时返回全部工作流', () => {
    workflowStoreMock.workflows = [{ name: 'wf1' }, { name: 'wf2' }]
    const wrapper = createWrapper()
    expect(wrapper.vm.filteredWorkflows).toHaveLength(2)
  })

  it('filteredWorkflows 有搜索时过滤工作流', () => {
    workflowStoreMock.workflows = [{ name: 'deploy-prod' }, { name: 'test-flow' }]
    const wrapper = createWrapper()
    wrapper.vm.workflowSearch = 'prod'
    expect(wrapper.vm.filteredWorkflows).toHaveLength(1)
    expect(wrapper.vm.filteredWorkflows[0].name).toBe('deploy-prod')
  })

  it('createNewWorkflow 成功时应该导航到编辑器', async () => {
    const { Md3Message } = await import('@/components/md3')
    const wrapper = createWrapper()
    await wrapper.vm.createNewWorkflow()
    expect(workflowStoreMock.createWorkflow).toHaveBeenCalled()
    expect(Md3Message.success).toHaveBeenCalled()
    expect(mockPush).toHaveBeenCalled()
  })

  it('createNewWorkflow 失败时应该显示错误', async () => {
    const { Md3Message } = await import('@/components/md3')
    workflowStoreMock.createWorkflow = vi.fn().mockRejectedValue(new Error('fail'))
    const wrapper = createWrapper()
    await wrapper.vm.createNewWorkflow()
    expect(Md3Message.error).toHaveBeenCalled()
  })

  it('createFromTemplate 成功时应该导航到编辑器', async () => {
    const { Md3Message } = await import('@/components/md3')
    const wrapper = createWrapper()
    await wrapper.vm.createFromTemplate('tpl-1')
    expect(workflowStoreMock.createFromTemplate).toHaveBeenCalledWith('tpl-1', '从模板创建')
    expect(Md3Message.success).toHaveBeenCalled()
    expect(mockPush).toHaveBeenCalled()
  })

  it('createFromTemplate 失败时应该显示错误', async () => {
    const { Md3Message } = await import('@/components/md3')
    workflowStoreMock.createFromTemplate = vi.fn().mockRejectedValue(new Error('fail'))
    const wrapper = createWrapper()
    await wrapper.vm.createFromTemplate('tpl-1')
    expect(Md3Message.error).toHaveBeenCalled()
  })

  it('editWorkflow 应该导航到编辑器', () => {
    const wrapper = createWrapper()
    wrapper.vm.editWorkflow({ id: 'wf-1' })
    expect(mockPush).toHaveBeenCalledWith({ name: 'workflow-editor', params: { id: 'wf-1' } })
  })

  it('executeWorkflow 成功时应该显示成功消息', async () => {
    const { Md3Message } = await import('@/components/md3')
    const wrapper = createWrapper()
    await wrapper.vm.executeWorkflow({ id: 'wf-1', name: 'TestWF' })
    expect(workflowStoreMock.executeWorkflow).toHaveBeenCalledWith('wf-1', 'manual')
    expect(Md3Message.success).toHaveBeenCalled()
  })

  it('executeWorkflow 失败时应该显示错误', async () => {
    const { Md3Message } = await import('@/components/md3')
    workflowStoreMock.executeWorkflow = vi.fn().mockRejectedValue(new Error('fail'))
    const wrapper = createWrapper()
    await wrapper.vm.executeWorkflow({ id: 'wf-1', name: 'TestWF' })
    expect(Md3Message.error).toHaveBeenCalled()
  })

  it('deleteWorkflow 确认时应该调用 store', async () => {
    const { Md3Message } = await import('@/components/md3')
    const wrapper = createWrapper()
    await wrapper.vm.deleteWorkflow({ id: 'wf-1', name: 'TestWF' })
    expect(workflowStoreMock.deleteWorkflow).toHaveBeenCalledWith('wf-1')
    expect(Md3Message.success).toHaveBeenCalled()
  })

  it('deleteWorkflow 取消时不应调用 store', async () => {
    const { Md3Confirm } = await import('@/components/md3/Md3Confirm')
    Md3Confirm.show.mockResolvedValueOnce(false)
    const wrapper = createWrapper()
    await wrapper.vm.deleteWorkflow({ id: 'wf-1', name: 'TestWF' })
    expect(workflowStoreMock.deleteWorkflow).not.toHaveBeenCalled()
  })

  it('toggleTask 启用任务', async () => {
    const { Md3Message } = await import('@/components/md3')
    const wrapper = createWrapper()
    await wrapper.vm.toggleTask({ id: 'task-1' }, true)
    expect(schedulerStoreMock.toggleTask).toHaveBeenCalledWith('task-1', true)
    expect(Md3Message.success).toHaveBeenCalled()
  })

  it('toggleTask 失败时应该显示错误', async () => {
    const { Md3Message } = await import('@/components/md3')
    schedulerStoreMock.toggleTask = vi.fn().mockRejectedValue(new Error('fail'))
    const wrapper = createWrapper()
    await wrapper.vm.toggleTask({ id: 'task-1' }, true)
    expect(Md3Message.error).toHaveBeenCalled()
  })

  it('runTaskNow 成功时应该显示成功消息', async () => {
    const { Md3Message } = await import('@/components/md3')
    const wrapper = createWrapper()
    await wrapper.vm.runTaskNow({ id: 'task-1', name: 'TestTask' })
    expect(schedulerStoreMock.runTaskNow).toHaveBeenCalledWith('task-1')
    expect(Md3Message.success).toHaveBeenCalled()
  })

  it('runTaskNow 失败时应该显示错误', async () => {
    const { Md3Message } = await import('@/components/md3')
    schedulerStoreMock.runTaskNow = vi.fn().mockRejectedValue(new Error('fail'))
    const wrapper = createWrapper()
    await wrapper.vm.runTaskNow({ id: 'task-1', name: 'TestTask' })
    expect(Md3Message.error).toHaveBeenCalled()
  })

  it('editTask 应该设置编辑状态并打开对话框', () => {
    const wrapper = createWrapper()
    const task = { id: 't1', name: 'Task1', cron_expression: '* * * * *', priority: 'high', command: 'ls', timeout_seconds: 300, max_concurrent: 1, retry_policy: { max_retries: 0, strategy: 'fixed', interval_seconds: 60 } }
    wrapper.vm.editTask(task)
    expect(wrapper.vm.editingTask).toBeTruthy()
    expect(wrapper.vm.showTaskDialog).toBe(true)
  })

  it('deleteTask 确认时应该调用 store', async () => {
    const { Md3Message } = await import('@/components/md3')
    const wrapper = createWrapper()
    await wrapper.vm.deleteTask({ id: 't1', name: 'Task1' })
    expect(schedulerStoreMock.deleteTask).toHaveBeenCalledWith('t1')
    expect(Md3Message.success).toHaveBeenCalled()
  })

  it('deleteTask 取消时不应调用 store', async () => {
    const { Md3Confirm } = await import('@/components/md3/Md3Confirm')
    Md3Confirm.show.mockResolvedValueOnce(false)
    const wrapper = createWrapper()
    await wrapper.vm.deleteTask({ id: 't1', name: 'Task1' })
    expect(schedulerStoreMock.deleteTask).not.toHaveBeenCalled()
  })

  it('saveTask 新建时应该调用 createTask', async () => {
    const { Md3Message } = await import('@/components/md3')
    const wrapper = createWrapper()
    wrapper.vm.editingTask = null
    await wrapper.vm.saveTask()
    expect(schedulerStoreMock.createTask).toHaveBeenCalled()
    expect(wrapper.vm.showTaskDialog).toBe(false)
  })

  it('saveTask 编辑时应该调用 updateTask', async () => {
    const { Md3Message } = await import('@/components/md3')
    const wrapper = createWrapper()
    wrapper.vm.editingTask = { id: 't1' }
    await wrapper.vm.saveTask()
    expect(schedulerStoreMock.updateTask).toHaveBeenCalled()
    expect(wrapper.vm.showTaskDialog).toBe(false)
  })

  it('saveTask 失败时应该显示错误', async () => {
    const { Md3Message } = await import('@/components/md3')
    schedulerStoreMock.createTask = vi.fn().mockRejectedValue(new Error('fail'))
    const wrapper = createWrapper()
    wrapper.vm.editingTask = null
    await wrapper.vm.saveTask()
    expect(Md3Message.error).toHaveBeenCalled()
  })

  it('toggleSource 启用事件源', async () => {
    const { Md3Message } = await import('@/components/md3')
    const wrapper = createWrapper()
    await wrapper.vm.toggleSource({ id: 'src-1' }, true)
    expect(eventTriggerStoreMock.updateSource).toHaveBeenCalledWith('src-1', { status: 'enabled' })
    expect(Md3Message.success).toHaveBeenCalled()
  })

  it('toggleSource 失败时应该显示错误', async () => {
    const { Md3Message } = await import('@/components/md3')
    eventTriggerStoreMock.updateSource = vi.fn().mockRejectedValue(new Error('fail'))
    const wrapper = createWrapper()
    await wrapper.vm.toggleSource({ id: 'src-1' }, true)
    expect(Md3Message.error).toHaveBeenCalled()
  })

  it('editSource 应该设置编辑状态并打开对话框', () => {
    const wrapper = createWrapper()
    const source = { id: 's1', name: 'Src1', source_type: 'webhook', description: 'desc', config: {} }
    wrapper.vm.editSource(source)
    expect(wrapper.vm.editingSource).toBeTruthy()
    expect(wrapper.vm.showSourceDialog).toBe(true)
  })

  it('showRoutes 应该显示信息消息', async () => {
    const { Md3Message } = await import('@/components/md3')
    const wrapper = createWrapper()
    wrapper.vm.showRoutes({ name: 'Src1' })
    expect(Md3Message.info).toHaveBeenCalled()
  })

  it('deleteSource 确认时应该调用 store', async () => {
    const { Md3Message } = await import('@/components/md3')
    const wrapper = createWrapper()
    await wrapper.vm.deleteSource({ id: 's1', name: 'Src1' })
    expect(eventTriggerStoreMock.deleteSource).toHaveBeenCalledWith('s1')
    expect(Md3Message.success).toHaveBeenCalled()
  })

  it('deleteSource 取消时不应调用 store', async () => {
    const { Md3Confirm } = await import('@/components/md3/Md3Confirm')
    Md3Confirm.show.mockResolvedValueOnce(false)
    const wrapper = createWrapper()
    await wrapper.vm.deleteSource({ id: 's1', name: 'Src1' })
    expect(eventTriggerStoreMock.deleteSource).not.toHaveBeenCalled()
  })

  it('saveSource 新建时应该调用 createSource', async () => {
    const { Md3Message } = await import('@/components/md3')
    const wrapper = createWrapper()
    wrapper.vm.editingSource = null
    await wrapper.vm.saveSource()
    expect(eventTriggerStoreMock.createSource).toHaveBeenCalled()
    expect(wrapper.vm.showSourceDialog).toBe(false)
  })

  it('saveSource 编辑时应该调用 updateSource', async () => {
    const { Md3Message } = await import('@/components/md3')
    const wrapper = createWrapper()
    wrapper.vm.editingSource = { id: 's1' }
    await wrapper.vm.saveSource()
    expect(eventTriggerStoreMock.updateSource).toHaveBeenCalled()
    expect(wrapper.vm.showSourceDialog).toBe(false)
  })

  it('saveSource 失败时应该显示错误', async () => {
    const { Md3Message } = await import('@/components/md3')
    eventTriggerStoreMock.createSource = vi.fn().mockRejectedValue(new Error('fail'))
    const wrapper = createWrapper()
    wrapper.vm.editingSource = null
    await wrapper.vm.saveSource()
    expect(Md3Message.error).toHaveBeenCalled()
  })

  it('replayEvent 成功时应该显示成功消息', async () => {
    const { Md3Message } = await import('@/components/md3')
    const wrapper = createWrapper()
    await wrapper.vm.replayEvent({ id: 'evt-1' })
    expect(eventTriggerStoreMock.replayEvent).toHaveBeenCalledWith('evt-1')
    expect(Md3Message.success).toHaveBeenCalled()
  })

  it('replayEvent 失败时应该显示错误', async () => {
    const { Md3Message } = await import('@/components/md3')
    eventTriggerStoreMock.replayEvent = vi.fn().mockRejectedValue(new Error('fail'))
    const wrapper = createWrapper()
    await wrapper.vm.replayEvent({ id: 'evt-1' })
    expect(Md3Message.error).toHaveBeenCalled()
  })

  it('fetchEventLogs 应该调用 store', () => {
    const wrapper = createWrapper()
    wrapper.vm.fetchEventLogs()
    expect(eventTriggerStoreMock.fetchEventLogs).toHaveBeenCalled()
  })

  it('onMounted 应该调用所有 store 的 fetch 方法', () => {
    createWrapper()
    expect(workflowStoreMock.fetchWorkflows).toHaveBeenCalled()
    expect(workflowStoreMock.fetchTemplates).toHaveBeenCalled()
    expect(schedulerStoreMock.fetchTasks).toHaveBeenCalled()
    expect(eventTriggerStoreMock.fetchSources).toHaveBeenCalled()
    expect(eventTriggerStoreMock.fetchEventLogs).toHaveBeenCalled()
  })

  it('copyWebhookUrl 成功时应该复制到剪贴板', async () => {
    const { Md3Message } = await import('@/components/md3')
    const mockWriteText = vi.fn().mockResolvedValue(undefined)
    Object.defineProperty(navigator, 'clipboard', { value: { writeText: mockWriteText }, writable: true, configurable: true })
    const wrapper = createWrapper()
    wrapper.vm.copyWebhookUrl('https://example.com/webhook')
    await nextTick()
    await nextTick()
    expect(mockWriteText).toHaveBeenCalledWith('https://example.com/webhook')
    expect(Md3Message.success).toHaveBeenCalledWith('Webhook URL 已复制')
  })

  it('copyWebhookUrl 失败时应该显示错误', async () => {
    const { Md3Message } = await import('@/components/md3')
    const mockWriteText = vi.fn().mockRejectedValue(new Error('fail'))
    Object.defineProperty(navigator, 'clipboard', { value: { writeText: mockWriteText }, writable: true, configurable: true })
    const wrapper = createWrapper()
    wrapper.vm.copyWebhookUrl('https://example.com/webhook')
    await nextTick()
    await nextTick()
    expect(Md3Message.error).toHaveBeenCalledWith('复制失败')
  })

  it('fetchEventLogs 有过滤时应该传递过滤参数', () => {
    const wrapper = createWrapper()
    wrapper.vm.logFilter = 'processed'
    wrapper.vm.fetchEventLogs()
    expect(eventTriggerStoreMock.fetchEventLogs).toHaveBeenCalledWith(undefined, undefined, 'processed')
  })

  it('fetchEventLogs 无过滤时不应传递过滤参数', () => {
    const wrapper = createWrapper()
    wrapper.vm.logFilter = ''
    wrapper.vm.fetchEventLogs()
    expect(eventTriggerStoreMock.fetchEventLogs).toHaveBeenCalledWith(undefined, undefined, undefined)
  })

  it('metrics 应该返回6个指标', () => {
    const wrapper = createWrapper()
    expect(wrapper.vm.metrics).toHaveLength(6)
    expect(wrapper.vm.metrics[0].label).toBe('活跃工作流')
  })

  it('tabItems 应该返回3个标签', () => {
    const wrapper = createWrapper()
    expect(wrapper.vm.tabItems).toHaveLength(3)
    expect(wrapper.vm.tabItems[0].value).toBe('workflow')
  })

  it('workflowColumns 应该包含6列', () => {
    const wrapper = createWrapper()
    expect(wrapper.vm.workflowColumns).toHaveLength(6)
  })

  it('taskColumns 应该包含7列', () => {
    const wrapper = createWrapper()
    expect(wrapper.vm.taskColumns).toHaveLength(7)
  })

  it('sourceColumns 应该包含6列', () => {
    const wrapper = createWrapper()
    expect(wrapper.vm.sourceColumns).toHaveLength(6)
  })

  it('logColumns 应该包含5列', () => {
    const wrapper = createWrapper()
    expect(wrapper.vm.logColumns).toHaveLength(5)
  })

  it('priorityOptions 应该包含3个选项', () => {
    const wrapper = createWrapper()
    expect(wrapper.vm.priorityOptions).toHaveLength(3)
  })

  it('retryStrategyOptions 应该包含2个选项', () => {
    const wrapper = createWrapper()
    expect(wrapper.vm.retryStrategyOptions).toHaveLength(2)
  })

  it('sourceTypeOptions 应该包含4个选项', () => {
    const wrapper = createWrapper()
    expect(wrapper.vm.sourceTypeOptions).toHaveLength(4)
  })

  it('logFilterOptions 应该包含4个选项', () => {
    const wrapper = createWrapper()
    expect(wrapper.vm.logFilterOptions).toHaveLength(4)
  })

  it('defaultTaskForm 应该返回默认表单值', () => {
    const wrapper = createWrapper()
    const form = wrapper.vm.defaultTaskForm()
    expect(form.name).toBe('')
    expect(form.priority).toBe('medium')
    expect(form.timeout_seconds).toBe(300)
    expect(form.max_concurrent).toBe(1)
    expect(form.retry_policy.max_retries).toBe(0)
    expect(form.retry_policy.strategy).toBe('fixed')
  })

  it('defaultSourceForm 应该返回默认表单值', () => {
    const wrapper = createWrapper()
    const form = wrapper.vm.defaultSourceForm()
    expect(form.name).toBe('')
    expect(form.source_type).toBe('webhook')
    expect(form.description).toBe('')
  })

  it('taskForm 初始值应该是默认值', () => {
    const wrapper = createWrapper()
    expect(wrapper.vm.taskForm.name).toBe('')
    expect(wrapper.vm.taskForm.priority).toBe('medium')
  })

  it('sourceForm 初始值应该是默认值', () => {
    const wrapper = createWrapper()
    expect(wrapper.vm.sourceForm.name).toBe('')
    expect(wrapper.vm.sourceForm.source_type).toBe('webhook')
  })

  it('showTemplateGallery 默认为 false', () => {
    const wrapper = createWrapper()
    expect(wrapper.vm.showTemplateGallery).toBe(false)
  })

  it('activeTab 默认为 workflow', () => {
    const wrapper = createWrapper()
    expect(wrapper.vm.activeTab).toBe('workflow')
  })
})

describe('CronBackupPage', () => {
  function createWrapper() {
    return mount(CronBackupPage, { global: { stubs: { Md3Icon: true } } })
  }

  it('应该渲染计划任务与备份页面容器', () => {
    const wrapper = createWrapper()
    expect(wrapper.find('.cron-backup-page').exists()).toBe(true)
  })

  it('应该渲染页面标题', () => {
    const wrapper = createWrapper()
    expect(wrapper.text()).toContain('计划任务与备份')
  })

  it('应该渲染 SSH 服务器选择器', () => {
    const wrapper = createWrapper()
    expect(wrapper.text()).toContain('选择服务器')
  })

  it('应该在未选择服务器时不显示 Tab', () => {
    const wrapper = createWrapper()
    expect(wrapper.vm.selectedAlias).toBe('')
  })

  it('选择服务器后应该显示 Tab', async () => {
    const wrapper = createWrapper()
    wrapper.vm.selectedAlias = 'test-server'
    await nextTick()
    expect(wrapper.find('.page-tabs').exists() || wrapper.find('.md3-tabs').exists()).toBe(true)
  })

  it('backupTypeLabel 应该返回正确的标签', () => {
    const wrapper = createWrapper()
    expect(wrapper.vm.backupTypeLabel('website')).toBe('网站')
    expect(wrapper.vm.backupTypeLabel('mysql')).toBe('MySQL')
    expect(wrapper.vm.backupTypeLabel('postgresql')).toBe('PostgreSQL')
    expect(wrapper.vm.backupTypeLabel('custom')).toBe('自定义')
    expect(wrapper.vm.backupTypeLabel('other')).toBe('other')
  })

  it('backupTypeColor 应该返回正确的颜色', () => {
    const wrapper = createWrapper()
    expect(wrapper.vm.backupTypeColor('website')).toBe('primary')
    expect(wrapper.vm.backupTypeColor('mysql')).toBe('success')
    expect(wrapper.vm.backupTypeColor('postgresql')).toBe('info')
    expect(wrapper.vm.backupTypeColor('custom')).toBe('warning')
    expect(wrapper.vm.backupTypeColor('other')).toBe('info')
  })

  it('cleanupActionLabel 应该返回正确的标签', () => {
    const wrapper = createWrapper()
    expect(wrapper.vm.cleanupActionLabel('delete')).toBe('删除')
    expect(wrapper.vm.cleanupActionLabel('compress')).toBe('压缩')
    expect(wrapper.vm.cleanupActionLabel('move')).toBe('移动')
    expect(wrapper.vm.cleanupActionLabel('other')).toBe('other')
  })

  it('cleanupActionColor 应该返回正确的颜色', () => {
    const wrapper = createWrapper()
    expect(wrapper.vm.cleanupActionColor('delete')).toBe('danger')
    expect(wrapper.vm.cleanupActionColor('compress')).toBe('warning')
    expect(wrapper.vm.cleanupActionColor('move')).toBe('primary')
    expect(wrapper.vm.cleanupActionColor('other')).toBe('info')
  })

  it('formatFileSize 应该正确格式化文件大小', () => {
    const wrapper = createWrapper()
    expect(wrapper.vm.formatFileSize(500)).toBe('500 B')
    expect(wrapper.vm.formatFileSize(1024)).toBe('1.0 KB')
    expect(wrapper.vm.formatFileSize(1048576)).toBe('1.0 MB')
    expect(wrapper.vm.formatFileSize(1073741824)).toBe('1.00 GB')
    expect(wrapper.vm.formatFileSize(0)).toBe('0 B')
  })

  it('onCronPresetChange 应该设置 cron 表达式', () => {
    const wrapper = createWrapper()
    wrapper.vm.onCronPresetChange('0 * * * *')
    expect(wrapper.vm.cronForm.cron_expression).toBe('0 * * * *')
  })

  it('onCronPresetChange 空值不应该覆盖', () => {
    const wrapper = createWrapper()
    wrapper.vm.cronForm.cron_expression = '0 2 * * *'
    wrapper.vm.onCronPresetChange('')
    expect(wrapper.vm.cronForm.cron_expression).toBe('0 2 * * *')
  })

  it('onBackupPresetChange 应该设置 cron 表达式', () => {
    const wrapper = createWrapper()
    wrapper.vm.onBackupPresetChange('0 3 * * 0')
    expect(wrapper.vm.backupForm.cron_expression).toBe('0 3 * * 0')
  })

  it('onLogPresetChange 应该设置 cron 表达式', () => {
    const wrapper = createWrapper()
    wrapper.vm.onLogPresetChange('0 4 1 * *')
    expect(wrapper.vm.logForm.cron_expression).toBe('0 4 1 * *')
  })

  it('openCronDialog 新建时应该重置表单', () => {
    const wrapper = createWrapper()
    wrapper.vm.openCronDialog()
    expect(wrapper.vm.editingCronId).toBe('')
    expect(wrapper.vm.cronDialogVisible).toBe(true)
  })

  it('openCronDialog 编辑时应该填充表单', () => {
    const wrapper = createWrapper()
    const job = { id: 'j1', name: 'Test', cron_expression: '* * * * *', task_type: 'shell', command: 'ls', http_method: 'GET', status: 'enabled' }
    wrapper.vm.openCronDialog(job)
    expect(wrapper.vm.editingCronId).toBe('j1')
    expect(wrapper.vm.cronForm.name).toBe('Test')
    expect(wrapper.vm.cronFormEnabled).toBe(true)
  })

  it('openBackupDialog 新建时应该重置表单', () => {
    const wrapper = createWrapper()
    wrapper.vm.openBackupDialog()
    expect(wrapper.vm.editingBackupId).toBe('')
    expect(wrapper.vm.backupDialogVisible).toBe(true)
  })

  it('openBackupDialog 编辑时应该填充表单', () => {
    const wrapper = createWrapper()
    const policy = { id: 'b1', name: 'Backup1', backup_type: 'website', source_path: '/var/www', db_name: '', db_host: 'localhost', db_port: undefined, db_username: '', storage_type: 'local', cron_expression: '0 3 * * *', retention_count: 7, compression: 'tar.gz', status: 'enabled', storage_config: {} }
    wrapper.vm.openBackupDialog(policy)
    expect(wrapper.vm.editingBackupId).toBe('b1')
    expect(wrapper.vm.backupForm.name).toBe('Backup1')
  })

  it('openLogDialog 新建时应该重置表单', () => {
    const wrapper = createWrapper()
    wrapper.vm.openLogDialog()
    expect(wrapper.vm.editingLogId).toBe('')
    expect(wrapper.vm.logDialogVisible).toBe(true)
  })

  it('openLogDialog 编辑时应该填充表单', () => {
    const wrapper = createWrapper()
    const policy = { id: 'l1', name: 'LogRule1', log_path_pattern: '/var/log/*.log', retention_days: 30, cleanup_action: 'delete', archive_path: '', cron_expression: '0 4 * * 0', status: 'disabled' }
    wrapper.vm.openLogDialog(policy)
    expect(wrapper.vm.editingLogId).toBe('l1')
    expect(wrapper.vm.logFormEnabled).toBe(false)
  })

  it('saveCronJob 信息不完整时应该显示警告', async () => {
    const { Md3Message } = await import('@/components/md3')
    const wrapper = createWrapper()
    wrapper.vm.cronForm = { name: '', cron_expression: '', task_type: 'shell', command: '', http_method: 'GET', status: 'enabled' }
    await wrapper.vm.saveCronJob()
    expect(Md3Message.warning).toHaveBeenCalled()
  })

  it('saveCronJob 新建时应该调用 createCronJob', async () => {
    const { Md3Message } = await import('@/components/md3')
    const wrapper = createWrapper()
    wrapper.vm.editingCronId = ''
    wrapper.vm.cronForm = { name: 'Test', cron_expression: '* * * * *', task_type: 'shell', command: 'ls', http_method: 'GET', status: 'enabled' }
    await wrapper.vm.saveCronJob()
    expect(cronBackupStoreMock.createCronJob).toHaveBeenCalled()
    expect(wrapper.vm.cronDialogVisible).toBe(false)
  })

  it('saveCronJob 编辑时应该调用 updateCronJob', async () => {
    const { Md3Message } = await import('@/components/md3')
    const wrapper = createWrapper()
    wrapper.vm.editingCronId = 'j1'
    wrapper.vm.cronForm = { name: 'Test', cron_expression: '* * * * *', task_type: 'shell', command: 'ls', http_method: 'GET', status: 'enabled' }
    await wrapper.vm.saveCronJob()
    expect(cronBackupStoreMock.updateCronJob).toHaveBeenCalled()
  })

  it('saveCronJob 失败时应该显示错误', async () => {
    const { Md3Message } = await import('@/components/md3')
    cronBackupStoreMock.createCronJob = vi.fn().mockRejectedValue(new Error('fail'))
    const wrapper = createWrapper()
    wrapper.vm.editingCronId = ''
    wrapper.vm.cronForm = { name: 'Test', cron_expression: '* * * * *', task_type: 'shell', command: 'ls', http_method: 'GET', status: 'enabled' }
    await wrapper.vm.saveCronJob()
    expect(Md3Message.error).toHaveBeenCalled()
  })

  it('saveBackupPolicy 信息不完整时应该显示警告', async () => {
    const { Md3Message } = await import('@/components/md3')
    const wrapper = createWrapper()
    wrapper.vm.backupForm = { name: '', cron_expression: '', backup_type: 'website', source_path: '', db_name: '', db_host: 'localhost', db_port: undefined, db_username: '', storage_type: 'local', retention_count: 7, compression: 'tar.gz', status: 'enabled' }
    await wrapper.vm.saveBackupPolicy()
    expect(Md3Message.warning).toHaveBeenCalled()
  })

  it('saveBackupPolicy 新建时应该调用 createBackupPolicy', async () => {
    const { Md3Message } = await import('@/components/md3')
    const wrapper = createWrapper()
    wrapper.vm.editingBackupId = ''
    wrapper.vm.backupForm = { name: 'Backup', cron_expression: '0 3 * * *', backup_type: 'website', source_path: '/var/www', db_name: '', db_host: 'localhost', db_port: undefined, db_username: '', storage_type: 'local', retention_count: 7, compression: 'tar.gz', status: 'enabled' }
    await wrapper.vm.saveBackupPolicy()
    expect(cronBackupStoreMock.createBackupPolicy).toHaveBeenCalled()
    expect(wrapper.vm.backupDialogVisible).toBe(false)
  })

  it('saveBackupPolicy 编辑时应该调用 updateBackupPolicy', async () => {
    const { Md3Message } = await import('@/components/md3')
    const wrapper = createWrapper()
    wrapper.vm.editingBackupId = 'b1'
    wrapper.vm.backupForm = { name: 'Backup', cron_expression: '0 3 * * *', backup_type: 'website', source_path: '/var/www', db_name: '', db_host: 'localhost', db_port: undefined, db_username: '', storage_type: 'local', retention_count: 7, compression: 'tar.gz', status: 'enabled' }
    await wrapper.vm.saveBackupPolicy()
    expect(cronBackupStoreMock.updateBackupPolicy).toHaveBeenCalled()
  })

  it('saveLogPolicy 信息不完整时应该显示警告', async () => {
    const { Md3Message } = await import('@/components/md3')
    const wrapper = createWrapper()
    wrapper.vm.logForm = { name: '', log_path_pattern: '', retention_days: 30, cleanup_action: 'delete', archive_path: '', cron_expression: '', status: 'enabled' }
    await wrapper.vm.saveLogPolicy()
    expect(Md3Message.warning).toHaveBeenCalled()
  })

  it('saveLogPolicy 新建时应该调用 createLogPolicy', async () => {
    const { Md3Message } = await import('@/components/md3')
    const wrapper = createWrapper()
    wrapper.vm.editingLogId = ''
    wrapper.vm.logForm = { name: 'LogRule', log_path_pattern: '/var/log/*.log', retention_days: 30, cleanup_action: 'delete', archive_path: '', cron_expression: '0 4 * * 0', status: 'enabled' }
    await wrapper.vm.saveLogPolicy()
    expect(cronBackupStoreMock.createLogPolicy).toHaveBeenCalled()
    expect(wrapper.vm.logDialogVisible).toBe(false)
  })

  it('toggleCronStatus 启用任务', async () => {
    const { Md3Message } = await import('@/components/md3')
    const wrapper = createWrapper()
    await wrapper.vm.toggleCronStatus({ id: 'j1' }, true)
    expect(cronBackupStoreMock.updateCronJob).toHaveBeenCalledWith('j1', { status: 'enabled' })
    expect(Md3Message.success).toHaveBeenCalled()
  })

  it('toggleCronStatus 失败时应该显示错误', async () => {
    const { Md3Message } = await import('@/components/md3')
    cronBackupStoreMock.updateCronJob = vi.fn().mockRejectedValue(new Error('fail'))
    const wrapper = createWrapper()
    await wrapper.vm.toggleCronStatus({ id: 'j1' }, true)
    expect(Md3Message.error).toHaveBeenCalled()
  })

  it('toggleBackupStatus 应该调用 store', async () => {
    const { Md3Message } = await import('@/components/md3')
    const wrapper = createWrapper()
    await wrapper.vm.toggleBackupStatus({ id: 'b1' }, true)
    expect(cronBackupStoreMock.updateBackupPolicy).toHaveBeenCalledWith('b1', { status: 'enabled' })
  })

  it('toggleLogStatus 应该调用 store', async () => {
    const { Md3Message } = await import('@/components/md3')
    const wrapper = createWrapper()
    await wrapper.vm.toggleLogStatus({ id: 'l1' }, true)
    expect(cronBackupStoreMock.updateLogPolicy).toHaveBeenCalledWith('l1', { status: 'enabled' })
  })

  it('deleteCron 确认时应该调用 store', async () => {
    const { Md3Message } = await import('@/components/md3')
    const wrapper = createWrapper()
    await wrapper.vm.deleteCron({ id: 'j1', name: 'TestCron' })
    expect(cronBackupStoreMock.deleteCronJob).toHaveBeenCalledWith('j1')
    expect(Md3Message.success).toHaveBeenCalled()
  })

  it('deleteCron 取消时不应调用 store', async () => {
    const { Md3Confirm } = await import('@/components/md3/Md3Confirm')
    Md3Confirm.show.mockResolvedValueOnce(false)
    const wrapper = createWrapper()
    await wrapper.vm.deleteCron({ id: 'j1', name: 'TestCron' })
    expect(cronBackupStoreMock.deleteCronJob).not.toHaveBeenCalled()
  })

  it('deleteBackup 确认时应该调用 store', async () => {
    const { Md3Message } = await import('@/components/md3')
    const wrapper = createWrapper()
    await wrapper.vm.deleteBackup({ id: 'b1', name: 'TestBackup' })
    expect(cronBackupStoreMock.deleteBackupPolicy).toHaveBeenCalledWith('b1')
  })

  it('deleteLog 确认时应该调用 store', async () => {
    const { Md3Message } = await import('@/components/md3')
    const wrapper = createWrapper()
    await wrapper.vm.deleteLog({ id: 'l1', name: 'TestLog' })
    expect(cronBackupStoreMock.deleteLogPolicy).toHaveBeenCalledWith('l1')
  })

  it('showCronLogs 成功时应该打开日志对话框', async () => {
    const wrapper = createWrapper()
    await wrapper.vm.showCronLogs({ id: 'j1' })
    expect(cronBackupStoreMock.fetchExecutionLogs).toHaveBeenCalledWith('j1')
    expect(wrapper.vm.logsDialogVisible).toBe(true)
  })

  it('showCronLogs 失败时应该显示错误', async () => {
    const { Md3Message } = await import('@/components/md3')
    cronBackupStoreMock.fetchExecutionLogs = vi.fn().mockRejectedValue(new Error('fail'))
    const wrapper = createWrapper()
    await wrapper.vm.showCronLogs({ id: 'j1' })
    expect(Md3Message.error).toHaveBeenCalled()
  })

  it('showBackupHistory 成功时应该打开历史对话框', async () => {
    const wrapper = createWrapper()
    await wrapper.vm.showBackupHistory({ id: 'b1' })
    expect(cronBackupStoreMock.fetchBackupHistory).toHaveBeenCalledWith('b1')
    expect(wrapper.vm.historyDialogVisible).toBe(true)
  })

  it('runBackup 成功时应该显示成功消息', async () => {
    const { Md3Message } = await import('@/components/md3')
    const wrapper = createWrapper()
    await wrapper.vm.runBackup({ id: 'b1' })
    expect(cronBackupStoreMock.runBackupNow).toHaveBeenCalledWith('b1')
    expect(Md3Message.success).toHaveBeenCalled()
  })

  it('runBackup 失败时应该显示错误', async () => {
    const { Md3Message } = await import('@/components/md3')
    cronBackupStoreMock.runBackupNow = vi.fn().mockRejectedValue(new Error('fail'))
    const wrapper = createWrapper()
    await wrapper.vm.runBackup({ id: 'b1' })
    expect(Md3Message.error).toHaveBeenCalled()
  })

  it('previewLogCleanup 成功时应该打开预览对话框', async () => {
    const wrapper = createWrapper()
    await wrapper.vm.previewLogCleanup({ id: 'l1' })
    expect(cronBackupStoreMock.previewLogCleanup).toHaveBeenCalledWith('l1')
    expect(wrapper.vm.previewDialogVisible).toBe(true)
  })

  it('previewLogCleanup 失败时应该显示错误', async () => {
    const { Md3Message } = await import('@/components/md3')
    cronBackupStoreMock.previewLogCleanup = vi.fn().mockRejectedValue(new Error('fail'))
    const wrapper = createWrapper()
    await wrapper.vm.previewLogCleanup({ id: 'l1' })
    expect(Md3Message.error).toHaveBeenCalled()
  })

  it('runLogCleanup 确认时应该执行清理', async () => {
    const { Md3Message } = await import('@/components/md3')
    const wrapper = createWrapper()
    await wrapper.vm.runLogCleanup({ id: 'l1', name: 'TestLog' })
    expect(cronBackupStoreMock.runLogCleanupNow).toHaveBeenCalledWith('l1')
    expect(Md3Message.success).toHaveBeenCalled()
  })

  it('runLogCleanup 取消时不应执行清理', async () => {
    const { Md3Confirm } = await import('@/components/md3/Md3Confirm')
    Md3Confirm.show.mockResolvedValueOnce(false)
    const wrapper = createWrapper()
    await wrapper.vm.runLogCleanup({ id: 'l1', name: 'TestLog' })
    expect(cronBackupStoreMock.runLogCleanupNow).not.toHaveBeenCalled()
  })

  it('onAccountChange 应该设置别名并加载数据', async () => {
    const wrapper = createWrapper()
    await wrapper.vm.onAccountChange('test-server')
    expect(wrapper.vm.selectedAlias).toBe('test-server')
    expect(cronBackupStoreMock.setAccountAlias).toHaveBeenCalledWith('test-server')
    expect(cronBackupStoreMock.fetchCronJobs).toHaveBeenCalled()
  })

  it('loadTabData cron tab 应该加载 cron 数据', async () => {
    const wrapper = createWrapper()
    wrapper.vm.selectedAlias = 'test-server'
    wrapper.vm.activeTab = 'cron'
    await wrapper.vm.loadTabData()
    expect(cronBackupStoreMock.fetchCronJobs).toHaveBeenCalled()
  })

  it('loadTabData backup tab 应该加载备份数据', async () => {
    const wrapper = createWrapper()
    wrapper.vm.selectedAlias = 'test-server'
    wrapper.vm.activeTab = 'backup'
    await wrapper.vm.loadTabData()
    expect(cronBackupStoreMock.fetchBackupPolicies).toHaveBeenCalled()
  })

  it('loadTabData log tab 应该加载日志和磁盘告警数据', async () => {
    const wrapper = createWrapper()
    wrapper.vm.selectedAlias = 'test-server'
    wrapper.vm.activeTab = 'log'
    await wrapper.vm.loadTabData()
    expect(cronBackupStoreMock.fetchLogPolicies).toHaveBeenCalled()
    expect(cronBackupStoreMock.fetchDiskAlert).toHaveBeenCalled()
  })

  it('onMounted 应该加载 SSH 账户并自动选择默认账户', () => {
    createWrapper()
    expect(sshStoreMock.fetchAccounts).toHaveBeenCalled()
  })

  it('filteredCronJobs 有搜索时应该过滤', () => {
    cronBackupStoreMock.cronJobs = [{ name: 'backup-daily', cron_expression: '0 2 * * *', task_type: 'shell', command: 'backup.sh', status: 'enabled', last_run_at: '' }, { name: 'cleanup-weekly', cron_expression: '0 3 * * 0', task_type: 'shell', command: 'cleanup.sh', status: 'enabled', last_run_at: '' }]
    const wrapper = createWrapper()
    wrapper.vm.cronSearch = 'daily'
    expect(wrapper.vm.filteredCronJobs).toHaveLength(1)
  })

  it('filteredBackupPolicies 有搜索时应该过滤', () => {
    cronBackupStoreMock.backupPolicies = [{ name: 'web-backup', backup_type: 'website', storage_type: 'local', cron_expression: '0 3 * * *', retention_count: 7, compression: 'tar.gz', status: 'enabled' }, { name: 'db-backup', backup_type: 'mysql', storage_type: 'local', cron_expression: '0 4 * * *', retention_count: 7, compression: 'tar.gz', status: 'enabled' }]
    const wrapper = createWrapper()
    wrapper.vm.backupSearch = 'web'
    expect(wrapper.vm.filteredBackupPolicies).toHaveLength(1)
  })

  it('filteredLogPolicies 有搜索时应该过滤', () => {
    cronBackupStoreMock.logPolicies = [{ name: 'nginx-log', log_path_pattern: '/var/log/nginx/*.log', retention_days: 30, cleanup_action: 'delete', cron_expression: '0 4 * * 0', status: 'enabled' }, { name: 'sys-log', log_path_pattern: '/var/log/syslog', retention_days: 60, cleanup_action: 'compress', cron_expression: '0 4 1 * *', status: 'enabled' }]
    const wrapper = createWrapper()
    wrapper.vm.logSearch = 'nginx'
    expect(wrapper.vm.filteredLogPolicies).toHaveLength(1)
  })

  it('cronDialogTitle 新建时应该显示新建标题', () => {
    const wrapper = createWrapper()
    expect(wrapper.vm.cronDialogTitle).toBe('新建计划任务')
  })

  it('cronDialogTitle 编辑时应该显示编辑标题', () => {
    const wrapper = createWrapper()
    wrapper.vm.editingCronId = 'j1'
    expect(wrapper.vm.cronDialogTitle).toBe('编辑计划任务')
  })
})
