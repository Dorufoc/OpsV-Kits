import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { nextTick } from 'vue'
import MonitorLineChart from '@/components/MonitorLineChart.vue'

const { mockChart } = vi.hoisted(() => {
  const chart = {
    setOption: vi.fn(),
    resize: vi.fn(),
    dispose: vi.fn(),
  }
  return { mockChart: chart }
})

vi.mock('echarts', () => ({
  init: vi.fn().mockReturnValue(mockChart),
  graphic: {
    LinearGradient: vi.fn().mockImplementation((x1: number, y1: number, x2: number, y2: number, stops: any[]) => ({
      type: 'linear',
      x1, y1, x2, y2, stops,
    })),
  },
  default: {
    init: vi.fn().mockReturnValue(mockChart),
    graphic: {
      LinearGradient: vi.fn().mockImplementation((x1: number, y1: number, x2: number, y2: number, stops: any[]) => ({
        type: 'linear',
        x1, y1, x2, y2, stops,
      })),
    },
  },
}))

const mockData = [
  { time: 1705312800, value: 25.5 },
  { time: 1705312860, value: 30.2 },
  { time: 1705312920, value: 28.7 },
  { time: 1705312980, value: 35.1 },
  { time: 1705313040, value: 22.8 },
]

async function createWrapper(props = {}) {
  const wrapper = mount(MonitorLineChart, {
    props: {
      data: mockData,
      ...props,
    },
    attachTo: document.body,
  })
  await nextTick()
  return wrapper
}

describe('MonitorLineChart', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('基础渲染', () => {
    it('应该渲染图表容器', async () => {
      const wrapper = await createWrapper()
      expect(wrapper.find('.monitor-line-chart').exists()).toBe(true)
    })

    it('默认高度应该是 200px', async () => {
      const wrapper = await createWrapper()
      expect(wrapper.find('.monitor-line-chart').attributes('style')).toContain('200px')
    })

    it('应该使用自定义高度', async () => {
      const wrapper = await createWrapper({ height: '300px' })
      expect(wrapper.find('.monitor-line-chart').attributes('style')).toContain('300px')
    })
  })

  describe('echarts 初始化', () => {
    it('挂载时应该调用 echarts.init', async () => {
      const echarts = await import('echarts')
      await createWrapper()
      expect(echarts.init).toHaveBeenCalled()
    })

    it('挂载时应该调用 setOption', async () => {
      await createWrapper()
      expect(mockChart.setOption).toHaveBeenCalled()
    })

    it('setOption 应该包含 series 配置', async () => {
      await createWrapper()
      const option = mockChart.setOption.mock.calls[0][0]
      expect(option.series).toBeDefined()
      expect(option.series.length).toBe(1)
      expect(option.series[0].type).toBe('line')
    })

    it('setOption 应该包含 xAxis 配置', async () => {
      await createWrapper()
      const option = mockChart.setOption.mock.calls[0][0]
      expect(option.xAxis).toBeDefined()
      expect(option.xAxis.type).toBe('category')
    })

    it('setOption 应该包含 yAxis 配置', async () => {
      await createWrapper()
      const option = mockChart.setOption.mock.calls[0][0]
      expect(option.yAxis).toBeDefined()
      expect(option.yAxis.type).toBe('value')
    })

    it('setOption 应该包含 tooltip 配置', async () => {
      await createWrapper()
      const option = mockChart.setOption.mock.calls[0][0]
      expect(option.tooltip).toBeDefined()
      expect(option.tooltip.trigger).toBe('axis')
    })

    it('setOption 应该包含 grid 配置', async () => {
      await createWrapper()
      const option = mockChart.setOption.mock.calls[0][0]
      expect(option.grid).toBeDefined()
    })

    it('背景色应该是透明的', async () => {
      await createWrapper()
      const option = mockChart.setOption.mock.calls[0][0]
      expect(option.backgroundColor).toBe('transparent')
    })
  })

  describe('数据绑定', () => {
    it('应该将数据映射到 x 轴和 y 轴', async () => {
      await createWrapper()
      const option = mockChart.setOption.mock.calls[0][0]
      expect(option.xAxis.data.length).toBe(5)
      expect(option.series[0].data.length).toBe(5)
    })

    it('y 轴数据应该与 props.data 的 value 对应', async () => {
      await createWrapper()
      const option = mockChart.setOption.mock.calls[0][0]
      expect(option.series[0].data).toEqual([25.5, 30.2, 28.7, 35.1, 22.8])
    })

    it('数据变化时应该重新调用 setOption', async () => {
      const wrapper = await createWrapper()
      mockChart.setOption.mockClear()

      const newData = [
        { time: 1705313100, value: 40.0 },
        { time: 1705313160, value: 45.3 },
      ]
      await wrapper.setProps({ data: newData })
      await nextTick()

      expect(mockChart.setOption).toHaveBeenCalled()
    })
  })

  describe('Props 配置', () => {
    it('smooth 默认应该为 true', async () => {
      await createWrapper()
      const option = mockChart.setOption.mock.calls[0][0]
      expect(option.series[0].smooth).toBe(true)
    })

    it('smooth 为 false 时应该关闭平滑', async () => {
      await createWrapper({ smooth: false })
      const option = mockChart.setOption.mock.calls[0][0]
      expect(option.series[0].smooth).toBe(false)
    })

    it('area 默认应该显示区域填充', async () => {
      await createWrapper()
      const option = mockChart.setOption.mock.calls[0][0]
      expect(option.series[0].areaStyle).toBeDefined()
    })

    it('area 为 false 时不应该显示区域填充', async () => {
      await createWrapper({ area: false })
      const option = mockChart.setOption.mock.calls[0][0]
      expect(option.series[0].areaStyle).toBeUndefined()
    })

    it('自定义颜色应该应用到线条', async () => {
      await createWrapper({ color: '#ff0000' })
      const option = mockChart.setOption.mock.calls[0][0]
      expect(option.series[0].lineStyle.color).toBe('#ff0000')
    })

    it('默认颜色应该是 #1a73e8', async () => {
      await createWrapper()
      const option = mockChart.setOption.mock.calls[0][0]
      expect(option.series[0].lineStyle.color).toBe('#1a73e8')
    })

    it('yAxisName 应该应用到 y 轴', async () => {
      await createWrapper({ yAxisName: 'CPU %' })
      const option = mockChart.setOption.mock.calls[0][0]
      expect(option.yAxis.name).toBe('CPU %')
    })

    it('title 应该应用到 series name', async () => {
      await createWrapper({ title: 'CPU Usage' })
      const option = mockChart.setOption.mock.calls[0][0]
      expect(option.series[0].name).toBe('CPU Usage')
    })

    it('线条宽度应该是 2', async () => {
      await createWrapper()
      const option = mockChart.setOption.mock.calls[0][0]
      expect(option.series[0].lineStyle.width).toBe(2)
    })

    it('symbol 应该为 none', async () => {
      await createWrapper()
      const option = mockChart.setOption.mock.calls[0][0]
      expect(option.series[0].symbol).toBe('none')
    })
  })

  describe('时间格式化', () => {
    it('x 轴数据应该是格式化后的时间字符串', async () => {
      await createWrapper()
      const option = mockChart.setOption.mock.calls[0][0]
      const xData = option.xAxis.data
      xData.forEach((val: string) => {
        expect(val).toMatch(/^\d{2}:\d{2}:\d{2}$/)
      })
    })
  })

  describe('生命周期', () => {
    it('卸载时应该销毁图表实例', async () => {
      const wrapper = await createWrapper()
      wrapper.unmount()
      expect(mockChart.dispose).toHaveBeenCalled()
    })

    it('窗口 resize 时应该调用 chart.resize', async () => {
      await createWrapper()
      mockChart.resize.mockClear()
      window.dispatchEvent(new Event('resize'))
      expect(mockChart.resize).toHaveBeenCalled()
    })
  })

  describe('空数据', () => {
    it('空数组数据时应该正常渲染', async () => {
      const wrapper = await createWrapper({ data: [] })
      expect(wrapper.find('.monitor-line-chart').exists()).toBe(true)
      expect(mockChart.setOption).toHaveBeenCalled()
      const option = mockChart.setOption.mock.calls[0][0]
      expect(option.xAxis.data).toEqual([])
      expect(option.series[0].data).toEqual([])
    })
  })
})
