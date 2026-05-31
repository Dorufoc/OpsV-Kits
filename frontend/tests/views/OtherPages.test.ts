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
  default: { name: 'Terminal', props: ['sessionName', 'showToolbar'], emits: ['data', 'resize'], template: '<div class="terminal" />' },
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

beforeEach(() => {
  setActivePinia(createPinia())
  vi.clearAllMocks()
  sshStoreMock = {
    accounts: [{ alias: 'test-server', host: '192.168.1.1', port: 22, default: true, status: 'online', username: 'root', auth_type: 'password', password: '', private_key: '', key_passphrase: '', group: '', last_connected: '' }],
    fetchAccounts: vi.fn().mockResolvedValue(undefined),
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
    createProject: vi.fn().mockResolvedValue(undefined),
    updateProject: vi.fn().mockResolvedValue(undefined),
    deleteProject: vi.fn().mockResolvedValue(undefined),
  }
  syncStoreMock = {
    syncStatus: null,
    progress: null,
    setLogCallback: vi.fn(),
  }
  buildStoreMock = {
    buildStatus: null,
    runStatus: null,
    setLogCallback: vi.fn(),
  }
  viteDeployStoreMock = {
    status: null,
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
})
