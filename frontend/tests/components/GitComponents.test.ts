import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'

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
  Md3Button: { name: 'Md3Button', props: ['size', 'variant', 'disabled', 'loading'], template: '<button class="md3-btn" :disabled="disabled" @click="$emit(\'click\')"><slot /></button>' },
  Md3Progress: { name: 'Md3Progress', props: ['percentage', 'color'], template: '<div class="md3-progress" />' },
}))

vi.mock('@/components/Md3Button.vue', () => ({
  default: { name: 'Md3Button', props: ['size', 'variant', 'disabled', 'loading', 'type'], template: '<button class="md3-btn" :disabled="disabled" @click="$emit(\'click\')"><slot /></button>' },
}))

beforeEach(() => {
  setActivePinia(createPinia())
  vi.clearAllMocks()
})

import GitBranchPanel from '@/components/GitBranchPanel.vue'
import GitCommitPanel from '@/components/GitCommitPanel.vue'
import GitRepoPanel from '@/components/GitRepoPanel.vue'
import GitSyncPanel from '@/components/GitSyncPanel.vue'

describe('GitBranchPanel', () => {
  it('应该渲染 Git 分支面板', () => {
    const wrapper = mount(GitBranchPanel)
    expect(wrapper.find('.git-branch-panel').exists()).toBe(true)
  })

  it('应该渲染面板容器', () => {
    const wrapper = mount(GitBranchPanel)
    expect(wrapper.element).toBeTruthy()
  })
})

describe('GitCommitPanel', () => {
  it('应该渲染 Git 提交面板', () => {
    const wrapper = mount(GitCommitPanel)
    expect(wrapper.find('.git-commit-panel').exists()).toBe(true)
  })

  it('应该渲染面板容器', () => {
    const wrapper = mount(GitCommitPanel)
    expect(wrapper.element).toBeTruthy()
  })
})

describe('GitRepoPanel', () => {
  it('应该渲染 Git 仓库面板', () => {
    const wrapper = mount(GitRepoPanel)
    expect(wrapper.find('.git-repo-panel').exists()).toBe(true)
  })

  it('应该渲染面板容器', () => {
    const wrapper = mount(GitRepoPanel)
    expect(wrapper.element).toBeTruthy()
  })
})

describe('GitSyncPanel', () => {
  it('应该渲染 Git 同步面板', () => {
    const wrapper = mount(GitSyncPanel)
    expect(wrapper.find('.git-sync-panel').exists()).toBe(true)
  })

  it('应该渲染面板容器', () => {
    const wrapper = mount(GitSyncPanel)
    expect(wrapper.element).toBeTruthy()
  })
})
