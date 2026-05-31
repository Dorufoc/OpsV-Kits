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
  Md3Empty: { name: 'Md3Empty', props: ['description', 'imageSize'], template: '<div class="md3-empty">{{ description }}</div>' },
  Md3Tag: { name: 'Md3Tag', props: ['type', 'size', 'variant'], template: '<span class="md3-tag"><slot /></span>' },
  Md3Table: { name: 'Md3Table', props: ['columns', 'data', 'stripe', 'emptyText', 'selection', 'maxHeight'], template: '<div class="md3-table"><slot /></div>' },
  Md3Tabs: { name: 'Md3Tabs', props: ['modelValue', 'tabs'], template: '<div class="md3-tabs" />' },
  Md3Dialog: { name: 'Md3Dialog', props: ['visible', 'title', 'width', 'closable'], emits: ['update:visible'], template: '<div class="md3-dialog" v-if="visible"><slot /><slot name="footer" /></div>' },
  Md3Input: { name: 'Md3Input', props: ['modelValue', 'label', 'placeholder', 'type', 'min', 'max'], emits: ['update:modelValue'], template: '<input class="md3-input" :value="modelValue" />' },
  Md3Select: { name: 'Md3Select', props: ['modelValue', 'options', 'placeholder', 'label', 'clearable', 'multiple', 'size'], emits: ['update:modelValue'], template: '<select class="md3-select" :data-placeholder="placeholder">{{ placeholder }}</select>' },
  Md3Alert: { name: 'Md3Alert', props: ['type', 'title', 'message'], template: '<div class="md3-alert"><slot name="title" /><slot name="message" /></div>' },
  Md3Switch: { name: 'Md3Switch', props: ['modelValue', 'onText', 'offText'], emits: ['update:modelValue'], template: '<div class="md3-switch" />' },
  Md3Progress: { name: 'Md3Progress', props: ['percentage', 'color'], template: '<div class="md3-progress" />' },
  Md3Collapse: { name: 'Md3Collapse', props: ['title'], template: '<div class="md3-collapse"><slot /></div>' },
  Md3Spinner: { name: 'Md3Spinner', props: ['size'], template: '<div class="md3-spinner" />' },
  Md3Checkbox: { name: 'Md3Checkbox', props: ['modelValue'], emits: ['update:modelValue'], template: '<input type="checkbox" class="md3-checkbox" />' },
  Md3Radio: { name: 'Md3Radio', props: ['modelValue', 'value', 'label'], emits: ['update:modelValue'], template: '<label class="md3-radio" />' },
  Md3Tooltip: { name: 'Md3Tooltip', props: ['content', 'placement'], template: '<div class="md3-tooltip"><slot /></div>' },
}))

vi.mock('@/components/Md3Button.vue', () => ({
  default: { name: 'Md3Button', props: ['size', 'variant', 'disabled', 'icon', 'loading', 'type'], template: '<button class="md3-btn" :disabled="disabled" @click="$emit(\'click\')"><slot /></button>' },
}))

vi.mock('@/components/Terminal.vue', () => ({
  default: { name: 'Terminal', props: ['sessionName', 'showToolbar', 'fontSize', 'fontFamily', 'theme'], emits: ['data', 'resize'], template: '<div class="terminal" />' },
}))

vi.mock('@/components/SessionManager.vue', () => ({
  default: { name: 'SessionManager', props: ['sessions', 'historyRecords', 'activeSessionId'], emits: ['select', 'disconnect', 'newSession', 'reconnect', 'deleteHistory'], template: '<div class="session-manager" />' },
}))

const mockPush = vi.fn()
vi.mock('vue-router', () => ({
  useRouter: () => ({ push: mockPush }),
  useRoute: () => ({}),
}))

let logAnalysisStoreMock: any
let healthProbeStoreMock: any
let auditLogStoreMock: any
let websshStoreMock: any
let sshStoreMock: any

vi.mock('@/stores/logAnalysisStore', () => ({
  useLogAnalysisStore: () => logAnalysisStoreMock,
}))

vi.mock('@/stores/healthProbeStore', () => ({
  useHealthProbeStore: () => healthProbeStoreMock,
}))

vi.mock('@/stores/auditLogStore', () => ({
  useAuditLogStore: () => auditLogStoreMock,
}))

vi.mock('@/stores/websshStore', () => ({
  useWebsshStore: () => websshStoreMock,
}))

vi.mock('@/stores/sshAccountStore', () => ({
  useSshAccountStore: () => sshStoreMock,
}))

beforeEach(() => {
  setActivePinia(createPinia())
  vi.clearAllMocks()
  logAnalysisStoreMock = {
    searchResult: { items: [], total: 0 },
    loading: false,
    realtimeConnected: false,
    search: vi.fn().mockResolvedValue(undefined),
    searchLogs: vi.fn().mockResolvedValue(undefined),
    connectRealtime: vi.fn(),
    disconnectRealtime: vi.fn(),
  }
  healthProbeStoreMock = {
    targets: [],
    overview: null,
    loading: false,
    fetchTargets: vi.fn().mockResolvedValue(undefined),
    fetchOverview: vi.fn().mockResolvedValue(undefined),
    createTarget: vi.fn().mockResolvedValue(undefined),
    deleteTarget: vi.fn().mockResolvedValue(undefined),
    probeNow: vi.fn().mockResolvedValue(undefined),
  }
  auditLogStoreMock = {
    logs: [],
    savedQueries: [],
    loading: false,
    fetchLogs: vi.fn().mockResolvedValue(undefined),
    fetchSavedQueries: vi.fn().mockResolvedValue(undefined),
    saveQuery: vi.fn().mockResolvedValue(undefined),
    exportLogs: vi.fn().mockResolvedValue(undefined),
  }
  websshStoreMock = {
    sessions: [],
    historyRecords: [],
    activeSessionId: null,
    connect: vi.fn().mockResolvedValue(undefined),
    disconnect: vi.fn().mockResolvedValue(undefined),
    sendCommand: vi.fn(),
    deleteHistory: vi.fn().mockResolvedValue(undefined),
    listSessions: vi.fn().mockResolvedValue(undefined),
    fetchHistory: vi.fn().mockResolvedValue(undefined),
  }
  sshStoreMock = {
    accounts: [{ alias: 'test-server', host: '192.168.1.1', default: true }],
    fetchAccounts: vi.fn().mockResolvedValue(undefined),
  }
})

import LogAnalysisPage from '@/views/LogAnalysisPage.vue'
import HealthProbePage from '@/views/HealthProbePage.vue'
import AuditLogPage from '@/views/AuditLogPage.vue'
import WebSSHPage from '@/views/WebSSHPage.vue'
import Tools from '@/views/Tools.vue'

const md3Stubs = {
  Md3Icon: true,
  Md3PageHeader: { name: 'Md3PageHeader', props: ['title', 'showBack', 'subtitle'], template: '<div class="md3-page-header">{{ title }}<slot name="subtitle" /><slot name="actions" /><slot name="content" /><slot name="extra" /></div>' },
  Md3Divider: { template: '<hr class="md3-divider" />' },
  Md3Card: { props: ['shadow', 'hoverable'], template: '<div class="md3-card"><slot /><slot name="header" /></div>' },
  Md3Empty: { props: ['description', 'imageSize'], template: '<div class="md3-empty">{{ description }}</div>' },
  Md3Tag: { props: ['type', 'size', 'variant'], template: '<span class="md3-tag"><slot /></span>' },
  Md3Table: { props: ['columns', 'data', 'stripe', 'emptyText', 'selection', 'maxHeight'], template: '<div class="md3-table"><slot /></div>' },
  Md3Tabs: { props: ['modelValue', 'tabs'], template: '<div class="md3-tabs" />' },
  Md3Dialog: { props: ['visible', 'title', 'width', 'closable'], emits: ['update:visible'], template: '<div class="md3-dialog" v-if="visible"><slot /><slot name="footer" /></div>' },
  Md3Input: { props: ['modelValue', 'label', 'placeholder', 'type', 'min', 'max'], emits: ['update:modelValue'], template: '<input class="md3-input" :value="modelValue" :placeholder="placeholder" />' },
  Md3Select: { props: ['modelValue', 'options', 'placeholder', 'label', 'clearable', 'multiple', 'size'], emits: ['update:modelValue'], template: '<select class="md3-select" :data-placeholder="placeholder">{{ placeholder }}</select>' },
  Md3Alert: { props: ['type', 'title', 'message'], template: '<div class="md3-alert"><slot name="title" /><slot name="message" /></div>' },
  Md3Switch: { props: ['modelValue', 'onText', 'offText'], emits: ['update:modelValue'], template: '<div class="md3-switch" />' },
  Md3Progress: { props: ['percentage', 'color'], template: '<div class="md3-progress" />' },
  Md3Collapse: { props: ['title'], template: '<div class="md3-collapse"><slot /></div>' },
  Md3Spinner: { props: ['size'], template: '<div class="md3-spinner" />' },
  Md3Checkbox: { props: ['modelValue'], emits: ['update:modelValue'], template: '<input type="checkbox" class="md3-checkbox" />' },
  Md3Radio: { props: ['modelValue', 'value', 'label'], emits: ['update:modelValue'], template: '<label class="md3-radio" />' },
  Md3Tooltip: { props: ['content', 'placement'], template: '<div class="md3-tooltip"><slot /></div>' },
  Md3Button: { props: ['size', 'variant', 'disabled', 'icon', 'loading', 'type'], template: '<button class="md3-btn" :disabled="disabled" @click="$emit(\'click\')"><slot /></button>' },
}

describe('LogAnalysisPage', () => {
  function createWrapper() {
    return mount(LogAnalysisPage, { global: { stubs: md3Stubs } })
  }

  it('应该渲染日志分析页面容器', () => {
    const wrapper = createWrapper()
    expect(wrapper.find('.log-analysis-page').exists()).toBe(true)
  })

  it('应该渲染页面标题', () => {
    const wrapper = createWrapper()
    expect(wrapper.text()).toContain('日志聚合分析')
  })

  it('应该渲染 Tab 切换', () => {
    const wrapper = createWrapper()
    expect(wrapper.find('.log-tabs').exists() || wrapper.find('.md3-tabs').exists()).toBe(true)
  })

  it('应该渲染搜索区域', () => {
    const wrapper = createWrapper()
    const inputs = wrapper.findAll('.md3-input')
    const hasSearchInput = inputs.some(el => el.attributes('placeholder')?.includes('全局搜索'))
    expect(hasSearchInput).toBe(true)
  })

  it('应该渲染实时推送按钮', () => {
    const wrapper = createWrapper()
    expect(wrapper.text()).toContain('实时推送')
  })
})

describe('HealthProbePage', () => {
  function createWrapper() {
    return mount(HealthProbePage, { global: { stubs: md3Stubs } })
  }

  it('应该渲染健康检查页面容器', () => {
    const wrapper = createWrapper()
    expect(wrapper.find('.health-probe-page').exists()).toBe(true)
  })

  it('应该渲染页面标题', () => {
    const wrapper = createWrapper()
    expect(wrapper.text()).toContain('健康检查')
  })

  it('应该渲染新增探测按钮', () => {
    const wrapper = createWrapper()
    expect(wrapper.text()).toContain('新增探测')
  })

  it('应该渲染刷新按钮', () => {
    const wrapper = createWrapper()
    expect(wrapper.text()).toContain('刷新')
  })

  it('应该在无目标时显示空状态', () => {
    const wrapper = createWrapper()
    expect(wrapper.text()).toContain('暂无探测目标')
  })

  it('应该在加载中时显示加载状态', async () => {
    healthProbeStoreMock.loading = true
    healthProbeStoreMock.targets = []
    const wrapper = createWrapper()
    await nextTick()
    expect(wrapper.find('.loading-state').exists()).toBe(true)
  })
})

describe('AuditLogPage', () => {
  function createWrapper() {
    return mount(AuditLogPage, { global: { stubs: md3Stubs } })
  }

  it('应该渲染审计日志页面容器', () => {
    const wrapper = createWrapper()
    expect(wrapper.find('.audit-log-page').exists()).toBe(true)
  })

  it('应该渲染页面标题', () => {
    const wrapper = createWrapper()
    expect(wrapper.text()).toContain('审计日志')
  })

  it('应该渲染 Tab 切换', () => {
    const wrapper = createWrapper()
    expect(wrapper.find('.page-tabs').exists() || wrapper.find('.md3-tabs').exists()).toBe(true)
  })

  it('应该渲染日志查询区域', () => {
    const wrapper = createWrapper()
    expect(wrapper.text()).toContain('日志查询')
  })
})

describe('WebSSHPage', () => {
  function createWrapper() {
    return mount(WebSSHPage, { global: { stubs: md3Stubs } })
  }

  it('应该渲染 WebSSH 页面容器', () => {
    const wrapper = createWrapper()
    expect(wrapper.find('.webssh-page').exists()).toBe(true)
  })

  it('应该渲染侧边栏', () => {
    const wrapper = createWrapper()
    expect(wrapper.find('.webssh-sidebar').exists()).toBe(true)
  })

  it('应该渲染主区域', () => {
    const wrapper = createWrapper()
    expect(wrapper.find('.webssh-main').exists()).toBe(true)
  })

  it('应该在无活跃会话时显示空状态', () => {
    const wrapper = createWrapper()
    expect(wrapper.text()).toContain('请新建或选择一个 SSH 会话')
  })
})

describe('Tools', () => {
  function createWrapper() {
    return mount(Tools, { global: { stubs: md3Stubs } })
  }

  it('应该渲染工具页面容器', () => {
    const wrapper = createWrapper()
    expect(wrapper.find('.tools').exists()).toBe(true)
  })

  it('应该渲染远程硬盘区域', () => {
    const wrapper = createWrapper()
    expect(wrapper.text()).toContain('远程硬盘')
  })

  it('应该渲染实验性功能标签', () => {
    const wrapper = createWrapper()
    expect(wrapper.text()).toContain('实验性功能')
  })

  it('应该渲染 WebDAV 地址', () => {
    const wrapper = createWrapper()
    expect(wrapper.text()).toContain('WebDAV')
  })
})
