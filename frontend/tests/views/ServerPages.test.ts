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
let auditLogStoreMock: any

vi.mock('@/stores/sshAccountStore', () => ({
  useSshAccountStore: () => sshStoreMock,
}))

vi.mock('@/stores/processStore', () => ({
  useProcessStore: () => processStoreMock,
}))

vi.mock('@/stores/securityNetworkStore', () => ({
  useSecurityNetworkStore: () => securityNetworkStoreMock,
}))

vi.mock('@/stores/auditLogStore', () => ({
  useAuditLogStore: () => auditLogStoreMock,
}))

vi.mock('@/stores/dockerStore', () => ({
  useDockerStore: () => ({
    setAccountAlias: vi.fn(),
    currentAlias: '',
  }),
}))

const mockRequestGet = vi.fn().mockResolvedValue({ entries: [] })
const mockRequestPost = vi.fn().mockResolvedValue({})
vi.mock('@/api', () => ({
  request: {
    get: (...args: any[]) => mockRequestGet(...args),
    post: (...args: any[]) => mockRequestPost(...args),
  },
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
     opsAuditLogs: [],
     fail2banStatus: null,
     loadingFirewall: false,
     loadingSsh: false,
     loadingLogs: false,
     loadingNetwork: false,
    fetchFirewallBackend: vi.fn().mockResolvedValue(undefined),
    fetchFirewallRules: vi.fn().mockResolvedValue(undefined),
    addPortRule: vi.fn().mockResolvedValue(undefined),
    removePortRule: vi.fn().mockResolvedValue(undefined),
    addIpRule: vi.fn().mockResolvedValue(undefined),
    removeIpRule: vi.fn().mockResolvedValue(undefined),
    fetchSshConfig: vi.fn().mockResolvedValue(undefined),
    loadFirewallBackend: vi.fn().mockResolvedValue(undefined),
    loadFirewallRules: vi.fn().mockResolvedValue(undefined),
    loadSshConfig: vi.fn().mockResolvedValue(undefined),
    loadSshKeys: vi.fn().mockResolvedValue(undefined),
    loadLoginLogs: vi.fn().mockResolvedValue(undefined),
    loadAuditLogs: vi.fn().mockResolvedValue(undefined),
    loadFail2banStatus: vi.fn().mockResolvedValue(undefined),
    loadOpsAuditLogs: vi.fn().mockResolvedValue(undefined),
    changeSshPort: vi.fn().mockResolvedValue(undefined),
    togglePasswordAuth: vi.fn().mockResolvedValue(undefined),
    addSshKey: vi.fn().mockResolvedValue(undefined),
    removeSshKey: vi.fn().mockResolvedValue(undefined),
    generateSshKey: vi.fn().mockResolvedValue(undefined),
    unbanIp: vi.fn().mockResolvedValue(undefined),
    runPing: vi.fn().mockResolvedValue({ output: '5 packets transmitted, 4 received, 20% packet loss' }),
    runTraceroute: vi.fn().mockResolvedValue({ output: '' }),
    runPortScan: vi.fn().mockResolvedValue({ output: '' }),
  }
  auditLogStoreMock = {
    logs: [],
    loading: false,
    loadRecentLogs: vi.fn().mockResolvedValue(undefined),
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

  it('filteredAccounts 全部时应该返回所有账户', () => {
    const wrapper = createWrapper()
    expect(wrapper.vm.filteredAccounts).toHaveLength(1)
  })

  it('filteredAccounts 按组过滤时应该返回对应组', () => {
    sshStoreMock.accounts = [
      { alias: 'server1', host: '192.168.1.1', port: 22, default: true, status: 'online', username: 'root', auth_type: 'password', password: '', private_key: '', key_passphrase: '', group: 'prod', last_connected: '' },
      { alias: 'server2', host: '192.168.1.2', port: 22, default: false, status: 'offline', username: 'root', auth_type: 'key', password: '', private_key: '/key', key_passphrase: '', group: 'dev', last_connected: '' },
    ]
    const wrapper = createWrapper()
    wrapper.vm.selectedGroup = 'prod'
    expect(wrapper.vm.filteredAccounts).toHaveLength(1)
    expect(wrapper.vm.filteredAccounts[0].alias).toBe('server1')
  })

  it('groupOptions 应该返回分组选项', () => {
    sshStoreMock.groups = [{ name: 'prod' }, { name: 'dev' }]
    const wrapper = createWrapper()
    expect(wrapper.vm.groupOptions).toHaveLength(2)
  })

  it('testConnection 成功时应该显示成功消息', async () => {
    const { Md3Message } = await import('@/components/md3')
    const wrapper = createWrapper()
    await wrapper.find('.account-list-item').trigger('click')
    await nextTick()
    await wrapper.vm.testConnection()
    expect(Md3Message.success).toHaveBeenCalled()
  })

  it('testConnection 失败时应该显示错误消息', async () => {
    const { Md3Message } = await import('@/components/md3')
    sshStoreMock.testConnection = vi.fn().mockResolvedValue({ success: false, message: '连接失败' })
    const wrapper = createWrapper()
    await wrapper.find('.account-list-item').trigger('click')
    await nextTick()
    await wrapper.vm.testConnection()
    expect(Md3Message.error).toHaveBeenCalled()
  })

  it('editAccount 应该设置编辑状态并打开对话框', async () => {
    const wrapper = createWrapper()
    await wrapper.find('.account-list-item').trigger('click')
    await nextTick()
    wrapper.vm.editAccount()
    expect(wrapper.vm.isEditing).toBe(true)
    expect(wrapper.vm.showAddDialog).toBe(true)
  })

  it('confirmRemoveAccount 取消时不应删除', async () => {
    const { Md3Confirm } = await import('@/components/md3')
    Md3Confirm.show.mockResolvedValueOnce(false)
    const wrapper = createWrapper()
    await wrapper.find('.account-list-item').trigger('click')
    await nextTick()
    await wrapper.vm.confirmRemoveAccount()
    expect(sshStoreMock.deleteAccount).not.toHaveBeenCalled()
  })

  it('confirmRemoveAccount 确认时应该删除账户', async () => {
    const wrapper = createWrapper()
    await wrapper.find('.account-list-item').trigger('click')
    await nextTick()
    await wrapper.vm.confirmRemoveAccount()
    expect(sshStoreMock.deleteAccount).toHaveBeenCalled()
  })

  it('setAsDefault 应该调用 store', async () => {
    const wrapper = createWrapper()
    await wrapper.find('.account-list-item').trigger('click')
    await nextTick()
    await wrapper.vm.setAsDefault()
    expect(sshStoreMock.setDefault).toHaveBeenCalled()
  })

  it('saveAccount 编辑时应该调用 updateAccount', async () => {
    const wrapper = createWrapper()
    await wrapper.find('.account-list-item').trigger('click')
    await nextTick()
    wrapper.vm.isEditing = true
    await wrapper.vm.saveAccount()
    expect(sshStoreMock.updateAccount).toHaveBeenCalled()
    expect(wrapper.vm.showAddDialog).toBe(false)
  })

  it('saveAccount 新建时应该调用 createAccount', async () => {
    const wrapper = createWrapper()
    wrapper.vm.isEditing = false
    await wrapper.vm.saveAccount()
    expect(sshStoreMock.createAccount).toHaveBeenCalled()
    expect(wrapper.vm.showAddDialog).toBe(false)
  })

  it('createGroup 空名称时不应调用 store', async () => {
    const wrapper = createWrapper()
    wrapper.vm.newGroupName = ''
    await wrapper.vm.createGroup()
    expect(sshStoreMock.createGroup).not.toHaveBeenCalled()
  })

  it('createGroup 成功时应该调用 store 并关闭对话框', async () => {
    const wrapper = createWrapper()
    wrapper.vm.newGroupName = 'new-group'
    wrapper.vm.showNewGroupDialog = true
    await wrapper.vm.createGroup()
    expect(sshStoreMock.createGroup).toHaveBeenCalledWith('new-group')
    expect(wrapper.vm.showNewGroupDialog).toBe(false)
  })

  it('createGroup 失败时应该显示错误', async () => {
    const { Md3Message } = await import('@/components/md3')
    sshStoreMock.createGroup = vi.fn().mockRejectedValue({ response: { data: { detail: '已存在' } } })
    const wrapper = createWrapper()
    wrapper.vm.newGroupName = 'dup-group'
    await wrapper.vm.createGroup()
    expect(Md3Message.error).toHaveBeenCalled()
  })

  it('openRenameGroup 应该打开重命名对话框', () => {
    const wrapper = createWrapper()
    wrapper.vm.openRenameGroup('prod')
    expect(wrapper.vm.renameGroupOldName).toBe('prod')
    expect(wrapper.vm.renameGroupNewName).toBe('prod')
    expect(wrapper.vm.showRenameGroupDialog).toBe(true)
  })

  it('renameGroup 名称相同时不应调用 store', async () => {
    const wrapper = createWrapper()
    wrapper.vm.renameGroupOldName = 'prod'
    wrapper.vm.renameGroupNewName = 'prod'
    await wrapper.vm.renameGroup()
    expect(sshStoreMock.updateGroup).not.toHaveBeenCalled()
  })

  it('renameGroup 成功时应该调用 store', async () => {
    const { Md3Message } = await import('@/components/md3')
    const wrapper = createWrapper()
    wrapper.vm.renameGroupOldName = 'prod'
    wrapper.vm.renameGroupNewName = 'production'
    await wrapper.vm.renameGroup()
    expect(sshStoreMock.updateGroup).toHaveBeenCalledWith('prod', { new_name: 'production' })
    expect(Md3Message.success).toHaveBeenCalled()
  })

  it('confirmDeleteGroup 取消时不应删除', async () => {
    const { Md3Confirm } = await import('@/components/md3')
    Md3Confirm.show.mockResolvedValueOnce(false)
    const wrapper = createWrapper()
    await wrapper.vm.confirmDeleteGroup('prod')
    expect(sshStoreMock.deleteGroup).not.toHaveBeenCalled()
  })

  it('confirmDeleteGroup 确认时应该删除分组', async () => {
    const { Md3Message } = await import('@/components/md3')
    const wrapper = createWrapper()
    await wrapper.vm.confirmDeleteGroup('prod')
    expect(sshStoreMock.deleteGroup).toHaveBeenCalledWith('prod')
    expect(Md3Message.success).toHaveBeenCalled()
  })

  it('descriptionItems 应该返回正确的描述项', async () => {
    const wrapper = createWrapper()
    await wrapper.find('.account-list-item').trigger('click')
    await nextTick()
    const items = wrapper.vm.descriptionItems
    expect(items.length).toBeGreaterThan(0)
    expect(items[0].label).toBe('别名')
  })

  it('loadAccounts 应该调用 fetchAccounts', async () => {
    const wrapper = createWrapper()
    await wrapper.vm.loadAccounts()
    expect(sshStoreMock.fetchAccounts).toHaveBeenCalled()
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

  it('switchAccount 应该更新 selectedAccount 并加载目录', () => {
    const wrapper = createWrapper()
    wrapper.vm.switchAccount({ alias: 'test-server' })
    expect(wrapper.vm.selectedAccount).toBe('test-server')
    expect(wrapper.vm.currentPath).toBe('/')
  })

  it('loadDirectory 无账户时不应加载', async () => {
    const wrapper = createWrapper()
    mockRequestGet.mockClear()
    wrapper.vm.selectedAccount = ''
    await wrapper.vm.loadDirectory('/var/log')
    expect(mockRequestGet).not.toHaveBeenCalled()
  })

  it('loadDirectory 有账户时应该请求文件列表', async () => {
    const wrapper = createWrapper()
    wrapper.vm.selectedAccount = 'test-server'
    mockRequestGet.mockResolvedValue({ entries: [{ name: 'file1.txt', path: '/file1.txt', is_dir: false }] })
    await wrapper.vm.loadDirectory('/var/log')
    expect(wrapper.vm.currentPath).toBe('/var/log')
    expect(wrapper.vm.fileItems).toHaveLength(1)
  })

  it('loadDirectory 失败时应该清空文件列表', async () => {
    mockRequestGet.mockRejectedValue(new Error('fail'))
    const wrapper = createWrapper()
    wrapper.vm.selectedAccount = 'test-server'
    await wrapper.vm.loadDirectory('/var/log')
    expect(wrapper.vm.fileItems).toEqual([])
  })

  it('createDirectory 空名称时不应调用 API', async () => {
    const wrapper = createWrapper()
    wrapper.vm.newDirName = ''
    await wrapper.vm.createDirectory()
    expect(mockRequestPost).not.toHaveBeenCalled()
  })

  it('createDirectory 成功时应该调用 API 并关闭对话框', async () => {
    const wrapper = createWrapper()
    wrapper.vm.selectedAccount = 'test-server'
    wrapper.vm.newDirName = 'test-dir'
    wrapper.vm.showMkdirDialog = true
    await wrapper.vm.createDirectory()
    expect(mockRequestPost).toHaveBeenCalled()
    expect(wrapper.vm.showMkdirDialog).toBe(false)
    expect(wrapper.vm.newDirName).toBe('')
  })

  it('createFile 空名称时不应调用 API', async () => {
    const wrapper = createWrapper()
    wrapper.vm.newFileName = ''
    await wrapper.vm.createFile()
    expect(mockRequestPost).not.toHaveBeenCalled()
  })

  it('createFile 成功时应该调用 API 并关闭对话框', async () => {
    const wrapper = createWrapper()
    wrapper.vm.selectedAccount = 'test-server'
    wrapper.vm.newFileName = 'test.txt'
    wrapper.vm.showCreateFileDialog = true
    await wrapper.vm.createFile()
    expect(mockRequestPost).toHaveBeenCalled()
    expect(wrapper.vm.showCreateFileDialog).toBe(false)
  })

  it('executeCommand 无命令时不应执行', async () => {
    const wrapper = createWrapper()
    wrapper.vm.quickCommand = ''
    await wrapper.vm.executeCommand()
    expect(mockRequestPost).not.toHaveBeenCalled()
  })

  it('executeCommand 成功时应该添加到历史', async () => {
    mockRequestPost.mockResolvedValue({ stdout: 'output' })
    const wrapper = createWrapper()
    wrapper.vm.selectedAccount = 'test-server'
    wrapper.vm.quickCommand = 'ls -la'
    await wrapper.vm.executeCommand()
    expect(wrapper.vm.commandHistory).toHaveLength(1)
    expect(wrapper.vm.commandHistory[0].command).toBe('ls -la')
    expect(wrapper.vm.quickCommand).toBe('')
  })

  it('executeCommand 失败时不应添加到历史', async () => {
    mockRequestPost.mockRejectedValue(new Error('fail'))
    const wrapper = createWrapper()
    wrapper.vm.selectedAccount = 'test-server'
    wrapper.vm.quickCommand = 'ls'
    await wrapper.vm.executeCommand()
    expect(wrapper.vm.commandHistory).toHaveLength(0)
  })

  it('handleDelete 应该调用 API 删除文件', async () => {
    const wrapper = createWrapper()
    wrapper.vm.selectedAccount = 'test-server'
    await wrapper.vm.handleDelete({ path: '/var/log/test.log', name: 'test.log' })
    expect(mockRequestPost).toHaveBeenCalled()
  })

  it('handleBatchDelete 取消时不应删除', async () => {
    const { Md3Confirm } = await import('@/components/md3')
    Md3Confirm.show.mockResolvedValueOnce(false)
    const wrapper = createWrapper()
    wrapper.vm.selectedAccount = 'test-server'
    wrapper.vm.selectedPaths = ['/var/log/test.log']
    await wrapper.vm.handleBatchDelete()
    expect(mockRequestPost).not.toHaveBeenCalled()
  })

  it('handleBatchDelete 确认时应该调用 API', async () => {
    const wrapper = createWrapper()
    wrapper.vm.selectedAccount = 'test-server'
    wrapper.vm.selectedPaths = ['/var/log/test.log']
    await wrapper.vm.handleBatchDelete()
    expect(mockRequestPost).toHaveBeenCalled()
  })

  it('openSingleChmod 应该打开权限对话框', () => {
    const wrapper = createWrapper()
    const item = { name: 'test.txt', path: '/test.txt', is_dir: false, permission: '-rw-r--r--' }
    wrapper.vm.openSingleChmod(item)
    expect(wrapper.vm.showChmodDialog).toBe(true)
    expect(wrapper.vm.chmodSingleItem).toBeTruthy()
  })

  it('chmodDialogTitle 单文件时应该显示文件名', () => {
    const wrapper = createWrapper()
    wrapper.vm.chmodSingleItem = { name: 'test.txt', path: '/test.txt' }
    expect(wrapper.vm.chmodDialogTitle).toContain('test.txt')
  })

  it('chmodDialogTitle 批量时应该显示数量', () => {
    const wrapper = createWrapper()
    wrapper.vm.chmodSingleItem = null
    wrapper.vm.selectedPaths = ['/a', '/b']
    expect(wrapper.vm.chmodDialogTitle).toContain('2')
  })

  it('chmodRecursiveItems 应该过滤目录项', () => {
    const wrapper = createWrapper()
    wrapper.vm.fileItems = [
      { name: 'dir1', path: '/dir1', is_dir: true },
      { name: 'file1', path: '/file1', is_dir: false },
    ]
    wrapper.vm.selectedPaths = ['/dir1', '/file1']
    expect(wrapper.vm.chmodRecursiveItems).toHaveLength(1)
    expect(wrapper.vm.chmodRecursiveItems[0].name).toBe('dir1')
  })

  it('applyChmod 单文件时应该调用单个 chmod API', async () => {
    const wrapper = createWrapper()
    wrapper.vm.selectedAccount = 'test-server'
    wrapper.vm.chmodSingleItem = { name: 'test.txt', path: '/test.txt' }
    wrapper.vm.chmodPaths = ['/test.txt']
    await wrapper.vm.applyChmod()
    expect(mockRequestPost).toHaveBeenCalled()
    expect(wrapper.vm.showChmodDialog).toBe(false)
  })

  it('applyChmod 批量时应该调用 batch chmod API', async () => {
    const wrapper = createWrapper()
    wrapper.vm.selectedAccount = 'test-server'
    wrapper.vm.chmodSingleItem = null
    wrapper.vm.chmodPaths = []
    wrapper.vm.selectedPaths = ['/a', '/b']
    await wrapper.vm.applyChmod()
    expect(mockRequestPost).toHaveBeenCalled()
  })

  it('onMounted 有账户时应该自动选择并加载', () => {
    const wrapper = createWrapper()
    expect(wrapper.vm.selectedAccount).toBe('test-server')
  })

  it('handleUpload 应该创建文件输入元素', async () => {
    const wrapper = createWrapper()
    const mockClick = vi.fn()
    const mockInput = { type: '', multiple: false, onchange: null as any, click: mockClick, files: null, setAttribute: vi.fn() }
    const createElementSpy = vi.spyOn(document, 'createElement').mockReturnValue(mockInput as any)
    try {
      wrapper.vm.selectedAccount = 'test-server'
      wrapper.vm.handleUpload()
      expect(mockInput.type).toBe('file')
      expect(mockInput.multiple).toBe(true)
      expect(mockClick).toHaveBeenCalled()
    } finally {
      createElementSpy.mockRestore()
    }
  })

  it('handleDownload 应该请求文件并创建下载链接', async () => {
    const mockBlob = new Blob(['test'])
    mockRequestGet.mockResolvedValue(mockBlob)
    const wrapper = createWrapper()
    const mockCreateObjectURL = vi.fn().mockReturnValue('blob:test')
    const mockRevokeObjectURL = vi.fn()
    const createURLSpy = vi.spyOn(URL, 'createObjectURL').mockImplementation(mockCreateObjectURL)
    const revokeURLSpy = vi.spyOn(URL, 'revokeObjectURL').mockImplementation(mockRevokeObjectURL)
    try {
      wrapper.vm.selectedAccount = 'test-server'
      await wrapper.vm.handleDownload({ name: 'test.txt', path: '/test.txt', is_dir: false } as any)
      expect(mockRequestGet).toHaveBeenCalled()
      expect(mockCreateObjectURL).toHaveBeenCalledWith(mockBlob)
    } finally {
      createURLSpy.mockRestore()
      revokeURLSpy.mockRestore()
    }
  })

  it('handleDownload 失败时不应崩溃', async () => {
    mockRequestGet.mockRejectedValue(new Error('fail'))
    const wrapper = createWrapper()
    wrapper.vm.selectedAccount = 'test-server'
    await wrapper.vm.handleDownload({ name: 'test.txt', path: '/test.txt', is_dir: false } as any)
  })

  it('handleRename 有新名称时应该调用 API', async () => {
    const wrapper = createWrapper()
    const promptSpy = vi.spyOn(window, 'prompt').mockReturnValue('new-name.txt')
    try {
      wrapper.vm.selectedAccount = 'test-server'
      await wrapper.vm.handleRename({ name: 'test.txt', path: '/dir/test.txt', is_dir: false } as any)
      expect(mockRequestPost).toHaveBeenCalledWith('/files/rename', expect.objectContaining({ src: '/dir/test.txt', dst: '/dir/new-name.txt', alias: 'test-server' }))
    } finally {
      promptSpy.mockRestore()
    }
  })

  it('handleRename 名称相同时不应调用 API', async () => {
    const wrapper = createWrapper()
    const promptSpy = vi.spyOn(window, 'prompt').mockReturnValue('test.txt')
    try {
      wrapper.vm.selectedAccount = 'test-server'
      mockRequestPost.mockClear()
      await wrapper.vm.handleRename({ name: 'test.txt', path: '/dir/test.txt', is_dir: false } as any)
      expect(mockRequestPost).not.toHaveBeenCalled()
    } finally {
      promptSpy.mockRestore()
    }
  })

  it('handleRename 取消时不应调用 API', async () => {
    const wrapper = createWrapper()
    const promptSpy = vi.spyOn(window, 'prompt').mockReturnValue(null)
    try {
      wrapper.vm.selectedAccount = 'test-server'
      mockRequestPost.mockClear()
      await wrapper.vm.handleRename({ name: 'test.txt', path: '/dir/test.txt', is_dir: false } as any)
      expect(mockRequestPost).not.toHaveBeenCalled()
    } finally {
      promptSpy.mockRestore()
    }
  })

  it('handleRename 失败时不应崩溃', async () => {
    const wrapper = createWrapper()
    const promptSpy = vi.spyOn(window, 'prompt').mockReturnValue('new-name.txt')
    mockRequestPost.mockRejectedValueOnce(new Error('fail'))
    try {
      wrapper.vm.selectedAccount = 'test-server'
      await wrapper.vm.handleRename({ name: 'test.txt', path: '/dir/test.txt', is_dir: false } as any)
    } finally {
      promptSpy.mockRestore()
    }
  })

  it('handleCopy 有目标路径时应该调用 API', async () => {
    const wrapper = createWrapper()
    const promptSpy = vi.spyOn(window, 'prompt').mockReturnValue('/dir/test_copy.txt')
    try {
      wrapper.vm.selectedAccount = 'test-server'
      await wrapper.vm.handleCopy({ name: 'test.txt', path: '/dir/test.txt', is_dir: false } as any)
      expect(mockRequestPost).toHaveBeenCalledWith('/files/copy', expect.objectContaining({ src: '/dir/test.txt', dst: '/dir/test_copy.txt', alias: 'test-server' }))
    } finally {
      promptSpy.mockRestore()
    }
  })

  it('handleCopy 取消时不应调用 API', async () => {
    const wrapper = createWrapper()
    const promptSpy = vi.spyOn(window, 'prompt').mockReturnValue(null)
    try {
      wrapper.vm.selectedAccount = 'test-server'
      mockRequestPost.mockClear()
      await wrapper.vm.handleCopy({ name: 'test.txt', path: '/dir/test.txt', is_dir: false } as any)
      expect(mockRequestPost).not.toHaveBeenCalled()
    } finally {
      promptSpy.mockRestore()
    }
  })

  it('handleCopy 失败时不应崩溃', async () => {
    const wrapper = createWrapper()
    const promptSpy = vi.spyOn(window, 'prompt').mockReturnValue('/dir/test_copy.txt')
    mockRequestPost.mockRejectedValueOnce(new Error('fail'))
    try {
      wrapper.vm.selectedAccount = 'test-server'
      await wrapper.vm.handleCopy({ name: 'test.txt', path: '/dir/test.txt', is_dir: false } as any)
    } finally {
      promptSpy.mockRestore()
    }
  })

  it('handleDelete 失败时不应崩溃', async () => {
    mockRequestPost.mockRejectedValueOnce(new Error('fail'))
    const wrapper = createWrapper()
    wrapper.vm.selectedAccount = 'test-server'
    await wrapper.vm.handleDelete({ path: '/test.txt', name: 'test.txt' })
  })

  it('handleBatchDelete 失败时不应崩溃', async () => {
    mockRequestPost.mockRejectedValueOnce(new Error('fail'))
    const wrapper = createWrapper()
    wrapper.vm.selectedAccount = 'test-server'
    wrapper.vm.selectedPaths = ['/test.txt']
    await wrapper.vm.handleBatchDelete()
  })

  it('createDirectory 失败时不应崩溃', async () => {
    mockRequestPost.mockRejectedValueOnce(new Error('fail'))
    const wrapper = createWrapper()
    wrapper.vm.selectedAccount = 'test-server'
    wrapper.vm.newDirName = 'test-dir'
    await wrapper.vm.createDirectory()
  })

  it('createFile 根路径时应该正确拼接路径', async () => {
    const wrapper = createWrapper()
    wrapper.vm.selectedAccount = 'test-server'
    wrapper.vm.currentPath = '/'
    wrapper.vm.newFileName = 'test.txt'
    wrapper.vm.showCreateFileDialog = true
    await wrapper.vm.createFile()
    expect(mockRequestPost).toHaveBeenCalledWith('/files/content', expect.objectContaining({ path: '/test.txt' }))
  })

  it('createFile 非根路径时应该正确拼接路径', async () => {
    const wrapper = createWrapper()
    wrapper.vm.selectedAccount = 'test-server'
    wrapper.vm.currentPath = '/var/log'
    wrapper.vm.newFileName = 'test.txt'
    wrapper.vm.showCreateFileDialog = true
    await wrapper.vm.createFile()
    expect(mockRequestPost).toHaveBeenCalledWith('/files/content', expect.objectContaining({ path: '/var/log/test.txt' }))
  })

  it('createFile 失败时不应崩溃', async () => {
    mockRequestPost.mockRejectedValueOnce(new Error('fail'))
    const wrapper = createWrapper()
    wrapper.vm.selectedAccount = 'test-server'
    wrapper.vm.newFileName = 'test.txt'
    await wrapper.vm.createFile()
  })

  it('executeCommand 无账户时不应执行', async () => {
    const wrapper = createWrapper()
    wrapper.vm.selectedAccount = ''
    wrapper.vm.quickCommand = 'ls'
    mockRequestPost.mockClear()
    await wrapper.vm.executeCommand()
    expect(mockRequestPost).not.toHaveBeenCalled()
  })

  it('executeCommand 失败时不应添加到历史', async () => {
    mockRequestPost.mockRejectedValue(new Error('fail'))
    const wrapper = createWrapper()
    wrapper.vm.selectedAccount = 'test-server'
    wrapper.vm.quickCommand = 'ls'
    await wrapper.vm.executeCommand()
    expect(wrapper.vm.commandHistory).toHaveLength(0)
  })

  it('openSingleChmod 有权限字符串时应该解析权限', () => {
    const wrapper = createWrapper()
    wrapper.vm.openSingleChmod({ name: 'test.txt', path: '/test.txt', is_dir: false, permission: '-rwxr-xr--' })
    expect(wrapper.vm.chmodMode).toBe(0o754)
    expect(wrapper.vm.showChmodDialog).toBe(true)
    expect(wrapper.vm.chmodSingleItem).toBeTruthy()
  })

  it('openSingleChmod 无权限字符串时应该使用默认值', () => {
    const wrapper = createWrapper()
    wrapper.vm.openSingleChmod({ name: 'test.txt', path: '/test.txt', is_dir: false })
    expect(wrapper.vm.showChmodDialog).toBe(true)
  })

  it('applyChmod 批量时应该调用 batch chmod API 并传递参数', async () => {
    const wrapper = createWrapper()
    wrapper.vm.selectedAccount = 'test-server'
    wrapper.vm.chmodSingleItem = null
    wrapper.vm.chmodPaths = []
    wrapper.vm.selectedPaths = ['/a', '/b']
    wrapper.vm.chmodMode = 0o755
    await wrapper.vm.applyChmod()
    expect(mockRequestPost).toHaveBeenCalledWith('/files/batch/chmod', expect.objectContaining({
      paths: ['/a', '/b'],
      mode: '0755',
      recursive: false,
      alias: 'test-server',
    }))
    expect(wrapper.vm.showChmodDialog).toBe(false)
  })

  it('applyChmod 失败时不应崩溃', async () => {
    mockRequestPost.mockRejectedValueOnce(new Error('fail'))
    const wrapper = createWrapper()
    wrapper.vm.selectedAccount = 'test-server'
    wrapper.vm.chmodSingleItem = { name: 'test.txt', path: '/test.txt' } as any
    wrapper.vm.chmodPaths = ['/test.txt']
    await wrapper.vm.applyChmod()
  })

  it('bookmarks 应该包含预定义路径', () => {
    const wrapper = createWrapper()
    expect(wrapper.vm.bookmarks).toHaveLength(4)
    expect(wrapper.vm.bookmarks[0].path).toBe('/var/log')
  })

  it('sshAccounts 应该返回 store 数据', () => {
    const wrapper = createWrapper()
    expect(wrapper.vm.sshAccounts).toHaveLength(1)
  })

  it('应该渲染批量工具栏（当有选中文件时）', async () => {
    const wrapper = createWrapper()
    wrapper.vm.selectedPaths = ['/test.txt']
    await nextTick()
    expect(wrapper.find('.batch-toolbar').exists()).toBe(true)
    expect(wrapper.text()).toContain('已选 1 项')
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

  it('displayProcesses 用户过滤应该生效', async () => {
    processStoreMock.processes = [
      { pid: 1, name: 'proc1', user: 'root', status: 'running', cpu_percent: 0, mem_percent: 0, vsz: 0, rss: 0, command: '' },
      { pid: 2, name: 'proc2', user: 'admin', status: 'running', cpu_percent: 0, mem_percent: 0, vsz: 0, rss: 0, command: '' },
    ]
    processStoreMock.filteredProcesses = processStoreMock.processes
    const wrapper = createWrapper()
    wrapper.vm.selectedAlias = 'test-server'
    wrapper.vm.userFilterValue = 'root'
    await nextTick()
    expect(wrapper.vm.displayProcesses.length).toBe(1)
    expect(wrapper.vm.displayProcesses[0].user).toBe('root')
  })

  it('displayProcesses 异常过滤应该生效', async () => {
    processStoreMock.processes = [
      { pid: 1, name: 'proc1', user: 'root', status: 'running', cpu_percent: 0, mem_percent: 0, vsz: 0, rss: 0, command: '' },
      { pid: 2, name: 'proc2', user: 'root', status: 'running', cpu_percent: 0, mem_percent: 0, vsz: 0, rss: 0, command: '' },
    ]
    processStoreMock.filteredProcesses = processStoreMock.processes
    processStoreMock.anomalyPidSet = new Set([1])
    const wrapper = createWrapper()
    wrapper.vm.selectedAlias = 'test-server'
    wrapper.vm.showAnomalyOnly = true
    await nextTick()
    expect(wrapper.vm.displayProcesses.length).toBe(1)
    expect(wrapper.vm.displayProcesses[0].pid).toBe(1)
  })

  it('displayProcesses 排序应该生效', async () => {
    processStoreMock.processes = [
      { pid: 1, name: 'proc1', user: 'root', status: 'running', cpu_percent: 10, mem_percent: 0, vsz: 0, rss: 0, command: '' },
      { pid: 2, name: 'proc2', user: 'root', status: 'running', cpu_percent: 50, mem_percent: 0, vsz: 0, rss: 0, command: '' },
    ]
    processStoreMock.filteredProcesses = processStoreMock.processes
    const wrapper = createWrapper()
    wrapper.vm.selectedAlias = 'test-server'
    wrapper.vm.sortColumn = 'cpu_percent'
    wrapper.vm.sortOrder = 'desc'
    await nextTick()
    expect(wrapper.vm.displayProcesses[0].cpu_percent).toBe(50)
  })

  it('statusColor idle 应该返回 primary', () => {
    const wrapper = createWrapper()
    expect(wrapper.vm.statusColor('idle')).toBe('primary')
  })

  it('statusColor 未知状态应该返回 info', () => {
    const wrapper = createWrapper()
    expect(wrapper.vm.statusColor('unknown')).toBe('info')
  })

  it('onRefreshIntervalChange 应该设置刷新间隔', () => {
    const wrapper = createWrapper()
    wrapper.vm.onRefreshIntervalChange(5000)
    expect(wrapper.vm.refreshIntervalValue).toBe(5000)
    expect(processStoreMock.refreshInterval).toBe(5000)
  })

  it('onRefreshIntervalChange 大于0且未流式时应该启动自动刷新', () => {
    processStoreMock.streaming = false
    const wrapper = createWrapper()
    wrapper.vm.onRefreshIntervalChange(5000)
    expect(processStoreMock.startAutoRefresh).toHaveBeenCalled()
  })

  it('onRefreshIntervalChange 为0时应该停止自动刷新', () => {
    const wrapper = createWrapper()
    wrapper.vm.onRefreshIntervalChange(0)
    expect(processStoreMock.stopAutoRefresh).toHaveBeenCalled()
  })

  it('toggleStream 流式中应该断开', () => {
    processStoreMock.streaming = true
    const wrapper = createWrapper()
    wrapper.vm.toggleStream()
    expect(processStoreMock.disconnect).toHaveBeenCalled()
  })

  it('toggleStream 非流式时应该连接', () => {
    processStoreMock.streaming = false
    const wrapper = createWrapper()
    wrapper.vm.toggleStream()
    expect(processStoreMock.connectWebSocket).toHaveBeenCalled()
  })

  it('showDetail 应该获取进程详情并打开对话框', async () => {
    const wrapper = createWrapper()
    await wrapper.vm.showDetail(1234)
    expect(processStoreMock.fetchProcessDetail).toHaveBeenCalledWith(1234)
    expect(wrapper.vm.detailVisible).toBe(true)
  })

  it('doKill 应该终止进程并刷新', async () => {
    const wrapper = createWrapper()
    await wrapper.vm.doKill(1234, 'SIGTERM')
    expect(processStoreMock.killProcess).toHaveBeenCalledWith(1234, 'SIGTERM')
    expect(processStoreMock.fetchProcessList).toHaveBeenCalled()
  })

  it('doBatchKill 无选中行时不应执行', async () => {
    const wrapper = createWrapper()
    wrapper.vm.selectedRows = []
    await wrapper.vm.doBatchKill('SIGTERM')
    expect(processStoreMock.batchKill).not.toHaveBeenCalled()
  })

  it('doBatchKill 有选中行时应该批量终止', async () => {
    const wrapper = createWrapper()
    wrapper.vm.selectedRows = [{ pid: 1 }, { pid: 2 }]
    await wrapper.vm.doBatchKill('SIGTERM')
    expect(processStoreMock.batchKill).toHaveBeenCalledWith([1, 2], 'SIGTERM')
  })

  it('showNiceDialog 应该设置 Nice 值并打开对话框', () => {
    processStoreMock.processes = [{ pid: 1234, name: 'test', nice: 5, user: 'root', status: 'running', cpu_percent: 0, mem_percent: 0, vsz: 0, rss: 0, command: '' }]
    const wrapper = createWrapper()
    wrapper.vm.showNiceDialog(1234)
    expect(wrapper.vm.nicePid).toBe(1234)
    expect(wrapper.vm.niceValue).toBe(5)
    expect(wrapper.vm.niceVisible).toBe(true)
  })

  it('doSetNice 应该设置 Nice 值并关闭对话框', async () => {
    const wrapper = createWrapper()
    wrapper.vm.nicePid = 1234
    wrapper.vm.niceValue = 10
    wrapper.vm.niceVisible = true
    await wrapper.vm.doSetNice()
    expect(processStoreMock.setNice).toHaveBeenCalledWith(1234, 10)
    expect(wrapper.vm.niceVisible).toBe(false)
  })

  it('goToFileManager 应该导航到文件管理器', () => {
    const wrapper = createWrapper()
    wrapper.vm.goToFileManager('/home/user')
    expect(mockPush).toHaveBeenCalledWith({ path: '/file-manager', query: { path: '/home/user' } })
  })

  it('serviceControl 应该调用 store', async () => {
    const wrapper = createWrapper()
    await wrapper.vm.serviceControl('nginx', 'restart')
    expect(processStoreMock.serviceControl).toHaveBeenCalledWith('nginx', 'restart')
  })

  it('toggleKillMenu 同一 pid 应该关闭菜单', () => {
    const wrapper = createWrapper()
    wrapper.vm.currentKillPid = 1234
    wrapper.vm.toggleKillMenu(1234)
    expect(wrapper.vm.currentKillPid).toBeNull()
  })

  it('toggleKillMenu 不同 pid 应该打开菜单', () => {
    const wrapper = createWrapper()
    wrapper.vm.currentKillPid = 1234
    wrapper.vm.toggleKillMenu(5678)
    expect(wrapper.vm.currentKillPid).toBe(5678)
  })

  it('onSelectionChange 应该更新 selectedRows', () => {
    const wrapper = createWrapper()
    const rows = [{ pid: 1 }, { pid: 2 }]
    wrapper.vm.onSelectionChange(rows)
    expect(wrapper.vm.selectedRows).toEqual(rows)
  })

  it('onSelectionChange 有 selectedPids 时应该同步到 store', () => {
    const wrapper = createWrapper()
    const rows = [{ pid: 1 }, { pid: 2 }]
    wrapper.vm.onSelectionChange(rows)
    expect(processStoreMock.selectedPids.has(1)).toBe(true)
    expect(processStoreMock.selectedPids.has(2)).toBe(true)
  })

  it('onMounted 有默认账户时应该自动选择并刷新', async () => {
    createWrapper()
    await nextTick()
    await nextTick()
    expect(processStoreMock.fetchProcessList).toHaveBeenCalled()
  })

  it('onBeforeUnmount 应该断开连接并停止自动刷新', () => {
    const wrapper = createWrapper()
    wrapper.unmount()
    expect(processStoreMock.disconnect).toHaveBeenCalled()
    expect(processStoreMock.stopAutoRefresh).toHaveBeenCalled()
  })

  it('displayProcesses 应该按用户过滤', async () => {
    processStoreMock.processes = [
      { pid: 1, name: 'proc1', user: 'root', status: 'running', cpu_percent: 0, mem_percent: 0, vsz: 0, rss: 0, command: '' },
      { pid: 2, name: 'proc2', user: 'www', status: 'running', cpu_percent: 0, mem_percent: 0, vsz: 0, rss: 0, command: '' },
    ]
    processStoreMock.filteredProcesses = processStoreMock.processes
    const wrapper = createWrapper()
    wrapper.vm.selectedAlias = 'test-server'
    wrapper.vm.userFilterValue = 'root'
    await nextTick()
    expect(wrapper.vm.displayProcesses).toHaveLength(1)
    expect(wrapper.vm.displayProcesses[0].user).toBe('root')
  })

  it('displayProcesses 应该按异常过滤', async () => {
    processStoreMock.processes = [
      { pid: 1, name: 'proc1', user: 'root', status: 'running', cpu_percent: 0, mem_percent: 0, vsz: 0, rss: 0, command: '' },
      { pid: 2, name: 'proc2', user: 'root', status: 'zombie', cpu_percent: 0, mem_percent: 0, vsz: 0, rss: 0, command: '' },
    ]
    processStoreMock.filteredProcesses = processStoreMock.processes
    processStoreMock.anomalyPidSet = new Set([2])
    const wrapper = createWrapper()
    wrapper.vm.selectedAlias = 'test-server'
    wrapper.vm.showAnomalyOnly = true
    await nextTick()
    expect(wrapper.vm.displayProcesses).toHaveLength(1)
    expect(wrapper.vm.displayProcesses[0].pid).toBe(2)
  })

  it('statusColor 未知状态应该返回 info', () => {
    const wrapper = createWrapper()
    expect(wrapper.vm.statusColor('unknown')).toBe('info')
  })

  it('formatStatus 空字符串应该返回 -', () => {
    const wrapper = createWrapper()
    expect(wrapper.vm.formatStatus('')).toBe('-')
  })

  it('formatStatus 应该首字母大写', () => {
    const wrapper = createWrapper()
    expect(wrapper.vm.formatStatus('running')).toBe('Running')
    expect(wrapper.vm.formatStatus('sleeping')).toBe('Sleeping')
  })

  it('onRefreshIntervalChange 正值且未流式时应该启动自动刷新', () => {
    processStoreMock.streaming = false
    const wrapper = createWrapper()
    wrapper.vm.onRefreshIntervalChange(3000)
    expect(wrapper.vm.refreshIntervalValue).toBe(3000)
    expect(processStoreMock.refreshInterval).toBe(3000)
    expect(processStoreMock.startAutoRefresh).toHaveBeenCalled()
  })

  it('onRefreshIntervalChange 正值且已流式时不应启动自动刷新', () => {
    processStoreMock.streaming = true
    const wrapper = createWrapper()
    wrapper.vm.onRefreshIntervalChange(3000)
    expect(processStoreMock.startAutoRefresh).not.toHaveBeenCalled()
  })

  it('onRefreshIntervalChange 零值时应该停止自动刷新', () => {
    const wrapper = createWrapper()
    wrapper.vm.onRefreshIntervalChange(0)
    expect(wrapper.vm.refreshIntervalValue).toBe(0)
    expect(processStoreMock.stopAutoRefresh).toHaveBeenCalled()
  })

  it('toggleStream 流式中应该断开连接', () => {
    processStoreMock.streaming = true
    const wrapper = createWrapper()
    wrapper.vm.toggleStream()
    expect(processStoreMock.disconnect).toHaveBeenCalled()
  })

  it('toggleStream 非流式应该连接 WebSocket', () => {
    processStoreMock.streaming = false
    const wrapper = createWrapper()
    wrapper.vm.selectedAlias = 'test-server'
    wrapper.vm.toggleStream()
    expect(processStoreMock.connectWebSocket).toHaveBeenCalledWith('test-server')
  })

  it('showDetail 应该获取详情并打开对话框', async () => {
    processStoreMock.fetchProcessDetail = vi.fn().mockResolvedValue({ pid: 1234, name: 'test', status: 'running' })
    const wrapper = createWrapper()
    await wrapper.vm.showDetail(1234)
    expect(processStoreMock.fetchProcessDetail).toHaveBeenCalledWith(1234)
    expect(wrapper.vm.currentDetail).toBeTruthy()
    expect(wrapper.vm.detailVisible).toBe(true)
  })

  it('doKill 应该清除 kill 菜单并终止进程', async () => {
    const wrapper = createWrapper()
    wrapper.vm.currentKillPid = 1234
    await wrapper.vm.doKill(1234, 'SIGTERM')
    expect(wrapper.vm.currentKillPid).toBeNull()
    expect(processStoreMock.killProcess).toHaveBeenCalledWith(1234, 'SIGTERM')
  })

  it('doBatchKill 应该批量终止选中进程', async () => {
    const wrapper = createWrapper()
    wrapper.vm.selectedRows = [{ pid: 1 }, { pid: 2 }]
    await wrapper.vm.doBatchKill('SIGTERM')
    expect(processStoreMock.batchKill).toHaveBeenCalledWith([1, 2], 'SIGTERM')
  })

  it('doBatchKill 无选中进程时不应调用 store', async () => {
    const wrapper = createWrapper()
    wrapper.vm.selectedRows = []
    await wrapper.vm.doBatchKill('SIGTERM')
    expect(processStoreMock.batchKill).not.toHaveBeenCalled()
  })

  it('showNiceDialog 应该设置 nice 值并打开对话框', () => {
    processStoreMock.processes = [{ pid: 1234, name: 'test', nice: 5 }]
    const wrapper = createWrapper()
    wrapper.vm.showNiceDialog(1234)
    expect(wrapper.vm.nicePid).toBe(1234)
    expect(wrapper.vm.currentNiceValue).toBe(5)
    expect(wrapper.vm.niceValue).toBe(5)
    expect(wrapper.vm.niceVisible).toBe(true)
  })

  it('showNiceDialog 进程无 nice 值时应该使用默认值', () => {
    processStoreMock.processes = [{ pid: 1234, name: 'test' }]
    const wrapper = createWrapper()
    wrapper.vm.showNiceDialog(1234)
    expect(wrapper.vm.currentNiceValue).toBeNull()
    expect(wrapper.vm.niceValue).toBe(0)
  })

  it('doSetNice 应该设置 nice 值并关闭对话框', async () => {
    const wrapper = createWrapper()
    wrapper.vm.nicePid = 1234
    wrapper.vm.niceValue = 10
    wrapper.vm.niceVisible = true
    await wrapper.vm.doSetNice()
    expect(processStoreMock.setNice).toHaveBeenCalledWith(1234, 10)
    expect(wrapper.vm.niceVisible).toBe(false)
  })

  it('goToFileManager 应该导航到文件管理器', () => {
    const wrapper = createWrapper()
    wrapper.vm.detailVisible = true
    wrapper.vm.goToFileManager('/home/user')
    expect(mockPush).toHaveBeenCalledWith({ path: '/file-manager', query: { path: '/home/user' } })
    expect(wrapper.vm.detailVisible).toBe(false)
  })

  it('serviceControl 应该调用 store 方法', async () => {
    const wrapper = createWrapper()
    await wrapper.vm.serviceControl('nginx', 'restart')
    expect(processStoreMock.serviceControl).toHaveBeenCalledWith('nginx', 'restart')
  })

  it('toggleKillMenu 不同 PID 应该设置新 PID', async () => {
    const wrapper = createWrapper()
    wrapper.vm.currentKillPid = 1234
    wrapper.vm.toggleKillMenu(5678)
    await nextTick()
    expect(wrapper.vm.currentKillPid).toBe(5678)
  })

  it('toggleKillMenu 相同 PID 应该关闭菜单', () => {
    const wrapper = createWrapper()
    wrapper.vm.currentKillPid = 1234
    wrapper.vm.toggleKillMenu(1234)
    expect(wrapper.vm.currentKillPid).toBeNull()
  })

  it('handleOutsideClick 非 kill-dropdown 区域应该关闭菜单', () => {
    const wrapper = createWrapper()
    wrapper.vm.currentKillPid = 1234
    const event = { target: document.createElement('div') } as unknown as MouseEvent
    wrapper.vm.handleOutsideClick(event)
    expect(wrapper.vm.currentKillPid).toBeNull()
  })

  it('onMounted 有默认账户且 refreshInterval > 0 时应该启动自动刷新', async () => {
    processStoreMock.refreshInterval = 3000
    createWrapper()
    await nextTick()
    await nextTick()
    await nextTick()
    await nextTick()
    expect(processStoreMock.startAutoRefresh).toHaveBeenCalled()
  })

  it('clearSelection 应该清空选中行', () => {
    const wrapper = createWrapper()
    wrapper.vm.selectedRows = [{ pid: 1 }, { pid: 2 }]
    wrapper.vm.clearSelection()
    expect(wrapper.vm.selectedRows).toEqual([])
  })

  it('resourceColor 应该返回正确的颜色', () => {
    const wrapper = createWrapper()
    expect(wrapper.vm.resourceColor(95, 'cpu')).toBe('#ef4444')
    expect(wrapper.vm.resourceColor(60, 'cpu')).toBe('#f59e0b')
    expect(wrapper.vm.resourceColor(30, 'cpu')).toBe('#22c55e')
    expect(wrapper.vm.resourceColor(85, 'mem')).toBe('#ef4444')
    expect(wrapper.vm.resourceColor(60, 'mem')).toBe('#f59e0b')
    expect(wrapper.vm.resourceColor(30, 'mem')).toBe('#22c55e')
  })

  it('formatBytes 应该正确格式化', () => {
    const wrapper = createWrapper()
    expect(wrapper.vm.formatBytes(500)).toBe('500 KB')
    expect(wrapper.vm.formatBytes(2048)).toBe('2.0 MB')
    expect(wrapper.vm.formatBytes(1048576)).toBe('1.00 GB')
  })

  it('formatBytes 无效值应该返回 -', () => {
    const wrapper = createWrapper()
    expect(wrapper.vm.formatBytes(NaN)).toBe('-')
  })

  it('toggleSort 同列应该切换排序方向', () => {
    const wrapper = createWrapper()
    wrapper.vm.sortColumn = 'cpu_percent'
    wrapper.vm.sortOrder = 'desc'
    wrapper.vm.toggleSort('cpu_percent')
    expect(wrapper.vm.sortOrder).toBe('asc')
  })

  it('toggleSort 不同列应该设置新列并默认降序', () => {
    const wrapper = createWrapper()
    wrapper.vm.sortColumn = 'cpu_percent'
    wrapper.vm.sortOrder = 'asc'
    wrapper.vm.toggleSort('mem_percent')
    expect(wrapper.vm.sortColumn).toBe('mem_percent')
    expect(wrapper.vm.sortOrder).toBe('desc')
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

  it('未选择服务器时应该显示空状态', () => {
    const wrapper = createWrapper()
    expect(wrapper.text()).toContain('请先选择一个 SSH 服务器')
  })

  it('选择服务器后应该显示 Tab 内容', async () => {
    const wrapper = createWrapper()
    wrapper.vm.selectedAlias = 'test-server'
    await nextTick()
    expect(wrapper.find('.tab-content').exists()).toBe(true)
  })

  it('onAccountChange 应该更新 selectedAlias 并刷新数据', async () => {
    const wrapper = createWrapper()
    wrapper.vm.onAccountChange('new-server')
    expect(wrapper.vm.selectedAlias).toBe('new-server')
  })

  it('默认 activeTab 应该是 firewall', () => {
    const wrapper = createWrapper()
    expect(wrapper.vm.activeTab).toBe('firewall')
  })

  it('切换到 ssh Tab 应该调用 refreshSsh', async () => {
    const wrapper = createWrapper()
    wrapper.vm.selectedAlias = 'test-server'
    await nextTick()
    vi.clearAllMocks()
    wrapper.vm.activeTab = 'ssh'
    await nextTick()
    expect(securityNetworkStoreMock.loadSshConfig).toHaveBeenCalled()
    expect(securityNetworkStoreMock.loadSshKeys).toHaveBeenCalled()
  })

  it('切换到 audit Tab 应该调用 refreshAudit', async () => {
    const wrapper = createWrapper()
    wrapper.vm.selectedAlias = 'test-server'
    await nextTick()
    vi.clearAllMocks()
    wrapper.vm.activeTab = 'audit'
    await nextTick()
    expect(securityNetworkStoreMock.loadLoginLogs).toHaveBeenCalled()
  })

  it('切换到 network Tab 不应该调用任何刷新', async () => {
    const wrapper = createWrapper()
    wrapper.vm.selectedAlias = 'test-server'
    await nextTick()
    vi.clearAllMocks()
    wrapper.vm.activeTab = 'network'
    await nextTick()
    expect(securityNetworkStoreMock.loadFirewallBackend).not.toHaveBeenCalled()
    expect(securityNetworkStoreMock.loadSshConfig).not.toHaveBeenCalled()
  })

  it('refreshFirewall 应该调用 store 方法', async () => {
    const wrapper = createWrapper()
    await wrapper.vm.refreshFirewall()
    expect(securityNetworkStoreMock.loadFirewallBackend).toHaveBeenCalled()
    expect(securityNetworkStoreMock.loadFirewallRules).toHaveBeenCalled()
  })

  it('refreshSsh 应该调用 store 方法', async () => {
    const wrapper = createWrapper()
    await wrapper.vm.refreshSsh()
    expect(securityNetworkStoreMock.loadSshConfig).toHaveBeenCalled()
    expect(securityNetworkStoreMock.loadSshKeys).toHaveBeenCalled()
  })

  it('addPortRule 无效端口应该显示警告', async () => {
    const { Md3Message } = await import('@/components/md3')
    const wrapper = createWrapper()
    wrapper.vm.newPort = ''
    await wrapper.vm.addPortRule()
    expect(Md3Message.warning).toHaveBeenCalled()
  })

  it('addPortRule 有效端口应该调用 store', async () => {
    const { Md3Message } = await import('@/components/md3')
    const wrapper = createWrapper()
    wrapper.vm.newPort = 8080
    wrapper.vm.newProtocol = 'tcp'
    wrapper.vm.newAction = 'allow'
    await wrapper.vm.addPortRule()
    expect(securityNetworkStoreMock.addPortRule).toHaveBeenCalledWith(8080, 'tcp', 'allow')
    expect(Md3Message.success).toHaveBeenCalled()
  })

  it('addPortRule 异常时应该显示错误', async () => {
    const { Md3Message } = await import('@/components/md3')
    securityNetworkStoreMock.addPortRule = vi.fn().mockRejectedValue(new Error('fail'))
    const wrapper = createWrapper()
    wrapper.vm.newPort = 8080
    await wrapper.vm.addPortRule()
    expect(Md3Message.error).toHaveBeenCalled()
  })

  it('addIpRule 空 IP 应该显示警告', async () => {
    const { Md3Message } = await import('@/components/md3')
    const wrapper = createWrapper()
    wrapper.vm.newIp = ''
    await wrapper.vm.addIpRule()
    expect(Md3Message.warning).toHaveBeenCalled()
  })

  it('addIpRule 有效 IP 应该调用 store', async () => {
    const { Md3Message } = await import('@/components/md3')
    const wrapper = createWrapper()
    wrapper.vm.newIp = '192.168.1.1'
    wrapper.vm.newIpAction = 'allow'
    await wrapper.vm.addIpRule()
    expect(securityNetworkStoreMock.addIpRule).toHaveBeenCalledWith('192.168.1.1', 'allow', undefined)
    expect(Md3Message.success).toHaveBeenCalled()
  })

  it('confirmChangeSshPort 无效端口应该显示警告', async () => {
    const { Md3Message } = await import('@/components/md3')
    const wrapper = createWrapper()
    wrapper.vm.sshPortInput = ''
    await wrapper.vm.confirmChangeSshPort()
    expect(Md3Message.warning).toHaveBeenCalled()
  })

  it('addSshKey 空公钥应该显示警告', async () => {
    const { Md3Message } = await import('@/components/md3')
    const wrapper = createWrapper()
    wrapper.vm.newPublicKey = ''
    await wrapper.vm.addSshKey()
    expect(Md3Message.warning).toHaveBeenCalled()
  })

  it('addSshKey 有效公钥应该调用 store', async () => {
    const { Md3Message } = await import('@/components/md3')
    const wrapper = createWrapper()
    wrapper.vm.newPublicKey = 'ssh-rsa AAAA...'
    await wrapper.vm.addSshKey()
    expect(securityNetworkStoreMock.addSshKey).toHaveBeenCalledWith('ssh-rsa AAAA...')
    expect(Md3Message.success).toHaveBeenCalled()
  })

  it('generateSshKey 应该调用 store', async () => {
    const { Md3Message } = await import('@/components/md3')
    const wrapper = createWrapper()
    wrapper.vm.keyAlgorithm = 'ed25519'
    wrapper.vm.keyBits = 256
    await wrapper.vm.generateSshKey()
    expect(securityNetworkStoreMock.generateSshKey).toHaveBeenCalled()
    expect(Md3Message.success).toHaveBeenCalled()
  })

  it('parsePingStats 应该正确解析 ping 输出', () => {
    const wrapper = createWrapper()
    const output = '5 packets transmitted, 4 received, 20% packet loss\nrtt min/avg/max/mdev = 1.2/3.4/5.6/1.1'
    const stats = wrapper.vm.parsePingStats(output)
    expect(stats.transmitted).toBe('5')
    expect(stats.received).toBe('4')
    expect(stats.loss).toBe('20')
    expect(stats.min).toBe('1.2')
    expect(stats.avg).toBe('3.4')
    expect(stats.max).toBe('5.6')
  })

  it('parseTraceroute 应该正确解析 traceroute 输出', () => {
    const wrapper = createWrapper()
    const output = ' 1  gateway (192.168.1.1) 1.234 ms 2.345 ms 3.456 ms'
    const hops = wrapper.vm.parseTraceroute(output)
    expect(hops).toHaveLength(1)
    expect(hops[0].hop).toBe('1')
    expect(hops[0].host).toBe('gateway')
    expect(hops[0].ip).toBe('192.168.1.1')
  })

  it('parsePortScan 应该正确解析端口扫描输出', () => {
    const wrapper = createWrapper()
    const output = '22/tcp open ssh\n80/tcp open http'
    const results = wrapper.vm.parsePortScan(output)
    expect(results).toHaveLength(2)
    expect(results[0].port).toBe('22/tcp')
    expect(results[0].state).toBe('open')
    expect(results[0].service).toBe('ssh')
  })

  it('runPing 空目标应该显示警告', async () => {
    const { Md3Message } = await import('@/components/md3')
    const wrapper = createWrapper()
    wrapper.vm.pingTarget = ''
    await wrapper.vm.runPing()
    expect(Md3Message.warning).toHaveBeenCalled()
  })

  it('runTraceroute 空目标应该显示警告', async () => {
    const { Md3Message } = await import('@/components/md3')
    const wrapper = createWrapper()
    wrapper.vm.tracerouteTarget = ''
    await wrapper.vm.runTraceroute()
    expect(Md3Message.warning).toHaveBeenCalled()
  })

  it('runPortScan 空目标应该显示警告', async () => {
    const { Md3Message } = await import('@/components/md3')
    const wrapper = createWrapper()
    wrapper.vm.scanTarget = ''
    await wrapper.vm.runPortScan()
    expect(Md3Message.warning).toHaveBeenCalled()
  })

  it('runPortScan 空端口范围应该显示警告', async () => {
    const { Md3Message } = await import('@/components/md3')
    const wrapper = createWrapper()
    wrapper.vm.scanTarget = '192.168.1.1'
    wrapper.vm.scanPortRange = ''
    await wrapper.vm.runPortScan()
    expect(Md3Message.warning).toHaveBeenCalled()
  })

  it('formatAuditTime 应该正确格式化时间戳', () => {
    const wrapper = createWrapper()
    const result = wrapper.vm.formatAuditTime('2024-01-15T10:30:00Z')
    expect(result).toBeTruthy()
  })

  it('goToAuditLog 应该导航到审计日志页面', () => {
    const wrapper = createWrapper()
    wrapper.vm.goToAuditLog()
    expect(mockPush).toHaveBeenCalledWith('/audit-log')
  })

  it('applyLogFilters 应该调用 loadLoginLogs', async () => {
    const wrapper = createWrapper()
    wrapper.vm.logTimeFilter = '24h'
    wrapper.vm.logStatusFilter = 'success'
    wrapper.vm.logIpFilter = '192.168.1.1'
    await wrapper.vm.applyLogFilters()
    expect(securityNetworkStoreMock.loadLoginLogs).toHaveBeenCalledWith(
      expect.objectContaining({ time_range: '24h', status: 'success', ip: '192.168.1.1' })
    )
  })

  it('applyLogFilters 全部默认时不应传递过滤参数', async () => {
    const wrapper = createWrapper()
    wrapper.vm.logTimeFilter = 'all'
    wrapper.vm.logStatusFilter = 'all'
    wrapper.vm.logIpFilter = ''
    await wrapper.vm.applyLogFilters()
    expect(securityNetworkStoreMock.loadLoginLogs).toHaveBeenCalledWith({})
  })

  it('sshOptions 计算属性应该返回正确的选项', () => {
    const wrapper = createWrapper()
    const options = wrapper.vm.sshOptions
    expect(options).toHaveLength(1)
    expect(options[0].value).toBe('test-server')
  })

  it('firewallBackend 计算属性应该返回 store 数据', () => {
    const wrapper = createWrapper()
    expect(wrapper.vm.firewallBackend).toBeNull()
  })

  it('sshConfig 计算属性应该返回 store 数据', () => {
    const wrapper = createWrapper()
    expect(wrapper.vm.sshConfig).toBeNull()
  })

  it('portRules 计算属性应该过滤端口规则', () => {
    securityNetworkStoreMock.firewallRules = [
      { port: 80, protocol: 'tcp', action: 'allow' },
      { source: '192.168.1.1', action: 'deny' },
    ]
    const wrapper = createWrapper()
    expect(wrapper.vm.portRules).toHaveLength(1)
    expect(wrapper.vm.portRules[0].port).toBe(80)
  })

  it('ipRules 计算属性应该过滤 IP 规则', () => {
    securityNetworkStoreMock.firewallRules = [
      { port: 80, protocol: 'tcp', action: 'allow' },
      { source: '192.168.1.1', action: 'deny' },
    ]
    const wrapper = createWrapper()
    expect(wrapper.vm.ipRules).toHaveLength(1)
    expect(wrapper.vm.ipRules[0].source).toBe('192.168.1.1')
  })

  it('bannedIpRows 应该从 fail2banStatus 解析封禁 IP', () => {
    securityNetworkStoreMock.fail2banStatus = {
      running: true,
      banned_ips: { sshd: ['1.2.3.4', '5.6.7.8'] },
    }
    const wrapper = createWrapper()
    expect(wrapper.vm.bannedIpRows).toHaveLength(2)
    expect(wrapper.vm.bannedIpRows[0].ip).toBe('1.2.3.4')
    expect(wrapper.vm.bannedIpRows[0].jail).toBe('sshd')
  })

  it('recentAuditLogs 应该返回 auditStore 的前5条', () => {
    const wrapper = createWrapper()
    expect(wrapper.vm.recentAuditLogs).toEqual([])
  })

  it('parseTraceroute 简单匹配应该正确解析', () => {
    const wrapper = createWrapper()
    const output = ' 1  192.168.1.1  1.234 ms'
    const hops = wrapper.vm.parseTraceroute(output)
    expect(hops).toHaveLength(1)
    expect(hops[0].hop).toBe('1')
    expect(hops[0].host).toBe('192.168.1.1')
    expect(hops[0].rtt1).toBe('1.234 ms')
    expect(hops[0].rtt2).toBe('-')
    expect(hops[0].rtt3).toBe('-')
  })

  it('runPing 成功时应该更新 pingOutput 和 pingStats', async () => {
    securityNetworkStoreMock.runPing = vi.fn().mockResolvedValue({ output: '5 packets transmitted, 5 received, 0% packet loss\nrtt min/avg/max/mdev = 1.0/2.0/3.0/0.5' })
    const wrapper = createWrapper()
    wrapper.vm.pingTarget = '192.168.1.1'
    await wrapper.vm.runPing()
    expect(wrapper.vm.pingOutput).toBeTruthy()
    expect(wrapper.vm.pingStats).toBeTruthy()
  })

  it('runPing 失败时应该显示错误', async () => {
    const { Md3Message } = await import('@/components/md3')
    securityNetworkStoreMock.runPing = vi.fn().mockRejectedValue(new Error('fail'))
    const wrapper = createWrapper()
    wrapper.vm.pingTarget = '192.168.1.1'
    await wrapper.vm.runPing()
    expect(Md3Message.error).toHaveBeenCalledWith('执行失败')
  })

  it('runTraceroute 成功有跳数时应该更新 tracerouteHops', async () => {
    securityNetworkStoreMock.runTraceroute = vi.fn().mockResolvedValue({ output: ' 1  gateway (192.168.1.1) 1.234 ms 2.345 ms 3.456 ms' })
    const wrapper = createWrapper()
    wrapper.vm.tracerouteTarget = '8.8.8.8'
    await wrapper.vm.runTraceroute()
    expect(wrapper.vm.tracerouteHops.length).toBeGreaterThan(0)
  })

  it('runTraceroute 成功无跳数时应该更新 tracerouteRaw', async () => {
    securityNetworkStoreMock.runTraceroute = vi.fn().mockResolvedValue({ output: 'no route' })
    const wrapper = createWrapper()
    wrapper.vm.tracerouteTarget = '8.8.8.8'
    await wrapper.vm.runTraceroute()
    expect(wrapper.vm.tracerouteRaw).toBe('no route')
  })

  it('runTraceroute 失败时应该显示错误', async () => {
    const { Md3Message } = await import('@/components/md3')
    securityNetworkStoreMock.runTraceroute = vi.fn().mockRejectedValue(new Error('fail'))
    const wrapper = createWrapper()
    wrapper.vm.tracerouteTarget = '8.8.8.8'
    await wrapper.vm.runTraceroute()
    expect(Md3Message.error).toHaveBeenCalledWith('执行失败')
  })

  it('runPortScan 成功有结果时应该更新 scanResults', async () => {
    securityNetworkStoreMock.runPortScan = vi.fn().mockResolvedValue({ output: '22/tcp open ssh\n80/tcp open http' })
    const wrapper = createWrapper()
    wrapper.vm.scanTarget = '192.168.1.1'
    wrapper.vm.scanPortRange = '1-1000'
    await wrapper.vm.runPortScan()
    expect(wrapper.vm.scanResults.length).toBeGreaterThan(0)
  })

  it('runPortScan 成功无结果时应该更新 scanRaw', async () => {
    securityNetworkStoreMock.runPortScan = vi.fn().mockResolvedValue({ output: 'no open ports' })
    const wrapper = createWrapper()
    wrapper.vm.scanTarget = '192.168.1.1'
    wrapper.vm.scanPortRange = '1-1000'
    await wrapper.vm.runPortScan()
    expect(wrapper.vm.scanRaw).toBe('no open ports')
  })

  it('runPortScan 失败时应该显示错误', async () => {
    const { Md3Message } = await import('@/components/md3')
    securityNetworkStoreMock.runPortScan = vi.fn().mockRejectedValue(new Error('fail'))
    const wrapper = createWrapper()
    wrapper.vm.scanTarget = '192.168.1.1'
    wrapper.vm.scanPortRange = '1-1000'
    await wrapper.vm.runPortScan()
    expect(Md3Message.error).toHaveBeenCalledWith('执行失败')
  })

  it('parseTraceroute simple match 应该解析简单格式', async () => {
    securityNetworkStoreMock.runTraceroute = vi.fn().mockResolvedValue({ output: ' 1  10.0.0.1  1.234 ms' })
    const wrapper = createWrapper()
    wrapper.vm.tracerouteTarget = '8.8.8.8'
    await wrapper.vm.runTraceroute()
    expect(wrapper.vm.tracerouteHops.length).toBe(1)
    expect(wrapper.vm.tracerouteHops[0].hop).toBe('1')
    expect(wrapper.vm.tracerouteHops[0].host).toBe('10.0.0.1')
    expect(wrapper.vm.tracerouteHops[0].ip).toBe('10.0.0.1')
    expect(wrapper.vm.tracerouteHops[0].rtt1).toBe('1.234 ms')
  })

  it('runPing 成功时应该解析统计数据', async () => {
    securityNetworkStoreMock.runPing = vi.fn().mockResolvedValue({
      output: '5 packets transmitted, 4 received, 20% packet loss\nrtt min/avg/max/mdev = 1.234/5.678/9.012/3.456'
    })
    const wrapper = createWrapper()
    wrapper.vm.pingTarget = '8.8.8.8'
    await wrapper.vm.runPing()
    expect(wrapper.vm.pingOutput).toBeTruthy()
    expect(wrapper.vm.pingStats).toBeTruthy()
    expect(wrapper.vm.pingStats!.transmitted).toBe('5')
    expect(wrapper.vm.pingStats!.received).toBe('4')
    expect(wrapper.vm.pingStats!.loss).toBe('20')
    expect(wrapper.vm.pingStats!.min).toBe('1.234')
    expect(wrapper.vm.pingStats!.avg).toBe('5.678')
    expect(wrapper.vm.pingStats!.max).toBe('9.012')
  })

  it('runPing 失败时应该显示错误', async () => {
    const { Md3Message } = await import('@/components/md3')
    securityNetworkStoreMock.runPing = vi.fn().mockRejectedValue(new Error('fail'))
    const wrapper = createWrapper()
    wrapper.vm.pingTarget = '8.8.8.8'
    await wrapper.vm.runPing()
    expect(Md3Message.error).toHaveBeenCalledWith('执行失败')
  })

  it('runPing 空目标时应该显示警告', async () => {
    const { Md3Message } = await import('@/components/md3')
    const wrapper = createWrapper()
    wrapper.vm.pingTarget = '  '
    await wrapper.vm.runPing()
    expect(Md3Message.warning).toHaveBeenCalledWith('请输入目标地址')
  })

  it('runTraceroute 空目标时应该显示警告', async () => {
    const { Md3Message } = await import('@/components/md3')
    const wrapper = createWrapper()
    wrapper.vm.tracerouteTarget = '  '
    await wrapper.vm.runTraceroute()
    expect(Md3Message.warning).toHaveBeenCalledWith('请输入目标地址')
  })

  it('runPortScan 空目标时应该显示警告', async () => {
    const { Md3Message } = await import('@/components/md3')
    const wrapper = createWrapper()
    wrapper.vm.scanTarget = '  '
    wrapper.vm.scanPortRange = '1-1000'
    await wrapper.vm.runPortScan()
    expect(Md3Message.warning).toHaveBeenCalledWith('请输入目标地址')
  })

  it('runPortScan 空端口范围时应该显示警告', async () => {
    const { Md3Message } = await import('@/components/md3')
    const wrapper = createWrapper()
    wrapper.vm.scanTarget = '192.168.1.1'
    wrapper.vm.scanPortRange = '  '
    await wrapper.vm.runPortScan()
    expect(Md3Message.warning).toHaveBeenCalledWith('请输入端口范围')
  })

  it('runPing 返回 error 时应该设置 pingOutput', async () => {
    securityNetworkStoreMock.runPing = vi.fn().mockResolvedValue({ error: 'timeout' })
    const wrapper = createWrapper()
    wrapper.vm.pingTarget = '8.8.8.8'
    await wrapper.vm.runPing()
    expect(wrapper.vm.pingOutput).toBe('timeout')
  })

  it('runTraceroute 返回 error 时应该设置 tracerouteRaw', async () => {
    securityNetworkStoreMock.runTraceroute = vi.fn().mockResolvedValue({ error: 'timeout' })
    const wrapper = createWrapper()
    wrapper.vm.tracerouteTarget = '8.8.8.8'
    await wrapper.vm.runTraceroute()
    expect(wrapper.vm.tracerouteRaw).toBe('timeout')
  })

  it('runPortScan 返回 error 时应该设置 scanRaw', async () => {
    securityNetworkStoreMock.runPortScan = vi.fn().mockResolvedValue({ error: 'timeout' })
    const wrapper = createWrapper()
    wrapper.vm.scanTarget = '192.168.1.1'
    wrapper.vm.scanPortRange = '1-1000'
    await wrapper.vm.runPortScan()
    expect(wrapper.vm.scanRaw).toBe('timeout')
  })
})
