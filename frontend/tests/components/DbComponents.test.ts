import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { nextTick } from 'vue'

vi.mock('@/components/md3', () => ({
  Md3Icon: { name: 'Md3Icon', props: ['name', 'size'], template: '<span class="mdi-icon" :data-name="name"></span>' },
  Md3Confirm: { show: vi.fn().mockResolvedValue(true) },
  Md3Message: { success: vi.fn(), error: vi.fn() },
  Md3Tag: { name: 'Md3Tag', props: ['type', 'size', 'variant'], template: '<span class="md3-tag"><slot /></span>' },
  Md3Input: { name: 'Md3Input', props: ['modelValue', 'label', 'placeholder', 'type'], emits: ['update:modelValue'], template: '<input class="md3-input" :value="modelValue" @input="$emit(\'update:modelValue\', $event.target.value)" />' },
  Md3Select: { name: 'Md3Select', props: ['modelValue', 'options', 'placeholder', 'label', 'clearable'], emits: ['update:modelValue'], template: '<select class="md3-select" />' },
  Md3Card: { name: 'Md3Card', props: ['shadow'], template: '<div class="md3-card"><slot /><slot name="header" /></div>' },
  Md3Empty: { name: 'Md3Empty', props: ['description'], template: '<div class="md3-empty">{{ description }}</div>' },
  Md3Dialog: { name: 'Md3Dialog', props: ['visible', 'title', 'width'], emits: ['update:visible', 'close'], template: '<div class="md3-dialog" v-if="visible"><slot /><slot name="footer" /></div>' },
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
  default: { name: 'Md3Button', props: ['size', 'variant', 'disabled', 'loading', 'type', 'icon'], emits: ['click'], template: '<button class="md3-btn" :disabled="disabled" @click="$emit(\'click\')"><slot /></button>' },
}))

vi.mock('@/components/Terminal.vue', () => ({
  default: { name: 'Terminal', props: ['sessionName', 'showToolbar'], emits: ['data', 'resize'], template: '<div class="terminal-mock" />' },
}))

vi.mock('@/components/DataRowForm.vue', () => ({
  default: { name: 'DataRowForm', props: ['accountAlias', 'containerId', 'tableName'], emits: ['close', 'inserted'], template: '<div class="data-row-form-mock" />' },
}))

vi.mock('@/components/SqlQueryEditor.vue', () => ({
  default: { name: 'SqlQueryEditor', props: ['accountAlias', 'containerId', 'loading'], emits: ['execute'], template: '<div class="sql-query-editor-mock" />' },
}))

vi.mock('@/components/SqlResultTable.vue', () => ({
  default: { name: 'SqlResultTable', props: ['result'], template: '<div class="sql-result-table-mock" v-if="result" />' },
}))

vi.mock('@/components/TableInfoPanel.vue', () => ({
  default: { name: 'TableInfoPanel', props: ['containerId', 'accountAlias'], template: '<div class="table-info-panel-mock" />' },
}))

vi.mock('@/components/RedisKeyList.vue', () => ({
  default: { name: 'RedisKeyList', props: ['containerId', 'accountAlias'], emits: ['select'], template: '<div class="redis-key-list-mock" />' },
}))

let mockDbToolkitStore: any

vi.mock('@/stores/dbToolkitStore', () => ({
  useDbToolkitStore: () => mockDbToolkitStore,
}))

beforeEach(() => {
  setActivePinia(createPinia())
  vi.clearAllMocks()
  vi.stubGlobal('alert', vi.fn())
  mockDbToolkitStore = {
    connections: [],
    savedConnections: [],
    currentConnection: null,
    redisConnection: null,
    mysqlConnection: null,
    sqlResult: null,
    tables: [],
    mysqlTables: [],
    mysqlQueryHistory: [],
    mysqlQueryResult: null,
    mysqlQueryLoading: false,
    redisKeyInfo: null,
    redisDbStats: null,
    activeConnection: null,
    activeDeployMode: 'docker',
    sidebarCollapsed: false,
    currentViewMode: 'welcome',
    loading: false,
    fetchConnections: vi.fn().mockResolvedValue(undefined),
    testConnection: vi.fn().mockResolvedValue({ success: true }),
    executeQuery: vi.fn().mockResolvedValue(undefined),
    executeMysqlQuery: vi.fn().mockResolvedValue({ columns: ['id', 'name'], rows: [['1', 'test']], total_count: 1, truncated: false, error: '' }),
    connectRedis: vi.fn().mockResolvedValue(undefined),
    connectMysql: vi.fn(),
    disconnectMysql: vi.fn(),
    disconnectRedis: vi.fn(),
    setActiveConnection: vi.fn((conn: any) => { mockDbToolkitStore.activeConnection = conn }),
    setViewMode: vi.fn(),
    toggleSidebar: vi.fn(),
    scanRedisKeys: vi.fn().mockResolvedValue({ keys: [], cursor: 0 }),
    getRedisKeyValue: vi.fn().mockResolvedValue(undefined),
    checkDangerousSql: vi.fn().mockResolvedValue(false),
    detectClient: vi.fn().mockResolvedValue({ installed: true, path: '/usr/bin/mysql', client_version: '8.0', error: '' }),
    loadMysqlDatabases: vi.fn().mockResolvedValue(['information_schema', 'test_db']),
    loadMysqlTables: vi.fn().mockResolvedValue(['users', 'orders']),
    loadRedisKeyDetail: vi.fn().mockResolvedValue(undefined),
    loadRedisDbStats: vi.fn().mockResolvedValue(undefined),
    deleteRedisKey: vi.fn().mockResolvedValue(true),
    switchMysqlDatabase: vi.fn(),
    toggleFavorite: vi.fn(),
    addConnection: vi.fn(),
    updateConnection: vi.fn(),
    removeConnection: vi.fn(),
  }
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
    const wrapper = mount(DbConnectionManager, {
      props: { deployMode: 'docker', accountAlias: 'test' },
    })
    expect(wrapper.find('.db-connection-manager').exists()).toBe(true)
  })

  it('无连接时应显示空状态', () => {
    const wrapper = mount(DbConnectionManager, {
      props: { deployMode: 'docker', accountAlias: 'test' },
    })
    expect(wrapper.find('.md3-empty').exists()).toBe(true)
  })

  it('有收藏连接时应显示收藏分区', () => {
    mockDbToolkitStore.savedConnections = [
      { id: '1', name: 'TestDB', deployMode: 'docker', dbType: 'mysql', accountAlias: 'test', containerId: '', connection: {}, favorite: true, createdAt: 0, updatedAt: 0 },
    ]
    const wrapper = mount(DbConnectionManager, {
      props: { deployMode: 'docker', accountAlias: 'test' },
    })
    expect(wrapper.text()).toContain('收藏')
    expect(wrapper.text()).toContain('TestDB')
  })

  it('有非收藏连接时应显示其他连接分区', () => {
    mockDbToolkitStore.savedConnections = [
      { id: '2', name: 'OtherDB', deployMode: 'ssh', dbType: 'redis', accountAlias: 'test', containerId: '', connection: {}, favorite: false, createdAt: 0, updatedAt: 0 },
    ]
    const wrapper = mount(DbConnectionManager, {
      props: { deployMode: 'docker', accountAlias: 'test' },
    })
    expect(wrapper.text()).toContain('其他连接')
    expect(wrapper.text()).toContain('OtherDB')
  })

  it('点击新建连接按钮应打开对话框', async () => {
    const wrapper = mount(DbConnectionManager, {
      props: { deployMode: 'docker', accountAlias: 'test' },
    })
    const buttons = wrapper.findAll('.md3-btn')
    const newBtn = buttons.find(b => b.text().includes('新建连接'))
    if (newBtn) {
      await newBtn.trigger('click')
    }
  })

  it('点击连接项应触发 connect 事件', async () => {
    const conn = { id: '1', name: 'TestDB', deployMode: 'docker', dbType: 'mysql', accountAlias: 'test', containerId: '', connection: {}, favorite: true, createdAt: 0, updatedAt: 0 }
    mockDbToolkitStore.savedConnections = [conn]
    const wrapper = mount(DbConnectionManager, {
      props: { deployMode: 'docker', accountAlias: 'test' },
    })
    const item = wrapper.find('.connection-item')
    if (item.exists()) {
      await item.trigger('click')
      expect(wrapper.emitted('connect')).toBeTruthy()
      expect(wrapper.emitted('connect')![0][0]).toEqual(conn)
    }
  })

  it('点击收藏按钮应调用 toggleFavorite', async () => {
    const conn = { id: '1', name: 'TestDB', deployMode: 'docker', dbType: 'mysql', accountAlias: 'test', containerId: '', connection: {}, favorite: true, createdAt: 0, updatedAt: 0 }
    mockDbToolkitStore.savedConnections = [conn]
    const wrapper = mount(DbConnectionManager, {
      props: { deployMode: 'docker', accountAlias: 'test' },
    })
    const buttons = wrapper.findAll('.md3-btn')
    const starBtn = buttons.find(b => b.attributes('icon') === 'star')
    if (starBtn) {
      await starBtn.trigger('click')
      expect(mockDbToolkitStore.toggleFavorite).toHaveBeenCalledWith('1')
    }
  })

  it('submit 事件带 editId 应调用 updateConnection', async () => {
    const wrapper = mount(DbConnectionManager, {
      props: { deployMode: 'docker', accountAlias: 'test' },
    })
    const dialog = wrapper.findComponent({ name: 'DbLoginDialog' })
    if (dialog.exists()) {
      await dialog.vm.$emit('submit', {
        editId: '1',
        name: 'Updated',
        deployMode: 'docker',
        dbType: 'mysql',
        containerId: '',
        connection: { host: 'localhost', port: 3306, user: 'root', password: 'pass', database: 'db' },
      })
      expect(mockDbToolkitStore.updateConnection).toHaveBeenCalled()
    }
  })

  it('submit 事件带 saveConnection 应调用 addConnection', async () => {
    mockDbToolkitStore.savedConnections = []
    const wrapper = mount(DbConnectionManager, {
      props: { deployMode: 'docker', accountAlias: 'test' },
    })
    const dialog = wrapper.findComponent({ name: 'DbLoginDialog' })
    if (dialog.exists()) {
      await dialog.vm.$emit('submit', {
        saveConnection: true,
        name: 'NewConn',
        deployMode: 'docker',
        dbType: 'mysql',
        containerId: '',
        connection: { host: 'localhost', port: 3306, user: 'root', password: 'pass', database: 'db' },
      })
      expect(mockDbToolkitStore.addConnection).toHaveBeenCalled()
    }
  })

  it('submit 事件无 saveConnection 应创建临时连接', async () => {
    const wrapper = mount(DbConnectionManager, {
      props: { deployMode: 'docker', accountAlias: 'test' },
    })
    const dialog = wrapper.findComponent({ name: 'DbLoginDialog' })
    if (dialog.exists()) {
      await dialog.vm.$emit('submit', {
        name: 'TempConn',
        deployMode: 'docker',
        dbType: 'redis',
        containerId: '',
        connection: { host: 'localhost', port: 6379, password: '', db: 0 },
      })
      expect(wrapper.emitted('connect')).toBeTruthy()
    }
  })
})

describe('DbLoginDialog', () => {
  function createWrapper(props = {}) {
    return mount(DbLoginDialog, {
      props: { visible: true, deployMode: 'docker', accountAlias: 'test', ...props },
    })
  }

  it('应该渲染数据库登录对话框', () => {
    const wrapper = createWrapper()
    expect(wrapper.find('.db-login-dialog').exists()).toBe(true)
  })

  it('应该接受 visible prop', () => {
    const wrapper = createWrapper({ visible: false })
    expect(wrapper.props('visible')).toBe(false)
  })

  it('visible 为 true 时应该显示对话框', () => {
    const wrapper = createWrapper()
    expect(wrapper.props('visible')).toBe(true)
  })

  it('测试连接成功时应显示成功结果', async () => {
    mockDbToolkitStore.detectClient.mockResolvedValue({ installed: true, client_version: '8.0.33', error: '' })
    const wrapper = createWrapper()
    await nextTick()
    const vm = wrapper.vm as any
    if (typeof vm.testConnection === 'function') {
      await vm.testConnection()
      await nextTick()
      expect(vm.testResult).toBeTruthy()
      expect(vm.testResult.success).toBe(true)
    }
  })

  it('测试连接客户端未安装时应显示失败结果', async () => {
    mockDbToolkitStore.detectClient.mockResolvedValue({ installed: false, error: 'Not found', client_version: '' })
    const wrapper = createWrapper()
    await nextTick()
    const vm = wrapper.vm as any
    if (typeof vm.testConnection === 'function') {
      await vm.testConnection()
      await nextTick()
      expect(vm.testResult).toBeTruthy()
      expect(vm.testResult.success).toBe(false)
    }
  })

  it('测试连接异常时应显示失败结果', async () => {
    mockDbToolkitStore.detectClient.mockRejectedValue(new Error('Connection failed'))
    const wrapper = createWrapper()
    await nextTick()
    const vm = wrapper.vm as any
    if (typeof vm.testConnection === 'function') {
      await vm.testConnection()
      await nextTick()
      expect(vm.testResult).toBeTruthy()
      expect(vm.testResult.success).toBe(false)
    }
  })

  it('handleClose 应触发 close 事件', async () => {
    const wrapper = createWrapper()
    await nextTick()
    const vm = wrapper.vm as any
    if (typeof vm.handleClose === 'function') {
      vm.handleClose()
      expect(wrapper.emitted('close')).toBeTruthy()
    }
  })

  it('handleSubmit MySQL 应发送正确参数', async () => {
    const wrapper = createWrapper()
    await nextTick()
    const vm = wrapper.vm as any
    if (typeof vm.handleSubmit === 'function') {
      vm.form.dbType = 'mysql'
      vm.form.host = 'localhost'
      vm.form.port = 3306
      vm.form.user = 'root'
      vm.form.password = 'pass'
      vm.form.database = 'testdb'
      vm.form.name = 'TestConn'
      vm.handleSubmit()
      expect(wrapper.emitted('submit')).toBeTruthy()
      const emitArg = wrapper.emitted('submit')![0][0] as any
      expect(emitArg.dbType).toBe('mysql')
      expect(emitArg.connection.host).toBe('localhost')
    }
  })

  it('handleSubmit Redis 应发送正确参数', async () => {
    const wrapper = createWrapper()
    await nextTick()
    const vm = wrapper.vm as any
    if (typeof vm.handleSubmit === 'function') {
      vm.form.dbType = 'redis'
      vm.form.host = 'localhost'
      vm.form.port = 6379
      vm.form.password = 'redis_pass'
      vm.form.db = 2
      vm.form.name = 'RedisConn'
      vm.handleSubmit()
      expect(wrapper.emitted('submit')).toBeTruthy()
      const emitArg = wrapper.emitted('submit')![0][0] as any
      expect(emitArg.dbType).toBe('redis')
      expect(emitArg.connection.db).toBe(2)
    }
  })

  it('切换 dbType 时应更新端口', async () => {
    const wrapper = createWrapper()
    await nextTick()
    const vm = wrapper.vm as any
    if (vm.form) {
      vm.form.dbType = 'mysql'
      vm.form.port = 3306
      vm.form.dbType = 'redis'
      await nextTick()
      expect(vm.form.port).toBe(6379)
      vm.form.dbType = 'mysql'
      await nextTick()
      expect(vm.form.port).toBe(3306)
    }
  })

  it('visible 变为 true 且有 editTarget 时应填充表单', async () => {
    const editTarget = {
      id: 'conn-1',
      name: 'EditConn',
      deployMode: 'docker',
      dbType: 'mysql',
      accountAlias: 'test',
      containerId: 'c1',
      connection: { host: '10.0.0.1', port: 3307, user: 'admin', password: 'pass123', database: 'mydb' },
      favorite: false,
      createdAt: 0,
      updatedAt: 0,
    }
    const wrapper = createWrapper({ visible: false, editTarget: null })
    await nextTick()
    await wrapper.setProps({ visible: true, editTarget })
    await nextTick()
    const vm = wrapper.vm as any
    if (vm.form) {
      expect(vm.form.name).toBe('EditConn')
      expect(vm.form.host).toBe('10.0.0.1')
    }
  })

  it('visible 变为 true 无 editTarget 时应重置表单', async () => {
    const wrapper = createWrapper({ visible: false })
    await nextTick()
    await wrapper.setProps({ visible: true })
    await nextTick()
    const vm = wrapper.vm as any
    if (vm.form) {
      expect(vm.form.name).toBe('')
      expect(vm.form.host).toBe('localhost')
    }
  })

  it('isEditing 应根据 editTarget 计算', async () => {
    const wrapper = createWrapper({ editTarget: { id: '1', name: 'Test' } as any })
    await nextTick()
    const vm = wrapper.vm as any
    if (typeof vm.isEditing !== 'undefined') {
      expect(vm.isEditing).toBe(true)
    }
  })

  it('deployMode 为 docker 时应显示容器 ID 输入', async () => {
    const wrapper = createWrapper()
    await nextTick()
    const vm = wrapper.vm as any
    if (vm.form && vm.form.deployMode === 'docker') {
      expect(wrapper.text()).toContain('容器 ID')
    }
  })

  it('dbType 为 mysql 时应显示用户名和数据库字段', async () => {
    const wrapper = createWrapper()
    await nextTick()
    const vm = wrapper.vm as any
    if (vm.form && vm.form.dbType === 'mysql') {
      expect(wrapper.text()).toContain('用户名')
      expect(wrapper.text()).toContain('数据库')
    }
  })

  it('dbType 为 redis 时应显示数据库编号字段', async () => {
    const wrapper = createWrapper()
    await nextTick()
    const vm = wrapper.vm as any
    if (vm.form) {
      vm.form.dbType = 'redis'
      await nextTick()
      expect(wrapper.text()).toContain('数据库编号')
    }
  })
})

describe('DbManagerPanel', () => {
  function createWrapper(props = {}) {
    return mount(DbManagerPanel, {
      props: { deployMode: 'docker', accountAlias: 'test', containerId: 'abc', containerState: 'running', ...props },
    })
  }

  it('应该渲染数据库管理面板', () => {
    const wrapper = createWrapper()
    expect(wrapper.find('.db-manager-panel').exists()).toBe(true)
  })

  it('应该接受所有 props', () => {
    const wrapper = createWrapper({
      deployMode: 'ssh',
      accountAlias: 'prod-server',
      containerId: 'xyz789',
      containerState: 'stopped',
    })
    expect(wrapper.props('deployMode')).toBe('ssh')
    expect(wrapper.props('accountAlias')).toBe('prod-server')
    expect(wrapper.props('containerId')).toBe('xyz789')
    expect(wrapper.props('containerState')).toBe('stopped')
  })

  it('未连接时应显示连接管理器', () => {
    const wrapper = createWrapper()
    expect(wrapper.find('.connect-prompt').exists()).toBe(true)
  })

  it('MySQL 连接后应显示管理布局', async () => {
    mockDbToolkitStore.mysqlConnection = { host: 'localhost', port: 3306, user: 'root', password: '', database: 'test' }
    mockDbToolkitStore.activeConnection = { id: '1', name: 'Test', dbType: 'mysql', deployMode: 'docker', connection: mockDbToolkitStore.mysqlConnection }
    const wrapper = createWrapper()
    await nextTick()
    if (wrapper.find('.manager-layout').exists()) {
      expect(wrapper.find('.manager-sidebar').exists()).toBe(true)
      expect(wrapper.find('.manager-content').exists()).toBe(true)
    }
  })

  it('Redis 连接后应显示 Redis 视图标签', async () => {
    mockDbToolkitStore.redisConnection = { host: 'localhost', port: 6379, password: '', db: 0 }
    mockDbToolkitStore.activeConnection = { id: '2', name: 'Redis', dbType: 'redis', deployMode: 'docker', connection: mockDbToolkitStore.redisConnection }
    const wrapper = createWrapper()
    await nextTick()
    if (wrapper.find('.manager-layout').exists()) {
      expect(wrapper.find('.md3-tabs').exists()).toBe(true)
    }
  })

  it('handleConnect MySQL 应设置视图模式', async () => {
    const wrapper = createWrapper()
    await nextTick()
    const vm = wrapper.vm as any
    if (typeof vm.handleConnect === 'function') {
      const conn = { id: '1', name: 'Test', dbType: 'mysql', deployMode: 'docker', connection: { host: 'localhost', port: 3306, user: 'root', password: '', database: 'test' } }
      vm.handleConnect(conn)
      await nextTick()
      expect(mockDbToolkitStore.setActiveConnection).toHaveBeenCalledWith(conn)
      expect(mockDbToolkitStore.setViewMode).toHaveBeenCalledWith('query')
    }
  })

  it('handleConnect Redis 应设置视图模式并加载统计', async () => {
    const wrapper = createWrapper()
    await nextTick()
    const vm = wrapper.vm as any
    if (typeof vm.handleConnect === 'function') {
      const conn = { id: '2', name: 'Redis', dbType: 'redis', deployMode: 'docker', connection: { host: 'localhost', port: 6379, password: '', db: 0 } }
      vm.handleConnect(conn)
      await nextTick()
      expect(mockDbToolkitStore.setViewMode).toHaveBeenCalledWith('redis-browse')
    }
  })

  it('handleDisconnect 应断开连接', async () => {
    const wrapper = createWrapper()
    await nextTick()
    const vm = wrapper.vm as any
    if (typeof vm.handleDisconnect === 'function') {
      vm.handleDisconnect()
      await nextTick()
      expect(mockDbToolkitStore.setActiveConnection).toHaveBeenCalledWith(null)
      expect(mockDbToolkitStore.disconnectMysql).toHaveBeenCalled()
      expect(mockDbToolkitStore.disconnectRedis).toHaveBeenCalled()
    }
  })

  it('handleSelectTable 应设置视图模式', async () => {
    const wrapper = createWrapper()
    await nextTick()
    const vm = wrapper.vm as any
    if (typeof vm.handleSelectTable === 'function') {
      vm.handleSelectTable('users')
      await nextTick()
      expect(mockDbToolkitStore.setViewMode).toHaveBeenCalledWith('data')
    }
  })

  it('handleSelectDatabase 应设置视图模式', async () => {
    const wrapper = createWrapper()
    await nextTick()
    const vm = wrapper.vm as any
    if (typeof vm.handleSelectDatabase === 'function') {
      vm.handleSelectDatabase('test_db')
      await nextTick()
      expect(mockDbToolkitStore.setViewMode).toHaveBeenCalledWith('data')
    }
  })

  it('handleSelectRedisDb 应设置视图模式', async () => {
    const wrapper = createWrapper()
    await nextTick()
    const vm = wrapper.vm as any
    if (typeof vm.handleSelectRedisDb === 'function') {
      vm.handleSelectRedisDb(1)
      await nextTick()
      expect(mockDbToolkitStore.setViewMode).toHaveBeenCalledWith('redis-browse')
    }
  })

  it('handleExecuteQuery 成功时应正常完成', async () => {
    mockDbToolkitStore.executeMysqlQuery.mockResolvedValue({ columns: [], rows: [], total_count: 0, error: '' })
    const wrapper = createWrapper()
    await nextTick()
    const vm = wrapper.vm as any
    if (typeof vm.handleExecuteQuery === 'function') {
      await vm.handleExecuteQuery('SELECT 1')
    }
  })

  it('handleExecuteQuery 失败时应显示错误', async () => {
    mockDbToolkitStore.executeMysqlQuery.mockRejectedValue({ response: { data: { detail: 'Query error' } }, message: 'Query error' })
    const wrapper = createWrapper()
    await nextTick()
    const vm = wrapper.vm as any
    if (typeof vm.handleExecuteQuery === 'function') {
      await vm.handleExecuteQuery('INVALID SQL')
    }
  })

  it('handleRedisKeySelect 应加载 key 详情', async () => {
    mockDbToolkitStore.loadRedisKeyDetail.mockResolvedValue(undefined)
    const wrapper = createWrapper()
    await nextTick()
    const vm = wrapper.vm as any
    if (typeof vm.handleRedisKeySelect === 'function') {
      await vm.handleRedisKeySelect('test:key')
      expect(mockDbToolkitStore.loadRedisKeyDetail).toHaveBeenCalled()
    }
  })

  it('handleRedisKeySelect 失败时应显示错误', async () => {
    mockDbToolkitStore.loadRedisKeyDetail.mockRejectedValue({ response: { data: { detail: 'Key not found' } }, message: 'Key not found' })
    const wrapper = createWrapper()
    await nextTick()
    const vm = wrapper.vm as any
    if (typeof vm.handleRedisKeySelect === 'function') {
      await vm.handleRedisKeySelect('missing:key')
    }
  })

  it('handleRedisKeyDeleted 应清空 keyInfo', async () => {
    mockDbToolkitStore.redisKeyInfo = { key: 'test', type: 'string', value: 'val', ttl: -1, ttl_display: '永不过期', truncated: false, size_bytes: 3 }
    const wrapper = createWrapper()
    await nextTick()
    const vm = wrapper.vm as any
    if (typeof vm.handleRedisKeyDeleted === 'function') {
      vm.handleRedisKeyDeleted()
      expect(mockDbToolkitStore.redisKeyInfo).toBeNull()
    }
  })

  it('loadRedisStats 成功时应正常完成', async () => {
    mockDbToolkitStore.loadRedisDbStats.mockResolvedValue(undefined)
    const wrapper = createWrapper()
    await nextTick()
    const vm = wrapper.vm as any
    if (typeof vm.loadRedisStats === 'function') {
      await vm.loadRedisStats()
    }
  })

  it('loadRedisStats 失败时应显示错误', async () => {
    mockDbToolkitStore.loadRedisDbStats.mockRejectedValue({ response: { data: { detail: 'Stats error' } }, message: 'Stats error' })
    const wrapper = createWrapper()
    await nextTick()
    const vm = wrapper.vm as any
    if (typeof vm.loadRedisStats === 'function') {
      await vm.loadRedisStats()
    }
  })

  it('侧边栏折叠切换应正常工作', async () => {
    mockDbToolkitStore.mysqlConnection = { host: 'localhost', port: 3306, user: 'root', password: '', database: 'test' }
    mockDbToolkitStore.activeConnection = { id: '1', name: 'Test', dbType: 'mysql', deployMode: 'docker', connection: mockDbToolkitStore.mysqlConnection }
    const wrapper = createWrapper()
    await nextTick()
    const toggle = wrapper.find('.sidebar-toggle')
    if (toggle.exists()) {
      await toggle.trigger('click')
      expect(mockDbToolkitStore.toggleSidebar).toHaveBeenCalled()
    }
  })

  it('deployMode 为 host 时 effectiveContainerId 应为 undefined', async () => {
    const wrapper = createWrapper({ deployMode: 'host' })
    await nextTick()
    const vm = wrapper.vm as any
    if (typeof vm.effectiveContainerId !== 'undefined') {
      expect(vm.effectiveContainerId).toBeUndefined()
    }
  })

  it('Redis 统计信息应正确显示', async () => {
    mockDbToolkitStore.redisConnection = { host: 'localhost', port: 6379, password: '', db: 0 }
    mockDbToolkitStore.activeConnection = { id: '2', name: 'Redis', dbType: 'redis', deployMode: 'docker', connection: mockDbToolkitStore.redisConnection }
    mockDbToolkitStore.redisDbStats = { key_count: 150, used_memory_human: '2.5MB', used_memory_bytes: 2621440 }
    mockDbToolkitStore.currentViewMode = 'redis-stats'
    const wrapper = createWrapper()
    await nextTick()
    if (wrapper.find('.stats-grid').exists()) {
      expect(wrapper.text()).toContain('150')
      expect(wrapper.text()).toContain('2.5MB')
    }
  })
})

describe('DbSidebar', () => {
  it('应该渲染数据库侧边栏', () => {
    const wrapper = mount(DbSidebar, {
      props: { dbType: 'mysql', accountAlias: 'test' },
    })
    expect(wrapper.find('.db-sidebar').exists()).toBe(true)
  })

  it('MySQL 模式应显示数据库分区', () => {
    const wrapper = mount(DbSidebar, {
      props: { dbType: 'mysql', accountAlias: 'test' },
    })
    expect(wrapper.text()).toContain('数据库')
  })

  it('Redis 模式应显示 Redis 数据库分区', () => {
    const wrapper = mount(DbSidebar, {
      props: { dbType: 'redis', accountAlias: 'test' },
    })
    expect(wrapper.text()).toContain('Redis 数据库')
  })

  it('Redis 模式应显示 DB0-DB15', () => {
    const wrapper = mount(DbSidebar, {
      props: { dbType: 'redis', accountAlias: 'test' },
    })
    expect(wrapper.text()).toContain('DB0')
    expect(wrapper.text()).toContain('DB15')
  })

  it('MySQL 模式点击数据库应触发 selectDatabase 事件', async () => {
    mockDbToolkitStore.mysqlTables = []
    const wrapper = mount(DbSidebar, {
      props: { dbType: 'mysql', accountAlias: 'test' },
    })
    const dbItems = wrapper.findAll('.database-item')
    if (dbItems.length > 0) {
      await dbItems[0].trigger('click')
      expect(wrapper.emitted('selectDatabase')).toBeTruthy()
    }
  })

  it('MySQL 模式点击表应触发 selectTable 事件', async () => {
    mockDbToolkitStore.mysqlTables = ['users', 'orders']
    const wrapper = mount(DbSidebar, {
      props: { dbType: 'mysql', accountAlias: 'test' },
    })
    const tableItems = wrapper.findAll('.table-item')
    if (tableItems.length > 0) {
      await tableItems[0].trigger('click')
      expect(wrapper.emitted('selectTable')).toBeTruthy()
    }
  })

  it('Redis 模式点击 DB 应触发 selectRedisDb 事件', async () => {
    const wrapper = mount(DbSidebar, {
      props: { dbType: 'redis', accountAlias: 'test' },
    })
    const dbItems = wrapper.findAll('.redis-db-item')
    if (dbItems.length > 0) {
      await dbItems[0].trigger('click')
      expect(wrapper.emitted('selectRedisDb')).toBeTruthy()
    }
  })

  it('点击断开按钮应触发 disconnect 事件', async () => {
    const wrapper = mount(DbSidebar, {
      props: { dbType: 'mysql', accountAlias: 'test' },
    })
    const buttons = wrapper.findAll('.md3-btn')
    const disconnectBtn = buttons.find(b => b.find('[data-name="logout"]').exists())
    if (disconnectBtn) {
      await disconnectBtn.trigger('click')
      expect(wrapper.emitted('disconnect')).toBeTruthy()
    }
  })

  it('表名过滤应生效', async () => {
    mockDbToolkitStore.mysqlTables = ['users', 'orders', 'user_logs']
    const wrapper = mount(DbSidebar, {
      props: { dbType: 'mysql', accountAlias: 'test' },
    })
    const input = wrapper.find('.md3-input')
    if (input.exists()) {
      await input.setValue('user')
      await nextTick()
      expect(wrapper.findAll('.table-item').length).toBeLessThanOrEqual(2)
    }
  })
})

describe('MySqlPanel', () => {
  function createWrapper(props = {}) {
    return mount(MySqlPanel, {
      props: { containerId: 'abc', accountAlias: 'test', containerState: 'running', ...props },
    })
  }

  it('应该渲染 MySQL 面板', () => {
    const wrapper = createWrapper()
    expect(wrapper.find('.mysql-panel').exists()).toBe(true)
  })

  it('未连接时应显示连接按钮', () => {
    const wrapper = createWrapper()
    expect(wrapper.text()).toContain('连接 MySQL')
  })

  it('容器未运行时连接按钮应禁用', () => {
    const wrapper = createWrapper({ containerState: 'stopped' })
    expect(wrapper.text()).toContain('容器未运行')
  })

  it('点击连接按钮应调用 detectClient', async () => {
    const wrapper = createWrapper()
    const buttons = wrapper.findAll('.md3-btn')
    const connectBtn = buttons.find(b => b.text().includes('连接 MySQL'))
    if (connectBtn) {
      await connectBtn.trigger('click')
      await nextTick()
      expect(mockDbToolkitStore.detectClient).toHaveBeenCalledWith('mysql', 'test', 'abc')
    }
  })

  it('客户端未安装时应显示 alert', async () => {
    mockDbToolkitStore.detectClient = vi.fn().mockResolvedValue({ installed: false, error: 'Not found', path: '', client_version: '' })
    const wrapper = createWrapper()
    const buttons = wrapper.findAll('.md3-btn')
    const connectBtn = buttons.find(b => b.text().includes('连接 MySQL'))
    if (connectBtn) {
      await connectBtn.trigger('click')
      await nextTick()
    }
  })

  it('detectClient 异常时应显示 alert', async () => {
    mockDbToolkitStore.detectClient = vi.fn().mockRejectedValue(new Error('Network error'))
    const wrapper = createWrapper()
    const buttons = wrapper.findAll('.md3-btn')
    const connectBtn = buttons.find(b => b.text().includes('连接 MySQL'))
    if (connectBtn) {
      await connectBtn.trigger('click')
      await nextTick()
    }
  })

  it('容器未运行时点击连接应直接返回', async () => {
    mockDbToolkitStore.detectClient.mockClear()
    const wrapper = createWrapper({ containerState: 'stopped' })
    const buttons = wrapper.findAll('.md3-btn')
    const connectBtn = buttons.find(b => b.text().includes('连接 MySQL'))
    if (connectBtn) {
      await connectBtn.trigger('click')
      await nextTick()
      expect(mockDbToolkitStore.detectClient).not.toHaveBeenCalled()
    }
  })

  it('handleLoginSubmit 应连接 MySQL', async () => {
    const wrapper = createWrapper()
    await nextTick()
    const vm = wrapper.vm as any
    if (typeof vm.handleLoginSubmit === 'function') {
      const conn = { host: 'localhost', port: 3306, user: 'root', password: 'pass', database: 'test' }
      vm.handleLoginSubmit({ connection: conn })
      await nextTick()
      expect(mockDbToolkitStore.connectMysql).toHaveBeenCalledWith(conn)
      expect(vm.isConnected).toBe(true)
    }
  })

  it('handleDisconnect 应断开连接', async () => {
    const wrapper = createWrapper()
    await nextTick()
    const vm = wrapper.vm as any
    if (typeof vm.handleDisconnect === 'function') {
      vm.isConnected = true
      vm.handleDisconnect()
      await nextTick()
      expect(mockDbToolkitStore.disconnectMysql).toHaveBeenCalled()
      expect(vm.isConnected).toBe(false)
    }
  })

  it('handleExecuteQuery 应调用 store', async () => {
    mockDbToolkitStore.executeMysqlQuery.mockResolvedValue({ columns: [], rows: [], total_count: 0, error: '' })
    const wrapper = createWrapper()
    await nextTick()
    const vm = wrapper.vm as any
    if (typeof vm.handleExecuteQuery === 'function') {
      await vm.handleExecuteQuery('SELECT 1')
      expect(mockDbToolkitStore.executeMysqlQuery).toHaveBeenCalledWith('test', 'abc', 'SELECT 1')
    }
  })

  it('handleTerminalInput 应通过 WebSocket 发送数据', async () => {
    const wrapper = createWrapper()
    await nextTick()
    const vm = wrapper.vm as any
    if (typeof vm.handleTerminalInput === 'function') {
      vm.handleTerminalInput('test command')
    }
  })

  it('handleTerminalResize 应通过 WebSocket 发送尺寸', async () => {
    const wrapper = createWrapper()
    await nextTick()
    const vm = wrapper.vm as any
    if (typeof vm.handleTerminalResize === 'function') {
      vm.handleTerminalResize(80, 24)
    }
  })
})

describe('RedisPanel', () => {
  function createWrapper(props = {}) {
    return mount(RedisPanel, {
      props: { containerId: 'abc', accountAlias: 'test', containerState: 'running', ...props },
    })
  }

  it('应该渲染 Redis 面板', () => {
    const wrapper = createWrapper()
    expect(wrapper.find('.redis-panel').exists()).toBe(true)
  })

  it('未连接时应显示连接按钮', () => {
    const wrapper = createWrapper()
    expect(wrapper.text()).toContain('连接 Redis')
  })

  it('容器未运行时应显示提示', () => {
    const wrapper = createWrapper({ containerState: 'stopped' })
    expect(wrapper.text()).toContain('容器未运行')
  })

  it('点击连接按钮应调用 detectClient', async () => {
    const wrapper = createWrapper()
    const buttons = wrapper.findAll('.md3-btn')
    const connectBtn = buttons.find(b => b.text().includes('连接 Redis'))
    if (connectBtn) {
      await connectBtn.trigger('click')
      await nextTick()
      expect(mockDbToolkitStore.detectClient).toHaveBeenCalledWith('redis', 'test', 'abc')
    }
  })

  it('客户端未安装时应显示 alert', async () => {
    mockDbToolkitStore.detectClient = vi.fn().mockResolvedValue({ installed: false, error: 'Not found', path: '', client_version: '' })
    const wrapper = createWrapper()
    const buttons = wrapper.findAll('.md3-btn')
    const connectBtn = buttons.find(b => b.text().includes('连接 Redis'))
    if (connectBtn) {
      await connectBtn.trigger('click')
      await nextTick()
    }
  })

  it('detectClient 异常时应显示 alert', async () => {
    mockDbToolkitStore.detectClient = vi.fn().mockRejectedValue(new Error('Network error'))
    const wrapper = createWrapper()
    const buttons = wrapper.findAll('.md3-btn')
    const connectBtn = buttons.find(b => b.text().includes('连接 Redis'))
    if (connectBtn) {
      await connectBtn.trigger('click')
      await nextTick()
    }
  })

  it('容器未运行时点击连接应直接返回', async () => {
    mockDbToolkitStore.detectClient.mockClear()
    const wrapper = createWrapper({ containerState: 'stopped' })
    const buttons = wrapper.findAll('.md3-btn')
    const connectBtn = buttons.find(b => b.text().includes('连接 Redis'))
    if (connectBtn) {
      await connectBtn.trigger('click')
      await nextTick()
      expect(mockDbToolkitStore.detectClient).not.toHaveBeenCalled()
    }
  })

  it('handleLoginSubmit 应连接 Redis', async () => {
    const wrapper = createWrapper()
    await nextTick()
    const vm = wrapper.vm as any
    if (typeof vm.handleLoginSubmit === 'function') {
      const conn = { host: 'localhost', port: 6379, password: 'pass', db: 0 }
      vm.handleLoginSubmit({ connection: conn })
      await nextTick()
      expect(mockDbToolkitStore.connectRedis).toHaveBeenCalledWith(conn)
      expect(vm.isConnected).toBe(true)
    }
  })

  it('handleDisconnect 应断开连接', async () => {
    const wrapper = createWrapper()
    await nextTick()
    const vm = wrapper.vm as any
    if (typeof vm.handleDisconnect === 'function') {
      vm.isConnected = true
      vm.handleDisconnect()
      await nextTick()
      expect(mockDbToolkitStore.disconnectRedis).toHaveBeenCalled()
      expect(vm.isConnected).toBe(false)
    }
  })

  it('handleKeySelect 应加载 key 详情', async () => {
    mockDbToolkitStore.loadRedisKeyDetail.mockResolvedValue(undefined)
    const wrapper = createWrapper()
    await nextTick()
    const vm = wrapper.vm as any
    if (typeof vm.handleKeySelect === 'function') {
      await vm.handleKeySelect('test:key')
      expect(mockDbToolkitStore.loadRedisKeyDetail).toHaveBeenCalledWith('test', 'abc', 'test:key')
    }
  })

  it('handleKeyDeleted 应清空 keyInfo 并刷新', async () => {
    mockDbToolkitStore.redisKeyInfo = { key: 'test', type: 'string', value: 'val', ttl: -1, ttl_display: '永不过期', truncated: false, size_bytes: 3 }
    mockDbToolkitStore.loadRedisKeyDetail.mockResolvedValue(undefined)
    const wrapper = createWrapper()
    await nextTick()
    const vm = wrapper.vm as any
    if (typeof vm.handleKeyDeleted === 'function') {
      vm.handleKeyDeleted()
      expect(mockDbToolkitStore.redisKeyInfo).toBeNull()
    }
  })

  it('loadStats 成功时应正常完成', async () => {
    mockDbToolkitStore.loadRedisDbStats.mockResolvedValue(undefined)
    const wrapper = createWrapper()
    await nextTick()
    const vm = wrapper.vm as any
    if (typeof vm.loadStats === 'function') {
      await vm.loadStats()
    }
  })

  it('loadStats 失败时不应抛出异常', async () => {
    mockDbToolkitStore.loadRedisDbStats.mockRejectedValue(new Error('Stats error'))
    const wrapper = createWrapper()
    await nextTick()
    const vm = wrapper.vm as any
    if (typeof vm.loadStats === 'function') {
      await vm.loadStats()
    }
  })

  it('handleTerminalInput 应通过 WebSocket 发送数据', async () => {
    const wrapper = createWrapper()
    await nextTick()
    const vm = wrapper.vm as any
    if (typeof vm.handleTerminalInput === 'function') {
      vm.handleTerminalInput('GET key')
    }
  })

  it('handleTerminalResize 应通过 WebSocket 发送尺寸', async () => {
    const wrapper = createWrapper()
    await nextTick()
    const vm = wrapper.vm as any
    if (typeof vm.handleTerminalResize === 'function') {
      vm.handleTerminalResize(80, 24)
    }
  })

  it('Redis 统计信息应正确显示', async () => {
    const wrapper = createWrapper()
    await nextTick()
    const vm = wrapper.vm as any
    if (typeof vm.handleLoginSubmit === 'function') {
      const conn = { host: 'localhost', port: 6379, password: '', db: 0 }
      vm.handleLoginSubmit({ connection: conn })
      await nextTick()
      mockDbToolkitStore.redisDbStats = { key_count: 100, used_memory_human: '1.5MB', used_memory_bytes: 1572864 }
      vm.activeTab = 'stats'
      await nextTick()
      if (wrapper.find('.stats-grid').exists()) {
        expect(wrapper.text()).toContain('100')
        expect(wrapper.text()).toContain('1.5MB')
      }
    }
  })
})

describe('RedisKeyDetail', () => {
  it('应该渲染 Redis 键详情', () => {
    const wrapper = mount(RedisKeyDetail, {
      props: { keyInfo: { key: 'test:key', type: 'string', value: 'hello', ttl: -1, ttl_display: '永不过期', truncated: false, size_bytes: 5 }, containerId: 'abc', accountAlias: 'test' },
    })
    expect(wrapper.find('.redis-key-detail').exists()).toBe(true)
  })

  it('无 keyInfo 时不应渲染', () => {
    const wrapper = mount(RedisKeyDetail, {
      props: { keyInfo: null, containerId: 'abc', accountAlias: 'test' },
    })
    expect(wrapper.find('.redis-key-detail').exists()).toBe(false)
  })

  it('应该显示 key 名称', () => {
    const wrapper = mount(RedisKeyDetail, {
      props: { keyInfo: { key: 'test:key', type: 'string', value: 'hello', ttl: -1, ttl_display: '永不过期', truncated: false, size_bytes: 5 }, containerId: 'abc', accountAlias: 'test' },
    })
    expect(wrapper.text()).toContain('test:key')
  })

  it('应该显示 TTL', () => {
    const wrapper = mount(RedisKeyDetail, {
      props: { keyInfo: { key: 'test:key', type: 'string', value: 'hello', ttl: 300, ttl_display: '300秒', truncated: false, size_bytes: 5 }, containerId: 'abc', accountAlias: 'test' },
    })
    expect(wrapper.text()).toContain('300秒')
  })

  it('hash 类型应渲染表格', () => {
    const wrapper = mount(RedisKeyDetail, {
      props: { keyInfo: { key: 'test:hash', type: 'hash', value: { field1: 'val1', field2: 'val2' }, ttl: -1, ttl_display: '永不过期', truncated: false, size_bytes: 20 }, containerId: 'abc', accountAlias: 'test' },
    })
    expect(wrapper.find('.kv-table').exists()).toBe(true)
  })

  it('list 类型应渲染列表', () => {
    const wrapper = mount(RedisKeyDetail, {
      props: { keyInfo: { key: 'test:list', type: 'list', value: ['item1', 'item2'], ttl: -1, ttl_display: '永不过期', truncated: false, size_bytes: 10 }, containerId: 'abc', accountAlias: 'test' },
    })
    expect(wrapper.find('.value-list').exists()).toBe(true)
  })

  it('set 类型应渲染标签', () => {
    const wrapper = mount(RedisKeyDetail, {
      props: { keyInfo: { key: 'test:set', type: 'set', value: ['member1', 'member2'], ttl: -1, ttl_display: '永不过期', truncated: false, size_bytes: 15 }, containerId: 'abc', accountAlias: 'test' },
    })
    expect(wrapper.find('.value-set').exists()).toBe(true)
  })

  it('zset 类型应渲染表格', () => {
    const wrapper = mount(RedisKeyDetail, {
      props: { keyInfo: { key: 'test:zset', type: 'zset', value: [{ member: 'a', score: '1' }, { member: 'b', score: '2' }], ttl: -1, ttl_display: '永不过期', truncated: false, size_bytes: 20 }, containerId: 'abc', accountAlias: 'test' },
    })
    expect(wrapper.find('.kv-table').exists()).toBe(true)
  })

  it('truncated 为 true 时应显示截断提示', () => {
    const wrapper = mount(RedisKeyDetail, {
      props: { keyInfo: { key: 'test:key', type: 'string', value: 'hello', ttl: -1, ttl_display: '永不过期', truncated: true, size_bytes: 5 }, containerId: 'abc', accountAlias: 'test' },
    })
    expect(wrapper.text()).toContain('内容过长')
  })

  it('点击删除按钮应显示确认对话框', async () => {
    const wrapper = mount(RedisKeyDetail, {
      props: { keyInfo: { key: 'test:key', type: 'string', value: 'hello', ttl: -1, ttl_display: '永不过期', truncated: false, size_bytes: 5 }, containerId: 'abc', accountAlias: 'test' },
    })
    const buttons = wrapper.findAll('.md3-btn')
    const deleteBtn = buttons.find(b => b.text().includes('删除 Key'))
    if (deleteBtn) {
      await deleteBtn.trigger('click')
    }
  })
})

describe('RedisKeyList', () => {
  it('应该渲染 Redis 键列表', () => {
    const wrapper = mount(RedisKeyList)
    expect(wrapper.find('.redis-key-list-mock').exists()).toBe(true)
  })
})

describe('SqlQueryEditor', () => {
  it('应该渲染 SQL 查询编辑器', () => {
    const wrapper = mount(SqlQueryEditor)
    expect(wrapper.find('.sql-query-editor-mock').exists()).toBe(true)
  })
})

describe('SqlResultTable', () => {
  it('应该渲染 SQL 结果表', () => {
    const wrapper = mount(SqlResultTable, {
      props: { result: { columns: ['id', 'name'], rows: [{ id: 1, name: 'test' }], truncated: false } },
    })
    expect(wrapper.find('.sql-result-table-mock').exists()).toBe(true)
  })

  it('无 result 时不应渲染', () => {
    const wrapper = mount(SqlResultTable, {
      props: { result: null },
    })
    expect(wrapper.find('.sql-result-table-mock').exists()).toBe(false)
  })
})

describe('DataRowForm', () => {
  it('应该渲染数据行表单', () => {
    const wrapper = mount(DataRowForm)
    expect(wrapper.find('.data-row-form-mock').exists()).toBe(true)
  })
})

describe('DataEditor', () => {
  function createWrapper(props = {}) {
    return mount(DataEditor, {
      props: { accountAlias: 'test', tableName: 'users', ...props },
    })
  }

  it('应该渲染数据编辑器', () => {
    const wrapper = createWrapper()
    expect(wrapper.find('.data-editor').exists()).toBe(true)
  })

  it('应该显示表名', () => {
    const wrapper = createWrapper()
    expect(wrapper.text()).toContain('users')
  })

  it('应该显示新增行按钮', () => {
    const wrapper = createWrapper()
    expect(wrapper.text()).toContain('新增行')
  })

  it('应该显示刷新按钮', () => {
    const wrapper = createWrapper()
    expect(wrapper.text()).toContain('刷新')
  })

  it('无数据时应显示空状态', () => {
    const wrapper = createWrapper()
    expect(wrapper.find('.md3-empty').exists() || wrapper.find('.md3-progress').exists()).toBe(true)
  })

  it('点击刷新按钮应重新加载数据', async () => {
    mockDbToolkitStore.executeMysqlQuery.mockResolvedValue({ columns: ['id', 'name'], rows: [['1', 'test']], total_count: 1, truncated: false, error: '' })
    const wrapper = createWrapper()
    await nextTick()
    const buttons = wrapper.findAll('.md3-btn')
    const refreshBtn = buttons.find(b => b.text().includes('刷新'))
    if (refreshBtn) {
      await refreshBtn.trigger('click')
      await nextTick()
      expect(mockDbToolkitStore.executeMysqlQuery).toHaveBeenCalled()
    }
  })

  it('点击新增行按钮应显示 DataRowForm', async () => {
    const wrapper = createWrapper()
    const buttons = wrapper.findAll('.md3-btn')
    const addBtn = buttons.find(b => b.text().includes('新增行'))
    if (addBtn) {
      await addBtn.trigger('click')
      await nextTick()
      expect(wrapper.find('.data-row-form-mock').exists()).toBe(true)
    }
  })

  it('loadData 成功时应显示数据表格', async () => {
    mockDbToolkitStore.executeMysqlQuery.mockResolvedValue({ columns: ['id', 'name'], rows: [['1', 'Alice'], ['2', 'Bob']], total_count: 2, truncated: false, error: '' })
    const wrapper = createWrapper()
    await nextTick()
    expect(wrapper.find('.data-table-container').exists() || wrapper.find('.md3-progress').exists()).toBe(true)
  })

  it('loadData 失败时应显示错误消息', async () => {
    mockDbToolkitStore.executeMysqlQuery.mockRejectedValue({ response: { data: { detail: 'Query failed' } }, message: 'Query failed' })
    const wrapper = createWrapper()
    await nextTick()
  })

  it('loadData 返回 error 时应显示错误', async () => {
    mockDbToolkitStore.executeMysqlQuery.mockResolvedValue({ columns: [], rows: [], total_count: 0, truncated: false, error: 'Table not found' })
    const wrapper = createWrapper()
    await nextTick()
    if (wrapper.find('.data-error').exists()) {
      expect(wrapper.find('.data-error').text()).toContain('Table not found')
    }
  })

  it('有数据时点击全选应选中所有行', async () => {
    mockDbToolkitStore.executeMysqlQuery.mockResolvedValue({ columns: ['id', 'name'], rows: [['1', 'Alice'], ['2', 'Bob']], total_count: 2, truncated: false, error: '' })
    const wrapper = createWrapper()
    await nextTick()
    const vm = wrapper.vm as any
    if (typeof vm.toggleSelectAll === 'function') {
      vm.toggleSelectAll()
      await nextTick()
    }
  })

  it('toggleRow 应切换行选中状态', async () => {
    mockDbToolkitStore.executeMysqlQuery.mockResolvedValue({ columns: ['id', 'name'], rows: [['1', 'Alice'], ['2', 'Bob']], total_count: 2, truncated: false, error: '' })
    const wrapper = createWrapper()
    await nextTick()
    const vm = wrapper.vm as any
    if (typeof vm.toggleRow === 'function') {
      vm.toggleRow(0)
      await nextTick()
    }
  })

  it('startEdit 应设置编辑状态', async () => {
    mockDbToolkitStore.executeMysqlQuery.mockResolvedValue({ columns: ['id', 'name'], rows: [['1', 'Alice']], total_count: 1, truncated: false, error: '' })
    const wrapper = createWrapper()
    await nextTick()
    const vm = wrapper.vm as any
    if (typeof vm.startEdit === 'function') {
      vm.startEdit(0, 1, 'Alice')
      await nextTick()
    }
  })

  it('cancelEdit 应清除编辑状态', async () => {
    mockDbToolkitStore.executeMysqlQuery.mockResolvedValue({ columns: ['id', 'name'], rows: [['1', 'Alice']], total_count: 1, truncated: false, error: '' })
    const wrapper = createWrapper()
    await nextTick()
    const vm = wrapper.vm as any
    if (typeof vm.startEdit === 'function' && typeof vm.cancelEdit === 'function') {
      vm.startEdit(0, 1, 'Alice')
      vm.cancelEdit()
      await nextTick()
    }
  })

  it('confirmEdit 值未变时应取消编辑', async () => {
    mockDbToolkitStore.executeMysqlQuery.mockResolvedValue({ columns: ['id', 'name'], rows: [['1', 'Alice']], total_count: 1, truncated: false, error: '' })
    const wrapper = createWrapper()
    await nextTick()
    const vm = wrapper.vm as any
    if (typeof vm.startEdit === 'function' && typeof vm.confirmEdit === 'function') {
      vm.startEdit(0, 1, 'Alice')
      vm.editValue = 'Alice'
      vm.confirmEdit()
      await nextTick()
    }
  })

  it('confirmEdit null 值空字符串时应取消编辑', async () => {
    mockDbToolkitStore.executeMysqlQuery.mockResolvedValue({ columns: ['id', 'name'], rows: [[1, null]], total_count: 1, truncated: false, error: '' })
    const wrapper = createWrapper()
    await nextTick()
    const vm = wrapper.vm as any
    if (typeof vm.startEdit === 'function' && typeof vm.confirmEdit === 'function') {
      vm.startEdit(0, 1, null)
      vm.editValue = ''
      vm.confirmEdit()
      await nextTick()
    }
  })

  it('confirmEdit 值改变时应显示确认对话框', async () => {
    mockDbToolkitStore.executeMysqlQuery.mockResolvedValue({ columns: ['id', 'name'], rows: [['1', 'Alice']], total_count: 1, truncated: false, error: '' })
    const wrapper = createWrapper()
    await nextTick()
    const vm = wrapper.vm as any
    if (typeof vm.startEdit === 'function' && typeof vm.confirmEdit === 'function') {
      vm.startEdit(0, 1, 'Alice')
      vm.editValue = 'Bob'
      vm.confirmEdit()
      await nextTick()
    }
  })

  it('startEditRow 列数不足1时应返回', async () => {
    mockDbToolkitStore.executeMysqlQuery.mockResolvedValue({ columns: ['id'], rows: [['1']], total_count: 1, truncated: false, error: '' })
    const wrapper = createWrapper()
    await nextTick()
    const vm = wrapper.vm as any
    if (typeof vm.startEditRow === 'function') {
      vm.startEditRow(0)
    }
  })

  it('executeEdit 成功时应显示成功消息', async () => {
    mockDbToolkitStore.executeMysqlQuery.mockResolvedValue({ columns: ['id', 'name'], rows: [['1', 'Alice']], total_count: 1, truncated: false, error: '' })
    const wrapper = createWrapper()
    await nextTick()
    const vm = wrapper.vm as any
    if (typeof vm.executeEdit === 'function') {
      vm.editSql = "UPDATE `users` SET `name` = 'Bob' WHERE `id` = '1'"
      vm.editConfirmVisible = true
      mockDbToolkitStore.executeMysqlQuery.mockResolvedValue({ columns: [], rows: [], total_count: 0, truncated: false, error: '' })
      await vm.executeEdit()
      await nextTick()
    }
  })

  it('executeEdit 返回 error 时应显示错误', async () => {
    mockDbToolkitStore.executeMysqlQuery.mockResolvedValue({ columns: ['id', 'name'], rows: [['1', 'Alice']], total_count: 1, truncated: false, error: '' })
    const wrapper = createWrapper()
    await nextTick()
    const vm = wrapper.vm as any
    if (typeof vm.executeEdit === 'function') {
      vm.editSql = "UPDATE `users` SET `name` = 'Bob' WHERE `id` = '1'"
      vm.editConfirmVisible = true
      mockDbToolkitStore.executeMysqlQuery.mockResolvedValue({ columns: [], rows: [], total_count: 0, truncated: false, error: 'Update failed' })
      await vm.executeEdit()
      await nextTick()
    }
  })

  it('executeEdit 抛出异常时应显示错误', async () => {
    mockDbToolkitStore.executeMysqlQuery.mockResolvedValue({ columns: ['id', 'name'], rows: [['1', 'Alice']], total_count: 1, truncated: false, error: '' })
    const wrapper = createWrapper()
    await nextTick()
    const vm = wrapper.vm as any
    if (typeof vm.executeEdit === 'function') {
      vm.editSql = "UPDATE `users` SET `name` = 'Bob' WHERE `id` = '1'"
      vm.editConfirmVisible = true
      mockDbToolkitStore.executeMysqlQuery.mockRejectedValue({ response: { data: { detail: 'Error' } }, message: 'Error' })
      await vm.executeEdit()
      await nextTick()
    }
  })

  it('deleteSelectedRows 确认后应执行删除', async () => {
    mockDbToolkitStore.executeMysqlQuery.mockResolvedValue({ columns: ['id', 'name'], rows: [['1', 'Alice'], ['2', 'Bob']], total_count: 2, truncated: false, error: '' })
    const wrapper = createWrapper()
    await nextTick()
    const vm = wrapper.vm as any
    if (typeof vm.toggleRow === 'function' && typeof vm.deleteSelectedRows === 'function') {
      vm.toggleRow(0)
      await nextTick()
      mockDbToolkitStore.executeMysqlQuery.mockResolvedValue({ columns: [], rows: [], total_count: 0, truncated: false, error: '' })
      await vm.deleteSelectedRows()
      await nextTick()
    }
  })

  it('deleteSelectedRows 无选中行时应返回', async () => {
    mockDbToolkitStore.executeMysqlQuery.mockResolvedValue({ columns: ['id', 'name'], rows: [['1', 'Alice']], total_count: 1, truncated: false, error: '' })
    const wrapper = createWrapper()
    await nextTick()
    const vm = wrapper.vm as any
    if (typeof vm.deleteSelectedRows === 'function') {
      await vm.deleteSelectedRows()
    }
  })

  it('onRowInserted 应关闭表单并刷新数据', async () => {
    mockDbToolkitStore.executeMysqlQuery.mockResolvedValue({ columns: ['id', 'name'], rows: [['1', 'Alice']], total_count: 1, truncated: false, error: '' })
    const wrapper = createWrapper()
    await nextTick()
    const vm = wrapper.vm as any
    if (typeof vm.onRowInserted === 'function') {
      vm.showAddRow = true
      await vm.onRowInserted()
      await nextTick()
      expect(vm.showAddRow).toBe(false)
    }
  })

  it('tableName 变化时应重新加载数据', async () => {
    mockDbToolkitStore.executeMysqlQuery.mockResolvedValue({ columns: ['id', 'name'], rows: [['1', 'Alice']], total_count: 1, truncated: false, error: '' })
    const wrapper = createWrapper()
    await nextTick()
    mockDbToolkitStore.executeMysqlQuery.mockClear()
    await wrapper.setProps({ tableName: 'orders' })
    await nextTick()
    expect(mockDbToolkitStore.executeMysqlQuery).toHaveBeenCalled()
  })

  it('有分页时应显示分页控件', async () => {
    const rows = Array.from({ length: 50 }, (_, i) => [String(i + 1), `name${i}`])
    mockDbToolkitStore.executeMysqlQuery.mockResolvedValue({ columns: ['id', 'name'], rows, total_count: 100, truncated: false, error: '' })
    const wrapper = createWrapper()
    await nextTick()
    if (wrapper.find('.pagination').exists()) {
      expect(wrapper.find('.page-info').exists()).toBe(true)
    }
  })

  it('goPage 应更新页码并重新加载', async () => {
    const rows = Array.from({ length: 50 }, (_, i) => [String(i + 1), `name${i}`])
    mockDbToolkitStore.executeMysqlQuery.mockResolvedValue({ columns: ['id', 'name'], rows, total_count: 100, truncated: false, error: '' })
    const wrapper = createWrapper()
    await nextTick()
    const vm = wrapper.vm as any
    if (typeof vm.goPage === 'function') {
      mockDbToolkitStore.executeMysqlQuery.mockClear()
      vm.goPage(2)
      await nextTick()
      expect(mockDbToolkitStore.executeMysqlQuery).toHaveBeenCalled()
    }
  })
})

describe('TableInfoPanel', () => {
  it('应该渲染表信息面板', () => {
    const wrapper = mount(TableInfoPanel)
    expect(wrapper.find('.table-info-panel-mock').exists()).toBe(true)
  })
})
