import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { nextTick } from 'vue'
import Terminal from '@/components/Terminal.vue'

const { mockTerm, mockFitAddon } = vi.hoisted(() => {
  const term = {
    open: vi.fn(),
    loadAddon: vi.fn(),
    write: vi.fn(),
    writeln: vi.fn(),
    clear: vi.fn(),
    focus: vi.fn(),
    dispose: vi.fn(),
    getSelection: vi.fn().mockReturnValue('selected text'),
    onData: vi.fn().mockReturnValue({ dispose: vi.fn() }),
    onResize: vi.fn().mockReturnValue({ dispose: vi.fn() }),
    buffer: {
      active: {
        length: 10,
        getLine: vi.fn().mockReturnValue({
          translateToString: vi.fn().mockReturnValue('line content'),
        }),
      },
    },
    options: {
      fontSize: 14,
      fontFamily: '',
      theme: {} as Record<string, string>,
    },
  }
  const fitAddon = {
    fit: vi.fn(),
    dispose: vi.fn(),
  }
  return { mockTerm: term, mockFitAddon: fitAddon }
})

vi.mock('xterm', () => ({
  Terminal: vi.fn().mockImplementation(() => mockTerm),
}))

vi.mock('xterm-addon-fit', () => ({
  FitAddon: vi.fn().mockImplementation(() => mockFitAddon),
}))

vi.mock('xterm/css/xterm.css', () => ({}))

vi.mock('@/components/md3', () => ({
  Md3Icon: {
    name: 'Md3Icon',
    props: ['name', 'size'],
    template: '<span class="mdi-icon" :data-name="name" :data-size="size"></span>',
  },
}))

vi.mock('@/components/Md3Button.vue', () => ({
  default: {
    name: 'Md3Button',
    props: ['size', 'variant', 'disabled', 'icon'],
    template: '<button class="md3-btn" :disabled="disabled" @click="$emit(\'click\')"><slot /></button>',
  },
}))

Object.defineProperty(globalThis, 'navigator', {
  value: {
    clipboard: {
      writeText: vi.fn().mockResolvedValue(undefined),
      readText: vi.fn().mockResolvedValue('pasted text'),
    },
  },
  writable: true,
})

Object.defineProperty(globalThis, 'ResizeObserver', {
  value: vi.fn().mockImplementation(() => ({
    observe: vi.fn(),
    disconnect: vi.fn(),
  })),
  writable: true,
})

function createWrapper(props = {}) {
  return mount(Terminal, {
    props: {
      ...props,
    },
    attachTo: document.body,
  })
}

describe('Terminal', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('基础渲染', () => {
    it('应该渲染终端容器', () => {
      const wrapper = createWrapper()
      expect(wrapper.find('.terminal-wrapper').exists()).toBe(true)
    })

    it('应该渲染终端 DOM 容器', () => {
      const wrapper = createWrapper()
      expect(wrapper.find('.terminal-container').exists()).toBe(true)
    })

    it('默认不显示工具栏', () => {
      const wrapper = createWrapper()
      expect(wrapper.find('.terminal-toolbar').exists()).toBe(false)
    })

    it('showToolbar 为 true 时应该显示工具栏', () => {
      const wrapper = createWrapper({ showToolbar: true })
      expect(wrapper.find('.terminal-toolbar').exists()).toBe(true)
    })

    it('工具栏应该包含会话标签', () => {
      const wrapper = createWrapper({ showToolbar: true, sessionName: 'SSH-01' })
      expect(wrapper.find('.session-label').text()).toBe('SSH-01')
    })

    it('没有 sessionName 时应该显示默认标签', () => {
      const wrapper = createWrapper({ showToolbar: true })
      expect(wrapper.find('.session-label').text()).toBe('终端')
    })
  })

  describe('xterm 初始化', () => {
    it('挂载时应该创建 Terminal 实例', async () => {
      const { Terminal: XTermTerminal } = await import('xterm')
      createWrapper()
      expect(XTermTerminal).toHaveBeenCalled()
    })

    it('应该调用 terminal.open', () => {
      createWrapper()
      expect(mockTerm.open).toHaveBeenCalled()
    })

    it('应该调用 terminal.loadAddon', () => {
      createWrapper()
      expect(mockTerm.loadAddon).toHaveBeenCalled()
    })

    it('应该调用 fitAddon.fit', () => {
      createWrapper()
      expect(mockFitAddon.fit).toHaveBeenCalled()
    })

    it('应该注册 onData 回调', () => {
      createWrapper()
      expect(mockTerm.onData).toHaveBeenCalled()
    })

    it('应该注册 onResize 回调', () => {
      createWrapper()
      expect(mockTerm.onResize).toHaveBeenCalled()
    })

    it('应该使用默认字体大小 14', async () => {
      const { Terminal: XTermTerminal } = await import('xterm')
      createWrapper()
      const callArgs = XTermTerminal.mock.calls[0][0]
      expect(callArgs.fontSize).toBe(14)
    })

    it('应该使用自定义字体大小', async () => {
      const { Terminal: XTermTerminal } = await import('xterm')
      createWrapper({ fontSize: 18 })
      const callArgs = XTermTerminal.mock.calls[0][0]
      expect(callArgs.fontSize).toBe(18)
    })

    it('应该使用 dark 主题作为默认', async () => {
      const { Terminal: XTermTerminal } = await import('xterm')
      createWrapper()
      const callArgs = XTermTerminal.mock.calls[0][0]
      expect(callArgs.theme.background).toBe('#1e1e1e')
    })

    it('应该使用 light 主题', async () => {
      const { Terminal: XTermTerminal } = await import('xterm')
      createWrapper({ theme: 'light' })
      const callArgs = XTermTerminal.mock.calls[0][0]
      expect(callArgs.theme.background).toBe('#ffffff')
    })
  })

  describe('暴露的方法', () => {
    it('write 方法应该向终端写入数据', async () => {
      const wrapper = createWrapper()
      const vm = wrapper.vm as any
      vm.write('hello world')
      expect(mockTerm.write).toHaveBeenCalledWith('hello world')
    })

    it('writeln 方法应该向终端写入一行数据', async () => {
      const wrapper = createWrapper()
      const vm = wrapper.vm as any
      vm.writeln('hello')
      expect(mockTerm.writeln).toHaveBeenCalledWith('hello')
    })

    it('clear 方法应该清空终端', async () => {
      const wrapper = createWrapper()
      const vm = wrapper.vm as any
      vm.clear()
      expect(mockTerm.clear).toHaveBeenCalled()
    })

    it('focus 方法应该聚焦终端', async () => {
      const wrapper = createWrapper()
      const vm = wrapper.vm as any
      vm.focus()
      expect(mockTerm.focus).toHaveBeenCalled()
    })

    it('resize 方法应该调用 fitAddon.fit', async () => {
      const wrapper = createWrapper()
      const vm = wrapper.vm as any
      vm.resize()
      expect(mockFitAddon.fit).toHaveBeenCalled()
    })

    it('getTerminal 方法应该返回终端实例', async () => {
      const wrapper = createWrapper()
      const vm = wrapper.vm as any
      const term = vm.getTerminal()
      expect(term).toBeDefined()
    })

    it('getIsFrozen 方法默认返回 false', async () => {
      const wrapper = createWrapper()
      const vm = wrapper.vm as any
      expect(vm.getIsFrozen()).toBe(false)
    })
  })

  describe('冻结功能', () => {
    it('冻结后写入数据应该缓冲而不写入终端', async () => {
      const wrapper = createWrapper()
      const vm = wrapper.vm as any

      vm.handleFreeze()
      await nextTick()

      expect(vm.getIsFrozen()).toBe(true)

      mockTerm.write.mockClear()
      vm.write('buffered data')
      expect(mockTerm.write).not.toHaveBeenCalled()
    })

    it('解冻后应该将缓冲数据写入终端', async () => {
      const wrapper = createWrapper()
      const vm = wrapper.vm as any

      vm.handleFreeze()
      await nextTick()
      vm.write('buffered data')

      mockTerm.write.mockClear()
      vm.handleFreeze()
      await nextTick()

      expect(mockTerm.write).toHaveBeenCalledWith('buffered data')
      expect(vm.getIsFrozen()).toBe(false)
    })

    it('syncFrozenData 应该在非冻结状态下刷新缓冲', async () => {
      const wrapper = createWrapper()
      const vm = wrapper.vm as any

      vm.handleFreeze()
      await nextTick()
      vm.write('data1')

      mockTerm.write.mockClear()
      vm.handleFreeze()
      await nextTick()

      vm.syncFrozenData()
      expect(vm.getIsFrozen()).toBe(false)
    })
  })

  describe('工具栏操作', () => {
    it('点击复制选中按钮应该调用 clipboard.writeText', async () => {
      const wrapper = createWrapper({ showToolbar: true })
      const copyBtn = wrapper.findAll('button').find(b => b.text().includes('复制选中'))
      await copyBtn?.trigger('click')
      expect(navigator.clipboard.writeText).toHaveBeenCalledWith('selected text')
    })

    it('点击复制全部按钮应该调用 clipboard.writeText', async () => {
      const wrapper = createWrapper({ showToolbar: true })
      const copyAllBtn = wrapper.findAll('button').find(b => b.text().includes('复制全部'))
      await copyAllBtn?.trigger('click')
      expect(navigator.clipboard.writeText).toHaveBeenCalled()
    })

    it('点击粘贴按钮应该触发 data 事件', async () => {
      const wrapper = createWrapper({ showToolbar: true })
      const pasteBtn = wrapper.findAll('button').find(b => b.text().includes('粘贴'))
      await pasteBtn?.trigger('click')
      await vi.waitFor(() => {
        expect(wrapper.emitted('data')).toBeTruthy()
      })
    })

    it('点击清屏按钮应该调用 clear', async () => {
      const wrapper = createWrapper({ showToolbar: true })
      mockTerm.clear.mockClear()
      const clearBtn = wrapper.findAll('button').find(b => b.text().includes('清屏'))
      await clearBtn?.trigger('click')
      expect(mockTerm.clear).toHaveBeenCalled()
    })
  })

  describe('Props 响应', () => {
    it('fontSize 变化时应该更新终端字体大小', async () => {
      const wrapper = createWrapper({ showToolbar: true })
      await wrapper.setProps({ fontSize: 20 })
      expect(mockTerm.options.fontSize).toBe(20)
    })

    it('fontFamily 变化时应该更新终端字体', async () => {
      const wrapper = createWrapper({ showToolbar: true })
      await wrapper.setProps({ fontFamily: 'Fira Code' })
      expect(mockTerm.options.fontFamily).toBe('Fira Code')
    })

    it('theme 变化时应该更新终端主题', async () => {
      const wrapper = createWrapper({ showToolbar: true })
      await wrapper.setProps({ theme: 'light' })
      expect(mockTerm.options.theme.background).toBe('#ffffff')
    })
  })

  describe('事件触发', () => {
    it('终端输入数据应该触发 data 事件', () => {
      createWrapper()
      const onDataCallback = mockTerm.onData.mock.calls[0][0]
      onDataCallback('ls -la\n')
    })

    it('终端大小变化应该触发 resize 事件', () => {
      createWrapper()
      const onResizeCallback = mockTerm.onResize.mock.calls[0][0]
      onResizeCallback({ cols: 120, rows: 40 })
    })
  })

  describe('生命周期', () => {
    it('卸载时应该销毁终端实例', async () => {
      const wrapper = createWrapper()
      wrapper.unmount()
      expect(mockTerm.dispose).toHaveBeenCalled()
    })
  })
})
