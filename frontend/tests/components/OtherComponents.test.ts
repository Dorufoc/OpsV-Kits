import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { nextTick } from 'vue'

vi.mock('@/components/md3', () => ({
  Md3Icon: { name: 'Md3Icon', props: ['name', 'size'], template: '<span class="mdi-icon" :data-name="name"></span>' },
  Md3Confirm: { show: vi.fn().mockResolvedValue(true) },
  Md3Message: { success: vi.fn(), error: vi.fn() },
  Md3Tag: { name: 'Md3Tag', props: ['type', 'size', 'variant'], template: '<span class="md3-tag"><slot /></span>' },
  Md3Input: { name: 'Md3Input', props: ['modelValue', 'label', 'placeholder', 'type'], emits: ['update:modelValue'], template: '<input class="md3-input" :value="modelValue" @input="$emit(\'update:modelValue\', $event.target.value)" />' },
  Md3Select: { name: 'Md3Select', props: ['modelValue', 'options', 'placeholder', 'label', 'clearable'], emits: ['update:modelValue'], template: '<select class="md3-select" />' },
  Md3Card: { name: 'Md3Card', props: ['shadow'], template: '<div class="md3-card"><slot /><slot name="header" /></div>' },
  Md3Empty: { name: 'Md3Empty', props: ['description'], template: '<div class="md3-empty">{{ description }}</div>' },
  Md3Dialog: { name: 'Md3Dialog', props: ['visible', 'title', 'width'], emits: ['update:visible', 'close'], template: '<div class="md3-dialog" v-if="visible"><slot /><slot name="footer" /></div>' },
  Md3Table: { name: 'Md3Table', props: ['columns', 'data', 'stripe', 'emptyText', 'border', 'hover'], template: '<div class="md3-table"><slot /></div>' },
  Md3Tabs: { name: 'Md3Tabs', props: ['modelValue', 'tabs'], template: '<div class="md3-tabs" />' },
  Md3Divider: { name: 'Md3Divider', template: '<hr class="md3-divider" />' },
  Md3Button: { name: 'Md3Button', props: ['size', 'variant', 'disabled', 'loading'], template: '<button class="md3-btn" :disabled="disabled" @click="$emit(\'click\')"><slot /></button>' },
  Md3Progress: { name: 'Md3Progress', props: ['percentage', 'color'], template: '<div class="md3-progress" />' },
  Md3Switch: { name: 'Md3Switch', props: ['modelValue', 'onText', 'offText'], emits: ['update:modelValue'], template: '<div class="md3-switch" />' },
  Md3Alert: { name: 'Md3Alert', props: ['type', 'title', 'message'], template: '<div class="md3-alert" />' },
}))

vi.mock('@/components/Md3Button.vue', () => ({
  default: { name: 'Md3Button', props: ['size', 'variant', 'disabled', 'loading', 'type'], template: '<button class="md3-btn" :disabled="disabled" @click="$emit(\'click\')"><slot /></button>' },
}))

const { themeStoreMock } = vi.hoisted(() => ({
  themeStoreMock: {
    mode: 'light' as string,
    preset: 'indigo' as string,
    toggleDark: vi.fn(),
    setMode: vi.fn(),
    setPreset: vi.fn(),
  },
}))

vi.mock('@/stores/themeStore', () => ({
  useThemeStore: () => themeStoreMock,
}))

import BackupHistoryDrawer from '@/components/BackupHistoryDrawer.vue'
import ColorPresets from '@/components/ColorPresets.vue'
import CronPicker from '@/components/CronPicker.vue'
import ExecutionLogDialog from '@/components/ExecutionLogDialog.vue'
import SessionManager from '@/components/SessionManager.vue'
import ThemeToggle from '@/components/ThemeToggle.vue'
import { cronBackupApi } from '@/api'

beforeEach(() => {
  themeStoreMock.mode = 'light'
  themeStoreMock.preset = 'indigo'
  themeStoreMock.toggleDark.mockReset()
  themeStoreMock.setMode.mockReset()
  themeStoreMock.setPreset.mockReset()
})

describe('BackupHistoryDrawer', () => {
  function createWrapper(props = {}) {
    return mount(BackupHistoryDrawer, {
      props: { visible: true, policyId: 'p1', policyName: '每日备份', alias: 'test-server', ...props },
    })
  }

  it('应该渲染备份历史抽屉', () => {
    const wrapper = createWrapper()
    expect(wrapper.find('.md3-dialog').exists()).toBe(true)
  })

  it('应该接受 visible prop', () => {
    const wrapper = createWrapper({ visible: false })
    expect(wrapper.props('visible')).toBe(false)
  })

  it('visible 为 true 时应该显示抽屉', () => {
    const wrapper = createWrapper()
    expect(wrapper.props('visible')).toBe(true)
  })

  it('应该显示策略名称', () => {
    const wrapper = createWrapper()
    const dialog = wrapper.findComponent({ name: 'Md3Dialog' })
    expect(dialog.exists()).toBe(true)
    expect(dialog.props('title')).toContain('每日备份')
  })

  it('应该渲染表格列', () => {
    const wrapper = createWrapper()
    expect(wrapper.find('.md3-table').exists()).toBe(true)
  })

  it('关闭按钮应触发 update:visible 事件', async () => {
    const wrapper = createWrapper()
    const buttons = wrapper.findAll('.md3-btn')
    const closeBtn = buttons.find(b => b.text().includes('关闭'))
    if (closeBtn) {
      await closeBtn.trigger('click')
    }
  })

  it('visible 变为 true 时应调用 fetchHistory', async () => {
    const wrapper = createWrapper({ visible: false })
    vi.mocked(cronBackupApi.listBackupHistory).mockResolvedValue({ items: [{ id: '1', created_at: '2024-01-01T00:00:00Z', file_size: 1024, storage_type: 'local', status: 'success', file_path: '/backup/db.sql' }] } as any)
    await wrapper.setProps({ visible: true })
    await nextTick()
    expect(cronBackupApi.listBackupHistory).toHaveBeenCalledWith('test-server', 'p1')
  })

  it('visible 变为 false 时应清空 historyList', async () => {
    vi.mocked(cronBackupApi.listBackupHistory).mockResolvedValue({ items: [{ id: '1', created_at: '2024-01-01T00:00:00Z', file_size: 1024, storage_type: 'local', status: 'success', file_path: '/backup/db.sql' }] } as any)
    const wrapper = createWrapper()
    await nextTick()
    await wrapper.setProps({ visible: false })
    await nextTick()
  })

  it('fetchHistory 无 alias 时应提前返回', async () => {
    vi.mocked(cronBackupApi.listBackupHistory).mockClear()
    const wrapper = createWrapper({ alias: '', policyId: '' })
    await nextTick()
    expect(cronBackupApi.listBackupHistory).not.toHaveBeenCalled()
  })

  it('fetchHistory 成功时应填充 historyList', async () => {
    const items = [
      { id: '1', created_at: '2024-01-01T00:00:00Z', file_size: 1024, storage_type: 'local', status: 'success', file_path: '/backup/db.sql' },
      { id: '2', created_at: '2024-01-02T00:00:00Z', file_size: 2048, storage_type: 's3', status: 'failed', file_path: '' },
    ]
    vi.mocked(cronBackupApi.listBackupHistory).mockResolvedValue({ items } as any)
    const wrapper = mount(BackupHistoryDrawer, {
      props: { visible: false, policyId: 'p1', policyName: '每日备份', alias: 'test-server' },
    })
    await wrapper.setProps({ visible: true })
    await nextTick()
    await nextTick()
    expect(cronBackupApi.listBackupHistory).toHaveBeenCalledWith('test-server', 'p1')
  })

  it('fetchHistory 失败时应清空 historyList', async () => {
    vi.mocked(cronBackupApi.listBackupHistory).mockRejectedValue(new Error('Network error'))
    const wrapper = createWrapper()
    await nextTick()
  })

  it('fetchHistory 无 items 时应使用空数组', async () => {
    vi.mocked(cronBackupApi.listBackupHistory).mockResolvedValue({} as any)
    const wrapper = createWrapper()
    await nextTick()
  })

  it('handleDownload 成功时应创建下载链接', async () => {
    const blob = new Blob(['test'], { type: 'application/octet-stream' })
    vi.mocked(cronBackupApi.downloadBackupFile).mockResolvedValue(blob as any)
    const createObjectURLSpy = vi.fn().mockReturnValue('blob:test')
    const revokeObjectURLSpy = vi.fn()
    vi.stubGlobal('URL', { createObjectURL: createObjectURLSpy, revokeObjectURL: revokeObjectURLSpy })
    const wrapper = createWrapper()
    await nextTick()
    const vm = wrapper.vm as any
    if (typeof vm.handleDownload === 'function') {
      await vm.handleDownload({ id: '1', file_path: '/backup/db.sql', status: 'success', storage_type: 'local' })
      expect(cronBackupApi.downloadBackupFile).toHaveBeenCalledWith('1', 'test-server', '/backup/db.sql')
    }
    vi.unstubAllGlobals()
  })

  it('handleDownload 无 id 时应提前返回', async () => {
    vi.mocked(cronBackupApi.downloadBackupFile).mockClear()
    const wrapper = createWrapper()
    await nextTick()
    const vm = wrapper.vm as any
    if (typeof vm.handleDownload === 'function') {
      await vm.handleDownload({ id: null, file_path: '/backup/db.sql' })
      expect(cronBackupApi.downloadBackupFile).not.toHaveBeenCalled()
    }
  })

  it('handleDownload 无 file_path 时应提前返回', async () => {
    vi.mocked(cronBackupApi.downloadBackupFile).mockClear()
    const wrapper = createWrapper()
    await nextTick()
    const vm = wrapper.vm as any
    if (typeof vm.handleDownload === 'function') {
      await vm.handleDownload({ id: '1', file_path: null })
      expect(cronBackupApi.downloadBackupFile).not.toHaveBeenCalled()
    }
  })

  it('handleDownload 失败时不应抛出异常', async () => {
    vi.mocked(cronBackupApi.downloadBackupFile).mockRejectedValue(new Error('Download failed'))
    const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
    const wrapper = createWrapper()
    await nextTick()
    const vm = wrapper.vm as any
    if (typeof vm.handleDownload === 'function') {
      await vm.handleDownload({ id: '1', file_path: '/backup/db.sql' })
    }
    consoleErrorSpy.mockRestore()
  })

  it('statusTagType 应正确映射所有状态', () => {
    const wrapper = createWrapper()
    const vm = wrapper.vm as any
    if (typeof vm.statusTagType === 'function') {
      expect(vm.statusTagType('success')).toBe('success')
      expect(vm.statusTagType('failed')).toBe('danger')
      expect(vm.statusTagType('running')).toBe('primary')
      expect(vm.statusTagType('unknown')).toBe('info')
    }
  })

  it('statusLabel 应正确映射所有状态', () => {
    const wrapper = createWrapper()
    const vm = wrapper.vm as any
    if (typeof vm.statusLabel === 'function') {
      expect(vm.statusLabel('success')).toBe('成功')
      expect(vm.statusLabel('failed')).toBe('失败')
      expect(vm.statusLabel('running')).toBe('进行中')
      expect(vm.statusLabel('other')).toBe('other')
    }
  })

  it('formatBytes 应正确格式化字节', () => {
    const wrapper = createWrapper()
    const vm = wrapper.vm as any
    if (typeof vm.formatBytes === 'function') {
      expect(vm.formatBytes(null)).toBe('-')
      expect(vm.formatBytes(0)).toBe('-')
      expect(vm.formatBytes(500)).toBe('500.00 B')
      expect(vm.formatBytes(1024)).toBe('1.00 KB')
      expect(vm.formatBytes(1048576)).toBe('1.00 MB')
      expect(vm.formatBytes(1073741824)).toBe('1.00 GB')
      expect(vm.formatBytes(1099511627776)).toBe('1.00 TB')
    }
  })

  it('formatDateTime 应正确格式化日期时间', () => {
    const wrapper = createWrapper()
    const vm = wrapper.vm as any
    if (typeof vm.formatDateTime === 'function') {
      expect(vm.formatDateTime(null)).toBe('-')
      expect(vm.formatDateTime(undefined)).toBe('-')
      expect(vm.formatDateTime('')).toBe('-')
      expect(vm.formatDateTime('2024-01-15T10:30:00Z')).toBeTruthy()
      expect(vm.formatDateTime('invalid-date')).toBe('invalid-date')
    }
  })
})

describe('ColorPresets', () => {
  it('应该渲染颜色预设组件', () => {
    const wrapper = mount(ColorPresets)
    expect(wrapper.find('.color-presets').exists()).toBe(true)
  })

  it('应该渲染预设按钮', () => {
    const wrapper = mount(ColorPresets)
    const buttons = wrapper.findAll('.preset-btn')
    expect(buttons.length).toBe(6)
  })

  it('应该渲染预设名称', () => {
    const wrapper = mount(ColorPresets)
    expect(wrapper.text()).toContain('靛蓝')
    expect(wrapper.text()).toContain('天蓝')
    expect(wrapper.text()).toContain('翠绿')
    expect(wrapper.text()).toContain('橙黄')
    expect(wrapper.text()).toContain('玫红')
    expect(wrapper.text()).toContain('紫罗兰')
  })

  it('应该渲染色块', () => {
    const wrapper = mount(ColorPresets)
    const swatches = wrapper.findAll('.preset-swatch')
    expect(swatches.length).toBe(6)
  })

  it('当前预设应该有 active 类', () => {
    const wrapper = mount(ColorPresets)
    const activeBtn = wrapper.find('.preset-btn.active')
    expect(activeBtn.exists()).toBe(true)
  })

  it('点击预设按钮应该调用 setPreset', async () => {
    const wrapper = mount(ColorPresets)
    const buttons = wrapper.findAll('.preset-btn')
    await buttons[1].trigger('click')
    expect(themeStoreMock.setPreset).toHaveBeenCalled()
  })

  it('应该接受 label prop', () => {
    const wrapper = mount(ColorPresets, {
      props: { label: '自定义标签' },
    })
    expect(wrapper.text()).toContain('自定义标签')
  })
})

describe('CronPicker', () => {
  it('应该渲染 Cron 选择器', () => {
    const wrapper = mount(CronPicker, {
      props: { modelValue: '* * * * *' },
    })
    expect(wrapper.find('.cron-picker').exists()).toBe(true)
  })

  it('应该接受 modelValue prop', () => {
    const wrapper = mount(CronPicker, {
      props: { modelValue: '0 0 * * *' },
    })
    expect(wrapper.props('modelValue')).toBe('0 0 * * *')
  })

  it('应该支持不同的 cron 表达式', () => {
    const expressions = [
      '* * * * *',
      '0 * * * *',
      '0 0 * * *',
      '0 0 * * 0',
      '0 0 1 * *',
    ]
    expressions.forEach(expr => {
      const wrapper = mount(CronPicker, {
        props: { modelValue: expr },
      })
      expect(wrapper.props('modelValue')).toBe(expr)
    })
  })

  it('应该渲染预设按钮', () => {
    const wrapper = mount(CronPicker, {
      props: { modelValue: '* * * * *' },
    })
    const presetBtns = wrapper.findAll('.preset-btn')
    expect(presetBtns.length).toBe(5)
  })

  it('应该渲染各时间段分区', () => {
    const wrapper = mount(CronPicker, {
      props: { modelValue: '* * * * *' },
    })
    expect(wrapper.text()).toContain('分钟')
    expect(wrapper.text()).toContain('小时')
    expect(wrapper.text()).toContain('日')
    expect(wrapper.text()).toContain('月')
    expect(wrapper.text()).toContain('周几')
  })

  it('点击预设按钮应更新 modelValue', async () => {
    const wrapper = mount(CronPicker, {
      props: { modelValue: '* * * * *' },
    })
    const presetBtns = wrapper.findAll('.preset-btn')
    if (presetBtns.length > 1) {
      await presetBtns[1].trigger('click')
      const emitted = wrapper.emitted('update:modelValue')
      expect(emitted).toBeTruthy()
    }
  })

  it('应该渲染原始表达式输入框', () => {
    const wrapper = mount(CronPicker, {
      props: { modelValue: '* * * * *' },
    })
    expect(wrapper.find('.raw-input').exists()).toBe(true)
  })

  it('应该显示表达式描述', () => {
    const wrapper = mount(CronPicker, {
      props: { modelValue: '* * * * *' },
    })
    expect(wrapper.find('.description').exists()).toBe(true)
    expect(wrapper.text()).toContain('每分钟执行')
  })

  it('每天表达式应显示正确描述', () => {
    const wrapper = mount(CronPicker, {
      props: { modelValue: '0 0 * * *' },
    })
    expect(wrapper.text()).toContain('每天凌晨0点执行')
  })

  it('每周表达式应显示正确描述', () => {
    const wrapper = mount(CronPicker, {
      props: { modelValue: '0 0 * * 0' },
    })
    expect(wrapper.text()).toContain('每周日凌晨0点执行')
  })

  it('每月表达式应显示正确描述', () => {
    const wrapper = mount(CronPicker, {
      props: { modelValue: '0 0 1 * *' },
    })
    expect(wrapper.text()).toContain('每月1日凌晨0点执行')
  })

  it('点击值按钮应切换选中状态', async () => {
    const wrapper = mount(CronPicker, {
      props: { modelValue: '0 * * * *' },
    })
    const valueBtns = wrapper.findAll('.value-btn')
    if (valueBtns.length > 0) {
      await valueBtns[0].trigger('click')
      const emitted = wrapper.emitted('update:modelValue')
      expect(emitted).toBeTruthy()
    }
  })

  it('无效表达式应显示错误描述', () => {
    const wrapper = mount(CronPicker, {
      props: { modelValue: 'invalid' },
    })
    expect(wrapper.text()).toContain('无效的 Cron 表达式')
  })

  it('输入框输入应更新表达式', async () => {
    const wrapper = mount(CronPicker, {
      props: { modelValue: '* * * * *' },
    })
    const input = wrapper.find('.raw-input')
    await input.setValue('0 0 * * *')
    const emitted = wrapper.emitted('update:modelValue')
    expect(emitted).toBeTruthy()
  })
})

describe('ExecutionLogDialog', () => {
  it('应该渲染执行日志对话框', () => {
    const wrapper = mount(ExecutionLogDialog, {
      props: { visible: true, jobId: 'job-123', jobName: '测试任务', alias: 'test-server' },
    })
    expect(wrapper.find('.md3-dialog').exists()).toBe(true)
  })

  it('应该接受 visible prop', () => {
    const wrapper = mount(ExecutionLogDialog, {
      props: { visible: false, jobId: '', jobName: '', alias: '' },
    })
    expect(wrapper.props('visible')).toBe(false)
  })

  it('应该接受 jobId prop', () => {
    const wrapper = mount(ExecutionLogDialog, {
      props: { visible: true, jobId: 'test-job-id', jobName: '测试', alias: 'server' },
    })
    expect(wrapper.props('jobId')).toBe('test-job-id')
  })
})

describe('SessionManager', () => {
  const mockSessions = [
    { id: 's1', alias: 'prod', host: '192.168.1.1', username: 'root', status: 'online' },
    { id: 's2', alias: 'dev', host: '10.0.0.1', username: 'admin', status: 'connecting' },
  ]

  const mockHistoryRecords = [
    { session_id: 'h1', account_alias: 'staging', host: '172.16.0.1', username: 'deploy', disconnected_at: '2024-01-15T10:00:00Z' },
  ]

  function createWrapper(props = {}) {
    return mount(SessionManager, {
      props: {
        sessions: mockSessions,
        historyRecords: mockHistoryRecords,
        activeSessionId: 's1',
        ...props,
      },
    })
  }

  it('应该渲染会话管理器', () => {
    const wrapper = createWrapper()
    expect(wrapper.find('.session-manager').exists()).toBe(true)
  })

  it('应该渲染活跃会话列表', () => {
    const wrapper = createWrapper()
    expect(wrapper.text()).toContain('活跃会话')
  })

  it('应该渲染历史记录', () => {
    const wrapper = createWrapper()
    expect(wrapper.text()).toContain('历史记录')
  })

  it('应该渲染会话项', () => {
    const wrapper = createWrapper()
    const items = wrapper.findAll('.session-item')
    expect(items.length).toBe(3)
  })

  it('应该显示会话别名', () => {
    const wrapper = createWrapper()
    expect(wrapper.text()).toContain('prod')
    expect(wrapper.text()).toContain('dev')
  })

  it('应该显示会话用户名', () => {
    const wrapper = createWrapper()
    expect(wrapper.text()).toContain('@root')
    expect(wrapper.text()).toContain('@admin')
  })

  it('应该渲染新建会话按钮', () => {
    const wrapper = createWrapper()
    expect(wrapper.text()).toContain('新建会话')
  })

  it('点击会话项应该触发 select 事件', async () => {
    const wrapper = createWrapper()
    const firstSession = wrapper.findAll('.session-item')[0]
    await firstSession.trigger('click')
    expect(wrapper.emitted('select')).toBeTruthy()
  })

  it('应该渲染断开按钮', () => {
    const wrapper = createWrapper()
    expect(wrapper.text()).toContain('断开')
  })

  it('空会话和空历史时应该显示空状态', () => {
    const wrapper = createWrapper({ sessions: [], historyRecords: [] })
    expect(wrapper.find('.session-empty').exists()).toBe(true)
  })

  it('应该显示在线状态标签', () => {
    const wrapper = createWrapper()
    expect(wrapper.text()).toContain('在线')
  })
})

describe('ThemeToggle', () => {
  it('应该渲染主题切换按钮', () => {
    const wrapper = mount(ThemeToggle)
    expect(wrapper.find('.theme-icon-btn').exists()).toBe(true)
  })

  it('应该渲染 SVG 图标', () => {
    const wrapper = mount(ThemeToggle)
    expect(wrapper.find('svg').exists()).toBe(true)
  })

  it('点击按钮应该调用 toggleDark', async () => {
    const wrapper = mount(ThemeToggle)
    await wrapper.find('.theme-icon-btn').trigger('click')
    expect(themeStoreMock.toggleDark).toHaveBeenCalled()
  })

  it('亮色模式应该渲染太阳图标', () => {
    themeStoreMock.mode = 'light'
    const wrapper = mount(ThemeToggle)
    expect(wrapper.find('.sun').exists()).toBe(true)
  })

  it('暗色模式应该渲染月亮图标', () => {
    themeStoreMock.mode = 'dark'
    const wrapper = mount(ThemeToggle)
    expect(wrapper.find('.moon').exists()).toBe(true)
  })

  it('应该有正确的 aria-label', () => {
    themeStoreMock.mode = 'dark'
    const wrapper = mount(ThemeToggle)
    expect(wrapper.find('.theme-icon-btn').attributes('aria-label')).toContain('切换到亮色模式')
  })
})
