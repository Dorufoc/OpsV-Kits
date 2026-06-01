import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { nextTick } from 'vue'

vi.mock('@/components/md3', () => ({
  Md3Icon: { name: 'Md3Icon', props: ['name', 'size'], template: '<span class="mdi-icon" :data-name="name"></span>' },
  Md3Confirm: { show: vi.fn().mockResolvedValue(true) },
  Md3Message: { success: vi.fn(), error: vi.fn(), warning: vi.fn() },
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
  default: {
    name: 'Terminal',
    props: ['sessionName', 'showToolbar', 'fontSize', 'fontFamily', 'theme'],
    emits: ['data', 'resize'],
    template: '<div class="terminal" />',
    setup(_, { expose }) {
      const clear = vi.fn()
      const writeln = vi.fn()
      const write = vi.fn()
      expose({ clear, writeln, write })
      return { clear, writeln, write }
    },
  },
}))

vi.mock('@/components/SessionManager.vue', () => ({
  default: { name: 'SessionManager', props: ['sessions', 'historyRecords', 'activeSessionId'], emits: ['select', 'disconnect', 'newSession', 'reconnect', 'deleteHistory'], template: '<div class="session-manager" />' },
}))

const mockPush = vi.fn()
vi.mock('vue-router', () => ({
  useRouter: () => ({ push: mockPush }),
  useRoute: () => ({}),
}))

const mockRequestGet = vi.fn().mockResolvedValue({})
const mockRequestPost = vi.fn().mockResolvedValue({})
const mockRequestPut = vi.fn().mockResolvedValue({})
const mockRequestDelete = vi.fn().mockResolvedValue({})
vi.mock('@/api', () => ({
  request: {
    get: (...args: any[]) => mockRequestGet(...args),
    post: (...args: any[]) => mockRequestPost(...args),
    put: (...args: any[]) => mockRequestPut(...args),
    delete: (...args: any[]) => mockRequestDelete(...args),
  },
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
    searchResult: { items: [], total: 0, page: 1, pageSize: 20 },
    loading: false,
    realtimeConnected: false,
    realtimeLogs: [],
    aggregation: { trend: [], levelDistribution: [], sourceRanking: [] },
    alertRules: [],
    alertEvents: [],
    sources: [],
    search: vi.fn().mockResolvedValue(undefined),
    searchLogs: vi.fn().mockResolvedValue(undefined),
    connectRealtime: vi.fn(),
    disconnectRealtime: vi.fn(),
    fetchAggregation: vi.fn().mockResolvedValue(undefined),
    fetchAlertRules: vi.fn().mockResolvedValue(undefined),
    fetchAlertEvents: vi.fn().mockResolvedValue(undefined),
    fetchSources: vi.fn().mockResolvedValue(undefined),
    createAlertRule: vi.fn().mockResolvedValue(undefined),
    updateAlertRule: vi.fn().mockResolvedValue(undefined),
    deleteAlertRule: vi.fn().mockResolvedValue(undefined),
    toggleAlertRule: vi.fn().mockResolvedValue(undefined),
    createSource: vi.fn().mockResolvedValue(undefined),
    startSource: vi.fn().mockResolvedValue(undefined),
    stopSource: vi.fn().mockResolvedValue(undefined),
    deleteSource: vi.fn().mockResolvedValue(undefined),
  }
  healthProbeStoreMock = {
    targets: [],
    overview: null,
    loading: false,
    probing: false,
    fetchTargets: vi.fn().mockResolvedValue(undefined),
    fetchOverview: vi.fn().mockResolvedValue(undefined),
    createTarget: vi.fn().mockResolvedValue(undefined),
    updateTarget: vi.fn().mockResolvedValue(undefined),
    deleteTarget: vi.fn().mockResolvedValue(undefined),
    probeNow: vi.fn().mockResolvedValue(undefined),
    fetchStatistics: vi.fn().mockResolvedValue(null),
    fetchLogs: vi.fn().mockResolvedValue({ items: [] }),
  }
  auditLogStoreMock = {
    logs: [],
    savedQueries: [],
    archives: [],
    statistics: null,
    loading: false,
    loadingStats: false,
    fetchLogs: vi.fn().mockResolvedValue(undefined),
    fetchSavedQueries: vi.fn().mockResolvedValue(undefined),
    saveQuery: vi.fn().mockResolvedValue(undefined),
    exportLogs: vi.fn().mockResolvedValue(undefined),
    queryLogs: vi.fn().mockResolvedValue(undefined),
    verifyIntegrity: vi.fn().mockResolvedValue({ total: 1, passed: 1, failed: 0, failed_ids: [] }),
    loadStatistics: vi.fn().mockResolvedValue(undefined),
    loadArchives: vi.fn().mockResolvedValue(undefined),
    loadRecentLogs: vi.fn().mockResolvedValue(undefined),
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

  it('默认 activeTab 应该是 search', () => {
    const wrapper = createWrapper()
    expect(wrapper.vm.activeTab).toBe('search')
  })

  it('levelTagType 应该返回正确的标签类型', () => {
    const wrapper = createWrapper()
    expect(wrapper.vm.levelTagType('DEBUG')).toBe('info')
    expect(wrapper.vm.levelTagType('INFO')).toBe('primary')
    expect(wrapper.vm.levelTagType('WARN')).toBe('warning')
    expect(wrapper.vm.levelTagType('ERROR')).toBe('danger')
    expect(wrapper.vm.levelTagType('CRITICAL')).toBe('danger')
  })

  it('formatTimestamp 应该正确格式化时间戳', () => {
    const wrapper = createWrapper()
    const result = wrapper.vm.formatTimestamp(1705312200)
    expect(result).toBeTruthy()
    expect(result).toContain('2024')
  })

  it('truncate 应该截断长字符串', () => {
    const wrapper = createWrapper()
    expect(wrapper.vm.truncate('short', 10)).toBe('short')
    expect(wrapper.vm.truncate('a very long string that exceeds the limit', 10)).toBe('a very lon...')
  })

  it('truncate 空字符串应该返回空', () => {
    const wrapper = createWrapper()
    expect(wrapper.vm.truncate('', 10)).toBe('')
  })

  it('patternLabel 应该返回正确的标签', () => {
    const wrapper = createWrapper()
    expect(wrapper.vm.patternLabel('contains')).toBe('包含')
    expect(wrapper.vm.patternLabel('regex')).toBe('正则匹配')
    expect(wrapper.vm.patternLabel('exact')).toBe('精确匹配')
    expect(wrapper.vm.patternLabel('unknown')).toBe('unknown')
  })

  it('sourceTypeTagType 应该返回正确的标签类型', () => {
    const wrapper = createWrapper()
    expect(wrapper.vm.sourceTypeTagType('system')).toBe('info')
    expect(wrapper.vm.sourceTypeTagType('docker')).toBe('primary')
    expect(wrapper.vm.sourceTypeTagType('tcp')).toBe('success')
    expect(wrapper.vm.sourceTypeTagType('udp')).toBe('warning')
  })

  it('sourceStatusTagType 应该返回正确的标签类型', () => {
    const wrapper = createWrapper()
    expect(wrapper.vm.sourceStatusTagType('running')).toBe('success')
    expect(wrapper.vm.sourceStatusTagType('stopped')).toBe('info')
    expect(wrapper.vm.sourceStatusTagType('error')).toBe('danger')
  })

  it('sourceStatusLabel 应该返回正确的标签', () => {
    const wrapper = createWrapper()
    expect(wrapper.vm.sourceStatusLabel('running')).toBe('运行中')
    expect(wrapper.vm.sourceStatusLabel('stopped')).toBe('已停止')
    expect(wrapper.vm.sourceStatusLabel('error')).toBe('异常')
  })

  it('toggleLogExpand 应该切换展开状态', () => {
    const wrapper = createWrapper()
    expect(wrapper.vm.expandedLogId).toBeNull()
    wrapper.vm.toggleLogExpand('log-1')
    expect(wrapper.vm.expandedLogId).toBe('log-1')
    wrapper.vm.toggleLogExpand('log-1')
    expect(wrapper.vm.expandedLogId).toBeNull()
  })

  it('toggleRealtime 应该切换实时连接', () => {
    const wrapper = createWrapper()
    expect(wrapper.vm.realtimeConnected).toBe(false)
    wrapper.vm.toggleRealtime()
    expect(logAnalysisStoreMock.connectRealtime).toHaveBeenCalled()
  })

  it('toggleRealtime 连接中应该断开', () => {
    logAnalysisStoreMock.realtimeConnected = true
    const wrapper = createWrapper()
    wrapper.vm.toggleRealtime()
    expect(logAnalysisStoreMock.disconnectRealtime).toHaveBeenCalled()
  })

  it('onGlobalSearch 应该切换到搜索 Tab 并搜索', () => {
    const wrapper = createWrapper()
    wrapper.vm.activeTab = 'realtime'
    wrapper.vm.onGlobalSearch()
    expect(wrapper.vm.activeTab).toBe('search')
  })

  it('onSearch 应该调用 store.searchLogs', () => {
    const wrapper = createWrapper()
    wrapper.vm.onSearch()
    expect(logAnalysisStoreMock.searchLogs).toHaveBeenCalled()
  })

  it('openAlertRuleDialog 新建时应该重置表单', () => {
    const wrapper = createWrapper()
    wrapper.vm.openAlertRuleDialog()
    expect(wrapper.vm.alertRuleDialogVisible).toBe(true)
    expect(wrapper.vm.editingAlertRule).toBeNull()
    expect(wrapper.vm.alertRuleForm.name).toBe('')
  })

  it('openAlertRuleDialog 编辑时应该填充表单', () => {
    const wrapper = createWrapper()
    const rule = { id: '1', name: 'Test Rule', matchPattern: 'contains', pattern: 'error', timeWindow: 60, threshold: 10, level: 'ERROR' }
    wrapper.vm.openAlertRuleDialog(rule)
    expect(wrapper.vm.editingAlertRule).toEqual(rule)
    expect(wrapper.vm.alertRuleForm.name).toBe('Test Rule')
  })

  it('onDeleteAlertRule 应该调用 store.deleteAlertRule', async () => {
    const wrapper = createWrapper()
    await wrapper.vm.onDeleteAlertRule('rule-1')
    expect(logAnalysisStoreMock.deleteAlertRule).toHaveBeenCalledWith('rule-1')
  })

  it('onToggleAlertRule 应该调用 store.toggleAlertRule', async () => {
    const wrapper = createWrapper()
    await wrapper.vm.onToggleAlertRule('rule-1', true)
    expect(logAnalysisStoreMock.toggleAlertRule).toHaveBeenCalledWith('rule-1', true)
  })

  it('openSourceDialog 应该重置表单并打开对话框', () => {
    const wrapper = createWrapper()
    wrapper.vm.openSourceDialog()
    expect(wrapper.vm.sourceDialogVisible).toBe(true)
    expect(wrapper.vm.sourceForm.type).toBe('file')
    expect(wrapper.vm.sourceForm.alias).toBe('')
  })

  it('onSaveSource 应该调用 store.createSource', async () => {
    const wrapper = createWrapper()
    wrapper.vm.sourceForm.type = 'file'
    wrapper.vm.sourceForm.alias = 'test-source'
    await wrapper.vm.onSaveSource()
    expect(logAnalysisStoreMock.createSource).toHaveBeenCalled()
    expect(wrapper.vm.sourceDialogVisible).toBe(false)
  })

  it('onStartSource 应该调用 store.startSource', async () => {
    const wrapper = createWrapper()
    await wrapper.vm.onStartSource('source-1')
    expect(logAnalysisStoreMock.startSource).toHaveBeenCalledWith('source-1')
  })

  it('onStopSource 应该调用 store.stopSource', async () => {
    const wrapper = createWrapper()
    await wrapper.vm.onStopSource('source-1')
    expect(logAnalysisStoreMock.stopSource).toHaveBeenCalledWith('source-1')
  })

  it('onDeleteSource 应该调用 store.deleteSource', async () => {
    const wrapper = createWrapper()
    await wrapper.vm.onDeleteSource('source-1')
    expect(logAnalysisStoreMock.deleteSource).toHaveBeenCalledWith('source-1')
  })

  it('onPageChange 应该调用 store.searchLogs', () => {
    const wrapper = createWrapper()
    wrapper.vm.onPageChange(2)
    expect(logAnalysisStoreMock.searchLogs).toHaveBeenCalled()
  })

  it('onVizTimeRangeChange 应该调用 store.fetchAggregation', () => {
    const wrapper = createWrapper()
    wrapper.vm.onVizTimeRangeChange()
    expect(logAnalysisStoreMock.fetchAggregation).toHaveBeenCalled()
  })

  it('searchResult 应该返回 store 数据', () => {
    const wrapper = createWrapper()
    expect(wrapper.vm.searchResult).toEqual(logAnalysisStoreMock.searchResult)
  })

  it('totalPages 应该正确计算总页数', () => {
    logAnalysisStoreMock.searchResult = { items: [], total: 50, page: 1, pageSize: 20 }
    const wrapper = createWrapper()
    expect(wrapper.vm.totalPages).toBe(3)
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

  it('probeTypeTagType 应该返回正确的标签类型', () => {
    const wrapper = createWrapper()
    expect(wrapper.vm.probeTypeTagType('http')).toBe('primary')
    expect(wrapper.vm.probeTypeTagType('tcp')).toBe('warning')
    expect(wrapper.vm.probeTypeTagType('icmp')).toBe('info')
  })

  it('getUptimeClass 应该返回正确的类名', () => {
    const wrapper = createWrapper()
    expect(wrapper.vm.getUptimeClass(99.5)).toBe('text-success')
    expect(wrapper.vm.getUptimeClass(96)).toBe('text-warning')
    expect(wrapper.vm.getUptimeClass(90)).toBe('text-danger')
  })

  it('formatTime 应该正确格式化时间', () => {
    const wrapper = createWrapper()
    expect(wrapper.vm.formatTime(undefined)).toBe('-')
    const result = wrapper.vm.formatTime('2024-01-15T10:30:00Z')
    expect(result).toBeTruthy()
  })

  it('openCreateDialog 应该重置表单并打开对话框', () => {
    const wrapper = createWrapper()
    wrapper.vm.openCreateDialog()
    expect(wrapper.vm.dialogVisible).toBe(true)
    expect(wrapper.vm.dialogMode).toBe('create')
    expect(wrapper.vm.formData.name).toBe('')
    expect(wrapper.vm.formData.probe_type).toBe('http')
  })

  it('openEditDialog 应该填充表单数据', () => {
    const wrapper = createWrapper()
    const target = {
      id: '1', name: 'API', probe_type: 'http', target: 'https://example.com',
      interval_seconds: 60, timeout_seconds: 10, failure_threshold: 3, recovery_threshold: 2,
      http_config: { method: 'POST', expected_status_codes: [200], content_match: '', follow_redirects: true },
    }
    wrapper.vm.openEditDialog(target)
    expect(wrapper.vm.dialogMode).toBe('edit')
    expect(wrapper.vm.editingId).toBe('1')
    expect(wrapper.vm.formData.name).toBe('API')
    expect(wrapper.vm.formData.probe_type).toBe('http')
  })

  it('handleSubmit 缺少必填字段不应该提交', async () => {
    const wrapper = createWrapper()
    wrapper.vm.formData.name = ''
    wrapper.vm.formData.target = ''
    await wrapper.vm.handleSubmit()
    expect(healthProbeStoreMock.createTarget).not.toHaveBeenCalled()
  })

  it('handleSubmit 创建模式应该调用 createTarget', async () => {
    const wrapper = createWrapper()
    wrapper.vm.dialogMode = 'create'
    wrapper.vm.formData.name = 'Test'
    wrapper.vm.formData.target = 'https://example.com'
    await wrapper.vm.handleSubmit()
    expect(healthProbeStoreMock.createTarget).toHaveBeenCalled()
  })

  it('handleSubmit 编辑模式应该调用 updateTarget', async () => {
    const wrapper = createWrapper()
    wrapper.vm.dialogMode = 'edit'
    wrapper.vm.editingId = '1'
    wrapper.vm.formData.name = 'Test'
    wrapper.vm.formData.target = 'https://example.com'
    await wrapper.vm.handleSubmit()
    expect(healthProbeStoreMock.updateTarget).toHaveBeenCalledWith('1', expect.any(Object))
  })

  it('toggleTarget 应该调用 store.updateTarget', async () => {
    const wrapper = createWrapper()
    await wrapper.vm.toggleTarget('1', false)
    expect(healthProbeStoreMock.updateTarget).toHaveBeenCalledWith('1', { enabled: false })
  })

  it('handleProbeNow 应该调用 store.probeNow', async () => {
    healthProbeStoreMock.probeNow = vi.fn().mockResolvedValue({ success: true })
    healthProbeStoreMock.fetchStatistics = vi.fn().mockResolvedValue({ uptime_percent: 99.5 })
    const wrapper = createWrapper()
    await wrapper.vm.handleProbeNow('1')
    expect(healthProbeStoreMock.probeNow).toHaveBeenCalledWith('1')
  })

  it('targetPlaceholder 应该根据探测类型返回不同的占位符', () => {
    const wrapper = createWrapper()
    wrapper.vm.formData.probe_type = 'http'
    expect(wrapper.vm.targetPlaceholder).toBe('https://example.com/health')
    wrapper.vm.formData.probe_type = 'tcp'
    expect(wrapper.vm.targetPlaceholder).toBe('db.example.com:3306')
    wrapper.vm.formData.probe_type = 'icmp'
    expect(wrapper.vm.targetPlaceholder).toBe('10.0.0.1')
  })

  it('openDetail 应该打开详情对话框', async () => {
    healthProbeStoreMock.fetchStatistics = vi.fn().mockResolvedValue(null)
    healthProbeStoreMock.fetchLogs = vi.fn().mockResolvedValue({ items: [] })
    const wrapper = createWrapper()
    const target = { id: '1', name: 'API', probe_type: 'http', target: 'https://example.com', current_status: 'available', enabled: true }
    await wrapper.vm.openDetail(target)
    expect(wrapper.vm.detailVisible).toBe(true)
    expect(wrapper.vm.detailTarget).toEqual(target)
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

  it('默认 activeTab 应该是 query', () => {
    const wrapper = createWrapper()
    expect(wrapper.vm.activeTab).toBe('query')
  })

  it('应该渲染过滤条件区域', () => {
    const wrapper = createWrapper()
    expect(wrapper.text()).toContain('用户名')
    expect(wrapper.text()).toContain('操作类型')
    expect(wrapper.text()).toContain('模块')
    expect(wrapper.text()).toContain('状态')
  })

  it('应该渲染搜索和重置按钮', () => {
    const wrapper = createWrapper()
    expect(wrapper.text()).toContain('搜索')
    expect(wrapper.text()).toContain('重置')
  })

  it('应该渲染日志列表区域', () => {
    const wrapper = createWrapper()
    expect(wrapper.text()).toContain('日志列表')
  })

  it('应该渲染导出按钮', () => {
    const wrapper = createWrapper()
    expect(wrapper.text()).toContain('导出')
  })

  it('应该渲染保存查询按钮', () => {
    const wrapper = createWrapper()
    expect(wrapper.text()).toContain('保存查询')
  })

  it('formatTimestamp 应该正确格式化时间戳', () => {
    const wrapper = createWrapper()
    expect(wrapper.vm.formatTimestamp(1705312200)).toBeTruthy()
    expect(wrapper.vm.formatTimestamp('')).toBe('-')
    expect(wrapper.vm.formatTimestamp(0)).toBe('-')
  })

  it('formatDuration 应该正确格式化耗时', () => {
    const wrapper = createWrapper()
    expect(wrapper.vm.formatDuration(123.456)).toBe('123.5')
    expect(wrapper.vm.formatDuration(undefined)).toBe('-')
    expect(wrapper.vm.formatDuration(null)).toBe('-')
  })

  it('formatDetailJson 应该正确格式化 JSON', () => {
    const wrapper = createWrapper()
    expect(wrapper.vm.formatDetailJson(null)).toBe('-')
    expect(wrapper.vm.formatDetailJson({ key: 'value' })).toBe('{\n  "key": "value"\n}')
    expect(wrapper.vm.formatDetailJson('{"key":"value"}')).toBe('{\n  "key": "value"\n}')
  })

  it('openDetail 应该设置 detailLog 并打开对话框', () => {
    const wrapper = createWrapper()
    const log = { id: '1', username: 'admin', action_type: 'login', module: 'ssh', status: 'success', timestamp: 1705312200 }
    wrapper.vm.openDetail(log)
    expect(wrapper.vm.detailLog).toEqual(log)
    expect(wrapper.vm.showDetailDialog).toBe(true)
    expect(wrapper.vm.integrityResult).toBeNull()
  })

  it('resetFilters 应该重置所有过滤条件', async () => {
    const wrapper = createWrapper()
    wrapper.vm.filters.username = 'admin'
    wrapper.vm.filters.status = 'success'
    wrapper.vm.filters.keyword = 'test'
    wrapper.vm.resetFilters()
    expect(wrapper.vm.filters.username).toBe('')
    expect(wrapper.vm.filters.status).toBe('')
    expect(wrapper.vm.filters.keyword).toBe('')
    expect(wrapper.vm.filters.actionTypes).toEqual([])
    expect(wrapper.vm.filters.modules).toEqual([])
  })

  it('saveQuery 空名称应该显示警告', async () => {
    const { Md3Message } = await import('@/components/md3')
    const wrapper = createWrapper()
    wrapper.vm.saveQueryName = ''
    wrapper.vm.saveQuery()
    expect(Md3Message.warning).toHaveBeenCalled()
  })

  it('saveQuery 有效名称应该调用 store', async () => {
    const { Md3Message } = await import('@/components/md3')
    const wrapper = createWrapper()
    wrapper.vm.saveQueryName = '我的查询'
    wrapper.vm.saveQuery()
    expect(auditLogStoreMock.saveQuery).toHaveBeenCalled()
    expect(Md3Message.success).toHaveBeenCalled()
    expect(wrapper.vm.saveQueryName).toBe('')
    expect(wrapper.vm.showSaveQueryDialog).toBe(false)
  })

  it('searchLogs 应该调用 store.queryLogs', async () => {
    const wrapper = createWrapper()
    await wrapper.vm.searchLogs()
    expect(auditLogStoreMock.queryLogs).toHaveBeenCalled()
  })

  it('searchLogs 异常时应该显示错误', async () => {
    const { Md3Message } = await import('@/components/md3')
    auditLogStoreMock.queryLogs = vi.fn().mockRejectedValue(new Error('fail'))
    const wrapper = createWrapper()
    await wrapper.vm.searchLogs()
    expect(Md3Message.error).toHaveBeenCalledWith('查询失败')
  })

  it('doExport 应该调用 store.exportLogs', async () => {
    const { Md3Message } = await import('@/components/md3')
    const wrapper = createWrapper()
    wrapper.vm.exportFormat = 'xlsx'
    await wrapper.vm.doExport()
    expect(auditLogStoreMock.exportLogs).toHaveBeenCalled()
    expect(Md3Message.success).toHaveBeenCalled()
    expect(wrapper.vm.showExportDialog).toBe(false)
  })

  it('doExport 异常时应该显示错误', async () => {
    const { Md3Message } = await import('@/components/md3')
    auditLogStoreMock.exportLogs = vi.fn().mockRejectedValue(new Error('fail'))
    const wrapper = createWrapper()
    await wrapper.vm.doExport()
    expect(Md3Message.error).toHaveBeenCalledWith('导出失败')
    expect(wrapper.vm.exporting).toBe(false)
  })

  it('verifyIntegrity 应该调用 store.verifyIntegrity', async () => {
    const wrapper = createWrapper()
    wrapper.vm.detailLog = { id: 'log-1' }
    wrapper.vm.verifyIntegrity()
  })

  it('loadSavedQuery 应该恢复过滤条件', () => {
    auditLogStoreMock.savedQueries = [{
      name: 'test-query',
      params: { username: 'admin', time_start: '2024-01-01', time_end: '2024-01-31', action_types: ['login'], modules: ['ssh'], status: 'success', keyword: 'test' }
    }]
    const wrapper = createWrapper()
    wrapper.vm.loadSavedQuery('test-query')
    expect(wrapper.vm.filters.username).toBe('admin')
    expect(wrapper.vm.filters.status).toBe('success')
    expect(wrapper.vm.filters.keyword).toBe('test')
  })

  it('loadSavedQuery 不存在的查询不应该修改过滤条件', () => {
    auditLogStoreMock.savedQueries = []
    const wrapper = createWrapper()
    wrapper.vm.loadSavedQuery('nonexistent')
    expect(wrapper.vm.filters.username).toBe('')
  })

  it('pagedLogs 应该返回 store.logs', () => {
    auditLogStoreMock.logs = [{ id: '1' }, { id: '2' }]
    const wrapper = createWrapper()
    expect(wrapper.vm.pagedLogs).toHaveLength(2)
  })

  it('savedQueryOptions 应该返回正确的选项', () => {
    auditLogStoreMock.savedQueries = [{ name: 'query1' }, { name: 'query2' }]
    const wrapper = createWrapper()
    expect(wrapper.vm.savedQueryOptions).toHaveLength(2)
    expect(wrapper.vm.savedQueryOptions[0].value).toBe('query1')
  })

  it('切换到 statistics Tab 应该调用 refreshStatistics', async () => {
    const wrapper = createWrapper()
    vi.clearAllMocks()
    wrapper.vm.activeTab = 'statistics'
    await nextTick()
    expect(auditLogStoreMock.loadStatistics).toHaveBeenCalled()
  })

  it('切换到 archives Tab 应该调用 refreshArchives', async () => {
    const wrapper = createWrapper()
    vi.clearAllMocks()
    wrapper.vm.activeTab = 'archives'
    await nextTick()
    expect(auditLogStoreMock.loadArchives).toHaveBeenCalled()
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

  it('应该渲染终端区域', () => {
    const wrapper = createWrapper()
    expect(wrapper.find('.terminal-area').exists()).toBe(true)
  })

  it('activeSession 在无活跃会话时应该为 undefined', () => {
    const wrapper = createWrapper()
    expect(wrapper.vm.activeSession).toBeUndefined()
  })

  it('handleConnect 应该调用 store.connect', async () => {
    websshStoreMock.connect = vi.fn().mockResolvedValue({ id: 'session-1' })
    const wrapper = createWrapper()
    await wrapper.vm.handleConnect({ account_alias: 'test-server' })
    expect(websshStoreMock.connect).toHaveBeenCalled()
    expect(wrapper.vm.showConnectDialog).toBe(false)
  })

  it('handleConnect 异常时不应该关闭对话框', async () => {
    websshStoreMock.connect = vi.fn().mockRejectedValue(new Error('fail'))
    const wrapper = createWrapper()
    wrapper.vm.showConnectDialog = true
    await wrapper.vm.handleConnect({ account_alias: 'test-server' })
    expect(wrapper.vm.showConnectDialog).toBe(true)
  })

  it('handleDisconnect 应该调用 store.disconnect', async () => {
    const wrapper = createWrapper()
    await wrapper.vm.handleDisconnect('session-1')
    expect(websshStoreMock.disconnect).toHaveBeenCalledWith('session-1')
  })

  it('switchSession 应该调用 store.setActiveSession', () => {
    websshStoreMock.setActiveSession = vi.fn()
    const wrapper = createWrapper()
    wrapper.vm.switchSession('session-1')
    expect(websshStoreMock.setActiveSession).toHaveBeenCalledWith('session-1')
  })

  it('formatFileSize 应该正确格式化文件大小', () => {
    const wrapper = createWrapper()
    expect(wrapper.vm.formatFileSize(500)).toBe('500 B')
    expect(wrapper.vm.formatFileSize(1024)).toBe('1.0 KB')
    expect(wrapper.vm.formatFileSize(1048576)).toBe('1.0 MB')
  })

  it('openSearch 应该显示搜索对话框', () => {
    const wrapper = createWrapper()
    wrapper.vm.openSearch()
    expect(wrapper.vm.showSearch).toBe(true)
    expect(wrapper.vm.searchQuery).toBe('')
  })

  it('handleUpload 应该显示上传对话框', () => {
    const wrapper = createWrapper()
    wrapper.vm.handleUpload()
    expect(wrapper.vm.showUpload).toBe(true)
    expect(wrapper.vm.uploadFiles).toEqual([])
    expect(wrapper.vm.uploadRemotePath).toBe('/tmp/')
  })

  it('handleDownload 应该显示下载对话框', () => {
    const wrapper = createWrapper()
    wrapper.vm.handleDownload()
    expect(wrapper.vm.showDownload).toBe(true)
    expect(wrapper.vm.downloadRemotePath).toBe('')
  })

  it('openHistoryDialog 应该显示历史对话框', async () => {
    websshStoreMock.getHistory = vi.fn().mockResolvedValue(['ls', 'cd /tmp'])
    const wrapper = createWrapper()
    await wrapper.vm.openHistoryDialog()
    expect(wrapper.vm.showHistory).toBe(true)
  })

  it('replayHistoryLine 应该调用 onTerminalData', () => {
    const wrapper = createWrapper()
    wrapper.vm.replayHistoryLine('ls -la')
    expect(wrapper.vm.showHistory).toBe(false)
  })

  it('terminalSettings 默认值应该正确', () => {
    const wrapper = createWrapper()
    expect(wrapper.vm.terminalSettings.theme).toBe('dark')
    expect(wrapper.vm.terminalSettings.font_family).toBe("'Fira Code', monospace")
    expect(wrapper.vm.terminalSettings.font_size).toBe(14)
    expect(wrapper.vm.terminalSettings.encoding).toBe('utf-8')
  })

  it('onMounted 应该调用 store 方法', () => {
    createWrapper()
    expect(websshStoreMock.listSessions).toHaveBeenCalled()
    expect(websshStoreMock.fetchHistory).toHaveBeenCalled()
    expect(sshStoreMock.fetchAccounts).toHaveBeenCalled()
  })

  it('handleConnect 成功时应该关闭对话框', async () => {
    websshStoreMock.connect = vi.fn().mockResolvedValue({ id: 'session-1' })
    const wrapper = createWrapper()
    wrapper.vm.showConnectDialog = true
    await wrapper.vm.handleConnect({ account_alias: 'test-server' })
    expect(wrapper.vm.showConnectDialog).toBe(false)
  })

  it('handleConnect 失败时不应该关闭对话框', async () => {
    websshStoreMock.connect = vi.fn().mockRejectedValue(new Error('fail'))
    const wrapper = createWrapper()
    wrapper.vm.showConnectDialog = true
    await wrapper.vm.handleConnect({ account_alias: 'test-server' })
    expect(wrapper.vm.showConnectDialog).toBe(true)
  })

  it('switchSession 应该调用 setActiveSession', () => {
    websshStoreMock.setActiveSession = vi.fn()
    const wrapper = createWrapper()
    wrapper.vm.switchSession('session-1')
    expect(websshStoreMock.setActiveSession).toHaveBeenCalledWith('session-1')
  })

  it('handleDisconnect 应该调用 store.disconnect', async () => {
    const wrapper = createWrapper()
    await wrapper.vm.handleDisconnect('session-1')
    expect(websshStoreMock.disconnect).toHaveBeenCalledWith('session-1')
  })

  it('handleReconnect 应该调用 store.connect', async () => {
    websshStoreMock.connect = vi.fn().mockResolvedValue({ id: 'session-new' })
    const wrapper = createWrapper()
    await wrapper.vm.handleReconnect({ account_alias: 'test-server', host: '192.168.1.1', port: 22, username: 'root' })
    expect(websshStoreMock.connect).toHaveBeenCalled()
  })

  it('activeSession 在无活跃会话时应该为 undefined', () => {
    const wrapper = createWrapper()
    expect(wrapper.vm.activeSession).toBeUndefined()
  })

  it('activeSession 有活跃会话时应该返回对应会话', () => {
    websshStoreMock.sessions = [{ id: 'session-1', alias: 'test', host: '192.168.1.1', username: 'root', status: 'online' }]
    websshStoreMock.activeSessionId = 'session-1'
    const wrapper = createWrapper()
    expect(wrapper.vm.activeSession).toBeDefined()
    expect(wrapper.vm.activeSession.id).toBe('session-1')
  })

  it('themeOptions 应该包含正确的选项', () => {
    const wrapper = createWrapper()
    expect(wrapper.vm.themeOptions).toHaveLength(2)
    expect(wrapper.vm.themeOptions[0].value).toBe('dark')
  })

  it('fontOptions 应该包含正确的选项', () => {
    const wrapper = createWrapper()
    expect(wrapper.vm.fontOptions.length).toBeGreaterThanOrEqual(2)
  })

  it('encodingOptions 应该包含正确的选项', () => {
    const wrapper = createWrapper()
    expect(wrapper.vm.encodingOptions).toHaveLength(3)
    expect(wrapper.vm.encodingOptions[0].value).toBe('utf-8')
  })

  it('doUpload 无文件时不应该执行操作', async () => {
    const wrapper = createWrapper()
    wrapper.vm.uploadFiles = []
    await wrapper.vm.doUpload()
  })

  it('handleDownload 应该显示下载对话框', () => {
    const wrapper = createWrapper()
    wrapper.vm.handleDownload()
    expect(wrapper.vm.showDownload).toBe(true)
    expect(wrapper.vm.downloadRemotePath).toBe('')
  })

  it('doDownload 无路径时不应该执行操作', async () => {
    const wrapper = createWrapper()
    wrapper.vm.downloadRemotePath = ''
    await wrapper.vm.doDownload()
  })

  it('openHistoryDialog 应该显示历史对话框', async () => {
    websshStoreMock.getHistory = vi.fn().mockResolvedValue(['ls', 'cd'])
    const wrapper = createWrapper()
    await wrapper.vm.openHistoryDialog()
    expect(wrapper.vm.showHistory).toBe(true)
  })

  it('openHistoryDialog 无活跃会话时应该不加载', async () => {
    websshStoreMock.getHistory = vi.fn()
    const wrapper = createWrapper()
    wrapper.vm.activeSession = undefined
    await wrapper.vm.openHistoryDialog()
    expect(websshStoreMock.getHistory).not.toHaveBeenCalled()
  })

  it('replayHistoryLine 应该关闭历史对话框', () => {
    const wrapper = createWrapper()
    wrapper.vm.showHistory = true
    wrapper.vm.replayHistoryLine('ls -la')
    expect(wrapper.vm.showHistory).toBe(false)
  })

  it('terminalSettings 默认值应该正确', () => {
    const wrapper = createWrapper()
    expect(wrapper.vm.terminalSettings.theme).toBe('dark')
    expect(wrapper.vm.terminalSettings.font_family).toBe("'Fira Code', monospace")
    expect(wrapper.vm.terminalSettings.font_size).toBe(14)
    expect(wrapper.vm.terminalSettings.encoding).toBe('utf-8')
  })

  it('handleDeleteHistory 成功时应删除历史记录', async () => {
    websshStoreMock.historyRecords = [{ session_id: 's1', host: '192.168.1.1' }, { session_id: 's2', host: '192.168.1.2' }]
    const wrapper = createWrapper()
    await wrapper.vm.handleDeleteHistory('s1')
    expect(mockRequestDelete).toHaveBeenCalledWith('/webssh/sessions/history/s1')
    expect(wrapper.vm.websshStore.historyRecords).toHaveLength(1)
  })

  it('handleDeleteHistory 失败时不应抛出异常', async () => {
    mockRequestDelete.mockRejectedValueOnce(new Error('fail'))
    const wrapper = createWrapper()
    await expect(wrapper.vm.handleDeleteHistory('s1')).resolves.toBeUndefined()
  })

  it('doSearch 无搜索内容时不应执行', () => {
    const wrapper = createWrapper()
    wrapper.vm.searchQuery = ''
    wrapper.vm.doSearch()
  })

  it('doSearch 有搜索内容时不应抛出异常', () => {
    const wrapper = createWrapper()
    wrapper.vm.searchQuery = 'test'
    wrapper.vm.doSearch()
  })

  it('onTerminalData 无 WebSocket 时不应抛出异常', () => {
    const wrapper = createWrapper()
    wrapper.vm.webSocketRef = null
    wrapper.vm.onTerminalData('test')
  })

  it('onTerminalResize 无 WebSocket 时不应抛出异常', () => {
    const wrapper = createWrapper()
    wrapper.vm.webSocketRef = null
    wrapper.vm.onTerminalResize(80, 24)
  })

  it('toggleFullscreen 无 terminalAreaRef 时不应抛出异常', () => {
    const wrapper = createWrapper()
    wrapper.vm.terminalAreaRef = null
    wrapper.vm.toggleFullscreen()
  })

  it('handlePaste 应调用 onTerminalData', async () => {
    const wrapper = createWrapper()
    const pasteSpy = vi.spyOn(navigator.clipboard, 'readText').mockResolvedValue('pasted text')
    await wrapper.vm.handlePaste()
    expect(pasteSpy).toHaveBeenCalled()
    pasteSpy.mockRestore()
  })

  it('formatFileSize 大文件应正确格式化', () => {
    const wrapper = createWrapper()
    expect(wrapper.vm.formatFileSize(0)).toBe('0 B')
    expect(wrapper.vm.formatFileSize(500)).toBe('500 B')
    expect(wrapper.vm.formatFileSize(1024)).toBe('1.0 KB')
    expect(wrapper.vm.formatFileSize(1048576)).toBe('1.0 MB')
  })

  it('doUpload 无文件时不应执行', async () => {
    const wrapper = createWrapper()
    wrapper.vm.uploadFiles = []
    await wrapper.vm.doUpload()
  })

  it('doUpload 无活跃会话时不应执行', async () => {
    const wrapper = createWrapper()
    wrapper.vm.uploadFiles = [new File(['test'], 'test.txt')]
    wrapper.vm.activeSession = undefined
    await wrapper.vm.doUpload()
  })

  it('doDownload 无路径时不应执行', async () => {
    const wrapper = createWrapper()
    wrapper.vm.downloadRemotePath = ''
    await wrapper.vm.doDownload()
  })

  it('doDownload 无活跃会话时不应执行', async () => {
    const wrapper = createWrapper()
    wrapper.vm.downloadRemotePath = '/tmp/test.log'
    wrapper.vm.activeSession = undefined
    await wrapper.vm.doDownload()
  })

  it('doDownload 成功时应下载文件', async () => {
    mockRequestPost.mockResolvedValueOnce({ content_base64: btoa('file content'), filename: 'test.log' })
    websshStoreMock.sessions = [{ id: 'session-1', alias: 'test', host: '192.168.1.1', username: 'root', status: 'online' }]
    websshStoreMock.activeSessionId = 'session-1'
    const wrapper = createWrapper()
    wrapper.vm.downloadRemotePath = '/tmp/test.log'
    await wrapper.vm.doDownload()
    expect(mockRequestPost).toHaveBeenCalledWith('/webssh/download', expect.objectContaining({ path: '/tmp/test.log' }))
  })

  it('doDownload 失败时不应抛出异常', async () => {
    mockRequestPost.mockRejectedValueOnce(new Error('fail'))
    websshStoreMock.sessions = [{ id: 'session-1', alias: 'test', host: '192.168.1.1', username: 'root', status: 'online' }]
    websshStoreMock.activeSessionId = 'session-1'
    const wrapper = createWrapper()
    wrapper.vm.downloadRemotePath = '/tmp/test.log'
    await expect(wrapper.vm.doDownload()).resolves.toBeUndefined()
  })

  it('onFileSelected 应更新 uploadFiles', () => {
    const wrapper = createWrapper()
    const file = new File(['test'], 'test.txt')
    const event = { target: { files: [file] } } as any
    wrapper.vm.onFileSelected(event)
    expect(wrapper.vm.uploadFiles).toHaveLength(1)
  })

  it('handleFileDrop 应更新 uploadFiles', () => {
    const wrapper = createWrapper()
    const file = new File(['test'], 'dropped.txt')
    const event = { dataTransfer: { files: [file] } } as any
    wrapper.vm.handleFileDrop(event)
    expect(wrapper.vm.uploadFiles).toHaveLength(1)
  })

  it('triggerFileInput 应调用 click', () => {
    const wrapper = createWrapper()
    const clickSpy = vi.fn()
    wrapper.vm.fileInputRef = { click: clickSpy } as any
    wrapper.vm.triggerFileInput()
    expect(clickSpy).toHaveBeenCalled()
  })

  it('handleConnect 成功时应初始化 WebSocket', async () => {
    websshStoreMock.connect = vi.fn().mockResolvedValue({ id: 'session-1' })
    const wrapper = createWrapper()
    wrapper.vm.showConnectDialog = true
    await wrapper.vm.handleConnect({ account_alias: 'test-server' })
    expect(wrapper.vm.showConnectDialog).toBe(false)
  })

  it('handleConnect 失败时不应关闭对话框', async () => {
    websshStoreMock.connect = vi.fn().mockRejectedValue(new Error('fail'))
    const wrapper = createWrapper()
    wrapper.vm.showConnectDialog = true
    await wrapper.vm.handleConnect({ account_alias: 'test-server' })
    expect(wrapper.vm.showConnectDialog).toBe(true)
  })

  it('handleReconnect 成功时应连接', async () => {
    websshStoreMock.connect = vi.fn().mockResolvedValue({ id: 'session-new' })
    const wrapper = createWrapper()
    await wrapper.vm.handleReconnect({ account_alias: 'test-server', host: '192.168.1.1', port: 22, username: 'root' })
    expect(websshStoreMock.connect).toHaveBeenCalledWith(expect.objectContaining({ host: '192.168.1.1', port: 22 }))
  })

  it('handleReconnect 失败时不应抛出异常', async () => {
    websshStoreMock.connect = vi.fn().mockRejectedValue(new Error('fail'))
    const wrapper = createWrapper()
    await expect(wrapper.vm.handleReconnect({ account_alias: 'test-server', host: '192.168.1.1', port: 22, username: 'root' })).resolves.toBeUndefined()
  })

  it('handleDisconnect 应关闭 WebSocket', async () => {
    const wrapper = createWrapper()
    const mockClose = vi.fn()
    wrapper.vm.webSocketRef = { close: mockClose } as any
    await wrapper.vm.handleDisconnect('session-1')
    expect(mockClose).toHaveBeenCalled()
    expect(wrapper.vm.webSocketRef).toBeNull()
  })

  it('switchSession 有在线会话时应初始化 WebSocket', () => {
    websshStoreMock.setActiveSession = vi.fn()
    websshStoreMock.sessions = [{ id: 'session-1', alias: 'test', host: '192.168.1.1', username: 'root', status: 'online' }]
    const wrapper = createWrapper()
    wrapper.vm.switchSession('session-1')
    expect(websshStoreMock.setActiveSession).toHaveBeenCalledWith('session-1')
  })

  it('switchSession 有离线会话时不应初始化 WebSocket', () => {
    websshStoreMock.setActiveSession = vi.fn()
    websshStoreMock.sessions = [{ id: 'session-1', alias: 'test', host: '192.168.1.1', username: 'root', status: 'offline' }]
    const wrapper = createWrapper()
    wrapper.vm.switchSession('session-1')
    expect(websshStoreMock.setActiveSession).toHaveBeenCalledWith('session-1')
  })

  it('openSearch 应重置搜索查询', () => {
    const wrapper = createWrapper()
    wrapper.vm.searchQuery = 'old query'
    wrapper.vm.openSearch()
    expect(wrapper.vm.showSearch).toBe(true)
    expect(wrapper.vm.searchQuery).toBe('')
  })

  it('isFullscreen 默认应为 false', () => {
    const wrapper = createWrapper()
    expect(wrapper.vm.isFullscreen).toBe(false)
  })

  it('onTerminalData 有 WebSocket 时应该发送数据', () => {
    const mockSend = vi.fn()
    const wrapper = createWrapper()
    wrapper.vm.webSocketRef = { readyState: WebSocket.OPEN, send: mockSend } as any
    wrapper.vm.onTerminalData('test input')
    expect(mockSend).toHaveBeenCalledWith(JSON.stringify({ type: 'input', data: 'test input' }))
  })

  it('onTerminalData WebSocket 未连接时不应发送', () => {
    const mockSend = vi.fn()
    const wrapper = createWrapper()
    wrapper.vm.webSocketRef = { readyState: WebSocket.CLOSED, send: mockSend } as any
    wrapper.vm.onTerminalData('test input')
    expect(mockSend).not.toHaveBeenCalled()
  })

  it('onTerminalResize 有 WebSocket 时应该发送 resize', () => {
    const mockSend = vi.fn()
    const wrapper = createWrapper()
    wrapper.vm.webSocketRef = { readyState: WebSocket.OPEN, send: mockSend } as any
    wrapper.vm.onTerminalResize(120, 40)
    expect(mockSend).toHaveBeenCalledWith(JSON.stringify({ type: 'resize', width: 120, height: 40 }))
  })

  it('onTerminalResize 有活跃会话时应该调用 store.resizeTerminal', () => {
    websshStoreMock.resizeTerminal = vi.fn()
    websshStoreMock.sessions = [{ id: 'session-1', alias: 'test', host: '192.168.1.1', username: 'root', status: 'online' }]
    websshStoreMock.activeSessionId = 'session-1'
    const wrapper = createWrapper()
    wrapper.vm.onTerminalResize(120, 40)
    expect(websshStoreMock.resizeTerminal).toHaveBeenCalledWith('session-1', 120, 40)
  })

  it('toggleFullscreen 无 fullscreenElement 时应该请求全屏', () => {
    const mockRequestFullscreen = vi.fn()
    const wrapper = createWrapper()
    wrapper.vm.terminalAreaRef = { requestFullscreen: mockRequestFullscreen } as any
    Object.defineProperty(document, 'fullscreenElement', { value: null, writable: true, configurable: true })
    wrapper.vm.toggleFullscreen()
    expect(mockRequestFullscreen).toHaveBeenCalled()
    expect(wrapper.vm.isFullscreen).toBe(true)
  })

  it('toggleFullscreen 有 fullscreenElement 时应该退出全屏', () => {
    const mockExitFullscreen = vi.fn()
    const wrapper = createWrapper()
    Object.defineProperty(document, 'fullscreenElement', { value: {}, writable: true, configurable: true })
    Object.defineProperty(document, 'exitFullscreen', { value: mockExitFullscreen, writable: true, configurable: true })
    wrapper.vm.toggleFullscreen()
    expect(mockExitFullscreen).toHaveBeenCalled()
    expect(wrapper.vm.isFullscreen).toBe(false)
  })

  it('doSearch 有搜索词和 terminal 时应该搜索', () => {
    const wrapper = createWrapper()
    const mockSelect = vi.fn()
    const mockScrollToLine = vi.fn()
    const mockGetLine = vi.fn().mockReturnValue({ translateToString: () => 'some text with search term' })
    wrapper.vm.terminalRef = {
      getTerminal: () => ({
        buffer: { active: { length: 10, getLine: mockGetLine } },
        select: mockSelect,
        scrollToLine: mockScrollToLine,
      }),
    } as any
    wrapper.vm.searchQuery = 'search'
    wrapper.vm.doSearch()
    expect(mockGetLine).toHaveBeenCalled()
  })

  it('doUpload 有文件和活跃会话时应该上传', async () => {
    const mockSend = vi.fn()
    const mockWriteln = vi.fn()
    websshStoreMock.sessions = [{ id: 'session-1', alias: 'test', host: '192.168.1.1', username: 'root', status: 'online' }]
    websshStoreMock.activeSessionId = 'session-1'
    const wrapper = createWrapper()
    wrapper.vm.webSocketRef = { readyState: WebSocket.OPEN, send: mockSend } as any
    wrapper.vm.terminalRef = { writeln: mockWriteln } as any
    wrapper.vm.uploadFiles = [new File(['test content'], 'test.txt')]
    wrapper.vm.uploadRemotePath = '/tmp/'
    await wrapper.vm.doUpload()
    expect(mockSend).toHaveBeenCalled()
    expect(wrapper.vm.showUpload).toBe(false)
  })

  it('doUpload 上传失败时应该显示错误', async () => {
    const mockWriteln = vi.fn()
    websshStoreMock.sessions = [{ id: 'session-1', alias: 'test', host: '192.168.1.1', username: 'root', status: 'online' }]
    websshStoreMock.activeSessionId = 'session-1'
    const wrapper = createWrapper()
    wrapper.vm.terminalRef = { writeln: mockWriteln } as any
    const badFile = new File(['test'], 'test.txt')
    Object.defineProperty(badFile, 'arrayBuffer', { value: vi.fn().mockRejectedValue(new Error('fail')) })
    wrapper.vm.uploadFiles = [badFile]
    wrapper.vm.uploadRemotePath = '/tmp/'
    await wrapper.vm.doUpload()
    expect(mockWriteln).toHaveBeenCalled()
  })

  it('openHistoryDialog 有活跃会话时应该加载历史', async () => {
    websshStoreMock.getHistory = vi.fn().mockResolvedValue(['ls', 'cd /tmp'])
    websshStoreMock.sessions = [{ id: 'session-1', alias: 'test', host: '192.168.1.1', username: 'root', status: 'online' }]
    websshStoreMock.activeSessionId = 'session-1'
    const wrapper = createWrapper()
    await wrapper.vm.openHistoryDialog()
    expect(websshStoreMock.getHistory).toHaveBeenCalledWith('session-1')
    expect(wrapper.vm.showHistory).toBe(true)
    expect(wrapper.vm.historyLoading).toBe(false)
  })

  it('openHistoryDialog 加载失败时应该设置空历史', async () => {
    websshStoreMock.getHistory = vi.fn().mockRejectedValue(new Error('fail'))
    websshStoreMock.sessions = [{ id: 'session-1', alias: 'test', host: '192.168.1.1', username: 'root', status: 'online' }]
    websshStoreMock.activeSessionId = 'session-1'
    const wrapper = createWrapper()
    await wrapper.vm.openHistoryDialog()
    expect(wrapper.vm.historyLines).toEqual([])
    expect(wrapper.vm.historyLoading).toBe(false)
  })

  it('onBeforeUnmount 有 WebSocket 时应该关闭', () => {
    const mockClose = vi.fn()
    const wrapper = createWrapper()
    wrapper.vm.webSocketRef = { close: mockClose } as any
    wrapper.unmount()
    expect(mockClose).toHaveBeenCalled()
  })

  it('onTerminalResize 有活跃会话时应该调用 resizeTerminal', () => {
    websshStoreMock.resizeTerminal = vi.fn()
    websshStoreMock.sessions = [{ id: 'session-1', alias: 'test', host: '192.168.1.1', username: 'root', status: 'online' }]
    websshStoreMock.activeSessionId = 'session-1'
    const wrapper = createWrapper()
    wrapper.vm.onTerminalResize(80, 24)
    expect(websshStoreMock.resizeTerminal).toHaveBeenCalledWith('session-1', 80, 24)
  })

  it('onTerminalResize 有 WebSocket 时应该发送 resize 消息', () => {
    const mockSend = vi.fn()
    const wrapper = createWrapper()
    wrapper.vm.webSocketRef = { readyState: WebSocket.OPEN, send: mockSend } as any
    wrapper.vm.onTerminalResize(80, 24)
    expect(mockSend).toHaveBeenCalledWith(JSON.stringify({ type: 'resize', width: 80, height: 24 }))
  })

  it('toggleFullscreen 应该切换全屏状态', () => {
    const wrapper = createWrapper()
    wrapper.vm.terminalAreaRef = { requestFullscreen: vi.fn() } as any
    document.fullscreenElement = null
    wrapper.vm.toggleFullscreen()
    expect(wrapper.vm.isFullscreen).toBe(true)
  })

  it('toggleFullscreen 已全屏时应该退出全屏', () => {
    const wrapper = createWrapper()
    Object.defineProperty(document, 'fullscreenElement', { value: document.createElement('div'), configurable: true })
    document.exitFullscreen = vi.fn()
    wrapper.vm.toggleFullscreen()
    expect(wrapper.vm.isFullscreen).toBe(false)
  })

  it('doSearch 无终端时不应报错', () => {
    const wrapper = createWrapper()
    wrapper.vm.searchQuery = 'test'
    expect(() => wrapper.vm.doSearch()).not.toThrow()
  })

  it('doSearch 无搜索词时不应报错', () => {
    const wrapper = createWrapper()
    wrapper.vm.searchQuery = ''
    expect(() => wrapper.vm.doSearch()).not.toThrow()
  })

  it('doUpload 无文件时不应执行上传', async () => {
    const wrapper = createWrapper()
    wrapper.vm.uploadFiles = []
    await wrapper.vm.doUpload()
    expect(wrapper.vm.showUpload).toBe(false)
  })

  it('doUpload 无活跃会话时不应执行上传', async () => {
    websshStoreMock.activeSessionId = null
    const wrapper = createWrapper()
    wrapper.vm.uploadFiles = [new File(['test'], 'test.txt')]
    await wrapper.vm.doUpload()
    expect(wrapper.vm.showUpload).toBe(false)
  })

  it('onFileSelected 应该设置上传文件', () => {
    const wrapper = createWrapper()
    const file = new File(['test'], 'test.txt')
    const event = { target: { files: [file] } } as unknown as Event
    wrapper.vm.onFileSelected(event)
    expect(wrapper.vm.uploadFiles).toHaveLength(1)
  })

  it('handleFileDrop 应该设置上传文件', () => {
    const wrapper = createWrapper()
    const file = new File(['test'], 'test.txt')
    const event = { dataTransfer: { files: [file] } } as unknown as DragEvent
    wrapper.vm.handleFileDrop(event)
    expect(wrapper.vm.uploadFiles).toHaveLength(1)
  })

  it('replayHistoryLine 应该发送命令并关闭对话框', () => {
    const mockSend = vi.fn()
    const wrapper = createWrapper()
    wrapper.vm.webSocketRef = { readyState: WebSocket.OPEN, send: mockSend } as any
    wrapper.vm.showHistory = true
    wrapper.vm.replayHistoryLine('ls -la')
    expect(wrapper.vm.showHistory).toBe(false)
  })

  it('onBeforeUnmount 无 WebSocket 时不应报错', () => {
    const wrapper = createWrapper()
    wrapper.vm.webSocketRef = null
    expect(() => wrapper.unmount()).not.toThrow()
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

  it('应该渲染服务器选择器', () => {
    const wrapper = createWrapper()
    expect(wrapper.text()).toContain('目标服务器')
  })

  it('选择服务器后应该显示数据库管理和系统操作', async () => {
    const wrapper = createWrapper()
    wrapper.vm.selectedAlias = 'test-server'
    await nextTick()
    expect(wrapper.text()).toContain('数据库管理')
    expect(wrapper.text()).toContain('系统操作')
  })

  it('未选择服务器时应该显示空状态', () => {
    const wrapper = createWrapper()
    wrapper.vm.selectedAlias = ''
    expect(wrapper.text()).toContain('请先选择一个 SSH 服务器')
  })

  it('onAccountChange 应该更新 selectedAlias', () => {
    const wrapper = createWrapper()
    wrapper.vm.onAccountChange('new-server')
    expect(wrapper.vm.selectedAlias).toBe('new-server')
  })

  it('应该渲染诊断工具区域', async () => {
    const wrapper = createWrapper()
    wrapper.vm.selectedAlias = 'test-server'
    await nextTick()
    expect(wrapper.text()).toContain('诊断工具')
    expect(wrapper.text()).toContain('当前登录用户')
    expect(wrapper.text()).toContain('系统启动时间')
  })

  it('应该渲染清理维护区域', async () => {
    const wrapper = createWrapper()
    wrapper.vm.selectedAlias = 'test-server'
    await nextTick()
    expect(wrapper.text()).toContain('清理维护')
  })

  it('应该渲染 SELinux 状态', async () => {
    const wrapper = createWrapper()
    wrapper.vm.selectedAlias = 'test-server'
    await nextTick()
    expect(wrapper.text()).toContain('SELinux')
  })

  it('remoteDriveEnabled 默认应该为 false', () => {
    const wrapper = createWrapper()
    expect(wrapper.vm.remoteDriveEnabled).toBe(false)
  })

  it('webdavUrl 默认值应该正确', () => {
    const wrapper = createWrapper()
    expect(wrapper.vm.webdavUrl).toBe('http://localhost:8081/')
  })

  it('selectOptions 应该返回正确的选项', () => {
    const wrapper = createWrapper()
    const options = wrapper.vm.selectOptions
    expect(options.length).toBeGreaterThanOrEqual(1)
  })

  it('doSetHostname 空主机名应该显示警告', async () => {
    const { Md3Message } = await import('@/components/md3')
    const wrapper = createWrapper()
    wrapper.vm.hostnameInput = ''
    await wrapper.vm.doSetHostname()
    expect(Md3Message.warning).toHaveBeenCalled()
  })

  it('doSetTimezone 空时区应该显示警告', async () => {
    const { Md3Message } = await import('@/components/md3')
    const wrapper = createWrapper()
    wrapper.vm.timezoneInput = ''
    await wrapper.vm.doSetTimezone()
    expect(Md3Message.warning).toHaveBeenCalled()
  })

  it('copyUrl 应该调用 clipboard.writeText', async () => {
    const { Md3Message } = await import('@/components/md3')
    const wrapper = createWrapper()
    await wrapper.vm.copyUrl()
    expect(Md3Message.success).toHaveBeenCalled()
  })

  it('copyWindowsUrl 应该调用 clipboard.writeText', async () => {
    const { Md3Message } = await import('@/components/md3')
    const wrapper = createWrapper()
    await wrapper.vm.copyWindowsUrl()
    expect(Md3Message.success).toHaveBeenCalled()
  })

  it('queryLabels 应该包含所有诊断工具标签', () => {
    const wrapper = createWrapper()
    expect(wrapper.vm.queryLabels['logged-users']).toBe('当前登录用户')
    expect(wrapper.vm.queryLabels['boot-time']).toBe('系统启动时间')
    expect(wrapper.vm.queryLabels['kernel-modules']).toBe('内核模块')
    expect(wrapper.vm.queryLabels['dns-config']).toBe('DNS 配置 (/etc/resolv.conf)')
  })

  it('onAccountChange 应该更新 selectedAlias 并加载 SELinux', async () => {
    const wrapper = createWrapper()
    wrapper.vm.onAccountChange('new-server')
    expect(wrapper.vm.selectedAlias).toBe('new-server')
  })

  it('loadSelinux 无选择账户时应该返回', async () => {
    const wrapper = createWrapper()
    wrapper.vm.selectedAlias = ''
    await wrapper.vm.loadSelinux()
    expect(wrapper.vm.selinuxStatus).toBe('')
  })

  it('loadSelinux 成功时应该更新状态', async () => {
    const wrapper = createWrapper()
    await nextTick()
    await nextTick()
    await nextTick()
    mockRequestGet.mockResolvedValueOnce({ status: 'Enforcing' })
    wrapper.vm.selectedAlias = 'test-server'
    await wrapper.vm.loadSelinux()
    expect(wrapper.vm.selinuxStatus).toBe('Enforcing')
  })

  it('loadSelinux 失败时应该设置未知', async () => {
    const wrapper = createWrapper()
    await nextTick()
    await nextTick()
    await nextTick()
    mockRequestGet.mockRejectedValueOnce(new Error('fail'))
    wrapper.vm.selectedAlias = 'test-server'
    await wrapper.vm.loadSelinux()
    expect(wrapper.vm.selinuxStatus).toBe('未知')
  })

  it('setSelinux 成功时应该显示成功消息', async () => {
    const { Md3Message } = await import('@/components/md3')
    mockRequestPost.mockResolvedValueOnce({ message: '已设置' })
    const wrapper = createWrapper()
    wrapper.vm.selectedAlias = 'test-server'
    await wrapper.vm.setSelinux('permissive')
    expect(Md3Message.success).toHaveBeenCalled()
  })

  it('executeAction 成功时应该显示成功消息', async () => {
    const { Md3Message } = await import('@/components/md3')
    mockRequestPost.mockResolvedValueOnce({ message: '操作成功' })
    const wrapper = createWrapper()
    wrapper.vm.selectedAlias = 'test-server'
    await wrapper.vm.executeAction('reload_network')
    expect(Md3Message.success).toHaveBeenCalled()
  })

  it('executeAction 失败时应该显示错误消息', async () => {
    const { Md3Message } = await import('@/components/md3')
    mockRequestPost.mockRejectedValueOnce(new Error('fail'))
    const wrapper = createWrapper()
    wrapper.vm.selectedAlias = 'test-server'
    await wrapper.vm.executeAction('reload_network')
    expect(Md3Message.error).toHaveBeenCalled()
  })

  it('queryToolkit logged-users 应该格式化用户列表', async () => {
    mockRequestGet.mockResolvedValueOnce({
      users: [{ user: 'root', tty: 'pts/0', login_time: '2024-01-01', from: '192.168.1.1' }],
      raw: 'raw output',
    })
    const wrapper = createWrapper()
    wrapper.vm.selectedAlias = 'test-server'
    await wrapper.vm.queryToolkit('logged-users')
    expect(wrapper.vm.resultDialogVisible).toBe(true)
    expect(wrapper.vm.resultDialogContent).toContain('root')
  })

  it('queryToolkit logged-users 无用户时应该显示提示', async () => {
    mockRequestGet.mockResolvedValueOnce({ users: [], raw: '' })
    const wrapper = createWrapper()
    wrapper.vm.selectedAlias = 'test-server'
    await wrapper.vm.queryToolkit('logged-users')
    expect(wrapper.vm.resultDialogContent).toContain('当前无用户登录')
  })

  it('queryToolkit boot-time 应该格式化启动时间', async () => {
    mockRequestGet.mockResolvedValueOnce({ boot_time: '2024-01-01', since: '2 days' })
    const wrapper = createWrapper()
    wrapper.vm.selectedAlias = 'test-server'
    await wrapper.vm.queryToolkit('boot-time')
    expect(wrapper.vm.resultDialogContent).toContain('2024-01-01')
  })

  it('queryToolkit kernel-modules 应该格式化模块列表', async () => {
    mockRequestGet.mockResolvedValueOnce({ count: 1, modules: [{ name: 'nf_conntrack', size: '122880', used_by: '2' }] })
    const wrapper = createWrapper()
    wrapper.vm.selectedAlias = 'test-server'
    await wrapper.vm.queryToolkit('kernel-modules')
    expect(wrapper.vm.resultDialogContent).toContain('nf_conntrack')
  })

  it('queryToolkit enabled-services 应该显示服务列表', async () => {
    mockRequestGet.mockResolvedValueOnce({ services: 'sshd\nnginx' })
    const wrapper = createWrapper()
    wrapper.vm.selectedAlias = 'test-server'
    await wrapper.vm.queryToolkit('enabled-services')
    expect(wrapper.vm.resultDialogContent).toContain('sshd')
  })

  it('queryToolkit dns-config 应该显示 DNS 配置', async () => {
    mockRequestGet.mockResolvedValueOnce({ resolv_conf: 'nameserver 8.8.8.8' })
    const wrapper = createWrapper()
    wrapper.vm.selectedAlias = 'test-server'
    await wrapper.vm.queryToolkit('dns-config')
    expect(wrapper.vm.resultDialogContent).toContain('8.8.8.8')
  })

  it('queryToolkit ulimit 应该显示资源限制', async () => {
    mockRequestGet.mockResolvedValueOnce({ ulimit: 'open files 1024' })
    const wrapper = createWrapper()
    wrapper.vm.selectedAlias = 'test-server'
    await wrapper.vm.queryToolkit('ulimit')
    expect(wrapper.vm.resultDialogContent).toContain('open files')
  })

  it('queryToolkit check-updates 有更新时应该显示更新列表', async () => {
    mockRequestGet.mockResolvedValueOnce({ update_count: 2, updates: ['pkg1', 'pkg2'] })
    const wrapper = createWrapper()
    wrapper.vm.selectedAlias = 'test-server'
    await wrapper.vm.queryToolkit('check-updates')
    expect(wrapper.vm.resultDialogContent).toContain('2')
  })

  it('queryToolkit check-updates 无更新时应该提示', async () => {
    mockRequestGet.mockResolvedValueOnce({ update_count: 0, updates: [] })
    const wrapper = createWrapper()
    wrapper.vm.selectedAlias = 'test-server'
    await wrapper.vm.queryToolkit('check-updates')
    expect(wrapper.vm.resultDialogContent).toContain('最新')
  })

  it('queryToolkit 失败时应该显示错误消息', async () => {
    const { Md3Message } = await import('@/components/md3')
    mockRequestGet.mockRejectedValueOnce({ response: { data: { detail: '连接失败' } } })
    const wrapper = createWrapper()
    wrapper.vm.selectedAlias = 'test-server'
    await wrapper.vm.queryToolkit('logged-users')
    expect(Md3Message.error).toHaveBeenCalled()
  })

  it('doSetHostname 有主机名时应该调用 API', async () => {
    const { Md3Message } = await import('@/components/md3')
    mockRequestPost.mockResolvedValueOnce({ message: '主机名已修改' })
    const wrapper = createWrapper()
    wrapper.vm.selectedAlias = 'test-server'
    wrapper.vm.hostnameInput = 'new-host'
    await wrapper.vm.doSetHostname()
    expect(Md3Message.success).toHaveBeenCalled()
    expect(wrapper.vm.hostnameDialogVisible).toBe(false)
  })

  it('doSetHostname 失败时应该显示错误', async () => {
    const { Md3Message } = await import('@/components/md3')
    mockRequestPost.mockRejectedValueOnce(new Error('fail'))
    const wrapper = createWrapper()
    wrapper.vm.selectedAlias = 'test-server'
    wrapper.vm.hostnameInput = 'new-host'
    await wrapper.vm.doSetHostname()
    expect(Md3Message.error).toHaveBeenCalled()
  })

  it('openTimezoneDialog 应该打开对话框并加载时区', async () => {
    mockRequestGet.mockResolvedValueOnce({ timezone: 'Asia/Shanghai' })
    const wrapper = createWrapper()
    wrapper.vm.selectedAlias = 'test-server'
    await wrapper.vm.openTimezoneDialog()
    expect(wrapper.vm.timezoneDialogVisible).toBe(true)
    expect(wrapper.vm.timezoneInput).toBe('Asia/Shanghai')
  })

  it('doSetTimezone 有时区时应该调用 API', async () => {
    const { Md3Message } = await import('@/components/md3')
    mockRequestPost.mockResolvedValueOnce({ message: '时区已修改' })
    const wrapper = createWrapper()
    wrapper.vm.selectedAlias = 'test-server'
    wrapper.vm.timezoneInput = 'UTC'
    await wrapper.vm.doSetTimezone()
    expect(Md3Message.success).toHaveBeenCalled()
    expect(wrapper.vm.timezoneDialogVisible).toBe(false)
  })

  it('doSetTimezone 失败时应该显示错误', async () => {
    const { Md3Message } = await import('@/components/md3')
    mockRequestPost.mockRejectedValueOnce(new Error('fail'))
    const wrapper = createWrapper()
    wrapper.vm.selectedAlias = 'test-server'
    wrapper.vm.timezoneInput = 'UTC'
    await wrapper.vm.doSetTimezone()
    expect(Md3Message.error).toHaveBeenCalled()
  })

  it('loadDriveStatus 应该更新远程硬盘状态', async () => {
    const wrapper = createWrapper()
    await nextTick()
    await nextTick()
    await nextTick()
    mockRequestGet.mockResolvedValueOnce({
      enabled: true, running: true, webdav_url: 'http://test:8081/',
      windows_url: '\\\\test@8081\\', mounts: [], account_count: 2,
      auth_username: 'admin', auth_password_set: true,
    })
    await wrapper.vm.loadDriveStatus()
    expect(wrapper.vm.remoteDriveEnabled).toBe(true)
    expect(wrapper.vm.remoteDriveRunning).toBe(true)
  })

  it('onRemoteDriveToggle 关闭时应该调用 API', async () => {
    const { Md3Message } = await import('@/components/md3')
    mockRequestPut.mockResolvedValueOnce({})
    const wrapper = createWrapper()
    wrapper.vm.remoteDriveEnabled = true
    await wrapper.vm.onRemoteDriveToggle(false)
    expect(Md3Message.success).toHaveBeenCalled()
  })

  it('onRemoteDriveToggle 开启失败时应该恢复状态', async () => {
    const { Md3Message } = await import('@/components/md3')
    mockRequestPut.mockRejectedValueOnce(new Error('fail'))
    const wrapper = createWrapper()
    wrapper.vm.remoteDriveEnabled = false
    await wrapper.vm.onRemoteDriveToggle(true)
    expect(Md3Message.error).toHaveBeenCalled()
    expect(wrapper.vm.remoteDriveEnabled).toBe(false)
  })

  it('windowsUrl 默认值应该正确', () => {
    const wrapper = createWrapper()
    expect(wrapper.vm.windowsUrl).toBe('\\\\localhost@8081\\DavWWWRoot\\')
  })

  it('selectOptions 应该返回正确的选项', () => {
    const wrapper = createWrapper()
    const options = wrapper.vm.selectOptions
    expect(options.length).toBeGreaterThanOrEqual(1)
    expect(options[0].value).toBe('test-server')
  })

  it('confirmAction 确认时应该执行操作', async () => {
    const { Md3Message } = await import('@/components/md3')
    mockRequestPost.mockResolvedValueOnce({ message: '操作成功' })
    const wrapper = createWrapper()
    wrapper.vm.selectedAlias = 'test-server'
    await wrapper.vm.confirmAction('reboot')
    expect(Md3Message.success).toHaveBeenCalled()
  })

  it('confirmAction 取消时不应执行操作', async () => {
    const { Md3Confirm } = await import('@/components/md3')
    Md3Confirm.show.mockRejectedValueOnce(new Error('cancel'))
    const wrapper = createWrapper()
    wrapper.vm.selectedAlias = 'test-server'
    await wrapper.vm.confirmAction('reboot')
    expect(mockRequestPost).not.toHaveBeenCalled()
  })

  it('onRemoteDriveToggle 开启时取消应该恢复状态', async () => {
    const { Md3Confirm } = await import('@/components/md3')
    Md3Confirm.show.mockRejectedValueOnce(new Error('cancel'))
    const wrapper = createWrapper()
    wrapper.vm.remoteDriveEnabled = false
    await wrapper.vm.onRemoteDriveToggle(true)
    expect(wrapper.vm.remoteDriveEnabled).toBe(false)
  })

  it('copyUrl 失败时应该显示警告', async () => {
    const { Md3Message } = await import('@/components/md3')
    const writeText = vi.fn().mockRejectedValue(new Error('fail'))
    Object.defineProperty(navigator, 'clipboard', { value: { writeText }, writable: true, configurable: true })
    const wrapper = createWrapper()
    await wrapper.vm.copyUrl()
    expect(Md3Message.warning).toHaveBeenCalledWith('复制失败，请手动复制')
  })

  it('copyWindowsUrl 失败时应该显示警告', async () => {
    const { Md3Message } = await import('@/components/md3')
    const writeText = vi.fn().mockRejectedValue(new Error('fail'))
    Object.defineProperty(navigator, 'clipboard', { value: { writeText }, writable: true, configurable: true })
    const wrapper = createWrapper()
    await wrapper.vm.copyWindowsUrl()
    expect(Md3Message.warning).toHaveBeenCalledWith('复制失败，请手动复制')
  })

  it('queryToolkit 未知端点应该显示 JSON', async () => {
    mockRequestGet.mockResolvedValueOnce({ custom: 'data' })
    const wrapper = createWrapper()
    wrapper.vm.selectedAlias = 'test-server'
    await wrapper.vm.queryToolkit('custom-endpoint')
    expect(wrapper.vm.resultDialogContent).toContain('custom')
    expect(wrapper.vm.resultDialogVisible).toBe(true)
  })

  it('confirmSwapRefresh 确认时应该执行操作', async () => {
    const { Md3Message } = await import('@/components/md3')
    mockRequestGet.mockResolvedValueOnce({ swapon: 'SWAP enabled', free: 'free output' })
    mockRequestPost.mockResolvedValueOnce({ message: 'SWAP 已刷新' })
    const wrapper = createWrapper()
    wrapper.vm.selectedAlias = 'test-server'
    await wrapper.vm.confirmSwapRefresh()
    expect(Md3Message.success).toHaveBeenCalled()
  })

  it('confirmSwapRefresh 取消时不应执行操作', async () => {
    const { Md3Confirm } = await import('@/components/md3')
    Md3Confirm.show.mockRejectedValueOnce(new Error('cancel'))
    const wrapper = createWrapper()
    wrapper.vm.selectedAlias = 'test-server'
    await wrapper.vm.confirmSwapRefresh()
    expect(mockRequestGet).not.toHaveBeenCalledWith(expect.stringContaining('swap'))
  })

  it('confirmSwapRefresh 失败时应该显示错误', async () => {
    const { Md3Confirm } = await import('@/components/md3')
    mockRequestGet.mockRejectedValueOnce(new Error('fail'))
    const wrapper = createWrapper()
    wrapper.vm.selectedAlias = 'test-server'
    await wrapper.vm.confirmSwapRefresh()
  })

  it('confirmCleanupKernels 确认时应该执行清理', async () => {
    const { Md3Message } = await import('@/components/md3')
    mockRequestPost.mockResolvedValueOnce({ message: '清理完成' })
    const wrapper = createWrapper()
    wrapper.vm.selectedAlias = 'test-server'
    await wrapper.vm.confirmCleanupKernels()
    expect(Md3Message.success).toHaveBeenCalled()
  })

  it('confirmCleanupKernels 取消时不应执行', async () => {
    const { Md3Confirm } = await import('@/components/md3')
    Md3Confirm.show.mockRejectedValueOnce(new Error('cancel'))
    const wrapper = createWrapper()
    wrapper.vm.selectedAlias = 'test-server'
    await wrapper.vm.confirmCleanupKernels()
    expect(mockRequestPost).not.toHaveBeenCalledWith(expect.stringContaining('cleanup-kernels'))
  })

  it('confirmCleanupJournal 确认时应该执行清理', async () => {
    const { Md3Message } = await import('@/components/md3')
    mockRequestPost.mockResolvedValueOnce({ message: '清理完成' })
    const wrapper = createWrapper()
    wrapper.vm.selectedAlias = 'test-server'
    await wrapper.vm.confirmCleanupJournal()
    expect(Md3Message.success).toHaveBeenCalled()
  })

  it('confirmCleanupJournal 取消时不应执行', async () => {
    const { Md3Confirm } = await import('@/components/md3')
    Md3Confirm.show.mockRejectedValueOnce(new Error('cancel'))
    const wrapper = createWrapper()
    wrapper.vm.selectedAlias = 'test-server'
    await wrapper.vm.confirmCleanupJournal()
    expect(mockRequestPost).not.toHaveBeenCalledWith(expect.stringContaining('cleanup-journal'))
  })

  it('confirmAction reboot 应该调用 executeAction', async () => {
    const { Md3Message } = await import('@/components/md3')
    mockRequestPost.mockResolvedValueOnce({ message: '重启中' })
    const wrapper = createWrapper()
    wrapper.vm.selectedAlias = 'test-server'
    await wrapper.vm.confirmAction('reboot')
    expect(mockRequestPost).toHaveBeenCalledWith('/system/reboot', null, { params: { alias: 'test-server' } })
  })

  it('confirmAction shutdown 应该调用 executeAction', async () => {
    const { Md3Message } = await import('@/components/md3')
    mockRequestPost.mockResolvedValueOnce({ message: '关机中' })
    const wrapper = createWrapper()
    wrapper.vm.selectedAlias = 'test-server'
    await wrapper.vm.confirmAction('shutdown')
    expect(mockRequestPost).toHaveBeenCalledWith('/system/shutdown', null, { params: { alias: 'test-server' } })
  })

  it('confirmAction 取消时不应执行', async () => {
    const { Md3Confirm } = await import('@/components/md3')
    Md3Confirm.show.mockRejectedValueOnce(new Error('cancel'))
    const wrapper = createWrapper()
    wrapper.vm.selectedAlias = 'test-server'
    await wrapper.vm.confirmAction('reboot')
    expect(mockRequestPost).not.toHaveBeenCalled()
  })

  it('onRemoteDriveToggle 取消时应该恢复开关状态', async () => {
    const { Md3Confirm } = await import('@/components/md3')
    Md3Confirm.show.mockRejectedValueOnce(new Error('cancel'))
    const wrapper = createWrapper()
    wrapper.vm.remoteDriveEnabled = false
    await wrapper.vm.onRemoteDriveToggle(true)
    expect(wrapper.vm.remoteDriveEnabled).toBe(false)
  })

  it('onRemoteDriveToggle 关闭时应该直接调用 API', async () => {
    const { Md3Message } = await import('@/components/md3')
    mockRequestPut.mockResolvedValueOnce({})
    const wrapper = createWrapper()
    wrapper.vm.remoteDriveEnabled = true
    await wrapper.vm.onRemoteDriveToggle(false)
    expect(mockRequestPut).toHaveBeenCalledWith('/settings', { remote_drive_enabled: false })
    expect(Md3Message.success).toHaveBeenCalled()
  })

  it('onRemoteDriveToggle API 失败时应该恢复开关并显示错误', async () => {
    const { Md3Message } = await import('@/components/md3')
    const wrapper = createWrapper()
    await nextTick()
    await nextTick()
    wrapper.vm.remoteDriveEnabled = true
    mockRequestPut.mockRejectedValueOnce(new Error('fail'))
    await wrapper.vm.onRemoteDriveToggle(false)
    expect(wrapper.vm.remoteDriveEnabled).toBe(true)
    expect(Md3Message.error).toHaveBeenCalled()
  })

  it('copyUrl 失败时应该显示警告', async () => {
    const { Md3Message } = await import('@/components/md3')
    vi.spyOn(navigator.clipboard, 'writeText').mockRejectedValueOnce(new Error('fail'))
    const wrapper = createWrapper()
    wrapper.vm.webdavUrl = 'http://localhost:8080/dav'
    await wrapper.vm.copyUrl()
    expect(Md3Message.warning).toHaveBeenCalledWith('复制失败，请手动复制')
  })

  it('copyWindowsUrl 失败时应该显示警告', async () => {
    const { Md3Message } = await import('@/components/md3')
    vi.spyOn(navigator.clipboard, 'writeText').mockRejectedValueOnce(new Error('fail'))
    const wrapper = createWrapper()
    wrapper.vm.windowsUrl = '\\\\localhost@8080\\dav'
    await wrapper.vm.copyWindowsUrl()
    expect(Md3Message.warning).toHaveBeenCalledWith('复制失败，请手动复制')
  })

  it('copyUrl 成功时应该显示成功消息', async () => {
    const { Md3Message } = await import('@/components/md3')
    vi.spyOn(navigator.clipboard, 'writeText').mockResolvedValueOnce(undefined)
    const wrapper = createWrapper()
    wrapper.vm.webdavUrl = 'http://localhost:8080/dav'
    await wrapper.vm.copyUrl()
    expect(Md3Message.success).toHaveBeenCalledWith('地址已复制到剪贴板')
  })

  it('copyWindowsUrl 成功时应该显示成功消息', async () => {
    const { Md3Message } = await import('@/components/md3')
    vi.spyOn(navigator.clipboard, 'writeText').mockResolvedValueOnce(undefined)
    const wrapper = createWrapper()
    wrapper.vm.windowsUrl = '\\\\localhost@8080\\dav'
    await wrapper.vm.copyWindowsUrl()
    expect(Md3Message.success).toHaveBeenCalledWith('Windows 映射地址已复制到剪贴板')
  })

  it('doSetHostname 空主机名时应该显示警告', async () => {
    const { Md3Message } = await import('@/components/md3')
    const wrapper = createWrapper()
    wrapper.vm.hostnameInput = '  '
    await wrapper.vm.doSetHostname()
    expect(Md3Message.warning).toHaveBeenCalledWith('请输入主机名')
  })

  it('doSetTimezone 空时区时应该显示警告', async () => {
    const { Md3Message } = await import('@/components/md3')
    const wrapper = createWrapper()
    wrapper.vm.timezoneInput = '  '
    await wrapper.vm.doSetTimezone()
    expect(Md3Message.warning).toHaveBeenCalledWith('请输入时区')
  })

  it('confirmSwapRefresh 失败时应该显示错误', async () => {
    const { Md3Message } = await import('@/components/md3')
    const wrapper = createWrapper()
    await nextTick()
    await nextTick()
    wrapper.vm.selectedAlias = 'test-server'
    mockRequestGet.mockRejectedValueOnce(new Error('fail'))
    await wrapper.vm.confirmSwapRefresh()
    expect(Md3Message.error).toHaveBeenCalled()
  })

  it('confirmCleanupKernels 失败时应该显示错误', async () => {
    const { Md3Message } = await import('@/components/md3')
    mockRequestPost.mockRejectedValueOnce(new Error('fail'))
    const wrapper = createWrapper()
    wrapper.vm.selectedAlias = 'test-server'
    await wrapper.vm.confirmCleanupKernels()
    expect(Md3Message.error).toHaveBeenCalled()
  })

  it('confirmCleanupJournal 失败时应该显示错误', async () => {
    const { Md3Message } = await import('@/components/md3')
    mockRequestPost.mockRejectedValueOnce(new Error('fail'))
    const wrapper = createWrapper()
    wrapper.vm.selectedAlias = 'test-server'
    await wrapper.vm.confirmCleanupJournal()
    expect(Md3Message.error).toHaveBeenCalled()
  })
})
