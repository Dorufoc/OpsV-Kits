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
  Md3Progress: { name: 'Md3Progress', props: ['percentage', 'color'], template: '<div class="md3-progress" />' },
  Md3Radio: { name: 'Md3Radio', props: ['modelValue', 'value', 'label'], emits: ['update:modelValue'], template: '<label class="md3-radio" />' },
  Md3Switch: { name: 'Md3Switch', props: ['modelValue', 'onText', 'offText'], emits: ['update:modelValue'], template: '<div class="md3-switch" />' },
  Md3Collapse: { name: 'Md3Collapse', props: ['title'], template: '<div class="md3-collapse"><slot /></div>' },
  Md3Tooltip: { name: 'Md3Tooltip', props: ['content', 'placement'], template: '<div class="md3-tooltip"><slot /></div>' },
}))

vi.mock('@/components/Md3Button.vue', () => ({
  default: { name: 'Md3Button', props: ['size', 'variant', 'disabled', 'icon', 'loading', 'type'], template: '<button class="md3-btn" :disabled="disabled" @click="$emit(\'click\')"><slot /></button>' },
}))

vi.mock('@/components/md3/Md3Input.vue', () => ({
  default: { name: 'Md3Input', props: ['modelValue', 'label', 'placeholder', 'type', 'min', 'max', 'class'], emits: ['update:modelValue'], template: '<input class="md3-input" :value="modelValue" />' },
}))

vi.mock('@/components/FileBrowser.vue', () => ({
  default: { name: 'FileBrowser', props: ['currentPath', 'items', 'selectedPaths', 'showCreate', 'showUpload'], emits: ['navigate', 'mkdir', 'createFile', 'upload', 'download', 'rename', 'copy', 'delete', 'chmod', 'update:selectedPaths'], template: '<div class="file-browser" />' },
}))

vi.mock('@/components/PermissionEditor.vue', () => ({
  default: { name: 'PermissionEditor', props: ['modelValue', 'showRecursive'], emits: ['update:modelValue', 'update:recursive'], template: '<div class="permission-editor" />' },
}))

const mockPush = vi.fn()
vi.mock('vue-router', () => ({
  useRouter: () => ({ push: mockPush }),
  useRoute: () => ({}),
}))

let sshStoreMock: any
let processStoreMock: any
let securityNetworkStoreMock: any

vi.mock('@/stores/sshAccountStore', () => ({
  useSshAccountStore: () => sshStoreMock,
}))

vi.mock('@/stores/processStore', () => ({
  useProcessStore: () => processStoreMock,
}))

vi.mock('@/stores/securityNetworkStore', () => ({
  useSecurityNetworkStore: () => securityNetworkStoreMock,
}))

vi.mock('@/stores/dockerStore', () => ({
  useDockerStore: () => ({
    setAccountAlias: vi.fn(),
    currentAlias: '',
  }),
}))

beforeEach(() => {
  setActivePinia(createPinia())
  vi.clearAllMocks()
  sshStoreMock = {
    accounts: [{ alias: 'test-server', host: '192.168.1.1', port: 22, default: true, status: 'online', username: 'root', auth_type: 'password', password: '', private_key: '', key_passphrase: '', group: '', last_connected: '' }],
    groups: [],
    fetchAccounts: vi.fn().mockResolvedValue(undefined),
    fetchGroups: vi.fn().mockResolvedValue(undefined),
    testConnection: vi.fn().mockResolvedValue({ success: true }),
    createAccount: vi.fn().mockResolvedValue(undefined),
    updateAccount: vi.fn().mockResolvedValue(undefined),
    deleteAccount: vi.fn().mockResolvedValue(undefined),
    setDefault: vi.fn().mockResolvedValue(undefined),
    createGroup: vi.fn().mockResolvedValue(undefined),
    updateGroup: vi.fn().mockResolvedValue(undefined),
    deleteGroup: vi.fn().mockResolvedValue(undefined),
  }
  processStoreMock = {
    processes: [],
    filteredProcesses: [],
    loading: false,
    streaming: false,
    currentAlias: '',
    refreshInterval: 0,
    anomalies: { total_anomalies: 0, zombies: [], high_cpu: [], high_mem: [] },
    anomalyPidSet: new Set(),
    uniqueUsers: [],
    selectedPids: new Set(),
    fetchProcessList: vi.fn().mockResolvedValue(undefined),
    fetchProcessDetail: vi.fn().mockResolvedValue({ pid: 1, name: 'test', status: 'running', user: 'root', cpu_percent: 0, mem_percent: 0, vsz: 0, rss: 0, command: '' }),
    killProcess: vi.fn().mockResolvedValue(undefined),
    setNice: vi.fn().mockResolvedValue(undefined),
    batchKill: vi.fn().mockResolvedValue(undefined),
    serviceControl: vi.fn().mockResolvedValue(undefined),
    connectWebSocket: vi.fn(),
    disconnect: vi.fn(),
    startAutoRefresh: vi.fn(),
    stopAutoRefresh: vi.fn(),
    fetchAlertConfig: vi.fn().mockResolvedValue(undefined),
    deselectAll: vi.fn(),
  }
  securityNetworkStoreMock = {
    firewallBackend: null,
    firewallRules: [],
    sshConfig: null,
    sshKeys: [],
     loginLogs: [],
     auditLogs: [],
     fail2banStatus: null,
     loadingFirewall: false,
    loadingSsh: false,
    fetchFirewallBackend: vi.fn().mockResolvedValue(undefined),
    fetchFirewallRules: vi.fn().mockResolvedValue(undefined),
    addPortRule: vi.fn().mockResolvedValue(undefined),
    removePortRule: vi.fn().mockResolvedValue(undefined),
    fetchSshConfig: vi.fn().mockResolvedValue(undefined),
    loadFirewallBackend: vi.fn().mockResolvedValue(undefined),
    loadFirewallRules: vi.fn().mockResolvedValue(undefined),
    loadSshConfig: vi.fn().mockResolvedValue(undefined),
    loadSshKeys: vi.fn().mockResolvedValue(undefined),
    loadLoginLogs: vi.fn().mockResolvedValue(undefined),
    loadAuditLogs: vi.fn().mockResolvedValue(undefined),
  }
})

import SshAccountPage from '@/views/SshAccountPage.vue'
import FileManagerPage from '@/views/FileManagerPage.vue'
import ProcessManagerPage from '@/views/ProcessManagerPage.vue'
import SecurityNetworkPage from '@/views/SecurityNetworkPage.vue'

describe('SshAccountPage', () => {
  function createWrapper() {
    return mount(SshAccountPage, { global: { stubs: { Md3Icon: true } } })
  }

  it('应该渲染 SSH 账户页面容器', () => {
    const wrapper = createWrapper()
    expect(wrapper.find('.ssh-account-page').exists()).toBe(true)
  })

  it('应该渲染侧边栏', () => {
    const wrapper = createWrapper()
    expect(wrapper.find('.account-sidebar').exists()).toBe(true)
  })

  it('应该渲染账户列表标题', () => {
    const wrapper = createWrapper()
    expect(wrapper.text()).toContain('账户列表')
  })

  it('应该渲染账户列表项', () => {
    const wrapper = createWrapper()
    expect(wrapper.findAll('.account-list-item').length).toBe(1)
  })

  it('应该显示账户别名', () => {
    const wrapper = createWrapper()
    expect(wrapper.text()).toContain('test-server')
  })

  it('应该显示账户主机信息', () => {
    const wrapper = createWrapper()
    expect(wrapper.text()).toContain('192.168.1.1')
  })

  it('点击账户应该选中', async () => {
    const wrapper = createWrapper()
    await wrapper.find('.account-list-item').trigger('click')
    expect(wrapper.vm.selectedAccount).toBeTruthy()
  })

  it('选中账户后应该显示账户详情', async () => {
    const wrapper = createWrapper()
    await wrapper.find('.account-list-item').trigger('click')
    await nextTick()
    expect(wrapper.find('.account-detail').exists()).toBe(true)
  })

  it('未选中账户时应该显示空状态', () => {
    const wrapper = createWrapper()
    expect(wrapper.text()).toContain('请选择一个 SSH 账户')
  })

  it('应该渲染分组导航', () => {
    const wrapper = createWrapper()
    expect(wrapper.text()).toContain('账户分组')
  })

  it('应该渲染添加按钮', () => {
    const wrapper = createWrapper()
    expect(wrapper.text()).toContain('添加')
  })

  it('authTypeLabel 应该返回正确的标签', () => {
    const wrapper = createWrapper()
    expect(wrapper.vm.authTypeLabel('password')).toBe('密码认证')
    expect(wrapper.vm.authTypeLabel('key')).toBe('SSH 密钥')
    expect(wrapper.vm.authTypeLabel('agent')).toBe('SSH Agent')
  })
})

describe('FileManagerPage', () => {
  function createWrapper() {
    return mount(FileManagerPage, { global: { stubs: { Md3Icon: true } } })
  }

  it('应该渲染文件管理页面容器', () => {
    const wrapper = createWrapper()
    expect(wrapper.find('.file-manager-page').exists()).toBe(true)
  })

  it('应该渲染页面标题', () => {
    const wrapper = createWrapper()
    expect(wrapper.text()).toContain('远程文件管理')
  })

  it('应该渲染侧边栏', () => {
    const wrapper = createWrapper()
    expect(wrapper.find('.file-sidebar').exists()).toBe(true)
  })

  it('应该渲染 SSH 账户列表', () => {
    const wrapper = createWrapper()
    expect(wrapper.text()).toContain('SSH 账户')
  })

  it('应该渲染快速导航', () => {
    const wrapper = createWrapper()
    expect(wrapper.text()).toContain('快速导航')
  })

  it('应该渲染快速命令区域', () => {
    const wrapper = createWrapper()
    expect(wrapper.find('.quick-command-area').exists()).toBe(true)
  })

  it('goToSshAccounts 应该导航到 SSH 账户页面', () => {
    const wrapper = createWrapper()
    wrapper.vm.goToSshAccounts()
    expect(mockPush).toHaveBeenCalledWith('/ssh-accounts')
  })

  it('clearHistory 应该清空命令历史', () => {
    const wrapper = createWrapper()
    wrapper.vm.commandHistory = [{ command: 'ls', output: 'file1' }]
    wrapper.vm.clearHistory()
    expect(wrapper.vm.commandHistory).toEqual([])
  })

  it('navigateTo 应该更新当前路径', () => {
    const wrapper = createWrapper()
    wrapper.vm.navigateTo('/var/log')
    expect(wrapper.vm.currentPath).toBe('/var/log')
  })
})

describe('ProcessManagerPage', () => {
  function createWrapper() {
    return mount(ProcessManagerPage, { global: { stubs: { Md3Icon: true } } })
  }

  it('应该渲染进程管理页面容器', () => {
    const wrapper = createWrapper()
    expect(wrapper.find('.process-manager-page').exists()).toBe(true)
  })

  it('应该渲染页面标题', () => {
    const wrapper = createWrapper()
    expect(wrapper.text()).toContain('进程管理')
  })

  it('应该在未选择服务器时显示空状态', () => {
    const wrapper = createWrapper()
    expect(wrapper.text()).toContain('请先选择一台服务器查看进程')
  })

  it('应该渲染搜索输入框', async () => {
    const wrapper = createWrapper()
    wrapper.vm.selectedAlias = 'test-server'
    await nextTick()
    expect(wrapper.find('.toolbar').exists() || wrapper.find('.md3-input').exists()).toBe(true)
  })

  it('应该渲染排序按钮', async () => {
    const wrapper = createWrapper()
    wrapper.vm.selectedAlias = 'test-server'
    await nextTick()
    expect(wrapper.find('.sort-buttons').exists()).toBe(true)
  })

  it('toggleSort 应该切换排序', () => {
    const wrapper = createWrapper()
    wrapper.vm.toggleSort('cpu_percent')
    expect(wrapper.vm.sortColumn).toBe('cpu_percent')
    expect(wrapper.vm.sortOrder).toBe('desc')
    wrapper.vm.toggleSort('cpu_percent')
    expect(wrapper.vm.sortOrder).toBe('asc')
  })

  it('statusColor 应该返回正确的颜色', () => {
    const wrapper = createWrapper()
    expect(wrapper.vm.statusColor('running')).toBe('success')
    expect(wrapper.vm.statusColor('zombie')).toBe('danger')
    expect(wrapper.vm.statusColor('sleeping')).toBe('info')
    expect(wrapper.vm.statusColor('stopped')).toBe('warning')
  })

  it('formatStatus 应该首字母大写', () => {
    const wrapper = createWrapper()
    expect(wrapper.vm.formatStatus('running')).toBe('Running')
    expect(wrapper.vm.formatStatus('')).toBe('-')
  })

  it('resourceColor 应该返回正确的颜色', () => {
    const wrapper = createWrapper()
    expect(wrapper.vm.resourceColor(95, 'cpu')).toBe('#ef4444')
    expect(wrapper.vm.resourceColor(60, 'cpu')).toBe('#f59e0b')
    expect(wrapper.vm.resourceColor(30, 'cpu')).toBe('#22c55e')
  })

  it('formatBytes 应该正确格式化字节', () => {
    const wrapper = createWrapper()
    expect(wrapper.vm.formatBytes(512)).toBe('512 KB')
    expect(wrapper.vm.formatBytes(2048)).toBe('2.0 MB')
    expect(wrapper.vm.formatBytes(1048576)).toBe('1.00 GB')
  })

  it('onAccountChange 应该更新 store 并刷新', async () => {
    const wrapper = createWrapper()
    wrapper.vm.selectedAlias = 'new-server'
    await nextTick()
    await wrapper.vm.onAccountChange('new-server')
    expect(processStoreMock.fetchProcessList).toHaveBeenCalled()
  })

  it('clearSelection 应该清空选中行', () => {
    const wrapper = createWrapper()
    wrapper.vm.selectedRows = [{ pid: 1 }]
    wrapper.vm.clearSelection()
    expect(wrapper.vm.selectedRows).toEqual([])
  })
})

describe('SecurityNetworkPage', () => {
  function createWrapper() {
    return mount(SecurityNetworkPage, { global: { stubs: { Md3Icon: true } } })
  }

  it('应该渲染安全与网络页面容器', () => {
    const wrapper = createWrapper()
    expect(wrapper.find('.security-network-page').exists()).toBe(true)
  })

  it('应该渲染页面标题', () => {
    const wrapper = createWrapper()
    expect(wrapper.text()).toContain('安全与网络')
  })

  it('应该渲染 SSH 服务器选择器', () => {
    const wrapper = createWrapper()
    expect(wrapper.find('.account-selector').exists()).toBe(true)
  })

  it('应该渲染 Tab 切换', async () => {
    const wrapper = createWrapper()
    wrapper.vm.selectedAlias = 'test-server'
    await nextTick()
    expect(wrapper.find('.page-tabs').exists() || wrapper.find('.md3-tabs').exists()).toBe(true)
  })
})
