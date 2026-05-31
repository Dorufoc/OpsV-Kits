import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import Md3Alert from '@/components/md3/Md3Alert.vue'
import Md3Card from '@/components/md3/Md3Card.vue'
import Md3Checkbox from '@/components/md3/Md3Checkbox.vue'
import Md3Collapse from '@/components/md3/Md3Collapse.vue'
import { Md3Confirm } from '@/components/md3/Md3Confirm'
import Md3Dialog from '@/components/md3/Md3Dialog.vue'
import Md3Divider from '@/components/md3/Md3Divider.vue'
import Md3Empty from '@/components/md3/Md3Empty.vue'
import Md3Icon from '@/components/md3/Md3Icon.vue'
import Md3Input from '@/components/md3/Md3Input.vue'
import { Md3Message } from '@/components/md3/Md3Message'

vi.mock('@/components/md3/Md3Message', () => {
  let idCounter = 0
  const createMockMethod = () => vi.fn(() => `md3-msg-${++idCounter}`)
  return {
    Md3Message: {
      success: createMockMethod(),
      error: createMockMethod(),
      warning: createMockMethod(),
      info: createMockMethod(),
      remove: vi.fn(),
      closeAll: vi.fn(),
    },
  }
})
import Md3PageHeader from '@/components/md3/Md3PageHeader.vue'
import Md3Progress from '@/components/md3/Md3Progress.vue'
import Md3Radio from '@/components/md3/Md3Radio.vue'
import Md3Select from '@/components/md3/Md3Select.vue'
import Md3Switch from '@/components/md3/Md3Switch.vue'
import Md3Table from '@/components/md3/Md3Table.vue'
import Md3Tabs from '@/components/md3/Md3Tabs.vue'
import Md3Tag from '@/components/md3/Md3Tag.vue'
import Md3Tooltip from '@/components/md3/Md3Tooltip.vue'

vi.mock('@/utils/icon-map', () => ({
  getMdiIconPath: (name: string) => `M10 20v-6h4v6h5v-8h3L12 3 2 12h3v8z`,
}))

describe('Md3Alert', () => {
  it('应该渲染 alert 容器', () => {
    const wrapper = mount(Md3Alert)
    expect(wrapper.find('.md3-alert').exists()).toBe(true)
  })

  it('默认 type 为 info', () => {
    const wrapper = mount(Md3Alert)
    expect(wrapper.classes()).toContain('md3-alert--info')
  })

  it('应该应用 type 对应的类', () => {
    const wrapper = mount(Md3Alert, { props: { type: 'success' } })
    expect(wrapper.classes()).toContain('md3-alert--success')
  })

  it('应该渲染 title 和 message', () => {
    const wrapper = mount(Md3Alert, { props: { title: 'Title', message: 'Msg' } })
    expect(wrapper.text()).toContain('Title')
    expect(wrapper.text()).toContain('Msg')
  })

  it('closable 时应该渲染关闭按钮', () => {
    const wrapper = mount(Md3Alert, { props: { closable: true } })
    expect(wrapper.find('.md3-alert__close').exists()).toBe(true)
  })

  it('非 closable 时不应渲染关闭按钮', () => {
    const wrapper = mount(Md3Alert)
    expect(wrapper.find('.md3-alert__close').exists()).toBe(false)
  })

  it('点击关闭按钮应该触发 close 事件', async () => {
    const wrapper = mount(Md3Alert, { props: { closable: true } })
    await wrapper.find('.md3-alert__close').trigger('click')
    expect(wrapper.emitted('close')).toHaveLength(1)
  })

  it('title slot 应该渲染', () => {
    const wrapper = mount(Md3Alert, { slots: { title: 'Slot Title' } })
    expect(wrapper.text()).toContain('Slot Title')
  })

  it('message slot 应该渲染', () => {
    const wrapper = mount(Md3Alert, { slots: { message: 'Slot Message' } })
    expect(wrapper.text()).toContain('Slot Message')
  })

  it('应该渲染 SVG 图标', () => {
    const wrapper = mount(Md3Alert)
    expect(wrapper.find('.md3-alert__icon').exists()).toBe(true)
  })

  it('应该有 role="alert" 属性', () => {
    const wrapper = mount(Md3Alert)
    expect(wrapper.attributes('role')).toBe('alert')
  })
})

describe('Md3Card', () => {
  it('应该渲染 card 容器', () => {
    const wrapper = mount(Md3Card)
    expect(wrapper.find('.md3-card').exists()).toBe(true)
  })

  it('默认不应该有 hoverable 类', () => {
    const wrapper = mount(Md3Card)
    expect(wrapper.classes()).not.toContain('md3-card--hoverable')
  })

  it('hoverable 应该应用 hoverable 类', () => {
    const wrapper = mount(Md3Card, { props: { hoverable: true } })
    expect(wrapper.classes()).toContain('md3-card--hoverable')
  })

  it('默认 slot 应该渲染到 card-body', () => {
    const wrapper = mount(Md3Card, { slots: { default: 'Body Content' } })
    expect(wrapper.find('.md3-card-body').text()).toContain('Body Content')
  })

  it('header slot 应该渲染', () => {
    const wrapper = mount(Md3Card, { slots: { header: 'Header' } })
    expect(wrapper.find('.md3-card-header').exists()).toBe(true)
    expect(wrapper.text()).toContain('Header')
  })

  it('没有 header slot 时不应该渲染 card-header', () => {
    const wrapper = mount(Md3Card)
    expect(wrapper.find('.md3-card-header').exists()).toBe(false)
  })

  it('actions slot 应该渲染', () => {
    const wrapper = mount(Md3Card, { slots: { actions: 'Actions' } })
    expect(wrapper.find('.md3-card-actions').exists()).toBe(true)
    expect(wrapper.text()).toContain('Actions')
  })

  it('没有 actions slot 时不应该渲染 card-actions', () => {
    const wrapper = mount(Md3Card)
    expect(wrapper.find('.md3-card-actions').exists()).toBe(false)
  })
})

describe('Md3Checkbox', () => {
  it('应该渲染 checkbox 容器', () => {
    const wrapper = mount(Md3Checkbox)
    expect(wrapper.find('.md3-checkbox').exists()).toBe(true)
  })

  it('应该渲染隐藏的 input checkbox', () => {
    const wrapper = mount(Md3Checkbox)
    expect(wrapper.find('input[type="checkbox"]').exists()).toBe(true)
  })

  it('modelValue 为 true 时应该应用 checked 类', () => {
    const wrapper = mount(Md3Checkbox, { props: { modelValue: true } })
    expect(wrapper.classes()).toContain('md3-checkbox--checked')
  })

  it('modelValue 为 false 时不应应用 checked 类', () => {
    const wrapper = mount(Md3Checkbox, { props: { modelValue: false } })
    expect(wrapper.classes()).not.toContain('md3-checkbox--checked')
  })

  it('disabled 应该应用 disabled 类', () => {
    const wrapper = mount(Md3Checkbox, { props: { disabled: true } })
    expect(wrapper.classes()).toContain('md3-checkbox--disabled')
  })

  it('indeterminate 应该应用 indeterminate 类', () => {
    const wrapper = mount(Md3Checkbox, { props: { indeterminate: true } })
    expect(wrapper.classes()).toContain('md3-checkbox--indeterminate')
  })

  it('应该渲染 label 文本', () => {
    const wrapper = mount(Md3Checkbox, { props: { label: 'Check me' } })
    expect(wrapper.text()).toContain('Check me')
  })

  it('没有 label 时不应该渲染 label 元素', () => {
    const wrapper = mount(Md3Checkbox)
    expect(wrapper.find('.md3-checkbox-label').exists()).toBe(false)
  })

  it('change 事件应该触发 update:modelValue', async () => {
    const wrapper = mount(Md3Checkbox, { props: { modelValue: false } })
    await wrapper.find('input').setValue(true)
    expect(wrapper.emitted('update:modelValue')).toBeTruthy()
    expect(wrapper.emitted('update:modelValue')![0][0]).toBe(true)
  })

  it('change 事件应该触发 change', async () => {
    const wrapper = mount(Md3Checkbox, { props: { modelValue: false } })
    await wrapper.find('input').setValue(true)
    expect(wrapper.emitted('change')).toBeTruthy()
  })

  it('数组模式 modelValue 应该正确判断 checked', () => {
    const wrapper = mount(Md3Checkbox, { props: { modelValue: ['a', 'b'], value: 'a' } })
    expect(wrapper.classes()).toContain('md3-checkbox--checked')
  })

  it('数组模式 change 应该更新数组', async () => {
    const wrapper = mount(Md3Checkbox, { props: { modelValue: ['a'], value: 'b' } })
    await wrapper.find('input').setValue(true)
    const emitted = wrapper.emitted('update:modelValue')![0][0] as string[]
    expect(emitted).toContain('b')
    expect(emitted).toContain('a')
  })
})

describe('Md3Collapse', () => {
  it('应该渲染 collapse 容器', () => {
    const wrapper = mount(Md3Collapse)
    expect(wrapper.find('.md3-collapse').exists()).toBe(true)
  })

  it('应该渲染 header 按钮', () => {
    const wrapper = mount(Md3Collapse)
    expect(wrapper.find('.md3-collapse__header').exists()).toBe(true)
  })

  it('应该渲染 title 文本', () => {
    const wrapper = mount(Md3Collapse, { props: { title: 'Section' } })
    expect(wrapper.text()).toContain('Section')
  })

  it('title slot 应该渲染', () => {
    const wrapper = mount(Md3Collapse, { slots: { title: 'Slot Title' } })
    expect(wrapper.text()).toContain('Slot Title')
  })

  it('默认 slot 应该渲染', () => {
    const wrapper = mount(Md3Collapse, { slots: { default: 'Content' } })
    expect(wrapper.find('.md3-collapse__inner').text()).toContain('Content')
  })

  it('点击 header 应该触发 update:modelValue', async () => {
    const wrapper = mount(Md3Collapse, { props: { modelValue: false } })
    await wrapper.find('.md3-collapse__header').trigger('click')
    expect(wrapper.emitted('update:modelValue')).toBeTruthy()
    expect(wrapper.emitted('update:modelValue')![0][0]).toBe(true)
  })

  it('modelValue 为 true 时应该应用 open 类到 icon', () => {
    const wrapper = mount(Md3Collapse, { props: { modelValue: true } })
    expect(wrapper.find('.md3-collapse__icon').classes()).toContain('md3-collapse__icon--open')
  })

  it('aria-expanded 应该跟随 modelValue', () => {
    const wrapper = mount(Md3Collapse, { props: { modelValue: true } })
    expect(wrapper.find('.md3-collapse__header').attributes('aria-expanded')).toBe('true')
  })
})

describe('Md3Confirm', () => {
  it('应该有 show 方法', () => {
    expect(Md3Confirm.show).toBeDefined()
    expect(typeof Md3Confirm.show).toBe('function')
  })

  it('show 接受字符串参数应该返回 Promise', () => {
    const result = Md3Confirm.show('Are you sure?')
    expect(result).toBeInstanceOf(Promise)
  })

  it('show 接受对象参数应该返回 Promise', () => {
    const result = Md3Confirm.show({ message: 'Are you sure?', type: 'danger' })
    expect(result).toBeInstanceOf(Promise)
  })
})

describe('Md3Dialog', () => {
  function createDialogWrapper(props = {}, slots = {}) {
    return mount(Md3Dialog, {
      props: { visible: true, ...props },
      slots,
      global: {
        stubs: {
          Teleport: {
            template: '<div><slot /></div>',
          },
        },
      },
    })
  }

  it('visible 为 false 时不应渲染 dialog-mask', () => {
    const wrapper = mount(Md3Dialog, {
      props: { visible: false },
      global: { stubs: { Teleport: { template: '<div><slot /></div>' } } },
    })
    expect(wrapper.find('.md3-dialog-mask').exists()).toBe(false)
  })

  it('visible 为 true 时应该渲染 dialog', () => {
    const wrapper = createDialogWrapper()
    expect(wrapper.find('.md3-dialog').exists()).toBe(true)
  })

  it('应该渲染 title', () => {
    const wrapper = createDialogWrapper({ title: 'Dialog Title' })
    expect(wrapper.text()).toContain('Dialog Title')
  })

  it('closable 为 true 时应该渲染关闭按钮', () => {
    const wrapper = createDialogWrapper({ title: 'Test', closable: true })
    expect(wrapper.find('.md3-dialog-close').exists()).toBe(true)
  })

  it('closable 为 false 时不应渲染关闭按钮', () => {
    const wrapper = createDialogWrapper({ title: 'Test', closable: false })
    expect(wrapper.find('.md3-dialog-close').exists()).toBe(false)
  })

  it('点击关闭按钮应该触发 close 和 update:visible', async () => {
    const wrapper = createDialogWrapper({ title: 'Test' })
    await wrapper.find('.md3-dialog-close').trigger('click')
    expect(wrapper.emitted('close')).toBeTruthy()
    expect(wrapper.emitted('update:visible')).toBeTruthy()
    expect(wrapper.emitted('update:visible')![0][0]).toBe(false)
  })

  it('fullscreen 应该应用 fullscreen 类', () => {
    const wrapper = createDialogWrapper({ fullscreen: true })
    expect(wrapper.find('.md3-dialog').classes()).toContain('md3-dialog--fullscreen')
  })

  it('默认 slot 应该渲染到 dialog-body', () => {
    const wrapper = createDialogWrapper({}, { default: 'Body Content' })
    expect(wrapper.find('.md3-dialog-body').text()).toContain('Body Content')
  })

  it('footer slot 应该渲染', () => {
    const wrapper = createDialogWrapper({}, { footer: 'Footer' })
    expect(wrapper.find('.md3-dialog-footer').exists()).toBe(true)
  })

  it('没有 footer slot 时不应该渲染 footer', () => {
    const wrapper = createDialogWrapper()
    expect(wrapper.find('.md3-dialog-footer').exists()).toBe(false)
  })

  it('width prop 应该影响 dialog 宽度', () => {
    const wrapper = createDialogWrapper({ width: '600px' })
    const style = wrapper.find('.md3-dialog').attributes('style')
    expect(style).toContain('600px')
  })
})

describe('Md3Divider', () => {
  it('应该渲染 divider', () => {
    const wrapper = mount(Md3Divider)
    expect(wrapper.find('.md3-divider').exists()).toBe(true)
  })

  it('默认 orientation 为 horizontal', () => {
    const wrapper = mount(Md3Divider)
    expect(wrapper.classes()).toContain('md3-divider--horizontal')
  })

  it('vertical orientation 应该应用 vertical 类', () => {
    const wrapper = mount(Md3Divider, { props: { orientation: 'vertical' } })
    expect(wrapper.classes()).toContain('md3-divider--vertical')
  })

  it('label prop 应该渲染文本', () => {
    const wrapper = mount(Md3Divider, { props: { label: 'Section' } })
    expect(wrapper.text()).toContain('Section')
  })

  it('default slot 应该渲染', () => {
    const wrapper = mount(Md3Divider, { slots: { default: 'Slot Label' } })
    expect(wrapper.text()).toContain('Slot Label')
  })

  it('horizontal 时应该渲染为 hr 元素', () => {
    const wrapper = mount(Md3Divider, { props: { orientation: 'horizontal' } })
    expect(wrapper.element.tagName).toBe('HR')
  })

  it('vertical 时应该渲染为 div 元素', () => {
    const wrapper = mount(Md3Divider, { props: { orientation: 'vertical' } })
    expect(wrapper.element.tagName).toBe('DIV')
  })
})

describe('Md3Empty', () => {
  it('应该渲染 empty 容器', () => {
    const wrapper = mount(Md3Empty)
    expect(wrapper.find('.md3-empty').exists()).toBe(true)
  })

  it('默认 title 为 "暂无数据"', () => {
    const wrapper = mount(Md3Empty)
    expect(wrapper.text()).toContain('暂无数据')
  })

  it('自定义 title 应该渲染', () => {
    const wrapper = mount(Md3Empty, { props: { title: 'No Data' } })
    expect(wrapper.text()).toContain('No Data')
  })

  it('description 应该渲染', () => {
    const wrapper = mount(Md3Empty, { props: { description: 'Try again' } })
    expect(wrapper.text()).toContain('Try again')
  })

  it('title slot 应该渲染', () => {
    const wrapper = mount(Md3Empty, { slots: { title: 'Custom Title' } })
    expect(wrapper.text()).toContain('Custom Title')
  })

  it('description slot 应该渲染', () => {
    const wrapper = mount(Md3Empty, { slots: { description: 'Custom Desc' } })
    expect(wrapper.text()).toContain('Custom Desc')
  })

  it('action slot 应该渲染', () => {
    const wrapper = mount(Md3Empty, { slots: { action: '<button>Retry</button>' } })
    expect(wrapper.find('.md3-empty__action').exists()).toBe(true)
  })

  it('应该渲染默认 SVG 图标', () => {
    const wrapper = mount(Md3Empty)
    expect(wrapper.find('.md3-empty__image svg').exists()).toBe(true)
  })

  it('image slot 应该覆盖默认图标', () => {
    const wrapper = mount(Md3Empty, { slots: { image: '<img src="empty.png" />' } })
    expect(wrapper.find('.md3-empty__image img').exists()).toBe(true)
  })
})

describe('Md3Icon', () => {
  it('应该渲染 SVG 元素', () => {
    const wrapper = mount(Md3Icon, { props: { name: 'refresh' } })
    expect(wrapper.find('svg').exists()).toBe(true)
  })

  it('应该应用 md3-icon 类', () => {
    const wrapper = mount(Md3Icon, { props: { name: 'refresh' } })
    expect(wrapper.classes()).toContain('md3-icon')
  })

  it('默认 size 为 20px', () => {
    const wrapper = mount(Md3Icon, { props: { name: 'refresh' } })
    const style = wrapper.find('svg').attributes('style')
    expect(style).toContain('20px')
  })

  it('自定义 size 应该应用', () => {
    const wrapper = mount(Md3Icon, { props: { name: 'refresh', size: 32 } })
    const style = wrapper.find('svg').attributes('style')
    expect(style).toContain('32px')
  })

  it('size 为字符串时应该直接使用', () => {
    const wrapper = mount(Md3Icon, { props: { name: 'refresh', size: '2em' } })
    const style = wrapper.find('svg').attributes('style')
    expect(style).toContain('2em')
  })

  it('color prop 应该设置 SVG 颜色', () => {
    const wrapper = mount(Md3Icon, { props: { name: 'refresh', color: 'red' } })
    const style = wrapper.find('svg').attributes('style')
    expect(style).toContain('red')
  })

  it('没有 color 时应该使用 currentColor', () => {
    const wrapper = mount(Md3Icon, { props: { name: 'refresh' } })
    const style = wrapper.find('svg').attributes('style')
    expect(style!.toLowerCase()).toContain('currentcolor')
  })

  it('viewBox 应该为 "0 0 24 24"', () => {
    const wrapper = mount(Md3Icon, { props: { name: 'refresh' } })
    expect(wrapper.find('svg').attributes('viewBox')).toBe('0 0 24 24')
  })
})

describe('Md3Input', () => {
  it('应该渲染 input 元素', () => {
    const wrapper = mount(Md3Input)
    expect(wrapper.find('input').exists()).toBe(true)
  })

  it('应该渲染 wrapper', () => {
    const wrapper = mount(Md3Input)
    expect(wrapper.find('.md3-input-wrapper').exists()).toBe(true)
  })

  it('默认 variant 为 outlined', () => {
    const wrapper = mount(Md3Input)
    expect(wrapper.classes()).toContain('md3-input--outlined')
  })

  it('filled variant 应该应用 filled 类', () => {
    const wrapper = mount(Md3Input, { props: { variant: 'filled' } })
    expect(wrapper.classes()).toContain('md3-input--filled')
  })

  it('disabled 应该应用 disabled 类', () => {
    const wrapper = mount(Md3Input, { props: { disabled: true } })
    expect(wrapper.classes()).toContain('md3-input--disabled')
  })

  it('readonly 应该应用 readonly 类', () => {
    const wrapper = mount(Md3Input, { props: { readonly: true } })
    expect(wrapper.classes()).toContain('md3-input--readonly')
  })

  it('error 应该应用 error 类', () => {
    const wrapper = mount(Md3Input, { props: { error: 'Required' } })
    expect(wrapper.classes()).toContain('md3-input--error')
  })

  it('error 文本应该渲染', () => {
    const wrapper = mount(Md3Input, { props: { error: 'Required' } })
    expect(wrapper.find('.md3-input-error').text()).toContain('Required')
  })

  it('label 应该渲染', () => {
    const wrapper = mount(Md3Input, { props: { label: 'Name' } })
    expect(wrapper.text()).toContain('Name')
  })

  it('input 事件应该触发 update:modelValue', async () => {
    const wrapper = mount(Md3Input)
    await wrapper.find('input').setValue('hello')
    expect(wrapper.emitted('update:modelValue')).toBeTruthy()
    expect(wrapper.emitted('update:modelValue')![0][0]).toBe('hello')
  })

  it('prefix slot 应该渲染', () => {
    const wrapper = mount(Md3Input, { slots: { prefix: '$' } })
    expect(wrapper.find('.md3-input-prefix').exists()).toBe(true)
    expect(wrapper.text()).toContain('$')
  })

  it('suffix slot 应该渲染', () => {
    const wrapper = mount(Md3Input, { slots: { suffix: '.com' } })
    expect(wrapper.find('.md3-input-suffix').exists()).toBe(true)
    expect(wrapper.text()).toContain('.com')
  })

  it('type 为 number 时应该转换值', async () => {
    const wrapper = mount(Md3Input, { props: { type: 'number' } })
    await wrapper.find('input').setValue('42')
    expect(wrapper.emitted('update:modelValue')![0][0]).toBe(42)
  })

  it('placeholder 应该设置到 input', () => {
    const wrapper = mount(Md3Input, { props: { placeholder: 'Enter text' } })
    expect(wrapper.find('input').attributes('placeholder')).toBe('Enter text')
  })
})

describe('Md3Message', () => {
  it('应该有 success 方法', () => {
    expect(typeof Md3Message.success).toBe('function')
  })

  it('应该有 error 方法', () => {
    expect(typeof Md3Message.error).toBe('function')
  })

  it('应该有 warning 方法', () => {
    expect(typeof Md3Message.warning).toBe('function')
  })

  it('应该有 info 方法', () => {
    expect(typeof Md3Message.info).toBe('function')
  })

  it('应该有 remove 方法', () => {
    expect(typeof Md3Message.remove).toBe('function')
  })

  it('应该有 closeAll 方法', () => {
    expect(typeof Md3Message.closeAll).toBe('function')
  })

  it('success 应该返回消息 ID', () => {
    const id = Md3Message.success('Test')
    expect(typeof id).toBe('string')
    expect(id).toBeTruthy()
  })

  it('error 应该返回消息 ID', () => {
    const id = Md3Message.error('Error')
    expect(typeof id).toBe('string')
  })

  it('closeAll 应该可以正常调用', () => {
    expect(() => Md3Message.closeAll()).not.toThrow()
  })

  it('remove 应该可以正常调用', () => {
    const id = Md3Message.info('Test')
    expect(() => Md3Message.remove(id)).not.toThrow()
  })
})

describe('Md3PageHeader', () => {
  it('应该渲染 page-header 容器', () => {
    const wrapper = mount(Md3PageHeader)
    expect(wrapper.find('.md3-page-header').exists()).toBe(true)
  })

  it('title prop 应该渲染', () => {
    const wrapper = mount(Md3PageHeader, { props: { title: 'Page Title' } })
    expect(wrapper.text()).toContain('Page Title')
  })

  it('subtitle prop 应该渲染', () => {
    const wrapper = mount(Md3PageHeader, { props: { subtitle: 'Subtitle' } })
    expect(wrapper.text()).toContain('Subtitle')
  })

  it('title slot 应该渲染', () => {
    const wrapper = mount(Md3PageHeader, { slots: { title: 'Slot Title' } })
    expect(wrapper.text()).toContain('Slot Title')
  })

  it('subtitle slot 应该渲染', () => {
    const wrapper = mount(Md3PageHeader, { slots: { subtitle: 'Slot Subtitle' } })
    expect(wrapper.text()).toContain('Slot Subtitle')
  })

  it('actions slot 应该渲染', () => {
    const wrapper = mount(Md3PageHeader, { slots: { actions: '<button>Action</button>' } })
    expect(wrapper.find('.md3-page-header__actions').exists()).toBe(true)
  })

  it('showBack 为 true 时应该渲染返回按钮', () => {
    const wrapper = mount(Md3PageHeader, { props: { showBack: true } })
    expect(wrapper.find('.md3-page-header__back').exists()).toBe(true)
  })

  it('showBack 为 false 时不应渲染返回按钮', () => {
    const wrapper = mount(Md3PageHeader)
    expect(wrapper.find('.md3-page-header__back').exists()).toBe(false)
  })

  it('点击返回按钮应该触发 back 事件', async () => {
    const wrapper = mount(Md3PageHeader, { props: { showBack: true } })
    await wrapper.find('.md3-page-header__back').trigger('click')
    expect(wrapper.emitted('back')).toHaveLength(1)
  })

  it('没有 subtitle 时不应该渲染 subtitle 元素', () => {
    const wrapper = mount(Md3PageHeader)
    expect(wrapper.find('.md3-page-header__subtitle').exists()).toBe(false)
  })
})

describe('Md3Progress', () => {
  it('应该渲染 progress 容器', () => {
    const wrapper = mount(Md3Progress)
    expect(wrapper.find('.md3-progress').exists()).toBe(true)
  })

  it('默认 type 为 line', () => {
    const wrapper = mount(Md3Progress)
    expect(wrapper.classes()).toContain('md3-progress--line')
  })

  it('line 类型应该渲染 track 和 bar', () => {
    const wrapper = mount(Md3Progress)
    expect(wrapper.find('.md3-progress__track').exists()).toBe(true)
    expect(wrapper.find('.md3-progress__bar').exists()).toBe(true)
  })

  it('showPercentage 应该渲染百分比文本', () => {
    const wrapper = mount(Md3Progress, { props: { showPercentage: true, percentage: 50 } })
    expect(wrapper.text()).toContain('50%')
  })

  it('percentage 应该限制在 0-100 之间', () => {
    const wrapper = mount(Md3Progress, { props: { percentage: 150 } })
    const style = wrapper.find('.md3-progress__bar').attributes('style')
    expect(style).toContain('100%')
  })

  it('circle 类型应该渲染 SVG', () => {
    const wrapper = mount(Md3Progress, { props: { type: 'circle' } })
    expect(wrapper.classes()).toContain('md3-progress--circle')
    expect(wrapper.find('.md3-progress__circle').exists()).toBe(true)
  })

  it('striped 应该应用 striped 类', () => {
    const wrapper = mount(Md3Progress, { props: { striped: true } })
    expect(wrapper.classes()).toContain('md3-progress--striped')
  })

  it('animated 应该应用 animated 类到 bar', () => {
    const wrapper = mount(Md3Progress, { props: { animated: true } })
    expect(wrapper.find('.md3-progress__bar').classes()).toContain('md3-progress__bar--animated')
  })

  it('color prop 应该设置 bar 颜色', () => {
    const wrapper = mount(Md3Progress, { props: { color: 'red' } })
    const style = wrapper.find('.md3-progress__bar').attributes('style')
    expect(style).toContain('red')
  })

  it('bar 应该有 role="progressbar"', () => {
    const wrapper = mount(Md3Progress)
    expect(wrapper.find('.md3-progress__bar').attributes('role')).toBe('progressbar')
  })
})

describe('Md3Radio', () => {
  it('应该渲染 radio 容器', () => {
    const wrapper = mount(Md3Radio)
    expect(wrapper.find('.md3-radio').exists()).toBe(true)
  })

  it('应该渲染隐藏的 input radio', () => {
    const wrapper = mount(Md3Radio)
    expect(wrapper.find('input[type="radio"]').exists()).toBe(true)
  })

  it('modelValue 等于 value 时应该应用 checked 类', () => {
    const wrapper = mount(Md3Radio, { props: { modelValue: 'a', value: 'a' } })
    expect(wrapper.classes()).toContain('md3-radio--checked')
  })

  it('modelValue 不等于 value 时不应应用 checked 类', () => {
    const wrapper = mount(Md3Radio, { props: { modelValue: 'a', value: 'b' } })
    expect(wrapper.classes()).not.toContain('md3-radio--checked')
  })

  it('disabled 应该应用 disabled 类', () => {
    const wrapper = mount(Md3Radio, { props: { disabled: true } })
    expect(wrapper.classes()).toContain('md3-radio--disabled')
  })

  it('label 应该渲染', () => {
    const wrapper = mount(Md3Radio, { props: { label: 'Option A' } })
    expect(wrapper.text()).toContain('Option A')
  })

  it('没有 label 时不应该渲染 label 元素', () => {
    const wrapper = mount(Md3Radio)
    expect(wrapper.find('.md3-radio-label').exists()).toBe(false)
  })

  it('change 事件应该触发 update:modelValue', async () => {
    const wrapper = mount(Md3Radio, { props: { modelValue: '', value: 'a' } })
    await wrapper.find('input').trigger('change')
    expect(wrapper.emitted('update:modelValue')).toBeTruthy()
    expect(wrapper.emitted('update:modelValue')![0][0]).toBe('a')
  })

  it('change 事件应该触发 change', async () => {
    const wrapper = mount(Md3Radio, { props: { modelValue: '', value: 'a' } })
    await wrapper.find('input').trigger('change')
    expect(wrapper.emitted('change')).toBeTruthy()
    expect(wrapper.emitted('change')![0][0]).toBe('a')
  })
})

describe('Md3Select', () => {
  const options = [
    { label: 'Option A', value: 'a' },
    { label: 'Option B', value: 'b' },
  ]

  it('应该渲染 select wrapper', () => {
    const wrapper = mount(Md3Select)
    expect(wrapper.find('.md3-select-wrapper').exists()).toBe(true)
  })

  it('应该渲染 trigger', () => {
    const wrapper = mount(Md3Select)
    expect(wrapper.find('.md3-select-trigger').exists()).toBe(true)
  })

  it('disabled 应该应用 disabled 类', () => {
    const wrapper = mount(Md3Select, { props: { disabled: true } })
    expect(wrapper.find('.md3-select-wrapper').classes()).toContain('md3-select--disabled')
  })

  it('label 应该渲染', () => {
    const wrapper = mount(Md3Select, { props: { label: 'Choose' } })
    expect(wrapper.text()).toContain('Choose')
  })

  it('placeholder 应该渲染', () => {
    const wrapper = mount(Md3Select, { props: { placeholder: 'Select one' } })
    expect(wrapper.text()).toContain('Select one')
  })

  it('error 应该渲染错误信息', () => {
    const wrapper = mount(Md3Select, { props: { error: 'Required' } })
    expect(wrapper.find('.md3-select-error').text()).toContain('Required')
  })

  it('默认 variant 为 outlined', () => {
    const wrapper = mount(Md3Select)
    expect(wrapper.find('.md3-select-trigger').classes()).toContain('md3-select--outlined')
  })

  it('filled variant 应该应用 filled 类', () => {
    const wrapper = mount(Md3Select, { props: { variant: 'filled' } })
    expect(wrapper.find('.md3-select-trigger').classes()).toContain('md3-select--filled')
  })

  it('有 modelValue 时应该显示选中项', () => {
    const wrapper = mount(Md3Select, { props: { modelValue: 'a', options } })
    expect(wrapper.text()).toContain('Option A')
  })

  it('clearable 且有选中值时应该渲染清除按钮', () => {
    const wrapper = mount(Md3Select, { props: { modelValue: 'a', options, clearable: true } })
    expect(wrapper.find('.md3-select-clear').exists()).toBe(true)
  })

  it('点击清除按钮应该触发 update:modelValue', async () => {
    const wrapper = mount(Md3Select, { props: { modelValue: 'a', options, clearable: true } })
    await wrapper.find('.md3-select-clear').trigger('click')
    expect(wrapper.emitted('update:modelValue')).toBeTruthy()
  })

  it('点击 trigger 应该打开下拉', async () => {
    const wrapper = mount(Md3Select, { props: { options } })
    await wrapper.find('.md3-select-trigger').trigger('click')
    expect(wrapper.find('.md3-select-wrapper').classes()).toContain('md3-select--open')
  })
})

describe('Md3Switch', () => {
  it('应该渲染 switch 按钮', () => {
    const wrapper = mount(Md3Switch)
    expect(wrapper.find('.md3-switch').exists()).toBe(true)
  })

  it('应该有 role="switch"', () => {
    const wrapper = mount(Md3Switch)
    expect(wrapper.attributes('role')).toBe('switch')
  })

  it('modelValue 为 true 时应该应用 checked 类', () => {
    const wrapper = mount(Md3Switch, { props: { modelValue: true } })
    expect(wrapper.classes()).toContain('md3-switch--checked')
  })

  it('modelValue 为 false 时不应应用 checked 类', () => {
    const wrapper = mount(Md3Switch, { props: { modelValue: false } })
    expect(wrapper.classes()).not.toContain('md3-switch--checked')
  })

  it('disabled 应该应用 disabled 类', () => {
    const wrapper = mount(Md3Switch, { props: { disabled: true } })
    expect(wrapper.classes()).toContain('md3-switch--disabled')
  })

  it('点击应该触发 update:modelValue', async () => {
    const wrapper = mount(Md3Switch, { props: { modelValue: false } })
    await wrapper.trigger('click')
    expect(wrapper.emitted('update:modelValue')).toBeTruthy()
    expect(wrapper.emitted('update:modelValue')![0][0]).toBe(true)
  })

  it('disabled 时点击不应触发 update:modelValue', async () => {
    const wrapper = mount(Md3Switch, { props: { disabled: true, modelValue: false } })
    await wrapper.trigger('click')
    expect(wrapper.emitted('update:modelValue')).toBeFalsy()
  })

  it('aria-checked 应该跟随 modelValue', () => {
    const wrapper = mount(Md3Switch, { props: { modelValue: true } })
    expect(wrapper.attributes('aria-checked')).toBe('true')
  })

  it('onText 和 offText 应该渲染', () => {
    const wrapper = mount(Md3Switch, { props: { onText: 'ON', offText: 'OFF' } })
    expect(wrapper.find('.md3-switch-track-text').exists()).toBe(true)
  })

  it('offText 在 modelValue 为 false 时应该显示', () => {
    const wrapper = mount(Md3Switch, { props: { modelValue: false, offText: 'OFF' } })
    expect(wrapper.text()).toContain('OFF')
  })

  it('onText 在 modelValue 为 true 时应该显示', () => {
    const wrapper = mount(Md3Switch, { props: { modelValue: true, onText: 'ON' } })
    expect(wrapper.text()).toContain('ON')
  })

  it('应该渲染 track 和 thumb', () => {
    const wrapper = mount(Md3Switch)
    expect(wrapper.find('.md3-switch-track').exists()).toBe(true)
    expect(wrapper.find('.md3-switch-thumb').exists()).toBe(true)
  })
})

describe('Md3Table', () => {
  const columns = [
    { prop: 'name', label: 'Name' },
    { prop: 'age', label: 'Age' },
  ]
  const data = [
    { name: 'Alice', age: 25 },
    { name: 'Bob', age: 30 },
  ]

  it('应该渲染 table', () => {
    const wrapper = mount(Md3Table, { props: { columns, data } })
    expect(wrapper.find('table').exists()).toBe(true)
  })

  it('应该渲染表头', () => {
    const wrapper = mount(Md3Table, { props: { columns, data } })
    expect(wrapper.find('thead').exists()).toBe(true)
    const headers = wrapper.findAll('th')
    expect(headers.length).toBe(2)
    expect(headers[0].text()).toContain('Name')
    expect(headers[1].text()).toContain('Age')
  })

  it('应该渲染数据行', () => {
    const wrapper = mount(Md3Table, { props: { columns, data } })
    const rows = wrapper.findAll('tbody tr')
    expect(rows.length).toBe(2)
  })

  it('应该渲染单元格内容', () => {
    const wrapper = mount(Md3Table, { props: { columns, data } })
    expect(wrapper.text()).toContain('Alice')
    expect(wrapper.text()).toContain('Bob')
  })

  it('空数据时应该显示 emptyText', () => {
    const wrapper = mount(Md3Table, { props: { columns, data: [] } })
    expect(wrapper.find('.md3-table-empty').exists()).toBe(true)
    expect(wrapper.text()).toContain('No data available')
  })

  it('自定义 emptyText 应该渲染', () => {
    const wrapper = mount(Md3Table, { props: { columns, data: [], emptyText: 'No items' } })
    expect(wrapper.text()).toContain('No items')
  })

  it('stripe 应该应用 stripe 类', () => {
    const wrapper = mount(Md3Table, { props: { columns, data, stripe: true } })
    expect(wrapper.find('table').classes()).toContain('md3-table--stripe')
  })

  it('border 应该应用 border 类', () => {
    const wrapper = mount(Md3Table, { props: { columns, data, border: true } })
    expect(wrapper.find('.md3-table-container').classes()).toContain('md3-table--border')
  })

  it('selection 应该渲染复选框列', () => {
    const wrapper = mount(Md3Table, { props: { columns, data, selection: true } })
    expect(wrapper.find('.md3-table-cell--selection').exists()).toBe(true)
    expect(wrapper.find('.md3-table-select-all').exists()).toBe(true)
  })

  it('点击行复选框应该触发 selection-change', async () => {
    const wrapper = mount(Md3Table, { props: { columns, data, selection: true } })
    const checkbox = wrapper.findAll('.md3-table-select')[0]
    await checkbox.trigger('change')
    expect(wrapper.emitted('selection-change')).toBeTruthy()
  })

  it('列 slot 应该渲染自定义内容', () => {
    const wrapper = mount(Md3Table, {
      props: { columns, data },
      slots: { name: '<span class="custom-cell">Custom</span>' },
    })
    expect(wrapper.find('.custom-cell').exists()).toBe(true)
  })
})

describe('Md3Tabs', () => {
  const tabs = [
    { label: 'Tab 1', value: 'tab1' },
    { label: 'Tab 2', value: 'tab2' },
    { label: 'Tab 3', value: 'tab3' },
  ]

  it('应该渲染 tabs 容器', () => {
    const wrapper = mount(Md3Tabs, { props: { tabs } })
    expect(wrapper.find('.md3-tabs').exists()).toBe(true)
  })

  it('应该渲染 tab 按钮', () => {
    const wrapper = mount(Md3Tabs, { props: { tabs } })
    const tabButtons = wrapper.findAll('.md3-tabs__tab')
    expect(tabButtons.length).toBe(3)
  })

  it('应该渲染 tab label', () => {
    const wrapper = mount(Md3Tabs, { props: { tabs } })
    expect(wrapper.text()).toContain('Tab 1')
    expect(wrapper.text()).toContain('Tab 2')
    expect(wrapper.text()).toContain('Tab 3')
  })

  it('当前 modelValue 对应的 tab 应该有 active 类', () => {
    const wrapper = mount(Md3Tabs, { props: { tabs, modelValue: 'tab2' } })
    const tabButtons = wrapper.findAll('.md3-tabs__tab')
    expect(tabButtons[1].classes()).toContain('md3-tabs__tab--active')
  })

  it('点击 tab 应该触发 update:modelValue', async () => {
    const wrapper = mount(Md3Tabs, { props: { tabs, modelValue: 'tab1' } })
    const tabButtons = wrapper.findAll('.md3-tabs__tab')
    await tabButtons[1].trigger('click')
    expect(wrapper.emitted('update:modelValue')).toBeTruthy()
    expect(wrapper.emitted('update:modelValue')![0][0]).toBe('tab2')
  })

  it('应该渲染 indicator', () => {
    const wrapper = mount(Md3Tabs, { props: { tabs } })
    expect(wrapper.find('.md3-tabs__indicator').exists()).toBe(true)
  })

  it('hideIndicator 应该隐藏 indicator', () => {
    const wrapper = mount(Md3Tabs, { props: { tabs, hideIndicator: true } })
    expect(wrapper.find('.md3-tabs__indicator').exists()).toBe(false)
  })

  it('default slot 应该渲染到 content 区域', () => {
    const wrapper = mount(Md3Tabs, { props: { tabs }, slots: { default: 'Tab Content' } })
    expect(wrapper.find('.md3-tabs__content').text()).toContain('Tab Content')
  })

  it('tab 应该有 role="tab"', () => {
    const wrapper = mount(Md3Tabs, { props: { tabs } })
    expect(wrapper.find('.md3-tabs__tab').attributes('role')).toBe('tab')
  })

  it('tab 应该有 aria-selected', () => {
    const wrapper = mount(Md3Tabs, { props: { tabs, modelValue: 'tab1' } })
    const tabButtons = wrapper.findAll('.md3-tabs__tab')
    expect(tabButtons[0].attributes('aria-selected')).toBe('true')
    expect(tabButtons[1].attributes('aria-selected')).toBe('false')
  })
})

describe('Md3Tag', () => {
  it('应该渲染 tag', () => {
    const wrapper = mount(Md3Tag, { slots: { default: 'Tag' } })
    expect(wrapper.find('.md3-tag').exists()).toBe(true)
    expect(wrapper.text()).toContain('Tag')
  })

  it('默认 type 为 info', () => {
    const wrapper = mount(Md3Tag, { slots: { default: 'Tag' } })
    expect(wrapper.classes()).toContain('md3-tag--info')
  })

  it('type prop 应该应用对应类', () => {
    const wrapper = mount(Md3Tag, { props: { type: 'success' }, slots: { default: 'Tag' } })
    expect(wrapper.classes()).toContain('md3-tag--success')
  })

  it('默认 size 为 md', () => {
    const wrapper = mount(Md3Tag, { slots: { default: 'Tag' } })
    expect(wrapper.classes()).toContain('md3-tag--md')
  })

  it('size prop 应该应用对应类', () => {
    const wrapper = mount(Md3Tag, { props: { size: 'sm' }, slots: { default: 'Tag' } })
    expect(wrapper.classes()).toContain('md3-tag--sm')
  })

  it('closable 应该渲染关闭按钮', () => {
    const wrapper = mount(Md3Tag, { props: { closable: true }, slots: { default: 'Tag' } })
    expect(wrapper.find('.md3-tag-close').exists()).toBe(true)
  })

  it('非 closable 时不应渲染关闭按钮', () => {
    const wrapper = mount(Md3Tag, { slots: { default: 'Tag' } })
    expect(wrapper.find('.md3-tag-close').exists()).toBe(false)
  })

  it('点击关闭按钮应该触发 close 事件', async () => {
    const wrapper = mount(Md3Tag, { props: { closable: true }, slots: { default: 'Tag' } })
    await wrapper.find('.md3-tag-close').trigger('click')
    expect(wrapper.emitted('close')).toHaveLength(1)
  })

  it('所有 type 应该应用对应类', () => {
    const types = ['primary', 'success', 'warning', 'danger', 'info'] as const
    for (const type of types) {
      const wrapper = mount(Md3Tag, { props: { type }, slots: { default: 'Tag' } })
      expect(wrapper.classes()).toContain(`md3-tag--${type}`)
    }
  })
})

describe('Md3Tooltip', () => {
  it('应该渲染 tooltip 容器', () => {
    const wrapper = mount(Md3Tooltip, { slots: { trigger: 'Hover me', default: 'Tip text' } })
    expect(wrapper.find('.md3-tooltip').exists()).toBe(true)
  })

  it('应该渲染 trigger slot', () => {
    const wrapper = mount(Md3Tooltip, { slots: { trigger: 'Hover me' } })
    expect(wrapper.find('.md3-tooltip__trigger').text()).toContain('Hover me')
  })

  it('默认 placement 为 top', () => {
    const wrapper = mount(Md3Tooltip, { slots: { trigger: 'Hover', default: 'Tip' } })
    expect(wrapper.classes()).toContain('md3-tooltip--top')
  })

  it('placement prop 应该应用对应类', () => {
    const wrapper = mount(Md3Tooltip, { props: { placement: 'bottom' }, slots: { trigger: 'Hover', default: 'Tip' } })
    expect(wrapper.classes()).toContain('md3-tooltip--bottom')
  })

  it('hover trigger 鼠标进入时应该显示 tooltip', async () => {
    const wrapper = mount(Md3Tooltip, { slots: { trigger: 'Hover', default: 'Tip text' } })
    await wrapper.trigger('mouseenter')
    expect(wrapper.find('.md3-tooltip__content').exists()).toBe(true)
    expect(wrapper.text()).toContain('Tip text')
  })

  it('hover trigger 鼠标离开时应该隐藏 tooltip', async () => {
    const wrapper = mount(Md3Tooltip, { slots: { trigger: 'Hover', default: 'Tip' } })
    await wrapper.trigger('mouseenter')
    expect(wrapper.find('.md3-tooltip__content').exists()).toBe(true)
    await wrapper.trigger('mouseleave')
    expect(wrapper.find('.md3-tooltip__content').exists()).toBe(false)
  })

  it('click trigger 点击时应该切换 tooltip', async () => {
    const wrapper = mount(Md3Tooltip, { props: { trigger: 'click' }, slots: { trigger: 'Click', default: 'Tip' } })
    await wrapper.trigger('click')
    expect(wrapper.find('.md3-tooltip__content').exists()).toBe(true)
    await wrapper.trigger('click')
    expect(wrapper.find('.md3-tooltip__content').exists()).toBe(false)
  })

  it('所有 placement 应该应用对应类', () => {
    const placements = ['top', 'bottom', 'left', 'right'] as const
    for (const placement of placements) {
      const wrapper = mount(Md3Tooltip, { props: { placement }, slots: { trigger: 'H', default: 'T' } })
      expect(wrapper.classes()).toContain(`md3-tooltip--${placement}`)
    }
  })

  it('tooltip content 应该有 role="tooltip"', async () => {
    const wrapper = mount(Md3Tooltip, { slots: { trigger: 'Hover', default: 'Tip' } })
    await wrapper.trigger('mouseenter')
    expect(wrapper.find('.md3-tooltip__content').attributes('role')).toBe('tooltip')
  })
})
