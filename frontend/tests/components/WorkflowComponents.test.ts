import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import WorkflowCanvas from '@/components/workflow/WorkflowCanvas.vue'
import WorkflowEdge from '@/components/workflow/WorkflowEdge.vue'
import WorkflowNode from '@/components/workflow/WorkflowNode.vue'
import WorkflowNodePanel from '@/components/workflow/WorkflowNodePanel.vue'
import NodeConfigPanel from '@/components/workflow/NodeConfigPanel.vue'
import WorkflowTemplateGallery from '@/components/workflow/WorkflowTemplateGallery.vue'

vi.mock('@/utils/icon-map', () => ({
  getMdiIconPath: (name: string) => `M10 20v-6h4v6h5v-8h3L12 3 2 12h3v8z`,
}))

vi.mock('@/components/md3', () => ({
  Md3Icon: {
    name: 'Md3Icon',
    props: ['name', 'size', 'color'],
    template: '<span class="md3-icon" :data-name="name" :data-size="size"></span>',
  },
  Md3Divider: {
    name: 'Md3Divider',
    props: ['orientation', 'label'],
    template: '<hr class="md3-divider" />',
  },
  Md3Input: {
    name: 'Md3Input',
    props: ['modelValue', 'label', 'placeholder', 'type', 'readonly', 'disabled'],
    emits: ['update:modelValue'],
    template: '<div class="md3-input-wrapper"><input :value="modelValue" :placeholder="placeholder" @input="$emit(\'update:modelValue\', $event.target.value)" /></div>',
  },
  Md3Select: {
    name: 'Md3Select',
    props: ['modelValue', 'options', 'label', 'placeholder'],
    emits: ['update:modelValue'],
    template: '<div class="md3-select-wrapper"><select :value="modelValue" @change="$emit(\'update:modelValue\', $event.target.value)"><option v-for="o in options" :key="o.value" :value="o.value">{{ o.label }}</option></select></div>',
  },
  Md3Switch: {
    name: 'Md3Switch',
    props: ['modelValue', 'disabled'],
    emits: ['update:modelValue'],
    template: '<button class="md3-switch" @click="$emit(\'update:modelValue\', !modelValue)"></button>',
  },
  Md3Dialog: {
    name: 'Md3Dialog',
    props: ['visible', 'title', 'fullscreen', 'closable'],
    emits: ['close', 'update:visible'],
    template: '<div class="md3-dialog" v-if="visible"><div class="md3-dialog-header">{{ title }}</div><div class="md3-dialog-body"><slot /></div><button class="md3-dialog-close" @click="$emit(\'close\'); $emit(\'update:visible\', false)">×</button></div>',
  },
  Md3Card: {
    name: 'Md3Card',
    props: { hoverable: { type: Boolean, default: false } },
    template: '<div class="md3-card" :class="{ \'md3-card--hoverable\': hoverable, \'template-card\': true }"><div v-if="$slots.header" class="md3-card-header"><slot name="header" /></div><div class="md3-card-body"><slot /></div></div>',
  },
  Md3Tag: {
    name: 'Md3Tag',
    props: ['type', 'size'],
    template: '<span class="md3-tag" :data-type="type" :data-size="size"><slot /></span>',
  },
  Md3Confirm: {
    show: vi.fn().mockResolvedValue(true),
  },
}))

vi.mock('@/components/Md3Button.vue', () => ({
  default: {
    name: 'Md3Button',
    props: ['variant', 'size', 'block', 'disabled', 'icon'],
    template: '<button class="md3-btn" :disabled="disabled" @click="$emit(\'click\')"><slot /></button>',
  },
}))

const mockNodes = [
  { id: 'node-1', node_type: 'trigger_cron', name: '定时触发', config: {}, position_x: 100, position_y: 100 },
  { id: 'node-2', node_type: 'action_shell', name: 'Shell 命令', config: {}, position_x: 400, position_y: 100 },
]

const mockEdges = [
  { id: 'edge-1', source_node_id: 'node-1', target_node_id: 'node-2', label: '成功' },
]

const mockEdgeSourceNode = { id: 'node-1', node_type: 'trigger_cron', name: '定时触发', config: {}, position_x: 100, position_y: 100 }
const mockEdgeTargetNode = { id: 'node-2', node_type: 'action_shell', name: 'Shell 命令', config: {}, position_x: 400, position_y: 100 }

describe('WorkflowCanvas', () => {
  it('应该渲染 canvas 容器', () => {
    const wrapper = mount(WorkflowCanvas, { props: { nodes: [], edges: [] } })
    expect(wrapper.find('.workflow-canvas').exists()).toBe(true)
  })

  it('应该渲染 SVG 画布', () => {
    const wrapper = mount(WorkflowCanvas, { props: { nodes: [], edges: [] } })
    expect(wrapper.find('.canvas-svg').exists()).toBe(true)
  })

  it('应该渲染控制按钮', () => {
    const wrapper = mount(WorkflowCanvas, { props: { nodes: [], edges: [] } })
    expect(wrapper.find('.canvas-controls').exists()).toBe(true)
    const buttons = wrapper.findAll('.canvas-control-btn')
    expect(buttons.length).toBe(3)
  })

  it('应该渲染小地图', () => {
    const wrapper = mount(WorkflowCanvas, { props: { nodes: [], edges: [] } })
    expect(wrapper.find('.canvas-minimap').exists()).toBe(true)
  })

  it('应该渲染 WorkflowNode 子组件', () => {
    const wrapper = mount(WorkflowCanvas, { props: { nodes: mockNodes, edges: [] } })
    expect(wrapper.findComponent({ name: 'WorkflowNode' }).exists()).toBe(true)
  })

  it('应该渲染 WorkflowEdge 子组件', () => {
    const wrapper = mount(WorkflowCanvas, { props: { nodes: mockNodes, edges: mockEdges } })
    expect(wrapper.findComponent({ name: 'WorkflowEdge' }).exists()).toBe(true)
  })

  it('点击画布应该触发 canvas-click 事件', async () => {
    const wrapper = mount(WorkflowCanvas, { props: { nodes: [], edges: [] } })
    await wrapper.find('.canvas-svg').trigger('mousedown', { button: 0 })
    expect(wrapper.emitted('canvas-click')).toBeTruthy()
  })

  it('点击放大按钮应该增加 zoom', async () => {
    const wrapper = mount(WorkflowCanvas, { props: { nodes: [], edges: [] } })
    const buttons = wrapper.findAll('.canvas-control-btn')
    await buttons[0].trigger('click')
  })

  it('点击缩小按钮应该减少 zoom', async () => {
    const wrapper = mount(WorkflowCanvas, { props: { nodes: [], edges: [] } })
    const buttons = wrapper.findAll('.canvas-control-btn')
    await buttons[1].trigger('click')
  })

  it('点击重置按钮应该重置视图', async () => {
    const wrapper = mount(WorkflowCanvas, { props: { nodes: [], edges: [] } })
    const buttons = wrapper.findAll('.canvas-control-btn')
    await buttons[2].trigger('click')
  })

  it('应该渲染网格背景', () => {
    const wrapper = mount(WorkflowCanvas, { props: { nodes: [], edges: [] } })
    const svg = wrapper.find('.canvas-svg')
    expect(svg.find('defs').exists()).toBe(true)
    expect(svg.find('pattern').exists()).toBe(true)
  })

  it('应该渲染箭头标记', () => {
    const wrapper = mount(WorkflowCanvas, { props: { nodes: [], edges: [] } })
    expect(wrapper.find('marker').exists()).toBe(true)
  })

  it('nodeExecutions 应该传递给子组件', () => {
    const executions = [{ node_id: 'node-1', status: 'running' }]
    const wrapper = mount(WorkflowCanvas, { props: { nodes: mockNodes, edges: [], nodeExecutions: executions } })
    const nodeComponent = wrapper.findComponent({ name: 'WorkflowNode' })
    expect(nodeComponent.props('executionStatus')).toBe('running')
  })

  it('小地图应该渲染节点', () => {
    const wrapper = mount(WorkflowCanvas, { props: { nodes: mockNodes, edges: [] } })
    const minimapRects = wrapper.findAll('.minimap-svg rect')
    expect(minimapRects.length).toBeGreaterThan(0)
  })
})

describe('WorkflowEdge', () => {
  it('应该渲染 edge SVG 组', () => {
    const wrapper = mount(WorkflowEdge, {
      props: {
        edge: mockEdges[0],
        sourceNode: mockEdgeSourceNode,
        targetNode: mockEdgeTargetNode,
      },
    })
    expect(wrapper.find('.workflow-edge').exists()).toBe(true)
  })

  it('应该渲染路径', () => {
    const wrapper = mount(WorkflowEdge, {
      props: {
        edge: mockEdges[0],
        sourceNode: mockEdgeSourceNode,
        targetNode: mockEdgeTargetNode,
      },
    })
    expect(wrapper.find('.edge-path').exists()).toBe(true)
  })

  it('应该渲染 hitbox 路径', () => {
    const wrapper = mount(WorkflowEdge, {
      props: {
        edge: mockEdges[0],
        sourceNode: mockEdgeSourceNode,
        targetNode: mockEdgeTargetNode,
      },
    })
    expect(wrapper.find('.edge-hitbox').exists()).toBe(true)
  })

  it('有 label 时应该渲染标签', () => {
    const wrapper = mount(WorkflowEdge, {
      props: {
        edge: mockEdges[0],
        sourceNode: mockEdgeSourceNode,
        targetNode: mockEdgeTargetNode,
      },
    })
    expect(wrapper.find('.edge-label').exists()).toBe(true)
    expect(wrapper.text()).toContain('成功')
  })

  it('没有 label 时不应该渲染标签', () => {
    const edge = { id: 'edge-2', source_node_id: 'node-1', target_node_id: 'node-2' }
    const wrapper = mount(WorkflowEdge, {
      props: {
        edge,
        sourceNode: mockEdgeSourceNode,
        targetNode: mockEdgeTargetNode,
      },
    })
    expect(wrapper.find('.edge-label').exists()).toBe(false)
  })

  it('selected 为 true 时应该渲染删除按钮', () => {
    const wrapper = mount(WorkflowEdge, {
      props: {
        edge: mockEdges[0],
        sourceNode: mockEdgeSourceNode,
        targetNode: mockEdgeTargetNode,
        selected: true,
      },
    })
    expect(wrapper.find('.edge-delete-btn').exists()).toBe(true)
  })

  it('selected 为 false 时不应该渲染删除按钮', () => {
    const wrapper = mount(WorkflowEdge, {
      props: {
        edge: mockEdges[0],
        sourceNode: mockEdgeSourceNode,
        targetNode: mockEdgeTargetNode,
        selected: false,
      },
    })
    expect(wrapper.find('.edge-delete-btn').exists()).toBe(false)
  })

  it('点击 edge 应该触发 click 事件', async () => {
    const wrapper = mount(WorkflowEdge, {
      props: {
        edge: mockEdges[0],
        sourceNode: mockEdgeSourceNode,
        targetNode: mockEdgeTargetNode,
      },
    })
    await wrapper.find('.workflow-edge').trigger('click')
    expect(wrapper.emitted('click')).toBeTruthy()
    expect(wrapper.emitted('click')![0][0]).toBe('edge-1')
  })

  it('点击删除按钮应该触发 delete 事件', async () => {
    const wrapper = mount(WorkflowEdge, {
      props: {
        edge: mockEdges[0],
        sourceNode: mockEdgeSourceNode,
        targetNode: mockEdgeTargetNode,
        selected: true,
      },
    })
    await wrapper.find('.edge-delete-btn').trigger('click')
    expect(wrapper.emitted('delete')).toBeTruthy()
    expect(wrapper.emitted('delete')![0][0]).toBe('edge-1')
  })

  it('selected 时路径应该使用 primary 颜色', () => {
    const wrapper = mount(WorkflowEdge, {
      props: {
        edge: mockEdges[0],
        sourceNode: mockEdgeSourceNode,
        targetNode: mockEdgeTargetNode,
        selected: true,
      },
    })
    const path = wrapper.find('.edge-path')
    expect(path.attributes('stroke')).toBe('var(--md3-primary)')
  })

  it('path 计算应该返回有效的 SVG 路径', () => {
    const wrapper = mount(WorkflowEdge, {
      props: {
        edge: mockEdges[0],
        sourceNode: mockEdgeSourceNode,
        targetNode: mockEdgeTargetNode,
      },
    })
    const path = wrapper.find('.edge-path')
    expect(path.attributes('d')).toBeTruthy()
    expect(path.attributes('d')).toContain('M')
  })
})

describe('WorkflowNode', () => {
  const mockNode = { id: 'node-1', node_type: 'trigger_cron', name: '定时触发', config: {}, position_x: 100, position_y: 100 }

  it('应该渲染 node SVG 组', () => {
    const wrapper = mount(WorkflowNode, { props: { node: mockNode } })
    expect(wrapper.find('.workflow-node').exists()).toBe(true)
  })

  it('应该渲染节点矩形', () => {
    const wrapper = mount(WorkflowNode, { props: { node: mockNode } })
    expect(wrapper.find('.node-body').exists()).toBe(true)
  })

  it('应该渲染节点名称', () => {
    const wrapper = mount(WorkflowNode, { props: { node: mockNode } })
    expect(wrapper.find('.node-name').text()).toContain('定时触发')
  })

  it('应该渲染输入端口', () => {
    const wrapper = mount(WorkflowNode, { props: { node: mockNode } })
    expect(wrapper.find('.node-port-input').exists()).toBe(true)
  })

  it('应该渲染输出端口', () => {
    const wrapper = mount(WorkflowNode, { props: { node: mockNode } })
    expect(wrapper.find('.node-port-output').exists()).toBe(true)
  })

  it('应该有 data-node-id 属性', () => {
    const wrapper = mount(WorkflowNode, { props: { node: mockNode } })
    expect(wrapper.find('.workflow-node').attributes('data-node-id')).toBe('node-1')
  })

  it('应该根据 position 设置 transform', () => {
    const wrapper = mount(WorkflowNode, { props: { node: mockNode } })
    const transform = wrapper.find('.workflow-node').attributes('transform')
    expect(transform).toContain('100')
    expect(transform).toContain('100')
  })

  it('executionStatus 为 running 时应该渲染状态点', () => {
    const wrapper = mount(WorkflowNode, { props: { node: mockNode, executionStatus: 'running' } })
    expect(wrapper.find('.node-status-dot').exists()).toBe(true)
  })

  it('executionStatus 不为 running 时不应该渲染状态点', () => {
    const wrapper = mount(WorkflowNode, { props: { node: mockNode, executionStatus: 'success' } })
    expect(wrapper.find('.node-status-dot').exists()).toBe(false)
  })

  it('没有 executionStatus 时不应该渲染状态点', () => {
    const wrapper = mount(WorkflowNode, { props: { node: mockNode } })
    expect(wrapper.find('.node-status-dot').exists()).toBe(false)
  })

  it('点击节点应该触发 click 事件', async () => {
    const wrapper = mount(WorkflowNode, { props: { node: mockNode } })
    await wrapper.find('.workflow-node').trigger('mousedown')
    expect(wrapper.emitted('click')).toBeTruthy()
    expect(wrapper.emitted('click')![0][0]).toBe('node-1')
  })

  it('不同 node_type 应该有不同的颜色', () => {
    const types = ['trigger_cron', 'action_shell', 'condition', 'loop', 'wait', 'notify', 'end']
    for (const type of types) {
      const node = { ...mockNode, node_type: type }
      const wrapper = mount(WorkflowNode, { props: { node } })
      const rect = wrapper.find('.node-body')
      expect(rect.attributes('fill')).toBeTruthy()
    }
  })

  it('executionStatus 为 success 时边框应该为 success 颜色', () => {
    const wrapper = mount(WorkflowNode, { props: { node: mockNode, executionStatus: 'success' } })
    const rect = wrapper.find('.node-body')
    expect(rect.attributes('stroke')).toContain('success')
  })

  it('executionStatus 为 failed 时边框应该为 error 颜色', () => {
    const wrapper = mount(WorkflowNode, { props: { node: mockNode, executionStatus: 'failed' } })
    const rect = wrapper.find('.node-body')
    expect(rect.attributes('stroke')).toContain('error')
  })

  it('点击端口应该触发 port-click 事件', async () => {
    const wrapper = mount(WorkflowNode, { props: { node: mockNode } })
    await wrapper.find('.node-port-input').trigger('mousedown')
    expect(wrapper.emitted('port-click')).toBeTruthy()
  })
})

describe('WorkflowNodePanel', () => {
  it('应该渲染面板容器', () => {
    const wrapper = mount(WorkflowNodePanel)
    expect(wrapper.find('.workflow-node-panel').exists()).toBe(true)
  })

  it('应该渲染面板标题', () => {
    const wrapper = mount(WorkflowNodePanel)
    expect(wrapper.text()).toContain('节点类型')
  })

  it('应该渲染所有分类', () => {
    const wrapper = mount(WorkflowNodePanel)
    expect(wrapper.text()).toContain('触发器')
    expect(wrapper.text()).toContain('操作')
    expect(wrapper.text()).toContain('控制')
    expect(wrapper.text()).toContain('输出')
  })

  it('应该渲染所有节点类型', () => {
    const wrapper = mount(WorkflowNodePanel)
    expect(wrapper.text()).toContain('定时触发')
    expect(wrapper.text()).toContain('Webhook')
    expect(wrapper.text()).toContain('事件触发')
    expect(wrapper.text()).toContain('Shell 命令')
    expect(wrapper.text()).toContain('HTTP 请求')
    expect(wrapper.text()).toContain('脚本执行')
    expect(wrapper.text()).toContain('条件判断')
    expect(wrapper.text()).toContain('循环')
    expect(wrapper.text()).toContain('等待')
    expect(wrapper.text()).toContain('通知')
    expect(wrapper.text()).toContain('结束')
  })

  it('每个节点项应该是可拖拽的', () => {
    const wrapper = mount(WorkflowNodePanel)
    const items = wrapper.findAll('.node-item')
    expect(items.length).toBe(11)
    for (const item of items) {
      expect(item.attributes('draggable')).toBe('true')
    }
  })

  it('应该渲染 Md3Icon 组件', () => {
    const wrapper = mount(WorkflowNodePanel)
    const icons = wrapper.findAll('.md3-icon')
    expect(icons.length).toBe(11)
  })

  it('拖拽开始应该触发 drag-start 事件', async () => {
    const wrapper = mount(WorkflowNodePanel)
    const firstItem = wrapper.find('.node-item')
    await firstItem.trigger('dragstart', { dataTransfer: { setData: vi.fn() } })
    expect(wrapper.emitted('drag-start')).toBeTruthy()
    expect(wrapper.emitted('drag-start')![0][0]).toBe('trigger_cron')
  })

  it('应该渲染分类标签', () => {
    const wrapper = mount(WorkflowNodePanel)
    const labels = wrapper.findAll('.category-label')
    expect(labels.length).toBe(4)
  })
})

describe('NodeConfigPanel', () => {
  const mockNode = {
    id: 'node-1',
    node_type: 'trigger_cron',
    name: '定时触发',
    config: { cron_expression: '0 * * * *', timezone: 'Asia/Shanghai' },
    position_x: 100,
    position_y: 100,
  }

  it('node 为 null 时不应渲染面板', () => {
    const wrapper = mount(NodeConfigPanel, { props: { node: null } })
    expect(wrapper.find('.node-config-panel').exists()).toBe(false)
  })

  it('node 不为 null 时应该渲染面板', () => {
    const wrapper = mount(NodeConfigPanel, { props: { node: mockNode } })
    expect(wrapper.find('.node-config-panel').exists()).toBe(true)
  })

  it('应该渲染节点名称', () => {
    const wrapper = mount(NodeConfigPanel, { props: { node: mockNode } })
    expect(wrapper.find('.panel-header-title').text()).toContain('定时触发')
  })

  it('应该渲染节点类型标签', () => {
    const wrapper = mount(NodeConfigPanel, { props: { node: mockNode } })
    expect(wrapper.text()).toContain('定时触发器')
  })

  it('应该渲染关闭按钮', () => {
    const wrapper = mount(NodeConfigPanel, { props: { node: mockNode } })
    expect(wrapper.find('.panel-close-btn').exists()).toBe(true)
  })

  it('点击关闭按钮应该触发 close 事件', async () => {
    const wrapper = mount(NodeConfigPanel, { props: { node: mockNode } })
    await wrapper.find('.panel-close-btn').trigger('click')
    expect(wrapper.emitted('close')).toBeTruthy()
  })

  it('应该渲染保存按钮', () => {
    const wrapper = mount(NodeConfigPanel, { props: { node: mockNode } })
    expect(wrapper.find('.panel-footer').exists()).toBe(true)
  })

  it('trigger_cron 类型应该渲染 Cron 表达式输入', () => {
    const wrapper = mount(NodeConfigPanel, { props: { node: mockNode } })
    const inputs = wrapper.findAllComponents({ name: 'Md3Input' })
    expect(inputs.length).toBeGreaterThanOrEqual(1)
  })

  it('action_shell 类型应该渲染命令输入', () => {
    const shellNode = { ...mockNode, node_type: 'action_shell', name: 'Shell 命令', config: { command: '' } }
    const wrapper = mount(NodeConfigPanel, { props: { node: shellNode } })
    expect(wrapper.text()).toContain('Shell 命令')
  })

  it('action_http 类型应该渲染 URL 输入', () => {
    const httpNode = { ...mockNode, node_type: 'action_http', name: 'HTTP 请求', config: { url: '' } }
    const wrapper = mount(NodeConfigPanel, { props: { node: httpNode } })
    expect(wrapper.text()).toContain('HTTP 请求')
  })

  it('condition 类型应该渲染条件表达式', () => {
    const condNode = { ...mockNode, node_type: 'condition', name: '条件判断', config: { expression: '' } }
    const wrapper = mount(NodeConfigPanel, { props: { node: condNode } })
    expect(wrapper.text()).toContain('条件判断')
  })

  it('end 类型应该显示无需配置提示', () => {
    const endNode = { ...mockNode, node_type: 'end', name: '结束', config: {} }
    const wrapper = mount(NodeConfigPanel, { props: { node: endNode } })
    expect(wrapper.text()).toContain('结束节点无需配置')
  })

  it('nodeTypeLabel 应该正确映射所有类型', () => {
    const typeMap: Record<string, string> = {
      trigger_cron: '定时触发器',
      trigger_webhook: 'Webhook 触发器',
      trigger_event: '事件触发器',
      action_shell: 'Shell 命令',
      action_http: 'HTTP 请求',
      action_script: '脚本执行',
      condition: '条件判断',
      loop: '循环',
      wait: '等待',
      notify: '通知',
      end: '结束',
    }
    for (const [type, label] of Object.entries(typeMap)) {
      const node = { ...mockNode, node_type: type, name: label, config: {} }
      const wrapper = mount(NodeConfigPanel, { props: { node } })
      expect(wrapper.text()).toContain(label)
    }
  })

  it('sshAccounts 应该传递给 SSH 账户选择', () => {
    const shellNode = { ...mockNode, node_type: 'action_shell', name: 'Shell', config: { command: '' } }
    const accounts = [{ id: 'acc-1', name: 'server-1' }]
    const wrapper = mount(NodeConfigPanel, { props: { node: shellNode, sshAccounts: accounts } })
    expect(wrapper.props('sshAccounts')).toEqual(accounts)
  })
})

describe('WorkflowTemplateGallery', () => {
  const templates = [
    { id: 'tpl-1', name: 'CI/CD Pipeline', description: '自动化构建部署', category: 'devops', icon: 'rocket' },
    { id: 'tpl-2', name: '监控告警', description: '服务监控通知', category: 'monitor' },
    { id: 'tpl-3', name: '安全扫描', description: '定期安全检查', category: 'security' },
  ]

  it('应该渲染模板画廊', () => {
    const wrapper = mount(WorkflowTemplateGallery, { props: { templates } })
    expect(wrapper.find('.template-gallery').exists()).toBe(true)
  })

  it('应该渲染所有模板卡片', () => {
    const wrapper = mount(WorkflowTemplateGallery, { props: { templates } })
    const cards = wrapper.findAll('.md3-card')
    expect(cards.length).toBe(3)
  })

  it('应该渲染模板名称', () => {
    const wrapper = mount(WorkflowTemplateGallery, { props: { templates } })
    expect(wrapper.text()).toContain('CI/CD Pipeline')
    expect(wrapper.text()).toContain('监控告警')
    expect(wrapper.text()).toContain('安全扫描')
  })

  it('应该渲染模板描述', () => {
    const wrapper = mount(WorkflowTemplateGallery, { props: { templates } })
    expect(wrapper.text()).toContain('自动化构建部署')
  })

  it('应该渲染分类标签', () => {
    const wrapper = mount(WorkflowTemplateGallery, { props: { templates } })
    expect(wrapper.text()).toContain('devops')
    expect(wrapper.text()).toContain('monitor')
    expect(wrapper.text()).toContain('security')
  })

  it('点击模板卡片应该触发 select 事件', async () => {
    const wrapper = mount(WorkflowTemplateGallery, { props: { templates } })
    const cards = wrapper.findAll('.md3-card')
    await cards[0].trigger('click')
    expect(wrapper.emitted('select')).toBeTruthy()
    expect(wrapper.emitted('select')![0][0]).toBe('tpl-1')
  })

  it('空模板列表应该正常渲染', () => {
    const wrapper = mount(WorkflowTemplateGallery, { props: { templates: [] } })
    expect(wrapper.find('.template-gallery').exists()).toBe(true)
    expect(wrapper.findAll('.md3-card').length).toBe(0)
  })

  it('模板卡片应该传递 hoverable 属性', () => {
    const wrapper = mount(WorkflowTemplateGallery, { props: { templates } })
    const cards = wrapper.findAllComponents({ name: 'Md3Card' })
    for (const card of cards) {
      expect(card.props('hoverable')).toBeTruthy()
    }
  })

  it('有 icon 的模板应该渲染 Md3Icon', () => {
    const wrapper = mount(WorkflowTemplateGallery, { props: { templates } })
    const icons = wrapper.findAll('.md3-icon')
    expect(icons.length).toBeGreaterThanOrEqual(1)
  })

  it('应该渲染模板网格', () => {
    const wrapper = mount(WorkflowTemplateGallery, { props: { templates } })
    expect(wrapper.find('.template-grid').exists()).toBe(true)
  })

  it('应该渲染模板卡片名称', () => {
    const wrapper = mount(WorkflowTemplateGallery, { props: { templates } })
    expect(wrapper.find('.template-card-name').exists()).toBe(true)
  })

  it('应该渲染模板卡片描述', () => {
    const wrapper = mount(WorkflowTemplateGallery, { props: { templates } })
    expect(wrapper.find('.template-card-desc').exists()).toBe(true)
  })
})
