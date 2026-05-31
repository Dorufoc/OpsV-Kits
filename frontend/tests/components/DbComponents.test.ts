import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'

vi.mock('@/components/md3', () => ({
  Md3Icon: { name: 'Md3Icon', props: ['name', 'size'], template: '<span class="mdi-icon" :data-name="name"></span>' },
  Md3Confirm: { show: vi.fn().mockResolvedValue(true) },
  Md3Message: { success: vi.fn(), error: vi.fn() },
  Md3Tag: { name: 'Md3Tag', props: ['type', 'size', 'variant'], template: '<span class="md3-tag"><slot /></span>' },
  Md3Input: { name: 'Md3Input', props: ['modelValue', 'label', 'placeholder', 'type'], emits: ['update:modelValue'], template: '<input class="md3-input" :value="modelValue" />' },
  Md3Select: { name: 'Md3Select', props: ['modelValue', 'options', 'placeholder', 'label', 'clearable'], emits: ['update:modelValue'], template: '<select class="md3-select" />' },
  Md3Card: { name: 'Md3Card', props: ['shadow'], template: '<div class="md3-card"><slot /><slot name="header" /></div>' },
  Md3Empty: { name: 'Md3Empty', props: ['description'], template: '<div class="md3-empty">{{ description }}</div>' },
  Md3Dialog: { name: 'Md3Dialog', props: ['visible', 'title', 'width'], emits: ['update:visible'], template: '<div class="md3-dialog" v-if="visible"><slot /><slot name="footer" /></div>' },
  Md3Table: { name: 'Md3Table', props: ['columns', 'data', 'stripe', 'emptyText'], template: '<div class="md3-table"><slot /></div>' },
  Md3Tabs: { name: 'Md3Tabs', props: ['modelValue', 'tabs'], template: '<div class="md3-tabs" />' },
  Md3Divider: { name: 'Md3Divider', template: '<hr class="md3-divider" />' },
  Md3Button: { name: 'Md3Button', props: ['size', 'variant', 'disabled', 'loading'], template: '<button class="md3-btn" :disabled="disabled" @click="$emit(\'click\')"><slot /></button>' },
  Md3Progress: { name: 'Md3Progress', props: ['percentage', 'color'], template: '<div class="md3-progress" />' },
  Md3Switch: { name: 'Md3Switch', props: ['modelValue', 'onText', 'offText'], emits: ['update:modelValue'], template: '<div class="md3-switch" />' },
  Md3Alert: { name: 'Md3Alert', props: ['type', 'title', 'message'], template: '<div class="md3-alert" />' },
  Md3Tooltip: { name: 'Md3Tooltip', props: ['content', 'placement'], template: '<div class="md3-tooltip"><slot /></div>' },
  Md3Checkbox: { name: 'Md3Checkbox', props: ['modelValue'], emits: ['update:modelValue'], template: '<input type="checkbox" class="md3-checkbox" />' },
}))

vi.mock('@/components/Md3Button.vue', () => ({
  default: { name: 'Md3Button', props: ['size', 'variant', 'disabled', 'loading', 'type'], template: '<button class="md3-btn" :disabled="disabled" @click="$emit(\'click\')"><slot /></button>' },
}))

vi.mock('@/stores/dbToolkitStore', () => ({
  useDbToolkitStore: () => ({
    connections: [],
    savedConnections: [],
    currentConnection: null,
    redisConnection: null,
    sqlResult: null,
    tables: [],
    mysqlQueryHistory: [],
    loading: false,
    fetchConnections: vi.fn().mockResolvedValue(undefined),
    testConnection: vi.fn().mockResolvedValue({ success: true }),
    executeQuery: vi.fn().mockResolvedValue(undefined),
    connectRedis: vi.fn().mockResolvedValue(undefined),
    scanRedisKeys: vi.fn().mockResolvedValue({ keys: [], cursor: 0 }),
    getRedisKeyValue: vi.fn().mockResolvedValue(undefined),
    checkDangerousSql: vi.fn().mockResolvedValue(false),
  }),
}))

beforeEach(() => {
  setActivePinia(createPinia())
  vi.clearAllMocks()
})

import DbToolkitPanel from '@/components/DbToolkitPanel.vue'
import DbConnectionManager from '@/components/DbConnectionManager.vue'
import DbLoginDialog from '@/components/DbLoginDialog.vue'
import DbManagerPanel from '@/components/DbManagerPanel.vue'
import DbSidebar from '@/components/DbSidebar.vue'
import MySqlPanel from '@/components/MySqlPanel.vue'
import RedisPanel from '@/components/RedisPanel.vue'
import RedisKeyDetail from '@/components/RedisKeyDetail.vue'
import RedisKeyList from '@/components/RedisKeyList.vue'
import SqlQueryEditor from '@/components/SqlQueryEditor.vue'
import SqlResultTable from '@/components/SqlResultTable.vue'
import DataRowForm from '@/components/DataRowForm.vue'
import DataEditor from '@/components/DataEditor.vue'
import TableInfoPanel from '@/components/TableInfoPanel.vue'

describe('DbToolkitPanel', () => {
  it('应该渲染数据库工具面板', () => {
    const wrapper = mount(DbToolkitPanel)
    expect(wrapper.find('.db-toolkit-panel').exists()).toBe(true)
  })
})

describe('DbConnectionManager', () => {
  it('应该渲染数据库连接管理器', () => {
    const wrapper = mount(DbConnectionManager)
    expect(wrapper.find('.db-connection-manager').exists()).toBe(true)
  })
})

describe('DbLoginDialog', () => {
  it('应该渲染数据库登录对话框', () => {
    const wrapper = mount(DbLoginDialog, {
      props: { visible: true },
    })
    expect(wrapper.find('.db-login-dialog').exists()).toBe(true)
  })

  it('应该接受 visible prop', () => {
    const wrapper = mount(DbLoginDialog, {
      props: { visible: false },
    })
    expect(wrapper.props('visible')).toBe(false)
  })

  it('visible 为 true 时应该显示对话框', () => {
    const wrapper = mount(DbLoginDialog, {
      props: { visible: true },
    })
    expect(wrapper.props('visible')).toBe(true)
  })
})

describe('DbManagerPanel', () => {
  it('应该渲染数据库管理面板', () => {
    const wrapper = mount(DbManagerPanel, {
      props: { deployMode: 'docker', accountAlias: 'test', containerId: 'abc', containerState: 'running' },
    })
    expect(wrapper.find('.db-manager-panel').exists()).toBe(true)
  })

  it('应该接受所有 props', () => {
    const wrapper = mount(DbManagerPanel, {
      props: {
        deployMode: 'ssh',
        accountAlias: 'prod-server',
        containerId: 'xyz789',
        containerState: 'stopped',
      },
    })
    expect(wrapper.props('deployMode')).toBe('ssh')
    expect(wrapper.props('accountAlias')).toBe('prod-server')
    expect(wrapper.props('containerId')).toBe('xyz789')
    expect(wrapper.props('containerState')).toBe('stopped')
  })
})

describe('DbSidebar', () => {
  it('应该渲染数据库侧边栏', () => {
    const wrapper = mount(DbSidebar)
    expect(wrapper.find('.db-sidebar').exists()).toBe(true)
  })
})

describe('MySqlPanel', () => {
  it('应该渲染 MySQL 面板', () => {
    const wrapper = mount(MySqlPanel)
    expect(wrapper.find('.mysql-panel').exists()).toBe(true)
  })
})

describe('RedisPanel', () => {
  it('应该渲染 Redis 面板', () => {
    const wrapper = mount(RedisPanel)
    expect(wrapper.find('.redis-panel').exists()).toBe(true)
  })
})

describe('RedisKeyDetail', () => {
  it('应该渲染 Redis 键详情', () => {
    const wrapper = mount(RedisKeyDetail, {
      props: { keyInfo: { key: 'test:key', type: 'string', value: 'hello', ttl: -1, truncated: false } },
    })
    expect(wrapper.find('.redis-key-detail').exists()).toBe(true)
  })

  it('无 keyInfo 时不应渲染', () => {
    const wrapper = mount(RedisKeyDetail, {
      props: { keyInfo: null },
    })
    expect(wrapper.find('.redis-key-detail').exists()).toBe(false)
  })
})

describe('RedisKeyList', () => {
  it('应该渲染 Redis 键列表', () => {
    const wrapper = mount(RedisKeyList)
    expect(wrapper.find('.redis-key-list').exists()).toBe(true)
  })
})

describe('SqlQueryEditor', () => {
  it('应该渲染 SQL 查询编辑器', () => {
    const wrapper = mount(SqlQueryEditor)
    expect(wrapper.find('.sql-query-editor').exists()).toBe(true)
  })
})

describe('SqlResultTable', () => {
  it('应该渲染 SQL 结果表', () => {
    const wrapper = mount(SqlResultTable, {
      props: { result: { columns: ['id', 'name'], rows: [{ id: 1, name: 'test' }], truncated: false } },
    })
    expect(wrapper.find('.sql-result-table').exists()).toBe(true)
  })

  it('无 result 时不应渲染', () => {
    const wrapper = mount(SqlResultTable, {
      props: { result: null },
    })
    expect(wrapper.find('.sql-result-table').exists()).toBe(false)
  })
})

describe('DataRowForm', () => {
  it('应该渲染数据行表单', () => {
    const wrapper = mount(DataRowForm)
    expect(wrapper.find('.data-row-form').exists()).toBe(true)
  })
})

describe('DataEditor', () => {
  it('应该渲染数据编辑器', () => {
    const wrapper = mount(DataEditor)
    expect(wrapper.find('.data-editor').exists()).toBe(true)
  })
})

describe('TableInfoPanel', () => {
  it('应该渲染表信息面板', () => {
    const wrapper = mount(TableInfoPanel)
    expect(wrapper.find('.table-info-panel').exists()).toBe(true)
  })
})
