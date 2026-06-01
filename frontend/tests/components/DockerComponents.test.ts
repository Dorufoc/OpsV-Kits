import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { nextTick } from 'vue'

vi.mock('@/components/md3', () => ({
  Md3Icon: { name: 'Md3Icon', props: ['name', 'size'], template: '<span class="mdi-icon" :data-name="name"></span>' },
  Md3Confirm: { show: vi.fn().mockResolvedValue(true) },
  Md3Message: { success: vi.fn(), error: vi.fn() },
  Md3Tag: { name: 'Md3Tag', props: ['type', 'size', 'variant'], template: '<span class="md3-tag" :data-type="type"><slot /></span>' },
  Md3Progress: { name: 'Md3Progress', props: ['percentage', 'color'], template: '<div class="md3-progress" />' },
  Md3Input: { name: 'Md3Input', props: ['modelValue', 'label', 'placeholder', 'type'], emits: ['update:modelValue'], template: '<input class="md3-input" :value="modelValue" />' },
  Md3Select: { name: 'Md3Select', props: ['modelValue', 'options', 'placeholder', 'label'], emits: ['update:modelValue'], template: '<select class="md3-select" />' },
  Md3Card: { name: 'Md3Card', props: ['shadow', 'hoverable'], template: '<div class="md3-card"><slot /><slot name="header" /></div>' },
  Md3Empty: { name: 'Md3Empty', props: ['description'], template: '<div class="md3-empty">{{ description }}</div>' },
  Md3Dialog: { name: 'Md3Dialog', props: ['visible', 'title', 'width'], emits: ['update:visible'], template: '<div class="md3-dialog" v-if="visible"><slot /><slot name="footer" /></div>' },
  Md3Tabs: { name: 'Md3Tabs', props: ['modelValue', 'tabs'], template: '<div class="md3-tabs" />' },
  Md3Table: { name: 'Md3Table', props: ['columns', 'data', 'stripe', 'emptyText'], template: '<div class="md3-table"><slot /></div>' },
  Md3Divider: { name: 'Md3Divider', template: '<hr class="md3-divider" />' },
  Md3PageHeader: { name: 'Md3PageHeader', props: ['title', 'showBack'], template: '<div class="md3-page-header" />' },
  Md3Alert: { name: 'Md3Alert', props: ['type', 'title', 'message'], template: '<div class="md3-alert" />' },
  Md3Switch: { name: 'Md3Switch', props: ['modelValue', 'onText', 'offText'], emits: ['update:modelValue'], template: '<div class="md3-switch" />' },
  Md3Spinner: { name: 'Md3Spinner', props: ['size'], template: '<div class="md3-spinner" />' },
}))

vi.mock('@/components/Md3Button.vue', () => ({
  default: { name: 'Md3Button', props: ['size', 'variant', 'disabled', 'icon', 'loading', 'type'], template: '<button class="md3-btn" :disabled="disabled" @click="$emit(\'click\')"><slot /></button>' },
}))

vi.mock('@/components/md3/Md3Tag.vue', () => ({
  default: { name: 'Md3Tag', props: ['variant', 'type', 'size'], template: '<span class="md3-tag" :data-variant="variant"><slot /></span>' },
}))

vi.mock('@/components/Terminal.vue', () => ({
  default: { name: 'Terminal', props: ['sessionName', 'showToolbar'], emits: ['data', 'resize'], template: '<div class="terminal" />' },
}))

vi.mock('@/components/DbManagerPanel.vue', () => ({
  default: { name: 'DbManagerPanel', props: ['deployMode', 'accountAlias', 'containerId', 'containerState'], template: '<div class="db-manager-panel" />' },
}))

let dockerStoreMock: any

const mockCronBackupApi = vi.hoisted(() => ({ getCronJobLogs: vi.fn().mockResolvedValue({ items: [] }) }))
vi.mock('@/stores/dockerStore', () => ({
  useDockerStore: () => dockerStoreMock,
}))

vi.mock('@/api', () => ({
  cronBackupApi: mockCronBackupApi,
}))

beforeEach(() => {
  setActivePinia(createPinia())
  vi.clearAllMocks()
  dockerStoreMock = {
    getContainerStats: vi.fn().mockResolvedValue([]),
  }
})

import ImageList from '@/components/ImageList.vue'
import ContainerStatsPanel from '@/components/ContainerStatsPanel.vue'
import ViteDeployPanel from '@/components/ViteDeployPanel.vue'
import ViteStatusCard from '@/components/ViteStatusCard.vue'
import WebhookDeployPanel from '@/components/WebhookDeployPanel.vue'
import BuildPanel from '@/components/BuildPanel.vue'
import ExecutionLogDialog from '@/components/ExecutionLogDialog.vue'

const mockImages = [
  { repository: 'nginx', tag: 'latest', id: 'sha256:abc123def456', size: '187MB', created: '2024-01-15', in_use: false },
  { repository: 'redis', tag: '7', id: 'sha256:789ghi012jkl', size: '130MB', created: '2024-01-14', in_use: true },
  { repository: 'mysql', tag: '8.0', id: 'sha256:mno345pqr678', size: '580MB', created: '2024-01-13', in_use: false },
]

describe('ImageList', () => {
  function createWrapper(props = {}) {
    return mount(ImageList, {
      props: { images: mockImages, ...props },
    })
  }

  it('应该渲染镜像列表容器', () => {
    const wrapper = createWrapper()
    expect(wrapper.find('.image-list').exists()).toBe(true)
  })

  it('应该渲染表格结构', () => {
    const wrapper = createWrapper()
    expect(wrapper.find('table').exists()).toBe(true)
    expect(wrapper.find('thead').exists()).toBe(true)
    expect(wrapper.find('tbody').exists()).toBe(true)
  })

  it('应该渲染表头列', () => {
    const wrapper = createWrapper()
    const headers = wrapper.findAll('th')
    expect(headers.length).toBe(6)
  })

  it('应该根据 images 数量渲染对应行数', () => {
    const wrapper = createWrapper()
    const rows = wrapper.findAll('tbody tr')
    expect(rows.length).toBe(3)
  })

  it('镜像为空时应该显示空状态', () => {
    const wrapper = createWrapper({ images: [] })
    expect(wrapper.text()).toContain('暂无镜像')
  })

  it('应该渲染镜像名称', () => {
    const wrapper = createWrapper()
    expect(wrapper.text()).toContain('nginx:latest')
    expect(wrapper.text()).toContain('redis:7')
  })

  it('应该渲染镜像 ID（截取前12位）', () => {
    const wrapper = createWrapper()
    expect(wrapper.text()).toContain('sha256:abc1')
  })

  it('应该渲染镜像大小', () => {
    const wrapper = createWrapper()
    expect(wrapper.text()).toContain('187MB')
    expect(wrapper.text()).toContain('130MB')
  })

  it('应该渲染使用状态标签', () => {
    const wrapper = createWrapper()
    expect(wrapper.text()).toContain('使用中')
    expect(wrapper.text()).toContain('未使用')
  })

  it('应该渲染操作按钮', () => {
    const wrapper = createWrapper()
    expect(wrapper.text()).toContain('拉取')
    expect(wrapper.text()).toContain('构建')
    expect(wrapper.text()).toContain('删除')
  })

  it('使用中的镜像删除按钮应该被禁用', () => {
    const wrapper = createWrapper()
    const rows = wrapper.findAll('tbody tr')
    const inUseRowButtons = rows[1].findAll('button')
    const deleteBtn = inUseRowButtons[inUseRowButtons.length - 1]
    expect(deleteBtn.attributes('disabled')).toBeDefined()
  })

  it('点击拉取按钮应该触发 pull 事件', async () => {
    const wrapper = createWrapper()
    const rows = wrapper.findAll('tbody tr')
    const firstRowButtons = rows[0].findAll('button')
    await firstRowButtons[0].trigger('click')
    expect(wrapper.emitted('pull')).toBeTruthy()
    expect(wrapper.emitted('pull')![0][0]).toEqual(mockImages[0])
  })

  it('点击构建按钮应该触发 build 事件', async () => {
    const wrapper = createWrapper()
    const rows = wrapper.findAll('tbody tr')
    const firstRowButtons = rows[0].findAll('button')
    await firstRowButtons[1].trigger('click')
    expect(wrapper.emitted('build')).toBeTruthy()
  })

  it('点击删除按钮应该调用 Md3Confirm', async () => {
    const { Md3Confirm } = await import('@/components/md3')
    const wrapper = createWrapper()
    const rows = wrapper.findAll('tbody tr')
    const firstRowButtons = rows[0].findAll('button')
    await firstRowButtons[2].trigger('click')
    expect(Md3Confirm.show).toHaveBeenCalled()
  })
})

describe('ContainerStatsPanel', () => {
  function createWrapper(props = {}) {
    return mount(ContainerStatsPanel, {
      props: { containerId: 'abc123', ...props },
    })
  }

  it('应该渲染容器统计面板', () => {
    const wrapper = createWrapper()
    expect(wrapper.find('.container-stats-panel').exists()).toBe(true)
  })

  it('应该接受 containerId prop', () => {
    const wrapper = createWrapper({ containerId: 'test-id' })
    expect(wrapper.props('containerId')).toBe('test-id')
  })

  it('应该渲染资源统计标题', () => {
    const wrapper = createWrapper()
    expect(wrapper.text()).toContain('资源统计')
  })

  it('应该渲染 CPU 使用率区域', () => {
    const wrapper = createWrapper()
    expect(wrapper.text()).toContain('CPU 使用率')
  })

  it('应该渲染内存使用区域', () => {
    const wrapper = createWrapper()
    expect(wrapper.text()).toContain('内存使用')
  })

  it('应该渲染网络 I/O 区域', () => {
    const wrapper = createWrapper()
    expect(wrapper.text()).toContain('网络 I/O')
  })

  it('应该渲染磁盘 I/O 区域', () => {
    const wrapper = createWrapper()
    expect(wrapper.text()).toContain('磁盘 I/O')
  })

  it('应该渲染自动刷新开关', () => {
    const wrapper = createWrapper()
    expect(wrapper.text()).toContain('自动刷新')
  })

  it('parseCPUPercent 应正确解析百分比字符串', () => {
    const wrapper = createWrapper()
    expect(wrapper.vm.parseCPUPercent('45.23%')).toBe(45.23)
    expect(wrapper.vm.parseCPUPercent('0%')).toBe(0)
    expect(wrapper.vm.parseCPUPercent('100%')).toBe(100)
  })

  it('parseCPUPercent 空值应返回 0', () => {
    const wrapper = createWrapper()
    expect(wrapper.vm.parseCPUPercent('')).toBe(0)
    expect(wrapper.vm.parseCPUPercent(undefined as any)).toBe(0)
  })

  it('parseCPUPercent 无效值应返回 0', () => {
    const wrapper = createWrapper()
    expect(wrapper.vm.parseCPUPercent('abc')).toBe(0)
  })

  it('parseBytes 应正确解析各种单位', () => {
    const wrapper = createWrapper()
    expect(wrapper.vm.parseBytes('1KiB')).toBe(1024)
    expect(wrapper.vm.parseBytes('1MiB')).toBe(1024 * 1024)
    expect(wrapper.vm.parseBytes('1GiB')).toBe(1024 ** 3)
  })

  it('parseBytes 应正确解析简写单位', () => {
    const wrapper = createWrapper()
    expect(wrapper.vm.parseBytes('1K')).toBe(1024)
    expect(wrapper.vm.parseBytes('1M')).toBe(1024 ** 2)
    expect(wrapper.vm.parseBytes('1G')).toBe(1024 ** 3)
  })

  it('parseBytes 数字输入应直接返回', () => {
    const wrapper = createWrapper()
    expect(wrapper.vm.parseBytes(1024)).toBe(1024)
  })

  it('parseBytes 空值应返回 0', () => {
    const wrapper = createWrapper()
    expect(wrapper.vm.parseBytes('')).toBe(0)
  })

  it('parseBytes 带 direction 参数应正确分割', () => {
    const wrapper = createWrapper()
    expect(wrapper.vm.parseBytes('1MiB / 2MiB', 'in')).toBe(1024 * 1024)
    expect(wrapper.vm.parseBytes('1MiB / 2MiB', 'out')).toBe(2 * 1024 * 1024)
  })

  it('formatBytes 应正确格式化字节数', () => {
    const wrapper = createWrapper()
    expect(wrapper.vm.formatBytes(0)).toBe('0 B')
    expect(wrapper.vm.formatBytes(1024)).toBe('1.0 KB')
    expect(wrapper.vm.formatBytes(1048576)).toBe('1.0 MB')
    expect(wrapper.vm.formatBytes(1073741824)).toBe('1.0 GB')
  })

  it('formatMemory 应格式化内存使用', () => {
    const wrapper = createWrapper()
    const result = wrapper.vm.formatMemory(1024 * 1024, 1024 * 1024 * 2)
    expect(result).toContain('1.0 MB')
    expect(result).toContain('2.0 MB')
  })

  it('memoryPercent 无数据时应为 0', () => {
    const wrapper = createWrapper()
    expect(wrapper.vm.memoryPercent).toBe(0)
  })

  it('memoryPercent 有数据时应正确计算', async () => {
    const wrapper = createWrapper()
    wrapper.vm.stats = { mem_usage: 536870912, mem_limit: 1073741824 }
    await nextTick()
    expect(wrapper.vm.memoryPercent).toBe(50)
  })

  it('loadStats 成功时应更新 stats', async () => {
    dockerStoreMock.getContainerStats.mockResolvedValue([{
      CPUPerc: '25.5%', MemUsage: '512MiB / 1GiB', NetIO: '1KiB / 2KiB', BlockIO: '3KiB / 4KiB', PIDs: 5,
    }])
    const wrapper = createWrapper()
    await wrapper.vm.loadStats()
    expect(wrapper.vm.stats.cpu_percent).toBe(25.5)
    expect(wrapper.vm.stats.pids).toBe(5)
    expect(wrapper.vm.lastUpdated).toBeTruthy()
  })

  it('loadStats 失败时不应抛出异常', async () => {
    dockerStoreMock.getContainerStats.mockRejectedValue(new Error('fail'))
    const wrapper = createWrapper()
    await expect(wrapper.vm.loadStats()).resolves.toBeUndefined()
  })

  it('loadStats 无数据时不应更新 stats', async () => {
    dockerStoreMock.getContainerStats.mockResolvedValue([])
    const wrapper = createWrapper()
    await wrapper.vm.loadStats()
    expect(wrapper.vm.stats.cpu_percent).toBeUndefined()
  })

  it('toggleRefresh 开启时应设置定时器', () => {
    vi.useFakeTimers()
    const wrapper = createWrapper()
    wrapper.vm.toggleRefresh(true)
    expect(wrapper.vm.refreshInterval).not.toBeNull()
    wrapper.vm.toggleRefresh(false)
    expect(wrapper.vm.refreshInterval).toBeNull()
    vi.useRealTimers()
  })

  it('onMounted 应调用 loadStats', () => {
    dockerStoreMock.getContainerStats.mockResolvedValue([])
    createWrapper()
    expect(dockerStoreMock.getContainerStats).toHaveBeenCalled()
  })
})

describe('ViteDeployPanel', () => {
  it('应该渲染 Vite 部署面板', () => {
    const wrapper = mount(ViteDeployPanel, {
      props: { projectConfig: { alias: 'test', local_path: '/tmp', remote_path: '/home/dev' } },
    })
    expect(wrapper.find('.vite-deploy-panel').exists()).toBe(true)
  })

  it('应该接受 projectConfig prop', () => {
    const config = { alias: 'myapp', local_path: 'E:\\Projects', remote_path: '/home/dev/myapp' }
    const wrapper = mount(ViteDeployPanel, {
      props: { projectConfig: config },
    })
    expect(wrapper.props('projectConfig')).toEqual(config)
  })
})

describe('ViteStatusCard', () => {
  it('应该渲染 Vite 状态卡片', () => {
    const wrapper = mount(ViteStatusCard, {
      props: { nodeStatus: { installed: true, version: 'v18.0.0', running: true }, nginxStatus: { installed: true, version: '1.24', running: true } },
    })
    expect(wrapper.find('.vite-status-card').exists()).toBe(true)
  })

  it('应该接受 nodeStatus 和 nginxStatus props', () => {
    const nodeStatus = { installed: true, version: 'v18.0.0', running: true }
    const nginxStatus = { installed: true, version: '1.24', running: true }
    const wrapper = mount(ViteStatusCard, {
      props: { nodeStatus, nginxStatus },
    })
    expect(wrapper.props('nodeStatus')).toEqual(nodeStatus)
    expect(wrapper.props('nginxStatus')).toEqual(nginxStatus)
  })
})

describe('WebhookDeployPanel', () => {
  it('应该渲染 Webhook 部署面板', () => {
    const wrapper = mount(WebhookDeployPanel)
    expect(wrapper.find('.webhook-deploy-panel').exists()).toBe(true)
  })
})

describe('BuildPanel', () => {
  it('应该渲染构建面板', () => {
    const wrapper = mount(BuildPanel, {
      props: { buildStatus: null, runStatus: null },
    })
    expect(wrapper.find('.build-panel').exists()).toBe(true)
  })

  it('应该接受 buildStatus 和 runStatus props', () => {
    const buildStatus = { status: 'success', output: 'Build completed' }
    const runStatus = { status: 'running', pid: 1234 }
    const wrapper = mount(BuildPanel, {
      props: { buildStatus, runStatus },
    })
    expect(wrapper.props('buildStatus')).toEqual(buildStatus)
    expect(wrapper.props('runStatus')).toEqual(runStatus)
  })

  it('应该在无状态时正常渲染', () => {
    const wrapper = mount(BuildPanel, {
      props: { buildStatus: null, runStatus: null },
    })
    expect(wrapper.find('.build-panel').exists()).toBe(true)
  })
})

describe('ExecutionLogDialog', () => {
  function createWrapper(props = {}) {
    return mount(ExecutionLogDialog, {
      props: {
        visible: true,
        jobId: 'job-1',
        jobName: 'TestJob',
        alias: 'test-server',
        ...props,
      },
    })
  }

  it('应该渲染对话框', () => {
    const wrapper = createWrapper()
    expect(wrapper.find('.execution-log-content').exists() || wrapper.find('.md3-dialog').exists()).toBe(true)
  })

  it('应该接受 visible prop', () => {
    const wrapper = createWrapper({ visible: false })
    expect(wrapper.props('visible')).toBe(false)
  })

  it('应该接受 jobId prop', () => {
    const wrapper = createWrapper({ jobId: 'test-job' })
    expect(wrapper.props('jobId')).toBe('test-job')
  })

  it('应该接受 jobName prop', () => {
    const wrapper = createWrapper({ jobName: 'MyJob' })
    expect(wrapper.props('jobName')).toBe('MyJob')
  })

  it('应该接受 alias prop', () => {
    const wrapper = createWrapper({ alias: 'my-server' })
    expect(wrapper.props('alias')).toBe('my-server')
  })

  it('formatDateTime 应正确格式化日期', () => {
    const wrapper = createWrapper()
    const result = wrapper.vm.formatDateTime('2024-01-15T10:30:00Z')
    expect(result).toContain('2024')
  })

  it('formatDateTime 空值应返回 -', () => {
    const wrapper = createWrapper()
    expect(wrapper.vm.formatDateTime(undefined)).toBe('-')
    expect(wrapper.vm.formatDateTime('')).toBe('-')
  })

  it('formatDateTime 无效日期应返回原值', () => {
    const wrapper = createWrapper()
    expect(wrapper.vm.formatDateTime('not-a-date')).toBe('not-a-date')
  })

  it('formatDuration 应正确格式化耗时', () => {
    const wrapper = createWrapper()
    expect(wrapper.vm.formatDuration(1.5)).toBe('1.50s')
    expect(wrapper.vm.formatDuration(0)).toBe('0.00s')
  })

  it('formatDuration null/undefined 应返回 -', () => {
    const wrapper = createWrapper()
    expect(wrapper.vm.formatDuration(null)).toBe('-')
    expect(wrapper.vm.formatDuration(undefined)).toBe('-')
  })

  it('formatDuration NaN 应返回 -', () => {
    const wrapper = createWrapper()
    expect(wrapper.vm.formatDuration(NaN)).toBe('-')
  })

  it('truncateOutput 短文本应原样返回', () => {
    const wrapper = createWrapper()
    expect(wrapper.vm.truncateOutput('short text', 60)).toBe('short text')
  })

  it('truncateOutput 长文本应截断', () => {
    const wrapper = createWrapper()
    const longText = 'a'.repeat(100)
    const result = wrapper.vm.truncateOutput(longText, 60)
    expect(result.length).toBeLessThan(100)
    expect(result).toContain('...')
  })

  it('truncateOutput 空值应返回 (无输出)', () => {
    const wrapper = createWrapper()
    expect(wrapper.vm.truncateOutput(undefined, 60)).toBe('(无输出)')
    expect(wrapper.vm.truncateOutput('', 60)).toBe('(无输出)')
  })

  it('toggleDetail 应切换展开状态', () => {
    const wrapper = createWrapper()
    const row = { id: 'log-1' }
    wrapper.vm.toggleDetail(row)
    expect(wrapper.vm.expandedRows.has('log-1')).toBe(true)
    wrapper.vm.toggleDetail(row)
    expect(wrapper.vm.expandedRows.has('log-1')).toBe(false)
  })

  it('expandedLogs 应返回展开的日志', () => {
    const wrapper = createWrapper()
    wrapper.vm.logs = [{ id: 'log-1', output: 'test' }, { id: 'log-2', output: 'test2' }]
    wrapper.vm.expandedRows.add('log-1')
    expect(wrapper.vm.expandedLogs).toHaveLength(1)
    expect(wrapper.vm.expandedLogs[0].id).toBe('log-1')
  })

  it('fetchLogs 成功时应更新 logs', async () => {
    mockCronBackupApi.getCronJobLogs.mockResolvedValue({ items: [{ id: '1', output: 'test' }] })
    const wrapper = createWrapper()
    await wrapper.vm.fetchLogs()
    expect(wrapper.vm.logs).toHaveLength(1)
  })

  it('fetchLogs 失败时应清空 logs', async () => {
    mockCronBackupApi.getCronJobLogs.mockRejectedValue(new Error('fail'))
    const wrapper = createWrapper()
    wrapper.vm.logs = [{ id: '1' }]
    await wrapper.vm.fetchLogs()
    expect(wrapper.vm.logs).toEqual([])
  })

  it('fetchLogs 无 jobId 时不应请求', async () => {
    mockCronBackupApi.getCronJobLogs.mockClear()
    const wrapper = createWrapper({ jobId: '' })
    await wrapper.vm.fetchLogs()
    expect(mockCronBackupApi.getCronJobLogs).not.toHaveBeenCalled()
  })

  it('fetchLogs 无 alias 时不应请求', async () => {
    mockCronBackupApi.getCronJobLogs.mockClear()
    const wrapper = createWrapper({ alias: '' })
    await wrapper.vm.fetchLogs()
    expect(mockCronBackupApi.getCronJobLogs).not.toHaveBeenCalled()
  })

  it('visible 变为 true 时应调用 fetchLogs', async () => {
    mockCronBackupApi.getCronJobLogs.mockClear()
    const wrapper = createWrapper({ visible: false })
    mockCronBackupApi.getCronJobLogs.mockResolvedValue({ items: [] })
    await wrapper.setProps({ visible: true })
    expect(mockCronBackupApi.getCronJobLogs).toHaveBeenCalled()
  })

  it('visible 变为 true 时应清空 expandedRows', async () => {
    const wrapper = createWrapper()
    wrapper.vm.expandedRows.add('log-1')
    await wrapper.setProps({ visible: false })
    await wrapper.setProps({ visible: true })
    expect(wrapper.vm.expandedRows.size).toBe(0)
  })
})
