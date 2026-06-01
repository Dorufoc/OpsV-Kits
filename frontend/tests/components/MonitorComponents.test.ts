import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { nextTick } from 'vue'

const { mockSetOption, mockDispose, mockResize, mockInit } = vi.hoisted(() => {
  const mockSetOption = vi.fn()
  const mockDispose = vi.fn()
  const mockResize = vi.fn()
  const mockInit = vi.fn().mockReturnValue({
    setOption: mockSetOption,
    dispose: mockDispose,
    resize: mockResize,
    on: vi.fn(),
    off: vi.fn(),
  })
  return { mockSetOption, mockDispose, mockResize, mockInit }
})

vi.mock('echarts', () => ({
  init: mockInit,
}))

vi.mock('@/components/md3', () => ({
  Md3Icon: { name: 'Md3Icon', props: ['name', 'size'], template: '<span class="mdi-icon" :data-name="name"></span>' },
}))

beforeEach(() => {
  setActivePinia(createPinia())
  vi.clearAllMocks()
  mockInit.mockReturnValue({
    setOption: mockSetOption,
    dispose: mockDispose,
    resize: mockResize,
    on: vi.fn(),
    off: vi.fn(),
  })
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

  it('数据变化时应重新渲染', async () => {
    const wrapper = createWrapper()
    await wrapper.setProps({ data: [{ name: 'C0', value: 90 }] })
    expect(wrapper.find('.monitor-heatmap').exists()).toBe(true)
  })

  it('高值数据应正常渲染', () => {
    const wrapper = createWrapper({ data: [{ name: 'Hot', value: 95 }] })
    expect(wrapper.find('.monitor-heatmap').exists()).toBe(true)
  })

  it('低值数据应正常渲染', () => {
    const wrapper = createWrapper({ data: [{ name: 'Cool', value: 10 }] })
    expect(wrapper.find('.monitor-heatmap').exists()).toBe(true)
  })

  it('有 title 时应正常渲染', () => {
    const wrapper = createWrapper({ title: '测试热力图' })
    expect(wrapper.find('.monitor-heatmap').exists()).toBe(true)
  })

  it('大量数据项应正常渲染', () => {
    const data = Array.from({ length: 24 }, (_, i) => ({ name: `C${i}`, value: Math.floor(Math.random() * 100) }))
    const wrapper = createWrapper({ data })
    expect(wrapper.find('.monitor-heatmap').exists()).toBe(true)
  })

  it('value 为 0 时应正常渲染', () => {
    const wrapper = createWrapper({ data: [{ name: 'Zero', value: 0 }] })
    expect(wrapper.find('.monitor-heatmap').exists()).toBe(true)
  })

  it('value 为 100 时应正常渲染', () => {
    const wrapper = createWrapper({ data: [{ name: 'Full', value: 100 }] })
    expect(wrapper.find('.monitor-heatmap').exists()).toBe(true)
  })

  it('容器高度应正确设置', () => {
    const wrapper = createWrapper({ height: '400px' })
    const el = wrapper.find('.monitor-heatmap').element as HTMLElement
    expect(el.style.height).toBe('400px')
  })

  it('colorFor v>=90 应返回 danger', () => {
    const wrapper = createWrapper()
    const colors = wrapper.vm.getChartColors()
    expect(wrapper.vm.colorFor(95, colors)).toBe(colors.danger)
  })

  it('colorFor v>=70 应返回 warning', () => {
    const wrapper = createWrapper()
    const colors = wrapper.vm.getChartColors()
    expect(wrapper.vm.colorFor(75, colors)).toBe(colors.warning)
  })

  it('colorFor v>=50 应返回 info', () => {
    const wrapper = createWrapper()
    const colors = wrapper.vm.getChartColors()
    expect(wrapper.vm.colorFor(55, colors)).toBe(colors.info)
  })

  it('colorFor v>=30 应返回 success', () => {
    const wrapper = createWrapper()
    const colors = wrapper.vm.getChartColors()
    expect(wrapper.vm.colorFor(35, colors)).toBe(colors.success)
  })

  it('colorFor v<30 应返回 primary', () => {
    const wrapper = createWrapper()
    const colors = wrapper.vm.getChartColors()
    expect(wrapper.vm.colorFor(10, colors)).toBe(colors.primary)
  })

  it('getChartColors 应返回包含所有颜色键的对象', () => {
    const wrapper = createWrapper()
    const colors = wrapper.vm.getChartColors()
    expect(colors).toHaveProperty('primary')
    expect(colors).toHaveProperty('success')
    expect(colors).toHaveProperty('warning')
    expect(colors).toHaveProperty('danger')
    expect(colors).toHaveProperty('info')
    expect(colors).toHaveProperty('text')
  })

  it('getChartColors 应在无 CSS 变量时使用默认值', () => {
    const wrapper = createWrapper()
    const colors = wrapper.vm.getChartColors()
    expect(colors.primary).toBeTruthy()
    expect(colors.text).toBeTruthy()
  })

  it('render 应调用 echarts.setOption', async () => {
    mockSetOption.mockClear()
    mockInit.mockClear()
    const wrapper = createWrapper()
    await nextTick()
    expect(mockInit).toHaveBeenCalled()
    expect(mockSetOption).toHaveBeenCalled()
  })

  it('数据变化时应重新调用 setOption', async () => {
    mockSetOption.mockClear()
    const wrapper = createWrapper()
    await wrapper.setProps({ data: [{ name: 'C0', value: 99 }] })
    expect(mockSetOption).toHaveBeenCalled()
  })

  it('有 title 时应正常渲染', async () => {
    mockSetOption.mockClear()
    const wrapper = createWrapper({ title: '测试' })
    await nextTick()
    expect(mockSetOption).toHaveBeenCalled()
    const lastCallArgs = mockSetOption.mock.calls[mockSetOption.mock.calls.length - 1][0]
    expect(lastCallArgs.title).toBeDefined()
    expect(lastCallArgs.title.text).toBe('测试')
  })

  it('无 title 时 title 应为 undefined', async () => {
    mockSetOption.mockClear()
    const wrapper = createWrapper()
    await nextTick()
    expect(mockSetOption).toHaveBeenCalled()
    const lastCallArgs = mockSetOption.mock.calls[mockSetOption.mock.calls.length - 1][0]
    expect(lastCallArgs.title).toBeUndefined()
  })

  it('setupThemeObserver 应创建 MutationObserver', () => {
    const wrapper = createWrapper()
    wrapper.vm.setupThemeObserver()
    expect(wrapper.vm.themeObserver).toBeTruthy()
  })

  it('setupThemeObserver 重复调用不应创建多个 observer', () => {
    const wrapper = createWrapper()
    wrapper.vm.setupThemeObserver()
    const first = wrapper.vm.themeObserver
    wrapper.vm.setupThemeObserver()
    expect(wrapper.vm.themeObserver).toBe(first)
  })

  it('onBeforeUnmount 应清理 chart 和 observer', async () => {
    mockDispose.mockClear()
    const wrapper = createWrapper()
    await nextTick()
    wrapper.vm.setupThemeObserver()
    wrapper.unmount()
    expect(mockDispose).toHaveBeenCalled()
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
