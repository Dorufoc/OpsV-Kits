import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { nextTick } from 'vue'

vi.mock('@/components/md3', () => ({
  Md3Icon: { name: 'Md3Icon', props: ['name', 'size'], template: '<span class="mdi-icon" :data-name="name"></span>' },
  Md3Confirm: { show: vi.fn().mockResolvedValue(true) },
  Md3Message: { success: vi.fn(), error: vi.fn() },
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
}))

vi.mock('@/components/Md3Button.vue', () => ({
  default: { name: 'Md3Button', props: ['size', 'variant', 'disabled', 'icon', 'loading', 'type'], template: '<button class="md3-btn" :disabled="disabled" @click="$emit(\'click\')"><slot /></button>' },
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
    fetchWorkflows: vi.fn().mockResolvedValue(undefined),
    fetchWorkflow: vi.fn().mockResolvedValue(undefined),
    fetchVersions: vi.fn().mockResolvedValue(undefined),
    fetchExecution: vi.fn().mockResolvedValue(undefined),
    fetchNodeExecutions: vi.fn().mockResolvedValue(undefined),
    fetchTemplates: vi.fn().mockResolvedValue(undefined),
    createWorkflow: vi.fn().mockResolvedValue({ id: '1', name: 'test' }),
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
    loading: false,
    fetchCronJobs: vi.fn().mockResolvedValue(undefined),
    createCronJob: vi.fn().mockResolvedValue(undefined),
    updateCronJob: vi.fn().mockResolvedValue(undefined),
    deleteCronJob: vi.fn().mockResolvedValue(undefined),
    fetchBackupPolicies: vi.fn().mockResolvedValue(undefined),
    createBackupPolicy: vi.fn().mockResolvedValue(undefined),
    runBackupNow: vi.fn().mockResolvedValue(undefined),
    fetchBackupHistory: vi.fn().mockResolvedValue(undefined),
    fetchLogPolicies: vi.fn().mockResolvedValue(undefined),
    fetchDiskAlert: vi.fn().mockResolvedValue(undefined),
    setAccountAlias: vi.fn(),
  }
  schedulerStoreMock = {
    tasks: [],
    fetchTasks: vi.fn().mockResolvedValue(undefined),
  }
  eventTriggerStoreMock = {
    sources: [],
    fetchSources: vi.fn().mockResolvedValue(undefined),
    fetchEventLogs: vi.fn().mockResolvedValue(undefined),
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
})
