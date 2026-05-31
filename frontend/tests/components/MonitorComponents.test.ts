import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'

vi.mock('echarts', () => ({
  init: vi.fn().mockReturnValue({
    setOption: vi.fn(),
    dispose: vi.fn(),
    resize: vi.fn(),
    on: vi.fn(),
    off: vi.fn(),
  }),
}))

vi.mock('@/components/md3', () => ({
  Md3Icon: { name: 'Md3Icon', props: ['name', 'size'], template: '<span class="mdi-icon" :data-name="name"></span>' },
}))

beforeEach(() => {
  setActivePinia(createPinia())
  vi.clearAllMocks()
})

import MonitorGaugeChart from '@/components/MonitorGaugeChart.vue'
import MonitorHeatmap from '@/components/MonitorHeatmap.vue'
import MonitorPieChart from '@/components/MonitorPieChart.vue'

describe('MonitorGaugeChart', () => {
  function createWrapper(props = {}) {
    return mount(MonitorGaugeChart, {
      props: {
        value: 50,
        ...props,
      },
    })
  }

  it('应该渲染仪表盘图表容器', () => {
    const wrapper = createWrapper()
    expect(wrapper.find('.monitor-gauge-chart').exists()).toBe(true)
  })

  it('应该接受 value prop', () => {
    const wrapper = createWrapper({ value: 75 })
    expect(wrapper.props('value')).toBe(75)
  })

  it('应该接受 title prop', () => {
    const wrapper = createWrapper({ title: 'CPU 使用率' })
    expect(wrapper.props('title')).toBe('CPU 使用率')
  })

  it('应该接受 height prop', () => {
    const wrapper = createWrapper({ height: '200px' })
    expect(wrapper.props('height')).toBe('200px')
  })

  it('应该接受 max prop', () => {
    const wrapper = createWrapper({ max: 200 })
    expect(wrapper.props('max')).toBe(200)
  })

  it('应该接受 min prop', () => {
    const wrapper = createWrapper({ min: 0 })
    expect(wrapper.props('min')).toBe(0)
  })

  it('应该接受 unit prop', () => {
    const wrapper = createWrapper({ unit: '%' })
    expect(wrapper.props('unit')).toBe('%')
  })

  it('应该有默认 props', () => {
    const wrapper = createWrapper()
    expect(wrapper.props('height')).toBe('180px')
    expect(wrapper.props('unit')).toBe('%')
    expect(wrapper.props('min')).toBe(0)
    expect(wrapper.props('max')).toBe(100)
  })

  it('应该设置容器高度', () => {
    const wrapper = createWrapper({ height: '300px' })
    const el = wrapper.find('.monitor-gauge-chart').element as HTMLElement
    expect(el.style.height).toBe('300px')
  })

  it('value 为 0 时应该正常渲染', () => {
    const wrapper = createWrapper({ value: 0 })
    expect(wrapper.find('.monitor-gauge-chart').exists()).toBe(true)
  })

  it('value 为 100 时应该正常渲染', () => {
    const wrapper = createWrapper({ value: 100 })
    expect(wrapper.find('.monitor-gauge-chart').exists()).toBe(true)
  })
})

describe('MonitorHeatmap', () => {
  function createWrapper(props = {}) {
    return mount(MonitorHeatmap, {
      props: {
        data: [
          { name: 'Core 0', value: 45 },
          { name: 'Core 1', value: 78 },
          { name: 'Core 2', value: 23 },
        ],
        ...props,
      },
    })
  }

  it('应该渲染热力图容器', () => {
    const wrapper = createWrapper()
    expect(wrapper.find('.monitor-heatmap').exists()).toBe(true)
  })

  it('应该接受 data prop', () => {
    const data = [{ name: 'C0', value: 50 }]
    const wrapper = createWrapper({ data })
    expect(wrapper.props('data')).toEqual(data)
  })

  it('应该接受 height prop', () => {
    const wrapper = createWrapper({ height: '300px' })
    expect(wrapper.props('height')).toBe('300px')
  })

  it('应该接受 title prop', () => {
    const wrapper = createWrapper({ title: 'CPU 热力图' })
    expect(wrapper.props('title')).toBe('CPU 热力图')
  })

  it('应该有默认 props', () => {
    const wrapper = createWrapper()
    expect(wrapper.props('height')).toBe('200px')
    expect(wrapper.props('title')).toBe('')
  })

  it('空数据时应该正常渲染', () => {
    const wrapper = createWrapper({ data: [] })
    expect(wrapper.find('.monitor-heatmap').exists()).toBe(true)
  })
})

describe('MonitorPieChart', () => {
  function createWrapper(props = {}) {
    return mount(MonitorPieChart, {
      props: {
        data: [
          { name: '已使用', value: 60 },
          { name: '可用', value: 40 },
        ],
        ...props,
      },
    })
  }

  it('应该渲染饼图容器', () => {
    const wrapper = createWrapper()
    expect(wrapper.find('.monitor-pie-chart').exists()).toBe(true)
  })

  it('应该接受 data prop', () => {
    const data = [{ name: 'A', value: 10 }, { name: 'B', value: 20 }]
    const wrapper = createWrapper({ data })
    expect(wrapper.props('data')).toEqual(data)
  })

  it('应该接受 height prop', () => {
    const wrapper = createWrapper({ height: '300px' })
    expect(wrapper.props('height')).toBe('300px')
  })

  it('应该接受 donut prop', () => {
    const wrapper = createWrapper({ donut: false })
    expect(wrapper.props('donut')).toBe(false)
  })

  it('应该接受 roseType prop', () => {
    const wrapper = createWrapper({ roseType: true })
    expect(wrapper.props('roseType')).toBe(true)
  })

  it('应该有默认 props', () => {
    const wrapper = createWrapper()
    expect(wrapper.props('height')).toBe('240px')
    expect(wrapper.props('donut')).toBe(true)
    expect(wrapper.props('roseType')).toBe(false)
  })

  it('空数据时应该正常渲染', () => {
    const wrapper = createWrapper({ data: [] })
    expect(wrapper.find('.monitor-pie-chart').exists()).toBe(true)
  })

  it('多数据项时应该正常渲染', () => {
    const data = [
      { name: 'A', value: 10 },
      { name: 'B', value: 20 },
      { name: 'C', value: 30 },
      { name: 'D', value: 40 },
    ]
    const wrapper = createWrapper({ data })
    expect(wrapper.find('.monitor-pie-chart').exists()).toBe(true)
  })
})
