import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import ContainerList from '@/components/ContainerList.vue'
import type { DockerContainer } from '@/stores/dockerStore'

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
    template: '<button class="md3-btn" :disabled="disabled" @click="$emit(\'click\')"><slot /></button>',
  },
}))

vi.mock('@/components/md3/Md3Tag.vue', () => ({
  default: {
    name: 'Md3Tag',
    props: ['variant'],
    template: '<span class="md3-tag" :data-variant="variant"><slot /></span>',
  },
}))

const mockContainers: DockerContainer[] = [
  {
    id: 'abc123',
    name: 'nginx-web',
    image: 'nginx:latest',
    status: 'Up 2 hours',
    state: 'running',
    ports: '0.0.0.0:80->80/tcp',
    created: '2024-01-15 10:00:00',
  },
  {
    id: 'def456',
    name: 'redis-cache',
    image: 'redis:7',
    status: 'Exited (0) 1 hour ago',
    state: 'exited',
    ports: '',
    created: '2024-01-14 08:30:00',
  },
  {
    id: 'ghi789',
    name: 'mysql-db',
    image: 'mysql:8.0',
    status: 'Paused',
    state: 'paused',
    ports: '0.0.0.0:3306->3306/tcp',
    created: '2024-01-13 12:00:00',
  },
]

function createWrapper(props = {}) {
  return mount(ContainerList, {
    props: {
      containers: mockContainers,
      ...props,
    },
  })
}

describe('ContainerList', () => {
  describe('基础渲染', () => {
    it('应该渲染容器列表容器', () => {
      const wrapper = createWrapper()
      expect(wrapper.find('.container-list').exists()).toBe(true)
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

    it('应该根据 containers 数量渲染对应行数', () => {
      const wrapper = createWrapper()
      const rows = wrapper.findAll('tbody tr')
      expect(rows.length).toBe(3)
    })

    it('容器为空时应该显示空状态', () => {
      const wrapper = createWrapper({ containers: [] })
      expect(wrapper.find('.md3-table-empty').exists()).toBe(true)
      expect(wrapper.text()).toContain('暂无容器')
    })

    it('应该渲染容器名称', () => {
      const wrapper = createWrapper()
      expect(wrapper.text()).toContain('nginx-web')
      expect(wrapper.text()).toContain('redis-cache')
      expect(wrapper.text()).toContain('mysql-db')
    })

    it('应该渲染容器镜像', () => {
      const wrapper = createWrapper()
      expect(wrapper.text()).toContain('nginx:latest')
      expect(wrapper.text()).toContain('redis:7')
      expect(wrapper.text()).toContain('mysql:8.0')
    })

    it('应该渲染端口信息', () => {
      const wrapper = createWrapper()
      expect(wrapper.text()).toContain('0.0.0.0:80->80/tcp')
    })

    it('端口为空时应该显示短横线', () => {
      const wrapper = createWrapper()
      const rows = wrapper.findAll('tbody tr')
      const redisRow = rows[1]
      expect(redisRow.text()).toContain('-')
    })

    it('应该渲染创建时间', () => {
      const wrapper = createWrapper()
      expect(wrapper.text()).toContain('2024-01-15 10:00:00')
    })
  })

  describe('状态标签', () => {
    it('running 状态应该渲染 Md3Tag', () => {
      const wrapper = createWrapper()
      const tags = wrapper.findAll('.md3-tag')
      expect(tags.length).toBe(3)
    })

    it('应该显示容器状态文本', () => {
      const wrapper = createWrapper()
      expect(wrapper.text()).toContain('running')
      expect(wrapper.text()).toContain('exited')
      expect(wrapper.text()).toContain('paused')
    })

    it('应该渲染状态对应的 status 文本', () => {
      const wrapper = createWrapper()
      expect(wrapper.text()).toContain('Up 2 hours')
      expect(wrapper.text()).toContain('Exited (0) 1 hour ago')
    })
  })

  describe('操作按钮', () => {
    it('每行应该渲染操作按钮区域', () => {
      const wrapper = createWrapper()
      const actionAreas = wrapper.findAll('.action-buttons')
      expect(actionAreas.length).toBe(3)
    })

    it('running 容器的启动按钮应该被禁用', () => {
      const wrapper = createWrapper()
      const rows = wrapper.findAll('tbody tr')
      const firstRowButtons = rows[0].findAll('button')
      const startBtn = firstRowButtons[0]
      expect(startBtn.attributes('disabled')).toBeDefined()
    })

    it('非 running 容器的停止按钮应该被禁用', () => {
      const wrapper = createWrapper()
      const rows = wrapper.findAll('tbody tr')
      const exitedRowButtons = rows[1].findAll('button')
      const stopBtn = exitedRowButtons[1]
      expect(stopBtn.attributes('disabled')).toBeDefined()
    })

    it('非 running 容器的终端按钮应该被禁用', () => {
      const wrapper = createWrapper()
      const rows = wrapper.findAll('tbody tr')
      const exitedRowButtons = rows[1].findAll('button')
      const terminalBtn = exitedRowButtons[4]
      expect(terminalBtn.attributes('disabled')).toBeDefined()
    })

    it('点击启动按钮应该触发 start 事件', async () => {
      const wrapper = createWrapper()
      const rows = wrapper.findAll('tbody tr')
      const exitedRowButtons = rows[1].findAll('button')
      const startBtn = exitedRowButtons[0]
      await startBtn.trigger('click')
      expect(wrapper.emitted('start')).toBeTruthy()
      expect(wrapper.emitted('start')![0][0]).toEqual(mockContainers[1])
    })

    it('点击停止按钮应该触发 stop 事件', async () => {
      const wrapper = createWrapper()
      const rows = wrapper.findAll('tbody tr')
      const runningRowButtons = rows[0].findAll('button')
      const stopBtn = runningRowButtons[1]
      await stopBtn.trigger('click')
      expect(wrapper.emitted('stop')).toBeTruthy()
      expect(wrapper.emitted('stop')![0][0]).toEqual(mockContainers[0])
    })

    it('点击重启按钮应该触发 restart 事件', async () => {
      const wrapper = createWrapper()
      const rows = wrapper.findAll('tbody tr')
      const runningRowButtons = rows[0].findAll('button')
      const restartBtn = runningRowButtons[2]
      await restartBtn.trigger('click')
      expect(wrapper.emitted('restart')).toBeTruthy()
      expect(wrapper.emitted('restart')![0][0]).toEqual(mockContainers[0])
    })

    it('点击日志按钮应该触发 logs 事件', async () => {
      const wrapper = createWrapper()
      const rows = wrapper.findAll('tbody tr')
      const runningRowButtons = rows[0].findAll('button')
      const logsBtn = runningRowButtons[3]
      await logsBtn.trigger('click')
      expect(wrapper.emitted('logs')).toBeTruthy()
      expect(wrapper.emitted('logs')![0][0]).toEqual(mockContainers[0])
    })

    it('点击终端按钮应该触发 terminal 事件', async () => {
      const wrapper = createWrapper()
      const rows = wrapper.findAll('tbody tr')
      const runningRowButtons = rows[0].findAll('button')
      const terminalBtn = runningRowButtons[4]
      await terminalBtn.trigger('click')
      expect(wrapper.emitted('terminal')).toBeTruthy()
      expect(wrapper.emitted('terminal')![0][0]).toEqual(mockContainers[0])
    })

    it('点击删除按钮应该触发 confirmDelete', async () => {
      const { Md3Confirm } = await import('@/components/md3')
      const wrapper = createWrapper()
      const rows = wrapper.findAll('tbody tr')
      const deleteBtn = rows[0].findAll('button')[5]
      await deleteBtn.trigger('click')
      expect(Md3Confirm.show).toHaveBeenCalled()
    })
  })

  describe('行选择', () => {
    it('每行应该有复选框', () => {
      const wrapper = createWrapper()
      const checkboxes = wrapper.findAll('tbody input[type="checkbox"]')
      expect(checkboxes.length).toBe(3)
    })

    it('表头应该有全选复选框', () => {
      const wrapper = createWrapper()
      const headerCheckbox = wrapper.find('thead input[type="checkbox"]')
      expect(headerCheckbox.exists()).toBe(true)
    })

    it('点击行复选框应该触发 selectionChange 事件', async () => {
      const wrapper = createWrapper()
      const firstCheckbox = wrapper.findAll('tbody input[type="checkbox"]')[0]
      await firstCheckbox.trigger('change')
      expect(wrapper.emitted('selectionChange')).toBeTruthy()
    })

    it('点击全选复选框应该选中所有行', async () => {
      const wrapper = createWrapper()
      const headerCheckbox = wrapper.find('thead input[type="checkbox"]')
      await headerCheckbox.trigger('change')
      expect(wrapper.emitted('selectionChange')).toBeTruthy()
      const emittedItems = wrapper.emitted('selectionChange')![0][0] as DockerContainer[]
      expect(emittedItems.length).toBe(3)
    })

    it('全选后再次点击全选应该取消所有选择', async () => {
      const wrapper = createWrapper()
      const headerCheckbox = wrapper.find('thead input[type="checkbox"]')
      await headerCheckbox.trigger('change')
      await headerCheckbox.trigger('change')
      const lastEmission = wrapper.emitted('selectionChange')!.at(-1)![0] as DockerContainer[]
      expect(lastEmission.length).toBe(0)
    })

    it('点击单个行复选框应该选中该行', async () => {
      const wrapper = createWrapper()
      const firstCheckbox = wrapper.findAll('tbody input[type="checkbox"]')[0]
      await firstCheckbox.trigger('change')
      const emittedItems = wrapper.emitted('selectionChange')![0][0] as DockerContainer[]
      expect(emittedItems.length).toBe(1)
      expect(emittedItems[0].id).toBe('abc123')
    })

    it('容器为空时全选复选框不应该被选中', () => {
      const wrapper = createWrapper({ containers: [] })
      const headerCheckbox = wrapper.find('thead input[type="checkbox"]')
      expect(headerCheckbox.element.checked).toBe(false)
    })
  })

  describe('不同容器状态', () => {
    it('created 状态的容器应该正常渲染', () => {
      const createdContainer: DockerContainer = {
        id: 'jkl012',
        name: 'test-created',
        image: 'alpine:latest',
        status: 'Created',
        state: 'created',
        ports: '',
        created: '2024-01-16 09:00:00',
      }
      const wrapper = createWrapper({ containers: [createdContainer] })
      expect(wrapper.text()).toContain('created')
      expect(wrapper.text()).toContain('test-created')
    })
  })
})
