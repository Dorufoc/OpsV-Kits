import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'

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

beforeEach(() => {
  setActivePinia(createPinia())
  vi.clearAllMocks()
})

import ImageList from '@/components/ImageList.vue'
import ContainerStatsPanel from '@/components/ContainerStatsPanel.vue'
import ViteDeployPanel from '@/components/ViteDeployPanel.vue'
import ViteStatusCard from '@/components/ViteStatusCard.vue'
import WebhookDeployPanel from '@/components/WebhookDeployPanel.vue'
import BuildPanel from '@/components/BuildPanel.vue'

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
  it('应该渲染容器统计面板', () => {
    const wrapper = mount(ContainerStatsPanel, {
      props: { containerId: 'abc123' },
    })
    expect(wrapper.find('.container-stats-panel').exists()).toBe(true)
  })

  it('应该接受 containerId prop', () => {
    const wrapper = mount(ContainerStatsPanel, {
      props: { containerId: 'test-id' },
    })
    expect(wrapper.props('containerId')).toBe('test-id')
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
