/**
 * Md3Button 组件单元测试
 * 测试不同 props 下的渲染、点击事件和禁用状态
 */
import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import Md3Button from '@/components/Md3Button.vue'
import { Md3Icon } from '@/components/md3'

// Mock Md3Icon to avoid importing the full component
vi.mock('@/components/md3', () => ({
  Md3Icon: {
    name: 'Md3Icon',
    props: ['name'],
    template: '<span class="mdi-icon" :data-name="name"></span>',
  },
}))

describe('Md3Button', () => {
  describe('基础渲染', () => {
    it('应该渲染为一个 button 元素', () => {
      const wrapper = mount(Md3Button)
      expect(wrapper.element.tagName).toBe('BUTTON')
    })

    it('应该应用 md3-btn 基础类', () => {
      const wrapper = mount(Md3Button)
      expect(wrapper.classes()).toContain('md3-btn')
    })

    it('默认应该应用 default variant 类', () => {
      const wrapper = mount(Md3Button)
      expect(wrapper.classes()).toContain('md3-btn--default')
    })

    it('默认应该应用 md size 类', () => {
      const wrapper = mount(Md3Button)
      expect(wrapper.classes()).toContain('md3-btn--md')
    })

    it('应该渲染 slot 内容', () => {
      const wrapper = mount(Md3Button, {
        slots: {
          default: 'Click Me',
        },
      })
      expect(wrapper.text()).toContain('Click Me')
    })
  })

  describe('Variant Props', () => {
    it('primary variant 应该应用 md3-btn--primary 类', () => {
      const wrapper = mount(Md3Button, {
        props: { variant: 'primary' },
      })
      expect(wrapper.classes()).toContain('md3-btn--primary')
    })

    it('danger variant 应该应用 md3-btn--danger 类', () => {
      const wrapper = mount(Md3Button, {
        props: { variant: 'danger' },
      })
      expect(wrapper.classes()).toContain('md3-btn--danger')
    })

    it('success variant 应该应用 md3-btn--success 类', () => {
      const wrapper = mount(Md3Button, {
        props: { variant: 'success' },
      })
      expect(wrapper.classes()).toContain('md3-btn--success')
    })

    it('warning variant 应该应用 md3-btn--warning 类', () => {
      const wrapper = mount(Md3Button, {
        props: { variant: 'warning' },
      })
      expect(wrapper.classes()).toContain('md3-btn--warning')
    })

    it('text variant 应该应用 md3-btn--text 类', () => {
      const wrapper = mount(Md3Button, {
        props: { variant: 'text' },
      })
      expect(wrapper.classes()).toContain('md3-btn--text')
    })
  })

  describe('Size Props', () => {
    it('sm size 应该应用 md3-btn--sm 类', () => {
      const wrapper = mount(Md3Button, {
        props: { size: 'sm' },
        slots: { default: 'Small' },
      })
      expect(wrapper.classes()).toContain('md3-btn--sm')
    })

    it('md size 应该应用 md3-btn--md 类', () => {
      const wrapper = mount(Md3Button, {
        props: { size: 'md' },
        slots: { default: 'Medium' },
      })
      expect(wrapper.classes()).toContain('md3-btn--md')
    })

    it('lg size 应该应用 md3-btn--lg 类', () => {
      const wrapper = mount(Md3Button, {
        props: { size: 'lg' },
        slots: { default: 'Large' },
      })
      expect(wrapper.classes()).toContain('md3-btn--lg')
    })

    it('没有 slot 内容时 icon-only 应该使用 sm size', () => {
      const wrapper = mount(Md3Button, {
        props: { icon: 'refresh' },
      })
      expect(wrapper.classes()).toContain('md3-btn--icon-only')
      expect(wrapper.classes()).toContain('md3-btn--sm')
    })

    it('有 slot 内容时应该使用 md size', () => {
      const wrapper = mount(Md3Button, {
        props: { icon: 'refresh' },
        slots: { default: 'Refresh' },
      })
      expect(wrapper.classes()).not.toContain('md3-btn--icon-only')
      expect(wrapper.classes()).toContain('md3-btn--md')
    })
  })

  describe('Icon Props', () => {
    it('传入 string icon 应该渲染 Md3Icon 组件', () => {
      const wrapper = mount(Md3Button, {
        props: { icon: 'refresh' },
      })
      expect(wrapper.findComponent(Md3Icon).exists()).toBe(true)
    })

    it('Md3Icon 应该传入正确的 name', () => {
      const wrapper = mount(Md3Button, {
        props: { icon: 'close' },
      })
      expect(wrapper.findComponent(Md3Icon).props('name')).toBe('close')
    })

    it('没有 icon 和 slot 时不应该渲染 Md3Icon', () => {
      const wrapper = mount(Md3Button, {
        slots: { default: 'No Icon' },
      })
      expect(wrapper.findComponent(Md3Icon).exists()).toBe(false)
    })
  })

  describe('Disabled State', () => {
    it('disabled 应该应用 md3-btn--disabled 类', () => {
      const wrapper = mount(Md3Button, {
        props: { disabled: true },
      })
      expect(wrapper.classes()).toContain('md3-btn--disabled')
    })

    it('disabled 时 button 应该被禁用', () => {
      const wrapper = mount(Md3Button, {
        props: { disabled: true },
      })
      expect(wrapper.attributes('disabled')).toBeDefined()
    })

    it('disabled 时不应该触发 click 事件', async () => {
      const onClick = vi.fn()
      const wrapper = mount(Md3Button, {
        props: { disabled: true },
        attrs: { onClick },
      })
      await wrapper.trigger('click')
      expect(onClick).not.toHaveBeenCalled()
    })

    it('disabled 为 false 时 button 不应该被禁用', () => {
      const wrapper = mount(Md3Button, {
        props: { disabled: false },
      })
      expect(wrapper.attributes('disabled')).toBeUndefined()
    })
  })

  describe('Loading State', () => {
    it('loading 应该应用 md3-btn--loading 类', () => {
      const wrapper = mount(Md3Button, {
        props: { loading: true },
        slots: { default: 'Loading...' },
      })
      expect(wrapper.classes()).toContain('md3-btn--loading')
    })

    it('loading 时应该显示 spinner', () => {
      const wrapper = mount(Md3Button, {
        props: { loading: true },
        slots: { default: 'Loading...' },
      })
      expect(wrapper.find('.md3-btn__spinner').exists()).toBe(true)
    })

    it('loading 时不应该渲染 Md3Icon', () => {
      const wrapper = mount(Md3Button, {
        props: { loading: true, icon: 'refresh' },
        slots: { default: 'Loading...' },
      })
      expect(wrapper.findComponent(Md3Icon).exists()).toBe(false)
    })

    it('loading 时 button 应该被禁用', () => {
      const wrapper = mount(Md3Button, {
        props: { loading: true },
      })
      expect(wrapper.attributes('disabled')).toBeDefined()
    })

    it('loading 时不应该触发 click 事件', async () => {
      const onClick = vi.fn()
      const wrapper = mount(Md3Button, {
        props: { loading: true },
        attrs: { onClick },
      })
      await wrapper.trigger('click')
      expect(onClick).not.toHaveBeenCalled()
    })

    it('loading 为 false 时不应该显示 spinner', () => {
      const wrapper = mount(Md3Button, {
        props: { loading: false },
        slots: { default: 'Normal' },
      })
      expect(wrapper.find('.md3-btn__spinner').exists()).toBe(false)
    })
  })

  describe('Block Prop', () => {
    it('block 应该应用 md3-btn--block 类', () => {
      const wrapper = mount(Md3Button, {
        props: { block: true },
        slots: { default: 'Full Width' },
      })
      expect(wrapper.classes()).toContain('md3-btn--block')
    })

    it('block 为 false 时不应该应用 block 类', () => {
      const wrapper = mount(Md3Button, {
        props: { block: false },
        slots: { default: 'Normal' },
      })
      expect(wrapper.classes()).not.toContain('md3-btn--block')
    })
  })

  describe('Tooltip Prop', () => {
    it('tooltip 应该设置 title 属性', () => {
      const wrapper = mount(Md3Button, {
        props: { tooltip: 'Click to refresh' },
        slots: { default: 'Refresh' },
      })
      expect(wrapper.attributes('title')).toBe('Click to refresh')
    })

    it('没有 tooltip 时 title 应该为 undefined', () => {
      const wrapper = mount(Md3Button, {
        slots: { default: 'No Tooltip' },
      })
      expect(wrapper.attributes('title')).toBeUndefined()
    })
  })

  describe('Click Event', () => {
    it('点击时应该触发 click 事件', async () => {
      const wrapper = mount(Md3Button, {
        slots: { default: 'Click Me' },
      })
      await wrapper.trigger('click')
      expect(wrapper.emitted('click')).toHaveLength(1)
    })

    it('click 事件应该传递 MouseEvent', async () => {
      const wrapper = mount(Md3Button, {
        slots: { default: 'Click Me' },
      })
      await wrapper.trigger('click')
      const event = wrapper.emitted('click')![0][0]
      expect(event).toBeDefined()
    })

    it('多次点击应该触发多次', async () => {
      const wrapper = mount(Md3Button, {
        slots: { default: 'Click Me' },
      })
      await wrapper.trigger('click')
      await wrapper.trigger('click')
      await wrapper.trigger('click')
      expect(wrapper.emitted('click')).toHaveLength(3)
    })
  })

  describe('Combined Props', () => {
    it('同时设置 loading 和 disabled 时应该被禁用', () => {
      const wrapper = mount(Md3Button, {
        props: { loading: true, disabled: true },
      })
      expect(wrapper.attributes('disabled')).toBeDefined()
      expect(wrapper.classes()).toContain('md3-btn--loading')
      expect(wrapper.classes()).toContain('md3-btn--disabled')
    })

    it('primary + loading + icon 应该显示 spinner 而非 icon', () => {
      const wrapper = mount(Md3Button, {
        props: { variant: 'primary', loading: true, icon: 'refresh' },
      })
      expect(wrapper.find('.md3-btn__spinner').exists()).toBe(true)
      expect(wrapper.findComponent(Md3Icon).exists()).toBe(false)
    })

    it('danger + disabled 应该同时应用对应类', () => {
      const wrapper = mount(Md3Button, {
        props: { variant: 'danger', disabled: true },
        slots: { default: 'Delete' },
      })
      expect(wrapper.classes()).toContain('md3-btn--danger')
      expect(wrapper.classes()).toContain('md3-btn--disabled')
    })
  })
})
