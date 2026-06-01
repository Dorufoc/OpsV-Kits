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
  Md3Empty: { name: 'Md3Empty', props: ['description', 'imageSize'], template: '<div class="md3-empty">{{ description }}</div>' },
  Md3Tag: { name: 'Md3Tag', props: ['type', 'size', 'variant'], template: '<span class="md3-tag"><slot /></span>' },
  Md3Table: { name: 'Md3Table', props: ['columns', 'data', 'stripe', 'emptyText', 'selection', 'maxHeight'], template: '<div class="md3-table"><slot /></div>' },
  Md3Tabs: { name: 'Md3Tabs', props: ['modelValue', 'tabs'], template: '<div class="md3-tabs" />' },
  Md3Dialog: { name: 'Md3Dialog', props: ['visible', 'title', 'width', 'closable'], emits: ['update:visible'], template: '<div class="md3-dialog" v-if="visible"><slot /><slot name="footer" /></div>' },
  Md3Input: { name: 'Md3Input', props: ['modelValue', 'label', 'placeholder', 'type', 'min', 'max'], emits: ['update:modelValue'], template: '<input class="md3-input" :value="modelValue" />' },
  Md3Select: { name: 'Md3Select', props: ['modelValue', 'options', 'placeholder', 'label', 'clearable', 'size'], emits: ['update:modelValue'], template: '<select class="md3-select" :data-placeholder="placeholder">{{ placeholder }}</select>' },
  Md3Alert: { name: 'Md3Alert', props: ['type', 'title', 'message'], template: '<div class="md3-alert" />' },
  Md3Switch: { name: 'Md3Switch', props: ['modelValue', 'onText', 'offText'], emits: ['update:modelValue'], template: '<div class="md3-switch" />' },
  Md3Progress: { name: 'Md3Progress', props: ['percentage', 'color'], template: '<div class="md3-progress" />' },
}))

vi.mock('@/components/Md3Button.vue', () => ({
  default: { name: 'Md3Button', props: ['size', 'variant', 'disabled', 'icon', 'loading', 'type'], template: '<button class="md3-btn" :disabled="disabled" @click="$emit(\'click\')"><slot /></button>' },
}))

vi.mock('@/components/ThemeToggle.vue', () => ({
  default: { name: 'ThemeToggle', template: '<button class="theme-toggle" />' },
}))

vi.mock('@/components/ColorPresets.vue', () => ({
  default: { name: 'ColorPresets', props: ['label'], template: '<div class="color-presets" />' },
}))

vi.mock('@/components/Terminal.vue', () => ({
  default: {
    name: 'Terminal',
    props: ['sessionName', 'showToolbar'],
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

vi.mock('@/components/ViteDeployPanel.vue', () => ({
  default: { name: 'ViteDeployPanel', props: ['projectConfig'], template: '<div class="vite-deploy-panel" />' },
}))

vi.mock('@/components/ViteStatusCard.vue', () => ({
  default: { name: 'ViteStatusCard', props: ['status'], template: '<div class="vite-status-card" />' },
}))

vi.mock('@/components/WebhookDeployPanel.vue', () => ({
  default: { name: 'WebhookDeployPanel', template: '<div class="webhook-deploy-panel" />' },
}))

vi.mock('@/components/BuildPanel.vue', () => ({
  default: { name: 'BuildPanel', props: ['buildStatus', 'runStatus'], template: '<div class="build-panel" />' },
}))

vi.mock('@/components/SyncPanel.vue', () => ({
  default: { name: 'SyncPanel', props: ['syncStatus', 'progress'], template: '<div class="sync-panel" />' },
}))

vi.mock('@/components/MonitorGaugeChart.vue', () => ({
  default: { name: 'MonitorGaugeChart', props: ['value', 'title', 'height', 'max'], template: '<div class="monitor-gauge-chart" />' },
}))

const mockPush = vi.fn()
vi.mock('vue-router', () => ({
  useRouter: () => ({ push: mockPush }),
  useRoute: () => ({}),
}))

let sshStoreMock: any
let dockerStoreMock: any
let websshStoreMock: any
let monitorStoreMock: any
let themeStoreMock: any
let projectStoreMock: any
let syncStoreMock: any
let buildStoreMock: any
let viteDeployStoreMock: any

vi.mock('@/stores/sshAccountStore', () => ({
  useSshAccountStore: () => sshStoreMock,
}))

vi.mock('@/stores/dockerStore', () => ({
  useDockerStore: () => dockerStoreMock,
}))

vi.mock('@/stores/websshStore', () => ({
  useWebsshStore: () => websshStoreMock,
}))

vi.mock('@/stores/monitorStore', () => ({
  useMonitorStore: () => monitorStoreMock,
}))

vi.mock('@/stores/themeStore', () => ({
  useThemeStore: () => themeStoreMock,
}))

vi.mock('@/stores/projectStore', () => ({
  useProjectStore: () => projectStoreMock,
}))

vi.mock('@/stores/syncStore', () => ({
  useSyncStore: () => syncStoreMock,
}))

vi.mock('@/stores/buildStore', () => ({
  useBuildStore: () => buildStoreMock,
}))

vi.mock('@/stores/viteDeployStore', () => ({
  useViteDeployStore: () => viteDeployStoreMock,
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

beforeEach(() => {
  setActivePinia(createPinia())
  vi.clearAllMocks()
  sshStoreMock = {
    accounts: [{ alias: 'test-server', host: '192.168.1.1', port: 22, default: true, status: 'online', username: 'root', auth_type: 'password', password: '', private_key: '', key_passphrase: '', group: '', last_connected: '' }],
    fetchAccounts: vi.fn().mockResolvedValue(undefined),
    createAccount: vi.fn().mockResolvedValue(undefined),
  }
  dockerStoreMock = {
    containers: [{ id: 'abc', name: 'nginx', image: 'nginx', status: 'Up', state: 'running', ports: '', created: '' }],
  }
  websshStoreMock = {
    sessions: [],
    historyRecords: [],
    activeSessionId: null,
  }
  monitorStoreMock = {
    snapshot: null,
    history: [],
    fetchSnapshot: vi.fn().mockResolvedValue(undefined),
    formatBytes: (b: number) => `${(b / 1024 / 1024).toFixed(1)} MB`,
  }
  themeStoreMock = {
    mode: 'dark',
    preset: 'indigo',
    toggleDark: vi.fn(),
    setPreset: vi.fn(),
  }
  projectStoreMock = {
    projects: [],
    fetchProjects: vi.fn().mockResolvedValue(undefined),
    createProject: vi.fn().mockResolvedValue({ alias: 'new-proj', local_path: '/test', remote_path: '/remote', ssh_alias: 'test-server', project_type: 'java' }),
    updateProject: vi.fn().mockResolvedValue({ alias: 'test-proj', local_path: '/updated', remote_path: '/remote', ssh_alias: 'test-server', project_type: 'java' }),
    deleteProject: vi.fn().mockResolvedValue(undefined),
  }
  syncStoreMock = {
    syncStatus: null,
    progress: null,
    setLogCallback: vi.fn(),
    startSync: vi.fn().mockResolvedValue(undefined),
    waitForCompletion: vi.fn().mockResolvedValue('success'),
    stopSync: vi.fn().mockResolvedValue(undefined),
  }
  buildStoreMock = {
    buildStatus: null,
    runStatus: null,
    setLogCallback: vi.fn(),
    startBuild: vi.fn().mockResolvedValue(undefined),
    startTest: vi.fn().mockResolvedValue(undefined),
    startRun: vi.fn().mockResolvedValue(undefined),
    waitForCompletion: vi.fn().mockResolvedValue('success'),
    stopTask: vi.fn().mockResolvedValue(undefined),
  }
  viteDeployStoreMock = {
    deployStatus: null,
    startDeploy: vi.fn().mockResolvedValue(undefined),
    waitForCompletion: vi.fn().mockResolvedValue('success'),
    startStep: vi.fn().mockResolvedValue(undefined),
    checkEnvironment: vi.fn().mockResolvedValue({ node: { installed: true, version: '20' }, nginx: { installed: true, running: true } }),
    stopDeploy: vi.fn().mockResolvedValue(undefined),
    pipeToTerminal: vi.fn(),
  }
})

import Home from '@/views/Home.vue'
import Settings from '@/views/Settings.vue'
import ProjectPage from '@/views/ProjectPage.vue'

describe('Home', () => {
  function createWrapper() {
    return mount(Home, { global: { stubs: { Md3Icon: true } } })
  }

  it('应该渲染首页容器', () => {
    const wrapper = createWrapper()
    expect(wrapper.find('.home').exists()).toBe(true)
  })

  it('应该渲染统计卡片行', () => {
    const wrapper = createWrapper()
    expect(wrapper.find('.stats-row').exists()).toBe(true)
  })

  it('应该渲染 SSH 账户统计', () => {
    const wrapper = createWrapper()
    expect(wrapper.text()).toContain('SSH 账户')
  })

  it('应该渲染 Docker 容器统计', () => {
    const wrapper = createWrapper()
    expect(wrapper.text()).toContain('Docker 容器')
  })

  it('应该渲染一键部署统计', () => {
    const wrapper = createWrapper()
    expect(wrapper.text()).toContain('一键部署')
  })

  it('应该渲染终端会话统计', () => {
    const wrapper = createWrapper()
    expect(wrapper.text()).toContain('终端会话')
  })

  it('应该渲染设备总览卡片', () => {
    const wrapper = createWrapper()
    expect(wrapper.text()).toContain('设备总览')
  })

  it('应该渲染服务器选择器', () => {
    const wrapper = createWrapper()
    expect(wrapper.text()).toContain('选择服务器')
  })

  it('应该显示正确的 SSH 账户数量', () => {
    const wrapper = createWrapper()
    expect(wrapper.text()).toContain('1')
  })

  it('formatBytes 应该正确格式化字节数', () => {
    const wrapper = createWrapper()
    expect(wrapper.vm.formatBytes(0)).toBe('0 B')
    expect(wrapper.vm.formatBytes(1024)).toBe('1.0 KB')
    expect(wrapper.vm.formatBytes(1048576)).toBe('1.0 MB')
    expect(wrapper.vm.formatBytes(1073741824)).toBe('1.0 GB')
    expect(wrapper.vm.formatBytes(1099511627776)).toBe('1.0 TB')
  })

  it('formatBytes 负数应该返回 0 B', () => {
    const wrapper = createWrapper()
    expect(wrapper.vm.formatBytes(-1)).toBe('0 B')
  })

  it('checkFirstLaunch 无账户时应该重试检查', async () => {
    sshStoreMock.accounts = []
    sshStoreMock.fetchAccounts = vi.fn().mockResolvedValue(undefined)
    mockRequestGet.mockResolvedValue({ exists: true })
    const wrapper = createWrapper()
    await nextTick()
    await nextTick()
    await nextTick()
    expect(mockRequestGet).toHaveBeenCalled()
  })

  it('checkFirstLaunch 无账户且检查失败时应该重试', async () => {
    sshStoreMock.accounts = []
    sshStoreMock.fetchAccounts = vi.fn().mockResolvedValue(undefined)
    mockRequestGet.mockRejectedValue(new Error('fail'))
    const wrapper = createWrapper()
    await nextTick()
    await nextTick()
    await nextTick()
  })

  it('validateForm 有效表单应该返回 true', () => {
    const wrapper = createWrapper()
    wrapper.vm.form = { alias: 'test', host: '192.168.1.1', port: 22, username: 'root', password: 'pass' }
    expect(wrapper.vm.validateForm()).toBe(true)
    expect(wrapper.vm.formErrors.alias).toBe('')
  })

  it('validateForm 无别名应该返回 false', () => {
    const wrapper = createWrapper()
    wrapper.vm.form = { alias: '', host: '192.168.1.1', port: 22, username: 'root', password: 'pass' }
    expect(wrapper.vm.validateForm()).toBe(false)
    expect(wrapper.vm.formErrors.alias).toBe('请输入账户别名')
  })

  it('validateForm 无主机应该返回 false', () => {
    const wrapper = createWrapper()
    wrapper.vm.form = { alias: 'test', host: '', port: 22, username: 'root', password: 'pass' }
    expect(wrapper.vm.validateForm()).toBe(false)
    expect(wrapper.vm.formErrors.host).toBe('请输入主机地址')
  })

  it('validateForm 无效端口应该返回 false', () => {
    const wrapper = createWrapper()
    wrapper.vm.form = { alias: 'test', host: '192.168.1.1', port: 0, username: 'root', password: 'pass' }
    expect(wrapper.vm.validateForm()).toBe(false)
    expect(wrapper.vm.formErrors.port).toBe('端口范围 1-65535')
  })

  it('validateForm 无用户名应该返回 false', () => {
    const wrapper = createWrapper()
    wrapper.vm.form = { alias: 'test', host: '192.168.1.1', port: 22, username: '', password: 'pass' }
    expect(wrapper.vm.validateForm()).toBe(false)
    expect(wrapper.vm.formErrors.username).toBe('请输入用户名')
  })

  it('validateForm 无密码应该返回 false', () => {
    const wrapper = createWrapper()
    wrapper.vm.form = { alias: 'test', host: '192.168.1.1', port: 22, username: 'root', password: '' }
    expect(wrapper.vm.validateForm()).toBe(false)
    expect(wrapper.vm.formErrors.password).toBe('请输入密码')
  })

  it('handleTest 成功时应该显示成功消息', async () => {
    const { Md3Message } = await import('@/components/md3')
    mockRequestPost.mockResolvedValueOnce({ alias: 'test' })
    const wrapper = createWrapper()
    wrapper.vm.form = { alias: 'test', host: '192.168.1.1', port: 22, username: 'root', password: 'pass' }
    await wrapper.vm.handleTest()
    expect(Md3Message.success).toHaveBeenCalledWith('连接测试成功')
  })

  it('handleTest 失败时应该显示错误消息', async () => {
    const { Md3Message } = await import('@/components/md3')
    mockRequestPost.mockRejectedValueOnce(new Error('fail'))
    const wrapper = createWrapper()
    wrapper.vm.form = { alias: 'test', host: '192.168.1.1', port: 22, username: 'root', password: 'pass' }
    await wrapper.vm.handleTest()
    expect(Md3Message.error).toHaveBeenCalled()
  })

  it('handleSave 成功时应该保存账户', async () => {
    const { Md3Message } = await import('@/components/md3')
    sshStoreMock.createAccount = vi.fn().mockResolvedValue(undefined)
    const wrapper = createWrapper()
    wrapper.vm.form = { alias: 'test', host: '192.168.1.1', port: 22, username: 'root', password: 'pass' }
    await wrapper.vm.handleSave()
    expect(sshStoreMock.createAccount).toHaveBeenCalled()
    expect(Md3Message.success).toHaveBeenCalled()
    expect(wrapper.vm.dialogVisible).toBe(false)
  })

  it('handleSave 失败时应该显示错误消息', async () => {
    const { Md3Message } = await import('@/components/md3')
    sshStoreMock.createAccount = vi.fn().mockRejectedValue(new Error('fail'))
    const wrapper = createWrapper()
    wrapper.vm.form = { alias: 'test', host: '192.168.1.1', port: 22, username: 'root', password: 'pass' }
    await wrapper.vm.handleSave()
    expect(Md3Message.error).toHaveBeenCalled()
  })

  it('validateForm 端口超出范围应该返回 false', () => {
    const wrapper = createWrapper()
    wrapper.vm.form = { alias: 'test', host: '192.168.1.1', port: 70000, username: 'root', password: 'pass' }
    expect(wrapper.vm.validateForm()).toBe(false)
    expect(wrapper.vm.formErrors.port).toBe('端口范围 1-65535')
  })

  it('handleTest 成功时应该设置 testResult', async () => {
    mockRequestPost.mockResolvedValueOnce({ alias: 'test' })
    const wrapper = createWrapper()
    wrapper.vm.form = { alias: 'test', host: '192.168.1.1', port: 22, username: 'root', password: 'pass' }
    await wrapper.vm.handleTest()
    expect(wrapper.vm.testResult).toEqual({ success: true, message: '连接成功' })
  })

  it('handleTest 失败时应该设置 testResult', async () => {
    const err = new Error('connection refused')
    mockRequestPost.mockRejectedValueOnce(err)
    const wrapper = createWrapper()
    wrapper.vm.form = { alias: 'test', host: '192.168.1.1', port: 22, username: 'root', password: 'pass' }
    await wrapper.vm.handleTest()
    expect(wrapper.vm.testResult!.success).toBe(false)
  })

  it('handleTest 无效表单时不应调用 API', async () => {
    const wrapper = createWrapper()
    wrapper.vm.form = { alias: '', host: '', port: 0, username: '', password: '' }
    await wrapper.vm.handleTest()
    expect(mockRequestPost).not.toHaveBeenCalled()
  })

  it('handleSave 成功时应该设置 accountsExist 和 dashboardAlias', async () => {
    sshStoreMock.createAccount = vi.fn().mockResolvedValue(undefined)
    sshStoreMock.fetchAccounts = vi.fn().mockResolvedValue(undefined)
    const wrapper = createWrapper()
    wrapper.vm.form = { alias: 'new-server', host: '10.0.0.1', port: 22, username: 'root', password: 'pass' }
    await wrapper.vm.handleSave()
    expect(wrapper.vm.accountsExist).toBe(true)
    expect(wrapper.vm.dashboardAlias).toBe('new-server')
  })

  it('handleSave 无效表单时不应调用 store', async () => {
    const wrapper = createWrapper()
    wrapper.vm.form = { alias: '', host: '', port: 0, username: '', password: '' }
    await wrapper.vm.handleSave()
    expect(sshStoreMock.createAccount).not.toHaveBeenCalled()
  })

  it('checkFirstLaunch 无账户且 exists 为 false 时应该打开对话框', async () => {
    sshStoreMock.accounts = []
    sshStoreMock.fetchAccounts = vi.fn().mockResolvedValue(undefined)
    mockRequestGet.mockResolvedValue({ exists: false })
    const wrapper = createWrapper()
    await nextTick()
    await nextTick()
    await nextTick()
    expect(wrapper.vm.dialogVisible).toBe(true)
    expect(wrapper.vm.accountsExist).toBe(false)
  })

  it('formatBytes 0 应该返回 0 B', () => {
    const wrapper = createWrapper()
    expect(wrapper.vm.formatBytes(0)).toBe('0 B')
  })

  it('memColor 应该返回正确的颜色', () => {
    const wrapper = createWrapper()
    expect(wrapper.vm.memColor(95)).toBe('#b3261e')
    expect(wrapper.vm.memColor(75)).toBe('#f9a825')
    expect(wrapper.vm.memColor(50)).toBe('#1b7d3a')
  })

  it('diskColor 应该返回正确的颜色', () => {
    const wrapper = createWrapper()
    expect(wrapper.vm.diskColor(95)).toBe('#b3261e')
    expect(wrapper.vm.diskColor(75)).toBe('#f9a825')
    expect(wrapper.vm.diskColor(50)).toBe('#1b7d3a')
  })

  it('formValid 有所有必填字段时应该为 truthy', () => {
    const wrapper = createWrapper()
    wrapper.vm.form = { alias: 'test', host: '192.168.1.1', port: 22, username: 'root', password: 'pass' }
    expect(wrapper.vm.formValid).toBeTruthy()
  })

  it('formValid 缺少必填字段时应该为 falsy', () => {
    const wrapper = createWrapper()
    wrapper.vm.form = { alias: '', host: '192.168.1.1', port: 22, username: 'root', password: 'pass' }
    expect(wrapper.vm.formValid).toBeFalsy()
  })

  it('selectOptions 应该返回正确的选项', () => {
    const wrapper = createWrapper()
    const options = wrapper.vm.selectOptions
    expect(options).toHaveLength(1)
    expect(options[0].value).toBe('test-server')
  })
})

describe('Settings', () => {
  function createWrapper() {
    return mount(Settings, { global: { stubs: { Md3Icon: true } } })
  }

  it('应该渲染设置页面容器', () => {
    const wrapper = createWrapper()
    expect(wrapper.find('.settings').exists()).toBe(true)
  })

  it('应该渲染主题设置区域', () => {
    const wrapper = createWrapper()
    expect(wrapper.text()).toContain('主题设置')
  })

  it('应该渲染外观模式', () => {
    const wrapper = createWrapper()
    expect(wrapper.text()).toContain('外观模式')
  })

  it('应该渲染主题色预设', () => {
    const wrapper = createWrapper()
    expect(wrapper.text()).toContain('主题色预设')
  })

  it('应该渲染会话历史管理', () => {
    const wrapper = createWrapper()
    expect(wrapper.text()).toContain('会话历史管理')
  })

  it('应该渲染保存设置按钮', () => {
    const wrapper = createWrapper()
    expect(wrapper.text()).toContain('保存设置')
  })

  it('应该显示当前主题模式', () => {
    const wrapper = createWrapper()
    expect(wrapper.text()).toContain('深色模式')
  })

  it('应该渲染远程硬盘映射区域', () => {
    const wrapper = createWrapper()
    expect(wrapper.text()).toContain('远程硬盘映射账户')
  })

  it('应该渲染登录用户名输入框', () => {
    const wrapper = createWrapper()
    expect(wrapper.text()).toContain('登录用户名')
  })

  it('应该渲染登录密码输入框', () => {
    const wrapper = createWrapper()
    expect(wrapper.text()).toContain('登录密码')
  })

  it('应该渲染保存按钮', () => {
    const wrapper = createWrapper()
    expect(wrapper.text()).toContain('保存设置')
  })

  it('saveSettings 成功时应显示成功消息', async () => {
    const { Md3Message } = await import('@/components/md3')
    const wrapper = createWrapper()
    await wrapper.vm.saveSettings()
    expect(Md3Message.success).toHaveBeenCalledWith('设置已保存')
    expect(wrapper.vm.saved).toBe(true)
    expect(wrapper.vm.saving).toBe(false)
  })

  it('saveSettings 失败时应显示错误消息', async () => {
    const { Md3Message } = await import('@/components/md3')
    mockRequestPut.mockRejectedValueOnce(new Error('fail'))
    const wrapper = createWrapper()
    await wrapper.vm.saveSettings()
    expect(Md3Message.error).toHaveBeenCalledWith('保存失败')
    expect(wrapper.vm.saving).toBe(false)
  })

  it('saveDriveAuth 成功时应显示成功消息', async () => {
    const { Md3Message } = await import('@/components/md3')
    const wrapper = createWrapper()
    wrapper.vm.driveUsername = 'testuser'
    wrapper.vm.drivePassword = 'testpass'
    await wrapper.vm.saveDriveAuth()
    expect(Md3Message.success).toHaveBeenCalledWith('映射账户已保存')
    expect(wrapper.vm.drivePassword).toBe('')
    expect(wrapper.vm.savingDrive).toBe(false)
  })

  it('saveDriveAuth 无密码时不应发送密码字段', async () => {
    const wrapper = createWrapper()
    wrapper.vm.driveUsername = 'testuser'
    wrapper.vm.drivePassword = ''
    await wrapper.vm.saveDriveAuth()
    expect(mockRequestPut).toHaveBeenCalledWith('/settings', expect.not.objectContaining({ remote_drive_password: expect.anything() }))
  })

  it('saveDriveAuth 失败时应显示错误消息', async () => {
    const { Md3Message } = await import('@/components/md3')
    mockRequestPut.mockRejectedValueOnce(new Error('fail'))
    const wrapper = createWrapper()
    await wrapper.vm.saveDriveAuth()
    expect(Md3Message.error).toHaveBeenCalledWith('保存失败')
    expect(wrapper.vm.savingDrive).toBe(false)
  })

  it('clearAllHistory 成功时应清空历史', async () => {
    const { Md3Message } = await import('@/components/md3')
    const wrapper = createWrapper()
    await nextTick()
    await nextTick()
    mockRequestGet.mockResolvedValueOnce({ sessions: [{ session_id: 's1' }, { session_id: 's2' }] })
    wrapper.vm.historyCount = 2
    await wrapper.vm.clearAllHistory()
    expect(mockRequestDelete).toHaveBeenCalledTimes(2)
    expect(wrapper.vm.historyCount).toBe(0)
    expect(Md3Message.success).toHaveBeenCalledWith('历史已清空')
  })

  it('clearAllHistory 失败时应显示错误消息', async () => {
    const { Md3Message } = await import('@/components/md3')
    const wrapper = createWrapper()
    await nextTick()
    await nextTick()
    mockRequestGet.mockRejectedValueOnce(new Error('fail'))
    await wrapper.vm.clearAllHistory()
    expect(Md3Message.error).toHaveBeenCalledWith('清空失败')
  })

  it('loadSettings 成功时应加载设置', async () => {
    const wrapper = createWrapper()
    await nextTick()
    await nextTick()
    mockRequestGet.mockResolvedValueOnce({ session_ttl_hours: 48, remote_drive_username: 'myuser', remote_drive_password_set: true })
    mockRequestGet.mockResolvedValueOnce({ count: 5 })
    await wrapper.vm.loadSettings()
    expect(wrapper.vm.sessionTtlHours).toBe(48)
    expect(wrapper.vm.driveUsername).toBe('myuser')
    expect(wrapper.vm.drivePasswordSet).toBe(true)
    expect(wrapper.vm.historyCount).toBe(5)
  })

  it('loadSettings 失败时应使用默认值', async () => {
    mockRequestGet.mockRejectedValue(new Error('fail'))
    const wrapper = createWrapper()
    await wrapper.vm.loadSettings()
    expect(wrapper.vm.sessionTtlHours).toBe(72)
    expect(wrapper.vm.driveUsername).toBe('opsv')
  })

  it('onMounted 应调用 loadSettings', () => {
    createWrapper()
    expect(mockRequestGet).toHaveBeenCalled()
  })
})

describe('ProjectPage', () => {
  function createWrapper() {
    return mount(ProjectPage, { global: { stubs: { Md3Icon: true } } })
  }

  it('应该渲染项目页面容器', () => {
    const wrapper = createWrapper()
    expect(wrapper.find('.project-page').exists()).toBe(true)
  })

  it('应该渲染项目侧边栏', () => {
    const wrapper = createWrapper()
    expect(wrapper.find('.project-sidebar').exists()).toBe(true)
  })

  it('应该渲染项目列表标题', () => {
    const wrapper = createWrapper()
    expect(wrapper.text()).toContain('项目列表')
  })

  it('应该渲染新建项目按钮', () => {
    const wrapper = createWrapper()
    expect(wrapper.text()).toContain('新建项目')
  })

  it('应该渲染项目主区域', () => {
    const wrapper = createWrapper()
    expect(wrapper.find('.project-main').exists()).toBe(true)
  })

  it('应该渲染操作按钮区域', () => {
    const wrapper = createWrapper()
    expect(wrapper.find('.action-bar').exists()).toBe(true)
  })

  it('应该渲染一键部署按钮', () => {
    const wrapper = createWrapper()
    expect(wrapper.text()).toContain('一键部署')
  })

  it('应该渲染停止按钮', () => {
    const wrapper = createWrapper()
    expect(wrapper.text()).toContain('停止')
  })

  it('isViteProject 默认应该是 false', () => {
    const wrapper = createWrapper()
    expect(wrapper.vm.isViteProject).toBe(false)
  })

  it('isViteProject 当 project_type 为 vite 时应该是 true', () => {
    const wrapper = createWrapper()
    wrapper.vm.projectConfig = { ...wrapper.vm.projectConfig, project_type: 'vite' }
    expect(wrapper.vm.isViteProject).toBe(true)
  })

  it('isRunning 默认应该是 false', () => {
    const wrapper = createWrapper()
    expect(wrapper.vm.isRunning).toBe(false)
  })

  it('isRunning 当 isDeploying 为 true 时应该是 true', () => {
    const wrapper = createWrapper()
    wrapper.vm.isDeploying = true
    expect(wrapper.vm.isRunning).toBe(true)
  })

  it('canSync 当配置完整且未运行时应该是 true', () => {
    const wrapper = createWrapper()
    wrapper.vm.projectConfig = { ...wrapper.vm.projectConfig, local_path: '/local', remote_path: '/remote', ssh_alias: 'test-server' }
    expect(wrapper.vm.canSync).toBe(true)
  })

  it('canSync 当缺少配置时应该是 false', () => {
    const wrapper = createWrapper()
    wrapper.vm.projectConfig = { ...wrapper.vm.projectConfig, local_path: '', remote_path: '/remote', ssh_alias: 'test-server' }
    expect(wrapper.vm.canSync).toBe(false)
  })

  it('canBuild 当有 remote_path 和 ssh_alias 时应该是 true', () => {
    const wrapper = createWrapper()
    wrapper.vm.projectConfig = { ...wrapper.vm.projectConfig, remote_path: '/remote', ssh_alias: 'test-server' }
    expect(wrapper.vm.canBuild).toBe(true)
  })

  it('canRun 当有 remote_path 和 ssh_alias 时应该是 true', () => {
    const wrapper = createWrapper()
    wrapper.vm.projectConfig = { ...wrapper.vm.projectConfig, remote_path: '/remote', ssh_alias: 'test-server' }
    expect(wrapper.vm.canRun).toBe(true)
  })

  it('canViteAction 当有 remote_path 和 ssh_alias 时应该是 true', () => {
    const wrapper = createWrapper()
    wrapper.vm.projectConfig = { ...wrapper.vm.projectConfig, remote_path: '/remote', ssh_alias: 'test-server' }
    expect(wrapper.vm.canViteAction).toBe(true)
  })

  it('sshAccountOptions 应该返回正确的选项', () => {
    const wrapper = createWrapper()
    const options = wrapper.vm.sshAccountOptions
    expect(options).toHaveLength(1)
    expect(options[0].value).toBe('test-server')
  })

  it('selectProject 应该更新 projectConfig 和 currentProject', () => {
    const wrapper = createWrapper()
    const proj = { alias: 'my-proj', local_path: '/local', remote_path: '/remote', ssh_alias: 'test-server', project_type: 'java' }
    wrapper.vm.selectProject(proj)
    expect(wrapper.vm.currentProject).toBe('my-proj')
    expect(wrapper.vm.selectedProject).toEqual(proj)
  })

  it('openEditDialog 应该设置编辑表单并打开对话框', () => {
    const wrapper = createWrapper()
    const proj = { alias: 'my-proj', local_path: '/local', remote_path: '/remote', ssh_alias: 'test-server', project_type: 'java', jdk_version: '21', node_version: '20', nginx_port: 8080, build_command: 'npm run build', run_mode: 'spring-boot' }
    wrapper.vm.openEditDialog(proj)
    expect(wrapper.vm.editProjectForm.alias).toBe('my-proj')
    expect(wrapper.vm.showEditProject).toBe(true)
  })

  it('handleEditProject 信息不完整时应该显示警告', async () => {
    const { Md3Message } = await import('@/components/md3')
    const wrapper = createWrapper()
    wrapper.vm.editProjectForm = { alias: 'test', local_path: '', remote_path: '', ssh_alias: '', project_type: 'java', jdk_version: '21', node_version: '20', nginx_port: 8080, build_command: 'npm run build', run_mode: 'spring-boot' }
    await wrapper.vm.handleEditProject()
    expect(Md3Message.warning).toHaveBeenCalled()
  })

  it('handleEditProject 成功时应该更新项目', async () => {
    const { Md3Message } = await import('@/components/md3')
    const wrapper = createWrapper()
    wrapper.vm.editProjectForm = { alias: 'test', local_path: '/local', remote_path: '/remote', ssh_alias: 'test-server', project_type: 'java', jdk_version: '21', node_version: '20', nginx_port: 8080, build_command: 'npm run build', run_mode: 'spring-boot' }
    await wrapper.vm.handleEditProject()
    expect(projectStoreMock.updateProject).toHaveBeenCalled()
    expect(wrapper.vm.showEditProject).toBe(false)
    expect(Md3Message.success).toHaveBeenCalled()
  })

  it('handleEditProject 失败时应该显示错误', async () => {
    const { Md3Message } = await import('@/components/md3')
    projectStoreMock.updateProject = vi.fn().mockRejectedValue(new Error('fail'))
    const wrapper = createWrapper()
    wrapper.vm.editProjectForm = { alias: 'test', local_path: '/local', remote_path: '/remote', ssh_alias: 'test-server', project_type: 'java', jdk_version: '21', node_version: '20', nginx_port: 8080, build_command: 'npm run build', run_mode: 'spring-boot' }
    await wrapper.vm.handleEditProject()
    expect(Md3Message.error).toHaveBeenCalled()
  })

  it('handleCreateProject 无别名时应该显示警告', async () => {
    const { Md3Message } = await import('@/components/md3')
    const wrapper = createWrapper()
    wrapper.vm.newProjectForm = { alias: '', local_path: '', remote_path: '', ssh_alias: '', project_type: 'java', jdk_version: '21', node_version: '20', nginx_port: 8080, build_command: 'npm run build', run_mode: 'spring-boot' }
    await wrapper.vm.handleCreateProject()
    expect(Md3Message.warning).toHaveBeenCalled()
  })

  it('handleCreateProject 别名重复时应该显示警告', async () => {
    const { Md3Message } = await import('@/components/md3')
    projectStoreMock.projects = [{ alias: 'existing-proj' }]
    const wrapper = createWrapper()
    wrapper.vm.newProjectForm = { alias: 'existing-proj', local_path: '/local', remote_path: '/remote', ssh_alias: 'test-server', project_type: 'java', jdk_version: '21', node_version: '20', nginx_port: 8080, build_command: 'npm run build', run_mode: 'spring-boot' }
    await wrapper.vm.handleCreateProject()
    expect(Md3Message.warning).toHaveBeenCalled()
  })

  it('handleCreateProject 成功时应该创建项目', async () => {
    const { Md3Message } = await import('@/components/md3')
    const wrapper = createWrapper()
    wrapper.vm.newProjectForm = { alias: 'new-proj', local_path: '/local', remote_path: '/remote', ssh_alias: 'test-server', project_type: 'java', jdk_version: '21', node_version: '20', nginx_port: 8080, build_command: 'npm run build', run_mode: 'spring-boot' }
    await wrapper.vm.handleCreateProject()
    expect(projectStoreMock.createProject).toHaveBeenCalled()
    expect(wrapper.vm.showNewProject).toBe(false)
    expect(Md3Message.success).toHaveBeenCalled()
  })

  it('handleCreateProject 失败时应该显示错误', async () => {
    const { Md3Message } = await import('@/components/md3')
    projectStoreMock.createProject = vi.fn().mockRejectedValue(new Error('fail'))
    const wrapper = createWrapper()
    wrapper.vm.newProjectForm = { alias: 'new-proj', local_path: '/local', remote_path: '/remote', ssh_alias: 'test-server', project_type: 'java', jdk_version: '21', node_version: '20', nginx_port: 8080, build_command: 'npm run build', run_mode: 'spring-boot' }
    await wrapper.vm.handleCreateProject()
    expect(Md3Message.error).toHaveBeenCalled()
  })

  it('handleViteCheck 成功时应该显示信息', async () => {
    const { Md3Message } = await import('@/components/md3')
    const wrapper = createWrapper()
    wrapper.vm.projectConfig = { ...wrapper.vm.projectConfig, remote_path: '/remote', ssh_alias: 'test-server' }
    await wrapper.vm.handleViteCheck()
    expect(viteDeployStoreMock.checkEnvironment).toHaveBeenCalled()
    expect(Md3Message.info).toHaveBeenCalled()
  })

  it('handleViteCheck 失败时应该显示错误', async () => {
    const { Md3Message } = await import('@/components/md3')
    viteDeployStoreMock.checkEnvironment = vi.fn().mockRejectedValue(new Error('fail'))
    const wrapper = createWrapper()
    wrapper.vm.projectConfig = { ...wrapper.vm.projectConfig, remote_path: '/remote', ssh_alias: 'test-server' }
    await wrapper.vm.handleViteCheck()
    expect(Md3Message.error).toHaveBeenCalled()
  })

  it('handleStop 非 Vite 项目时应该停止同步和构建', async () => {
    const wrapper = createWrapper()
    syncStoreMock.syncStatus = 'syncing'
    buildStoreMock.buildStatus = 'building'
    await wrapper.vm.handleStop()
    expect(syncStoreMock.stopSync).toHaveBeenCalled()
    expect(buildStoreMock.stopTask).toHaveBeenCalled()
  })

  it('handleStop Vite 项目时应该调用 stopDeploy', async () => {
    const wrapper = createWrapper()
    wrapper.vm.projectConfig = { ...wrapper.vm.projectConfig, project_type: 'vite' }
    await wrapper.vm.handleStop()
    expect(viteDeployStoreMock.stopDeploy).toHaveBeenCalled()
  })

  it('onMounted 应该加载账户和项目', async () => {
    createWrapper()
    await nextTick()
    await nextTick()
    await nextTick()
    expect(sshStoreMock.fetchAccounts).toHaveBeenCalled()
    expect(projectStoreMock.fetchProjects).toHaveBeenCalled()
  })

  it('onMounted 有项目时应该自动选择第一个', async () => {
    projectStoreMock.projects = [{ alias: 'proj1', local_path: '/local', remote_path: '/remote', ssh_alias: 'test-server', project_type: 'java' }]
    const wrapper = createWrapper()
    await nextTick()
    await nextTick()
    await nextTick()
    expect(wrapper.vm.currentProject).toBe('proj1')
  })

  it('handleDeploy 成功时应完成所有步骤', async () => {
    const wrapper = createWrapper()
    wrapper.vm.projectConfig = { ...wrapper.vm.projectConfig, local_path: '/local', remote_path: '/remote', ssh_alias: 'test-server' }
    await wrapper.vm.handleDeploy()
    expect(syncStoreMock.startSync).toHaveBeenCalled()
    expect(buildStoreMock.startBuild).toHaveBeenCalled()
    expect(buildStoreMock.startTest).toHaveBeenCalled()
    expect(buildStoreMock.startRun).toHaveBeenCalled()
    expect(wrapper.vm.isDeploying).toBe(false)
  })

  it('handleDeploy 运行中时不应重复执行', async () => {
    const wrapper = createWrapper()
    wrapper.vm.isDeploying = true
    await wrapper.vm.handleDeploy()
    expect(syncStoreMock.startSync).not.toHaveBeenCalled()
  })

  it('handleViteDeploy 成功时应调用 startDeploy', async () => {
    const wrapper = createWrapper()
    wrapper.vm.projectConfig = { ...wrapper.vm.projectConfig, project_type: 'vite', remote_path: '/remote', ssh_alias: 'test-server' }
    await wrapper.vm.handleViteDeploy()
    expect(viteDeployStoreMock.startDeploy).toHaveBeenCalled()
    expect(wrapper.vm.isViteDeploying).toBe(false)
  })

  it('handleViteDeploy 运行中时不应重复执行', async () => {
    const wrapper = createWrapper()
    wrapper.vm.isViteDeploying = true
    await wrapper.vm.handleViteDeploy()
    expect(viteDeployStoreMock.startDeploy).not.toHaveBeenCalled()
  })

  it('handleViteDeploy 失败时应调用 pipeToTerminal', async () => {
    viteDeployStoreMock.waitForCompletion = vi.fn().mockResolvedValue('failed')
    const wrapper = createWrapper()
    wrapper.vm.projectConfig = { ...wrapper.vm.projectConfig, project_type: 'vite', remote_path: '/remote', ssh_alias: 'test-server' }
    await wrapper.vm.handleViteDeploy()
    expect(viteDeployStoreMock.pipeToTerminal).toHaveBeenCalled()
    expect(wrapper.vm.isViteDeploying).toBe(false)
  })

  it('handleViteSetup 成功时应调用 startStep', async () => {
    const wrapper = createWrapper()
    wrapper.vm.projectConfig = { ...wrapper.vm.projectConfig, remote_path: '/remote', ssh_alias: 'test-server' }
    await wrapper.vm.handleViteSetup()
    expect(viteDeployStoreMock.startStep).toHaveBeenCalledWith('setup', expect.any(Object))
  })

  it('handleViteSetup 失败时应显示错误', async () => {
    const { Md3Message } = await import('@/components/md3')
    viteDeployStoreMock.startStep = vi.fn().mockRejectedValue(new Error('fail'))
    const wrapper = createWrapper()
    wrapper.vm.projectConfig = { ...wrapper.vm.projectConfig, remote_path: '/remote', ssh_alias: 'test-server' }
    await expect(wrapper.vm.handleViteSetup()).rejects.toThrow()
    expect(Md3Message.error).toHaveBeenCalled()
  })

  it('handleViteInstallDeps 成功时应调用 startStep', async () => {
    const wrapper = createWrapper()
    wrapper.vm.projectConfig = { ...wrapper.vm.projectConfig, remote_path: '/remote', ssh_alias: 'test-server' }
    await wrapper.vm.handleViteInstallDeps()
    expect(viteDeployStoreMock.startStep).toHaveBeenCalledWith('install-deps', expect.any(Object))
  })

  it('handleViteBuild 成功时应调用 startStep', async () => {
    const wrapper = createWrapper()
    wrapper.vm.projectConfig = { ...wrapper.vm.projectConfig, remote_path: '/remote', ssh_alias: 'test-server' }
    await wrapper.vm.handleViteBuild()
    expect(viteDeployStoreMock.startStep).toHaveBeenCalledWith('build', expect.any(Object))
  })

  it('handleViteNginx 成功时应调用 startStep', async () => {
    const wrapper = createWrapper()
    wrapper.vm.projectConfig = { ...wrapper.vm.projectConfig, remote_path: '/remote', ssh_alias: 'test-server' }
    await wrapper.vm.handleViteNginx()
    expect(viteDeployStoreMock.startStep).toHaveBeenCalledWith('nginx', expect.any(Object))
  })

  it('handleSync 成功时应调用 startSync', async () => {
    const wrapper = createWrapper()
    wrapper.vm.projectConfig = { ...wrapper.vm.projectConfig, local_path: '/local', remote_path: '/remote', ssh_alias: 'test-server' }
    await wrapper.vm.handleSync()
    expect(syncStoreMock.startSync).toHaveBeenCalled()
  })

  it('handleSync 不可用时不应执行', async () => {
    const wrapper = createWrapper()
    wrapper.vm.projectConfig = { ...wrapper.vm.projectConfig, local_path: '', remote_path: '', ssh_alias: '' }
    wrapper.vm.isDeploying = false
    await wrapper.vm.handleSync()
    expect(syncStoreMock.startSync).not.toHaveBeenCalled()
  })

  it('handleBuild 成功时应调用 startBuild', async () => {
    const wrapper = createWrapper()
    wrapper.vm.projectConfig = { ...wrapper.vm.projectConfig, remote_path: '/remote', ssh_alias: 'test-server' }
    await wrapper.vm.handleBuild()
    expect(buildStoreMock.startBuild).toHaveBeenCalled()
  })

  it('handleTest 成功时应调用 startTest', async () => {
    const wrapper = createWrapper()
    wrapper.vm.projectConfig = { ...wrapper.vm.projectConfig, remote_path: '/remote', ssh_alias: 'test-server' }
    await wrapper.vm.handleTest()
    expect(buildStoreMock.startTest).toHaveBeenCalled()
  })

  it('handleRun 成功时应调用 startRun', async () => {
    const wrapper = createWrapper()
    wrapper.vm.projectConfig = { ...wrapper.vm.projectConfig, remote_path: '/remote', ssh_alias: 'test-server' }
    await wrapper.vm.handleRun()
    expect(buildStoreMock.startRun).toHaveBeenCalled()
  })

  it('handleStop 非 Vite 且 syncStatus 为 idle 时不调用 stopSync', async () => {
    const wrapper = createWrapper()
    syncStoreMock.syncStatus = 'idle'
    buildStoreMock.buildStatus = null
    buildStoreMock.runStatus = null
    await wrapper.vm.handleStop()
    expect(syncStoreMock.stopSync).not.toHaveBeenCalled()
    expect(buildStoreMock.stopTask).not.toHaveBeenCalled()
  })

  it('projectTypeOptions 应包含 Java 和 Vite', () => {
    const wrapper = createWrapper()
    expect(wrapper.vm.projectTypeOptions).toHaveLength(2)
    expect(wrapper.vm.projectTypeOptions[0].value).toBe('java')
    expect(wrapper.vm.projectTypeOptions[1].value).toBe('vite')
  })

  it('jdkOptions 应包含多个版本', () => {
    const wrapper = createWrapper()
    expect(wrapper.vm.jdkOptions.length).toBeGreaterThanOrEqual(4)
  })

  it('runModeOptions 应包含 Spring Boot 和默认模式', () => {
    const wrapper = createWrapper()
    expect(wrapper.vm.runModeOptions).toHaveLength(2)
  })
})
