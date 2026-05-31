import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { nextTick } from 'vue'

vi.mock('@/components/md3', () => ({
  Md3Icon: { name: 'Md3Icon', props: ['name', 'size'], template: '<span class="mdi-icon" :data-name="name"></span>' },
  Md3Confirm: { show: vi.fn().mockResolvedValue(true) },
  Md3Message: { success: vi.fn(), error: vi.fn() },
  Md3Tag: { name: 'Md3Tag', props: ['type', 'size', 'variant'], template: '<span class="md3-tag"><slot /></span>' },
  Md3Input: { name: 'Md3Input', props: ['modelValue', 'label', 'placeholder', 'type'], emits: ['update:modelValue'], template: '<input class="md3-input" :value="modelValue" />' },
  Md3Select: { name: 'Md3Select', props: ['modelValue', 'options', 'placeholder', 'label'], emits: ['update:modelValue'], template: '<select class="md3-select" />' },
  Md3Card: { name: 'Md3Card', props: ['shadow'], template: '<div class="md3-card"><slot /><slot name="header" /></div>' },
  Md3Empty: { name: 'Md3Empty', props: ['description'], template: '<div class="md3-empty">{{ description }}</div>' },
  Md3Dialog: { name: 'Md3Dialog', props: ['visible', 'title', 'width'], emits: ['update:visible'], template: '<div class="md3-dialog" v-if="visible"><slot /><slot name="footer" /></div>' },
  Md3Table: { name: 'Md3Table', props: ['columns', 'data', 'stripe', 'emptyText'], template: '<div class="md3-table"><slot /></div>' },
  Md3Tabs: { name: 'Md3Tabs', props: ['modelValue', 'tabs'], template: '<div class="md3-tabs" />' },
  Md3Divider: { name: 'Md3Divider', template: '<hr class="md3-divider" />' },
  Md3PageHeader: { name: 'Md3PageHeader', props: ['title'], template: '<div class="md3-page-header" />' },
  Md3Button: { name: 'Md3Button', props: ['size', 'variant', 'disabled', 'loading'], template: '<button class="md3-btn" :disabled="disabled" @click="$emit(\'click\')"><slot /></button>' },
  Md3Progress: { name: 'Md3Progress', props: ['percentage', 'color'], template: '<div class="md3-progress" />' },
  Md3Switch: { name: 'Md3Switch', props: ['modelValue', 'onText', 'offText'], emits: ['update:modelValue'], template: '<div class="md3-switch" />' },
  Md3Checkbox: { name: 'Md3Checkbox', props: ['modelValue'], emits: ['update:modelValue'], template: '<input type="checkbox" class="md3-checkbox" />' },
  Md3Alert: { name: 'Md3Alert', props: ['type', 'title', 'message'], template: '<div class="md3-alert" />' },
}))

vi.mock('@/components/Md3Button.vue', () => ({
  default: { name: 'Md3Button', props: ['size', 'variant', 'disabled', 'loading', 'type'], template: '<button class="md3-btn" :disabled="disabled" @click="$emit(\'click\')"><slot /></button>' },
}))

vi.mock('@/components/Terminal.vue', () => ({
  default: { name: 'Terminal', props: ['sessionName', 'showToolbar'], emits: ['data', 'resize'], template: '<div class="terminal" />' },
}))

beforeEach(() => {
  setActivePinia(createPinia())
  vi.clearAllMocks()
})

import SyncPanel from '@/components/SyncPanel.vue'
import PermissionEditor from '@/components/PermissionEditor.vue'

describe('SyncPanel', () => {
  function createWrapper(props = {}) {
    return mount(SyncPanel, {
      props: {
        syncStatus: 'idle',
        progress: { total: 0, transferred: 0, current_file: '', speed: '' },
        ...props,
      },
    })
  }

  it('应该渲染同步面板', () => {
    const wrapper = createWrapper()
    expect(wrapper.find('.sync-panel').exists()).toBe(true)
  })

  it('应该接受 syncStatus prop', () => {
    const wrapper = createWrapper({ syncStatus: 'syncing' })
    expect(wrapper.props('syncStatus')).toBe('syncing')
  })

  it('应该接受 progress prop', () => {
    const progress = { total: 100, transferred: 50, current_file: 'src/main.ts', speed: '1.2 MB/s' }
    const wrapper = createWrapper({ progress })
    expect(wrapper.props('progress')).toEqual(progress)
  })

  it('应该在空闲状态时正常渲染', () => {
    const wrapper = createWrapper({ syncStatus: 'idle', progress: { total: 0, transferred: 0, current_file: '', speed: '' } })
    expect(wrapper.find('.sync-panel').exists()).toBe(true)
  })

  it('应该在同步中时显示进度', () => {
    const wrapper = createWrapper({ syncStatus: 'syncing', progress: { total: 100, transferred: 50, current_file: 'src/app.ts', speed: '1.5 MB/s' } })
    expect(wrapper.find('.sync-panel').exists()).toBe(true)
  })

  it('应该在同步完成时正常渲染', () => {
    const wrapper = createWrapper({ syncStatus: 'completed', progress: { total: 100, transferred: 100, current_file: '', speed: '' } })
    expect(wrapper.find('.sync-panel').exists()).toBe(true)
  })
})

describe('PermissionEditor', () => {
  function createWrapper(props = {}) {
    return mount(PermissionEditor, {
      props: {
        modelValue: 0o644,
        showRecursive: false,
        ...props,
      },
    })
  }

  it('应该渲染权限编辑器', () => {
    const wrapper = createWrapper()
    expect(wrapper.find('.permission-editor').exists()).toBe(true)
  })

  it('应该接受 modelValue prop', () => {
    const wrapper = createWrapper({ modelValue: 0o755 })
    expect(wrapper.props('modelValue')).toBe(0o755)
  })

  it('应该接受 showRecursive prop', () => {
    const wrapper = createWrapper({ showRecursive: true })
    expect(wrapper.props('showRecursive')).toBe(true)
  })

  it('应该支持不同的权限值', () => {
    const wrapper644 = createWrapper({ modelValue: 0o644 })
    expect(wrapper644.props('modelValue')).toBe(0o644)

    const wrapper755 = createWrapper({ modelValue: 0o755 })
    expect(wrapper755.props('modelValue')).toBe(0o755)

    const wrapper777 = createWrapper({ modelValue: 0o777 })
    expect(wrapper777.props('modelValue')).toBe(0o777)
  })

  it('应该在 showRecursive 为 true 时显示递归选项', () => {
    const wrapper = createWrapper({ showRecursive: true })
    expect(wrapper.props('showRecursive')).toBe(true)
  })

  it('应该在 showRecursive 为 false 时不显示递归选项', () => {
    const wrapper = createWrapper({ showRecursive: false })
    expect(wrapper.props('showRecursive')).toBe(false)
  })
})
