import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import FileBrowser from '@/components/FileBrowser.vue'
import type { FileItem } from '@/components/FileBrowser.vue'

vi.mock('@/components/md3', () => ({
  Md3Icon: {
    name: 'Md3Icon',
    props: ['name', 'size'],
    template: '<span class="mdi-icon" :data-name="name" :data-size="size"></span>',
  },
  Md3Confirm: {
    show: vi.fn().mockResolvedValue(true),
  },
}))

vi.mock('@/components/Md3Button.vue', () => ({
  default: {
    name: 'Md3Button',
    props: ['size', 'variant', 'disabled', 'icon'],
    template: '<button class="md3-btn" :disabled="disabled" @click.stop="$emit(\'click\', $event)"><slot /></button>',
  },
}))

vi.mock('@/components/md3/Md3Input.vue', () => ({
  default: {
    name: 'Md3Input',
    props: ['modelValue', 'placeholder', 'type'],
    emits: ['update:modelValue'],
    template: '<input class="md3-input" :value="modelValue" :placeholder="placeholder" @input="$emit(\'update:modelValue\', $event.target.value)" />',
  },
}))

vi.mock('@/components/md3/Md3Checkbox.vue', () => ({
  default: {
    name: 'Md3Checkbox',
    props: ['modelValue', 'value', 'indeterminate'],
    emits: ['update:modelValue'],
    template: '<input type="checkbox" class="md3-checkbox" :checked="Array.isArray(modelValue) ? modelValue.includes(value) : modelValue" :data-indeterminate="indeterminate" @change="$emit(\'update:modelValue\', $event.target.checked)" />',
  },
}))

const mockItems: FileItem[] = [
  {
    name: 'documents',
    path: '/home/user/documents',
    is_dir: true,
    size: 0,
    permission: 'drwxr-xr-x',
    owner: 'user',
    group: 'user',
    modified: '2024-01-15 10:00:00',
  },
  {
    name: 'readme.md',
    path: '/home/user/readme.md',
    is_dir: false,
    size: 2048,
    permission: '-rw-r--r--',
    owner: 'user',
    group: 'user',
    modified: '2024-01-14 08:30:00',
  },
  {
    name: 'config.yaml',
    path: '/home/user/config.yaml',
    is_dir: false,
    size: 512,
    permission: '-rw-------',
    owner: 'root',
    group: 'root',
    modified: '2024-01-13 12:00:00',
  },
]

function createWrapper(props = {}) {
  return mount(FileBrowser, {
    props: {
      currentPath: '/home/user',
      items: mockItems,
      ...props,
    },
  })
}

describe('FileBrowser', () => {
  describe('基础渲染', () => {
    it('应该渲染文件浏览器容器', () => {
      const wrapper = createWrapper()
      expect(wrapper.find('.file-browser').exists()).toBe(true)
    })

    it('应该渲染工具栏', () => {
      const wrapper = createWrapper()
      expect(wrapper.find('.browser-toolbar').exists()).toBe(true)
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
      expect(headers.length).toBe(7)
    })

    it('应该根据 items 数量渲染对应行数', () => {
      const wrapper = createWrapper()
      const rows = wrapper.findAll('tbody tr')
      expect(rows.length).toBe(3)
    })

    it('文件为空时应该显示空状态', () => {
      const wrapper = createWrapper({ items: [] })
      expect(wrapper.find('.md3-table-empty').exists()).toBe(true)
      expect(wrapper.text()).toContain('暂无文件')
    })

    it('应该渲染文件/目录名称', () => {
      const wrapper = createWrapper()
      expect(wrapper.text()).toContain('documents')
      expect(wrapper.text()).toContain('readme.md')
      expect(wrapper.text()).toContain('config.yaml')
    })

    it('应该渲染权限信息', () => {
      const wrapper = createWrapper()
      expect(wrapper.text()).toContain('drwxr-xr-x')
      expect(wrapper.text()).toContain('-rw-r--r--')
    })

    it('应该渲染所有者信息', () => {
      const wrapper = createWrapper()
      expect(wrapper.text()).toContain('user')
      expect(wrapper.text()).toContain('root')
    })

    it('应该渲染修改时间', () => {
      const wrapper = createWrapper()
      expect(wrapper.text()).toContain('2024-01-15 10:00:00')
    })
  })

  describe('文件大小格式化', () => {
    it('目录应该显示短横线', () => {
      const wrapper = createWrapper()
      const rows = wrapper.findAll('tbody tr')
      const dirRow = rows[0]
      expect(dirRow.text()).toContain('-')
    })

    it('文件应该显示格式化后的大小', () => {
      const wrapper = createWrapper()
      const rows = wrapper.findAll('tbody tr')
      const fileRow = rows[1]
      expect(fileRow.text()).toContain('2 KB')
    })

    it('小文件应该显示字节大小', () => {
      const wrapper = createWrapper()
      const rows = wrapper.findAll('tbody tr')
      const smallFileRow = rows[2]
      expect(smallFileRow.text()).toContain('512 B')
    })
  })

  describe('面包屑导航', () => {
    it('应该渲染面包屑导航', () => {
      const wrapper = createWrapper()
      expect(wrapper.find('.path-breadcrumb').exists()).toBe(true)
    })

    it('应该根据路径渲染面包屑段', () => {
      const wrapper = createWrapper()
      const segments = wrapper.findAll('.breadcrumb-item')
      expect(segments.length).toBe(2)
    })

    it('最后一个段应该是当前目录', () => {
      const wrapper = createWrapper()
      const currentSegment = wrapper.find('.breadcrumb-current')
      expect(currentSegment.text()).toBe('user')
    })

    it('非最后段应该是可点击链接', () => {
      const wrapper = createWrapper()
      const links = wrapper.findAll('.breadcrumb-link')
      expect(links.length).toBe(1)
    })

    it('点击面包屑链接应该触发 navigate 事件', async () => {
      const wrapper = createWrapper()
      const link = wrapper.find('.breadcrumb-link')
      await link.trigger('click')
      expect(wrapper.emitted('navigate')).toBeTruthy()
    })

    it('根路径时上级按钮应该被禁用', () => {
      const wrapper = createWrapper({ currentPath: '/' })
      const backBtn = wrapper.findAll('button').find(b => b.text().includes('上级'))
      expect(backBtn?.attributes('disabled')).toBeDefined()
    })

    it('非根路径时上级按钮应该可用', () => {
      const wrapper = createWrapper()
      const backBtn = wrapper.findAll('button').find(b => b.text().includes('上级'))
      expect(backBtn?.attributes('disabled')).toBeUndefined()
    })

    it('点击上级按钮应该触发 navigate 事件', async () => {
      const wrapper = createWrapper()
      const backBtn = wrapper.findAll('button').find(b => b.text().includes('上级'))
      await backBtn?.trigger('click')
      expect(wrapper.emitted('navigate')).toBeTruthy()
      expect(wrapper.emitted('navigate')![0][0]).toBe('/home')
    })
  })

  describe('操作按钮', () => {
    it('每行应该渲染操作按钮区域', () => {
      const wrapper = createWrapper()
      const actionAreas = wrapper.findAll('.action-buttons')
      expect(actionAreas.length).toBe(3)
    })

    it('点击下载按钮应该触发 download 事件', async () => {
      const wrapper = createWrapper()
      const rows = wrapper.findAll('tbody tr')
      const downloadBtn = rows[1].findAll('button')[0]
      await downloadBtn.trigger('click')
      expect(wrapper.emitted('download')).toBeTruthy()
    })

    it('点击重命名按钮应该触发 rename 事件', async () => {
      const wrapper = createWrapper()
      const rows = wrapper.findAll('tbody tr')
      const renameBtn = rows[1].findAll('button')[1]
      await renameBtn.trigger('click')
      expect(wrapper.emitted('rename')).toBeTruthy()
    })

    it('点击复制按钮应该触发 copy 事件', async () => {
      const wrapper = createWrapper()
      const rows = wrapper.findAll('tbody tr')
      const copyBtn = rows[1].findAll('button')[2]
      await copyBtn.trigger('click')
      expect(wrapper.emitted('copy')).toBeTruthy()
    })

    it('点击权限按钮应该触发 chmod 事件', async () => {
      const wrapper = createWrapper()
      const rows = wrapper.findAll('tbody tr')
      const chmodBtn = rows[1].findAll('button')[3]
      await chmodBtn.trigger('click')
      expect(wrapper.emitted('chmod')).toBeTruthy()
    })

    it('点击删除按钮应该触发 confirmDelete', async () => {
      const { Md3Confirm } = await import('@/components/md3')
      const wrapper = createWrapper()
      const rows = wrapper.findAll('tbody tr')
      const deleteBtn = rows[1].findAll('button')[4]
      await deleteBtn.trigger('click')
      expect(Md3Confirm.show).toHaveBeenCalled()
    })
  })

  describe('新建与上传', () => {
    it('showCreate 为 true 时应该显示新建按钮', () => {
      const wrapper = createWrapper({ showCreate: true })
      const buttons = wrapper.findAll('button')
      const createBtn = buttons.find(b => b.text().includes('新建'))
      expect(createBtn).toBeTruthy()
    })

    it('showCreate 为 false 时不应该显示新建按钮', () => {
      const wrapper = createWrapper({ showCreate: false })
      const buttons = wrapper.findAll('button')
      const createBtn = buttons.find(b => b.text().includes('新建'))
      expect(createBtn).toBeUndefined()
    })

    it('showUpload 为 true 时应该显示上传按钮', () => {
      const wrapper = createWrapper({ showUpload: true })
      const buttons = wrapper.findAll('button')
      const uploadBtn = buttons.find(b => b.text().includes('上传'))
      expect(uploadBtn).toBeTruthy()
    })

    it('showUpload 为 false 时不应该显示上传按钮', () => {
      const wrapper = createWrapper({ showUpload: false })
      const buttons = wrapper.findAll('button')
      const uploadBtn = buttons.find(b => b.text().includes('上传'))
      expect(uploadBtn).toBeUndefined()
    })

    it('点击上传按钮应该触发 upload 事件', async () => {
      const wrapper = createWrapper({ showUpload: true })
      const buttons = wrapper.findAll('button')
      const uploadBtn = buttons.find(b => b.text().includes('上传'))
      await uploadBtn?.trigger('click')
      expect(wrapper.emitted('upload')).toBeTruthy()
    })
  })

  describe('行交互', () => {
    it('单击行应该触发 rowClick 事件', async () => {
      const wrapper = createWrapper()
      const rows = wrapper.findAll('tbody tr')
      await rows[1].trigger('click')
      expect(wrapper.emitted('rowClick')).toBeTruthy()
      expect(wrapper.emitted('rowClick')![0][0]).toEqual(mockItems[1])
    })

    it('双击目录行应该触发 navigate 事件', async () => {
      const wrapper = createWrapper()
      const rows = wrapper.findAll('tbody tr')
      await rows[0].trigger('dblclick')
      expect(wrapper.emitted('navigate')).toBeTruthy()
      expect(wrapper.emitted('navigate')![0][0]).toBe('/home/user/documents')
    })

    it('双击文件行不应该触发 navigate 事件', async () => {
      const wrapper = createWrapper()
      const rows = wrapper.findAll('tbody tr')
      await rows[1].trigger('dblclick')
      expect(wrapper.emitted('navigate')).toBeFalsy()
    })

    it('双击文件行应该触发 rowDblClick 事件', async () => {
      const wrapper = createWrapper()
      const rows = wrapper.findAll('tbody tr')
      await rows[1].trigger('dblclick')
      expect(wrapper.emitted('rowDblClick')).toBeTruthy()
      expect(wrapper.emitted('rowDblClick')![0][0]).toEqual(mockItems[1])
    })
  })

  describe('状态栏', () => {
    it('应该显示项目数量', () => {
      const wrapper = createWrapper()
      expect(wrapper.find('.browser-status').exists()).toBe(true)
      expect(wrapper.text()).toContain('3 项')
    })

    it('空列表时应该显示 0 项', () => {
      const wrapper = createWrapper({ items: [] })
      expect(wrapper.text()).toContain('0 项')
    })

    it('有选中项时应该显示选中数量', () => {
      const wrapper = createWrapper({ selectedPaths: ['/home/user/readme.md'] })
      expect(wrapper.text()).toContain('已选择 1 项')
    })

    it('没有选中项时不应该显示选中信息', () => {
      const wrapper = createWrapper()
      expect(wrapper.find('.selected-info').exists()).toBe(false)
    })
  })

  describe('路径处理', () => {
    it('应该正确处理 Windows 风格路径', () => {
      const wrapper = createWrapper({ currentPath: 'C:\\Users\\test' })
      const segments = wrapper.findAll('.breadcrumb-item')
      expect(segments.length).toBe(3)
    })

    it('空路径时上级按钮应该被禁用', () => {
      const wrapper = createWrapper({ currentPath: '' })
      const backBtn = wrapper.findAll('button').find(b => b.text().includes('上级'))
      expect(backBtn?.attributes('disabled')).toBeDefined()
    })
  })
})
