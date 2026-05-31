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

vi.mock('@/components/MonitorLineChart.vue', () => ({
  default: { name: 'MonitorLineChart', props: ['data', 'color', 'yAxisName', 'height'], template: '<div class="monitor-line-chart" />' },
}))

vi.mock('@/components/MonitorGaugeChart.vue', () => ({
  default: { name: 'MonitorGaugeChart', props: ['value', 'title', 'height', 'max', 'min', 'unit'], template: '<div class="monitor-gauge-chart" />' },
}))

vi.mock('@/components/MonitorPieChart.vue', () => ({
  default: { name: 'MonitorPieChart', props: ['data', 'height', 'donut', 'roseType'], template: '<div class="monitor-pie-chart" />' },
}))

vi.mock('@/components/MonitorHeatmap.vue', () => ({
  default: { name: 'MonitorHeatmap', props: ['data', 'height', 'title'], template: '<div class="monitor-heatmap" />' },
}))

const mockPush = vi.fn()
vi.mock('vue-router', () => ({
  useRouter: () => ({ push: mockPush }),
  useRoute: () => ({}),
}))

const mockSnapshot = {
  hostname: 'test-server',
  uptime: 86400,
  cpu: { usage_percent: 45, user_percent: 30, system_percent: 15, iowait_percent: 2, cores: 4 },
  memory: { usage_percent: 60, total: 8589934592, used: 5153960755, available: 3435973837, free: 2000000000, swap: { total: 2147483648, used: 0, usage_percent: 0 } },
  disks: [{ mount: '/', filesystem: '/dev/sda1', total: 107374182400, used: 53687091200, available: 53687091200, usage_percent: 50 }],
  network: [{ interface: 'eth0', rx_bytes_per_sec: 1024, tx_bytes_per_sec: 512, rx_packets_per_sec: 10, tx_packets_per_sec: 5 }],
  load: { load_1m: 1.5, load_5m: 1.2, load_15m: 0.8, running: 120, total_processes: 200 },
  connections: { ESTABLISHED: 10, TIME_WAIT: 5, CLOSE_WAIT: 2 },
  top_processes: [],
  docker_containers: [],
  cores: [],
}

let monitorStoreMock: any
let sshStoreMock: any
let themeStoreMock: any

vi.mock('@/stores/monitorStore', () => ({
  useMonitorStore: () => monitorStoreMock,
}))

vi.mock('@/stores/sshAccountStore', () => ({
  useSshAccountStore: () => sshStoreMock,
}))

vi.mock('@/stores/themeStore', () => ({
  useThemeStore: () => themeStoreMock,
}))

beforeEach(() => {
  setActivePinia(createPinia())
  vi.clearAllMocks()
  sshStoreMock = {
    accounts: [{ alias: 'test-server', host: '192.168.1.1', default: true }],
    fetchAccounts: vi.fn().mockResolvedValue(undefined),
  }
  monitorStoreMock = {
    snapshot: null,
    loading: false,
    history: [],
    currentAlias: '',
    fetchSnapshot: vi.fn().mockResolvedValue(undefined),
    initWithHistory: vi.fn().mockResolvedValue(undefined),
    connectWebSocket: vi.fn(),
    disconnect: vi.fn(),
    formatBytes: (b: number) => `${(b / 1024 / 1024).toFixed(1)} MB`,
  }
  themeStoreMock = { mode: 'dark' }
})

import MonitorDashboard from '@/views/MonitorDashboard.vue'
import MonitorLargeScreen from '@/views/MonitorLargeScreen.vue'

describe('MonitorDashboard', () => {
  function createWrapper() {
    return mount(MonitorDashboard, { global: { stubs: { Md3Icon: true } } })
  }

  it('应该渲染监控仪表盘页面容器', () => {
    const wrapper = createWrapper()
    expect(wrapper.find('.monitor-dashboard').exists()).toBe(true)
  })

  it('应该渲染页面标题', () => {
    const wrapper = createWrapper()
    expect(wrapper.text()).toContain('全维度资源监控')
  })

  it('应该在未选择服务器时显示空状态', () => {
    const wrapper = createWrapper()
    expect(wrapper.text()).toContain('请先选择一台服务器查看监控')
  })

  it('应该在加载中时显示加载状态', async () => {
    monitorStoreMock.loading = true
    const wrapper = createWrapper()
    wrapper.vm.selectedAlias = 'test-server'
    await nextTick()
    expect(wrapper.find('.loading-state').exists()).toBe(true)
  })

  it('应该在有 snapshot 时渲染状态横幅', async () => {
    monitorStoreMock.snapshot = mockSnapshot
    const wrapper = createWrapper()
    wrapper.vm.selectedAlias = 'test-server'
    await nextTick()
    expect(wrapper.find('.status-banner').exists()).toBe(true)
    expect(wrapper.text()).toContain('test-server')
  })

  it('应该渲染仪表盘卡片', async () => {
    monitorStoreMock.snapshot = mockSnapshot
    const wrapper = createWrapper()
    wrapper.vm.selectedAlias = 'test-server'
    await nextTick()
    expect(wrapper.findAll('.gauge-card').length).toBe(4)
  })

  it('应该渲染 Tab 切换', async () => {
    monitorStoreMock.snapshot = mockSnapshot
    const wrapper = createWrapper()
    wrapper.vm.selectedAlias = 'test-server'
    await nextTick()
    expect(wrapper.find('.monitor-tabs').exists()).toBe(true)
  })

  it('goLargeScreen 应该导航到大屏模式', () => {
    const wrapper = createWrapper()
    wrapper.vm.goLargeScreen()
    expect(mockPush).toHaveBeenCalledWith('/monitor/large-screen')
  })

  it('toggleStream 应该切换流式推送', () => {
    const wrapper = createWrapper()
    wrapper.vm.selectedAlias = 'test-server'
    expect(wrapper.vm.streaming).toBe(false)
    wrapper.vm.toggleStream()
    expect(wrapper.vm.streaming).toBe(true)
    expect(monitorStoreMock.connectWebSocket).toHaveBeenCalledWith('test-server')
  })

  it('toggleStream 关闭时应该断开连接', () => {
    const wrapper = createWrapper()
    wrapper.vm.selectedAlias = 'test-server'
    wrapper.vm.streaming = true
    wrapper.vm.toggleStream()
    expect(wrapper.vm.streaming).toBe(false)
    expect(monitorStoreMock.disconnect).toHaveBeenCalled()
  })

  it('formatUptime 应该正确格式化运行时间', () => {
    const wrapper = createWrapper()
    expect(wrapper.vm.formatUptime(86400)).toBe('1d 0h 0m')
    expect(wrapper.vm.formatUptime(90061)).toBe('1d 1h 1m')
  })

  it('onAccountChange 应该更新 store 并刷新', async () => {
    monitorStoreMock.snapshot = mockSnapshot
    const wrapper = createWrapper()
    wrapper.vm.selectedAlias = 'new-server'
    await nextTick()
    await wrapper.vm.onAccountChange('new-server')
    expect(monitorStoreMock.fetchSnapshot).toHaveBeenCalled()
  })
})

describe('MonitorLargeScreen', () => {
  function createWrapper() {
    return mount(MonitorLargeScreen, { global: { stubs: { Md3Icon: true } } })
  }

  it('应该渲染大屏模式页面容器', () => {
    const wrapper = createWrapper()
    expect(wrapper.find('.large-screen').exists()).toBe(true)
  })

  it('应该渲染页面标题', () => {
    const wrapper = createWrapper()
    expect(wrapper.text()).toContain('全维度资源监控')
  })

  it('应该在无 snapshot 时显示空状态', () => {
    const wrapper = createWrapper()
    expect(wrapper.find('.ls-empty').exists()).toBe(true)
  })

  it('应该在有 snapshot 时渲染仪表盘', async () => {
    monitorStoreMock.snapshot = mockSnapshot
    const wrapper = createWrapper()
    wrapper.vm.selectedAlias = 'test-server'
    await nextTick()
    expect(wrapper.find('.ls-body').exists()).toBe(true)
    expect(wrapper.text()).toContain('test-server')
  })

  it('formatUptime 应该正确格式化运行时间', () => {
    const wrapper = createWrapper()
    expect(wrapper.vm.formatUptime(86400)).toBe('1d 0h 0m')
  })

  it('refreshNow 应该调用 fetchSnapshot', () => {
    const wrapper = createWrapper()
    wrapper.vm.selectedAlias = 'test-server'
    wrapper.vm.refreshNow()
    expect(monitorStoreMock.fetchSnapshot).toHaveBeenCalled()
  })

  it('onChange 应该更新 store 并刷新', () => {
    const wrapper = createWrapper()
    wrapper.vm.onChange('new-server')
    expect(monitorStoreMock.currentAlias).toBe('new-server')
    expect(monitorStoreMock.fetchSnapshot).toHaveBeenCalled()
  })
})
