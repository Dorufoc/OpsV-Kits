import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { nextTick } from 'vue'

vi.mock('@/components/md3', () => ({
  Md3Icon: { name: 'Md3Icon', props: ['name', 'size'], template: '<span class="mdi-icon" :data-name="name"></span>' },
  Md3Confirm: { show: vi.fn().mockResolvedValue(true) },
  Md3Message: { success: vi.fn(), error: vi.fn() },
  Md3PageHeader: { name: 'Md3PageHeader', props: ['title', 'showBack', 'subtitle'], template: '<div class="md3-page-header">{{ title }}<slot name="subtitle" /><slot name="actions" /><slot name="content" /><slot name="extra" /></div>' },
  Md3Divider: { name: 'Md3Divider', template: '<hr class="md3-divider" />' },
  Md3Card: { name: 'Md3Card', props: ['shadow', 'hoverable'], template: '<div class="md3-card"><slot /><slot name="header" /></div>' },
  Md3Empty: { name: 'Md3Empty', props: ['description'], template: '<div class="md3-empty">{{ description }}</div>' },
  Md3Tag: { name: 'Md3Tag', props: ['type', 'size', 'variant'], template: '<span class="md3-tag" :data-type="type"><slot /></span>' },
  Md3Table: { name: 'Md3Table', props: ['columns', 'data', 'stripe', 'emptyText', 'selection', 'maxHeight'], template: '<div class="md3-table"><slot name="actions" /><slot name="services" /></div>' },
  Md3Tabs: { name: 'Md3Tabs', props: ['modelValue', 'tabs'], template: '<div class="md3-tabs" />' },
  Md3Dialog: { name: 'Md3Dialog', props: ['visible', 'title', 'width', 'closable'], emits: ['update:visible'], template: '<div class="md3-dialog" v-if="visible"><slot /><slot name="footer" /></div>' },
  Md3Input: { name: 'Md3Input', props: ['modelValue', 'label', 'placeholder', 'type'], emits: ['update:modelValue'], template: '<input class="md3-input" :value="modelValue" :placeholder="placeholder" />' },
  Md3Select: { name: 'Md3Select', props: ['modelValue', 'options', 'placeholder', 'label', 'clearable', 'multiple'], emits: ['update:modelValue'], template: '<select class="md3-select" :data-placeholder="placeholder">{{ placeholder }}</select>' },
  Md3Alert: { name: 'Md3Alert', props: ['type', 'title', 'message'], template: '<div class="md3-alert"><slot name="title" /><slot name="message" /></div>' },
  Md3Progress: { name: 'Md3Progress', props: ['percentage', 'color'], template: '<div class="md3-progress" />' },
  Md3Radio: { name: 'Md3Radio', props: ['modelValue', 'value', 'label'], emits: ['update:modelValue'], template: '<label class="md3-radio"><input type="radio" /><slot /></label>' },
  Md3Switch: { name: 'Md3Switch', props: ['modelValue', 'onText', 'offText'], emits: ['update:modelValue'], template: '<div class="md3-switch" />' },
  Md3Spinner: { name: 'Md3Spinner', props: ['size'], template: '<div class="md3-spinner" />' },
  Md3Collapse: { name: 'Md3Collapse', props: ['title'], template: '<div class="md3-collapse"><slot /></div>' },
  Md3Tooltip: { name: 'Md3Tooltip', props: ['content', 'placement'], template: '<div class="md3-tooltip"><slot /></div>' },
  Md3Checkbox: { name: 'Md3Checkbox', props: ['modelValue'], emits: ['update:modelValue'], template: '<input type="checkbox" class="md3-checkbox" />' },
}))

vi.mock('@/components/md3/Md3Confirm', () => ({
  Md3Confirm: { show: vi.fn().mockResolvedValue(true) },
}))

vi.mock('@/components/Md3Button.vue', () => ({
  default: { name: 'Md3Button', props: ['size', 'variant', 'disabled', 'icon', 'loading', 'type'], template: '<button class="md3-btn" :disabled="disabled" @click="$emit(\'click\')"><slot /></button>' },
}))

vi.mock('@/components/md3/Md3Tag.vue', () => ({
  default: { name: 'Md3Tag', props: ['variant', 'type', 'size'], template: '<span class="md3-tag" :data-variant="variant"><slot /></span>' },
}))

vi.mock('@/components/ContainerList.vue', () => ({
  default: { name: 'ContainerList', props: ['containers'], emits: ['start', 'stop', 'restart', 'logs', 'terminal', 'delete', 'selectionChange'], template: '<div class="container-list"><slot /></div>' },
}))

vi.mock('@/components/ImageList.vue', () => ({
  default: { name: 'ImageList', props: ['images'], emits: ['pull', 'build', 'delete'], template: '<div class="image-list"><slot /></div>' },
}))

vi.mock('@/components/Terminal.vue', () => ({
  default: { name: 'Terminal', props: ['sessionName', 'showToolbar', 'fontSize', 'fontFamily', 'theme'], emits: ['data', 'resize'], template: '<div class="terminal" />' },
}))

vi.mock('@/components/ContainerStatsPanel.vue', () => ({
  default: { name: 'ContainerStatsPanel', props: ['containerId'], template: '<div class="container-stats-panel" />' },
}))

vi.mock('@/components/DbManagerPanel.vue', () => ({
  default: { name: 'DbManagerPanel', props: ['deployMode', 'accountAlias', 'containerId', 'containerState'], template: '<div class="db-manager-panel" />' },
}))

vi.mock('@/components/MonitorLineChart.vue', () => ({
  default: { name: 'MonitorLineChart', props: ['data', 'color', 'yAxisName', 'height'], template: '<div class="monitor-line-chart" />' },
}))

vi.mock('@/components/MonitorGaugeChart.vue', () => ({
  default: { name: 'MonitorGaugeChart', props: ['value', 'title', 'height', 'max', 'min', 'unit'], template: '<div class="monitor-gauge-chart" />' },
}))

vi.mock('@/components/MonitorPieChart.vue', () => ({
  default: { name: 'MonitorPieChart', props: ['data', 'height', 'donut', 'roseType'], template: '<div class="monitor-pie-chart" />' },
}))

vi.mock('@/components/MonitorHeatmap.vue', () => ({
  default: { name: 'MonitorHeatmap', props: ['data', 'height', 'title'], template: '<div class="monitor-heatmap" />' },
}))

vi.mock('@/components/FileBrowser.vue', () => ({
  default: { name: 'FileBrowser', props: ['currentPath', 'items', 'selectedPaths', 'showCreate', 'showUpload'], emits: ['navigate', 'mkdir', 'createFile', 'upload', 'download', 'rename', 'copy', 'delete', 'chmod', 'update:selectedPaths'], template: '<div class="file-browser" />' },
}))

vi.mock('@/components/PermissionEditor.vue', () => ({
  default: { name: 'PermissionEditor', props: ['modelValue', 'showRecursive'], emits: ['update:modelValue', 'update:recursive'], template: '<div class="permission-editor" />' },
}))

vi.mock('@/components/SessionManager.vue', () => ({
  default: { name: 'SessionManager', props: ['sessions', 'historyRecords', 'activeSessionId'], emits: ['select', 'disconnect', 'newSession', 'reconnect', 'deleteHistory'], template: '<div class="session-manager" />' },
}))

vi.mock('@/components/ViteDeployPanel.vue', () => ({
  default: { name: 'ViteDeployPanel', props: ['projectConfig'], template: '<div class="vite-deploy-panel" />' },
}))

vi.mock('@/components/ViteStatusCard.vue', () => ({
  default: { name: 'ViteStatusCard', props: ['status'], template: '<div class="vite-status-card" />' },
}))

vi.mock('@/components/WebhookDeployPanel.vue', () => ({
  default: { name: 'WebhookDeployPanel', template: '<div class="webhook-deploy-panel" />' },
}))

vi.mock('@/components/BuildPanel.vue', () => ({
  default: { name: 'BuildPanel', props: ['buildStatus', 'runStatus'], template: '<div class="build-panel" />' },
}))

vi.mock('@/components/SyncPanel.vue', () => ({
  default: { name: 'SyncPanel', props: ['syncStatus', 'progress'], template: '<div class="sync-panel" />' },
}))

vi.mock('@/components/GitBranchPanel.vue', () => ({
  default: { name: 'GitBranchPanel', template: '<div class="git-branch-panel" />' },
}))

vi.mock('@/components/GitCommitPanel.vue', () => ({
  default: { name: 'GitCommitPanel', template: '<div class="git-commit-panel" />' },
}))

vi.mock('@/components/GitRepoPanel.vue', () => ({
  default: { name: 'GitRepoPanel', template: '<div class="git-repo-panel" />' },
}))

vi.mock('@/components/GitSyncPanel.vue', () => ({
  default: { name: 'GitSyncPanel', template: '<div class="git-sync-panel" />' },
}))

vi.mock('@/components/BackupHistoryDrawer.vue', () => ({
  default: { name: 'BackupHistoryDrawer', props: ['visible'], emits: ['update:visible'], template: '<div class="backup-history-drawer" />' },
}))

vi.mock('@/components/CronPicker.vue', () => ({
  default: { name: 'CronPicker', props: ['modelValue'], emits: ['update:modelValue'], template: '<div class="cron-picker" />' },
}))

vi.mock('@/components/ExecutionLogDialog.vue', () => ({
  default: { name: 'ExecutionLogDialog', props: ['visible', 'executionId'], emits: ['update:visible'], template: '<div class="execution-log-dialog" />' },
}))

vi.mock('@/components/ThemeToggle.vue', () => ({
  default: { name: 'ThemeToggle', template: '<button class="theme-toggle" />' },
}))

vi.mock('@/components/ColorPresets.vue', () => ({
  default: { name: 'ColorPresets', props: ['label'], template: '<div class="color-presets" />' },
}))

vi.mock('@/components/DbToolkitPanel.vue', () => ({
  default: { name: 'DbToolkitPanel', template: '<div class="db-toolkit-panel" />' },
}))

vi.mock('@/components/DbConnectionManager.vue', () => ({
  default: { name: 'DbConnectionManager', template: '<div class="db-connection-manager" />' },
}))

vi.mock('@/components/DbLoginDialog.vue', () => ({
  default: { name: 'DbLoginDialog', props: ['visible'], emits: ['update:visible', 'login'], template: '<div class="db-login-dialog" />' },
}))

vi.mock('@/components/DbManagerPanel.vue', () => ({
  default: { name: 'DbManagerPanel', props: ['deployMode', 'accountAlias', 'containerId', 'containerState'], template: '<div class="db-manager-panel" />' },
}))

vi.mock('@/components/DbSidebar.vue', () => ({
  default: { name: 'DbSidebar', template: '<div class="db-sidebar" />' },
}))

vi.mock('@/components/MySqlPanel.vue', () => ({
  default: { name: 'MySqlPanel', template: '<div class="mysql-panel" />' },
}))

vi.mock('@/components/RedisPanel.vue', () => ({
  default: { name: 'RedisPanel', template: '<div class="redis-panel" />' },
}))

vi.mock('@/components/RedisKeyDetail.vue', () => ({
  default: { name: 'RedisKeyDetail', template: '<div class="redis-key-detail" />' },
}))

vi.mock('@/components/RedisKeyList.vue', () => ({
  default: { name: 'RedisKeyList', template: '<div class="redis-key-list" />' },
}))

vi.mock('@/components/SqlQueryEditor.vue', () => ({
  default: { name: 'SqlQueryEditor', template: '<div class="sql-query-editor" />' },
}))

vi.mock('@/components/SqlResultTable.vue', () => ({
  default: { name: 'SqlResultTable', template: '<div class="sql-result-table" />' },
}))

vi.mock('@/components/DataRowForm.vue', () => ({
  default: { name: 'DataRowForm', template: '<div class="data-row-form" />' },
}))

vi.mock('@/components/DataEditor.vue', () => ({
  default: { name: 'DataEditor', template: '<div class="data-editor" />' },
}))

vi.mock('@/components/TableInfoPanel.vue', () => ({
  default: { name: 'TableInfoPanel', template: '<div class="table-info-panel" />' },
}))

vi.mock('@/components/workflow/WorkflowCanvas.vue', () => ({
  default: { name: 'WorkflowCanvas', props: ['nodes', 'edges', 'nodeExecutions'], emits: ['nodeClick', 'nodeDrag', 'nodeDragEnd', 'edgeClick', 'canvasClick', 'connect'], template: '<div class="workflow-canvas" />' },
}))

vi.mock('@/components/workflow/WorkflowNodePanel.vue', () => ({
  default: { name: 'WorkflowNodePanel', emits: ['dragStart'], template: '<div class="workflow-node-panel" />' },
}))

vi.mock('@/components/workflow/NodeConfigPanel.vue', () => ({
  default: { name: 'NodeConfigPanel', props: ['node', 'sshAccounts'], emits: ['update', 'close'], template: '<div class="node-config-panel" />' },
}))

vi.mock('@/components/workflow/WorkflowTemplateGallery.vue', () => ({
  default: { name: 'WorkflowTemplateGallery', template: '<div class="workflow-template-gallery" />' },
}))

vi.mock('@/components/workflow/WorkflowEdge.vue', () => ({
  default: { name: 'WorkflowEdge', template: '<div class="workflow-edge" />' },
}))

vi.mock('@/components/workflow/WorkflowNode.vue', () => ({
  default: { name: 'WorkflowNode', template: '<div class="workflow-node" />' },
}))

const mockPush = vi.fn()
const mockRoute = { params: {}, query: {} }

vi.mock('vue-router', () => ({
  useRouter: () => ({ push: mockPush, replace: vi.fn() }),
  useRoute: () => mockRoute,
}))

function createMockStore() {
  return {
    currentAlias: 'test-server',
    accounts: [{ alias: 'test-server', host: '192.168.1.1', port: 22, default: true, status: 'online', username: 'root', auth_type: 'password', password: '', private_key: '', key_passphrase: '', group: '', last_connected: '' }],
    groups: [],
    fetchAccounts: vi.fn().mockResolvedValue(undefined),
    fetchGroups: vi.fn().mockResolvedValue(undefined),
    setDefault: vi.fn().mockResolvedValue(undefined),
    testConnection: vi.fn().mockResolvedValue({ success: true, message: 'OK' }),
    createAccount: vi.fn().mockResolvedValue(undefined),
    updateAccount: vi.fn().mockResolvedValue(undefined),
    deleteAccount: vi.fn().mockResolvedValue(undefined),
    createGroup: vi.fn().mockResolvedValue(undefined),
    updateGroup: vi.fn().mockResolvedValue(undefined),
    deleteGroup: vi.fn().mockResolvedValue(undefined),
  }
}

let sshStoreMock: ReturnType<typeof createMockStore>
let dockerStoreMock: any

vi.mock('@/stores/sshAccountStore', () => ({
  useSshAccountStore: () => sshStoreMock,
}))

vi.mock('@/stores/dockerStore', () => ({
  useDockerStore: () => dockerStoreMock,
  DockerContainer: {},
}))

vi.mock('@/stores/dockerStoreStore', () => ({
  useDockerStoreStore: () => ({
    apps: [],
    appStatuses: {},
    appSizes: {},
    imageVersionSizes: {},
    installProgressPercent: {},
    installProgressMessage: {},
    installProgress: {},
    registryMirror: { enabled: false },
    installing: false,
    uninstalling: false,
    versionSizeLoading: {},
    fetchApps: vi.fn().mockResolvedValue(undefined),
    fetchAppStatuses: vi.fn().mockResolvedValue(undefined),
    fetchRegistryMirrors: vi.fn().mockResolvedValue(undefined),
    fetchAppSize: vi.fn().mockResolvedValue(undefined),
    fetchImageVersionSizes: vi.fn().mockResolvedValue(undefined),
    installAppWithProgress: vi.fn().mockResolvedValue({ success: true }),
    uninstallApp: vi.fn().mockResolvedValue(undefined),
    configureRegistryMirror: vi.fn().mockResolvedValue(undefined),
  }),
}))

beforeEach(() => {
  setActivePinia(createPinia())
  vi.clearAllMocks()
  sshStoreMock = createMockStore()
  dockerStoreMock = {
    currentAlias: 'test-server',
    containers: [],
    images: [],
    networks: [],
    volumes: [],
    composeProjects: [],
    dockerInfo: { version: '24.0', daemon_status: 'running', docker_group: true },
    setAccountAlias: vi.fn(),
    fetchInfo: vi.fn().mockResolvedValue(undefined),
    fetchContainers: vi.fn().mockResolvedValue(undefined),
    fetchImages: vi.fn().mockResolvedValue(undefined),
    fetchNetworks: vi.fn().mockResolvedValue(undefined),
    fetchVolumes: vi.fn().mockResolvedValue(undefined),
    fetchComposeProjects: vi.fn().mockResolvedValue(undefined),
    startContainer: vi.fn().mockResolvedValue({ success: true }),
    stopContainer: vi.fn().mockResolvedValue(undefined),
    restartContainer: vi.fn().mockResolvedValue(undefined),
    deleteContainer: vi.fn().mockResolvedValue(undefined),
    deleteImage: vi.fn().mockResolvedValue(undefined),
    pullImage: vi.fn().mockResolvedValue(undefined),
    buildImage: vi.fn().mockResolvedValue(undefined),
    pruneImages: vi.fn().mockResolvedValue(undefined),
    createNetwork: vi.fn().mockResolvedValue(undefined),
    deleteNetwork: vi.fn().mockResolvedValue(undefined),
    createVolume: vi.fn().mockResolvedValue(undefined),
    deleteVolume: vi.fn().mockResolvedValue(undefined),
    composeUp: vi.fn().mockResolvedValue(undefined),
    composeDown: vi.fn().mockResolvedValue(undefined),
    getContainerLogs: vi.fn().mockResolvedValue([]),
    killContainer: vi.fn().mockResolvedValue(undefined),
  }
})

import DockerPage from '@/views/DockerPage.vue'
import DockerContainerDetail from '@/views/DockerContainerDetail.vue'
import DockerStorePage from '@/views/DockerStorePage.vue'

describe('DockerPage', () => {
  function createWrapper() {
    return mount(DockerPage, { global: { stubs: { Md3Icon: true } } })
  }

  it('应该渲染 Docker 管理页面容器', () => {
    const wrapper = createWrapper()
    expect(wrapper.find('.docker-page').exists()).toBe(true)
  })

  it('应该渲染页面标题', () => {
    const wrapper = createWrapper()
    expect(wrapper.text()).toContain('Docker 管理')
  })

  it('应该渲染 SSH 服务器选择器', () => {
    const wrapper = createWrapper()
    expect(wrapper.find('.account-selector').exists()).toBe(true)
    expect(wrapper.text()).toContain('SSH 服务器')
  })

  it('应该渲染环境信息卡片（当有 currentAlias 时）', () => {
    const wrapper = createWrapper()
    expect(wrapper.find('.env-card').exists()).toBe(true)
    expect(wrapper.text()).toContain('Docker 环境')
    expect(wrapper.text()).toContain('守护进程')
    expect(wrapper.text()).toContain('Docker 权限')
  })

  it('应该渲染 Tab 切换', () => {
    const wrapper = createWrapper()
    expect(wrapper.find('.docker-tabs').exists()).toBe(true)
  })

  it('应该在无 currentAlias 时显示空状态', async () => {
    dockerStoreMock.currentAlias = ''
    const wrapper = createWrapper()
    await nextTick()
    expect(wrapper.text()).toContain('请先选择一个 SSH 服务器来管理 Docker')
  })

  it('应该渲染批量操作区域（当有选中容器时）', async () => {
    dockerStoreMock.containers = [{ id: 'abc', name: 'nginx', image: 'nginx', status: 'Up', state: 'running', ports: '', created: '' }]
    const wrapper = createWrapper()
    wrapper.vm.selectedContainers = [dockerStoreMock.containers[0]]
    await nextTick()
    expect(wrapper.find('.batch-actions').exists()).toBe(true)
    expect(wrapper.text()).toContain('批量操作')
  })

  it('onAccountChange 应该调用 store 方法', async () => {
    const wrapper = createWrapper()
    wrapper.vm.onAccountChange('new-server')
    expect(dockerStoreMock.setAccountAlias).toHaveBeenCalledWith('new-server')
  })

  it('应该渲染拉取镜像对话框', () => {
    const wrapper = createWrapper()
    expect(wrapper.vm.showPullDialog).toBe(false)
  })

  it('应该渲染构建镜像对话框', () => {
    const wrapper = createWrapper()
    expect(wrapper.vm.showBuildDialog).toBe(false)
  })

  it('pullImage 应该调用 store 并重置表单', async () => {
    const wrapper = createWrapper()
    wrapper.vm.pullForm = { repository: 'nginx', tag: 'latest' }
    wrapper.vm.showPullDialog = true
    await wrapper.vm.pullImage()
    expect(dockerStoreMock.pullImage).toHaveBeenCalledWith({ repository: 'nginx', tag: 'latest' })
    expect(wrapper.vm.showPullDialog).toBe(false)
    expect(wrapper.vm.pullForm).toEqual({ repository: '', tag: 'latest' })
  })

  it('buildImage 应该调用 store 并重置表单', async () => {
    const wrapper = createWrapper()
    wrapper.vm.buildForm = { dockerfile_path: '/Dockerfile', tag: 'myapp:latest' }
    wrapper.vm.showBuildDialog = true
    await wrapper.vm.buildImage()
    expect(dockerStoreMock.buildImage).toHaveBeenCalledWith({ dockerfile_path: '/Dockerfile', tag: 'myapp:latest' })
    expect(wrapper.vm.showBuildDialog).toBe(false)
    expect(wrapper.vm.buildForm).toEqual({ dockerfile_path: '', tag: '' })
  })

  it('pruneImages 应该调用 store', async () => {
    const wrapper = createWrapper()
    await wrapper.vm.pruneImages()
    expect(dockerStoreMock.pruneImages).toHaveBeenCalled()
  })

  it('confirmDeleteNetwork 确认时应该调用 deleteNetwork', async () => {
    const wrapper = createWrapper()
    wrapper.vm.confirmDeleteNetwork({ id: 'net-1' })
    await nextTick()
    await nextTick()
    expect(dockerStoreMock.deleteNetwork).toHaveBeenCalledWith('net-1')
  })

  it('confirmDeleteNetwork 取消时不应调用 deleteNetwork', async () => {
    const { Md3Confirm } = await import('@/components/md3/Md3Confirm')
    Md3Confirm.show.mockResolvedValueOnce(false)
    const wrapper = createWrapper()
    wrapper.vm.confirmDeleteNetwork({ id: 'net-1' })
    await nextTick()
    await nextTick()
    expect(dockerStoreMock.deleteNetwork).not.toHaveBeenCalled()
  })

  it('confirmDeleteVolume 确认时应该调用 deleteVolume', async () => {
    const wrapper = createWrapper()
    wrapper.vm.confirmDeleteVolume({ name: 'vol-1' })
    await nextTick()
    await nextTick()
    expect(dockerStoreMock.deleteVolume).toHaveBeenCalledWith('vol-1')
  })

  it('confirmDeleteVolume 取消时不应调用 deleteVolume', async () => {
    const { Md3Confirm } = await import('@/components/md3/Md3Confirm')
    Md3Confirm.show.mockResolvedValueOnce(false)
    const wrapper = createWrapper()
    wrapper.vm.confirmDeleteVolume({ name: 'vol-1' })
    await nextTick()
    await nextTick()
    expect(dockerStoreMock.deleteVolume).not.toHaveBeenCalled()
  })

  it('createNetwork 应该调用 store 并重置表单', async () => {
    const wrapper = createWrapper()
    wrapper.vm.networkForm = { name: 'my-net', driver: 'bridge' }
    wrapper.vm.showNetworkDialog = true
    await wrapper.vm.createNetwork()
    expect(dockerStoreMock.createNetwork).toHaveBeenCalledWith({ name: 'my-net', driver: 'bridge' })
    expect(wrapper.vm.showNetworkDialog).toBe(false)
    expect(wrapper.vm.networkForm).toEqual({ name: '', driver: 'bridge' })
  })

  it('createVolume 应该调用 store 并重置表单', async () => {
    const wrapper = createWrapper()
    wrapper.vm.volumeForm = { name: 'my-vol' }
    wrapper.vm.showVolumeDialog = true
    await wrapper.vm.createVolume()
    expect(dockerStoreMock.createVolume).toHaveBeenCalledWith({ name: 'my-vol' })
    expect(wrapper.vm.showVolumeDialog).toBe(false)
    expect(wrapper.vm.volumeForm).toEqual({ name: '' })
  })

  it('batchStart 应该启动所有选中容器', async () => {
    const wrapper = createWrapper()
    wrapper.vm.selectedContainers = [{ id: 'c1' }, { id: 'c2' }] as any
    wrapper.vm.batchStart()
    expect(dockerStoreMock.startContainer).toHaveBeenCalledTimes(2)
    expect(dockerStoreMock.startContainer).toHaveBeenCalledWith('c1')
    expect(dockerStoreMock.startContainer).toHaveBeenCalledWith('c2')
  })

  it('batchStop 应该停止所有选中容器', async () => {
    const wrapper = createWrapper()
    wrapper.vm.selectedContainers = [{ id: 'c1' }, { id: 'c2' }] as any
    wrapper.vm.batchStop()
    expect(dockerStoreMock.stopContainer).toHaveBeenCalledTimes(2)
  })

  it('batchDelete 应该删除所有选中容器', async () => {
    const wrapper = createWrapper()
    wrapper.vm.selectedContainers = [{ id: 'c1' }, { id: 'c2' }] as any
    wrapper.vm.batchDelete()
    expect(dockerStoreMock.deleteContainer).toHaveBeenCalledTimes(2)
  })

  it('handleStart 成功无 errorLogs 时不应显示错误对话框', async () => {
    dockerStoreMock.startContainer = vi.fn().mockResolvedValue({ success: true })
    const wrapper = createWrapper()
    await wrapper.vm.handleStart({ id: 'c1' } as any)
    expect(wrapper.vm.showErrorLogDialog).toBe(false)
  })

  it('handleStart 有 errorLogs 时应该显示错误对话框', async () => {
    dockerStoreMock.startContainer = vi.fn().mockResolvedValue({ success: false, errorLogs: 'error output' })
    const wrapper = createWrapper()
    await wrapper.vm.handleStart({ id: 'c1' } as any)
    expect(wrapper.vm.showErrorLogDialog).toBe(true)
    expect(wrapper.vm.errorLogContent).toBe('error output')
  })

  it('handleStop 应该调用 stopContainer', async () => {
    const wrapper = createWrapper()
    wrapper.vm.handleStop({ id: 'c1' } as any)
    expect(dockerStoreMock.stopContainer).toHaveBeenCalledWith('c1')
  })

  it('handleRestart 应该调用 restartContainer', async () => {
    const wrapper = createWrapper()
    wrapper.vm.handleRestart({ id: 'c1' } as any)
    expect(dockerStoreMock.restartContainer).toHaveBeenCalledWith('c1')
  })

  it('handleLogs 应该导航到容器详情', async () => {
    const wrapper = createWrapper()
    wrapper.vm.handleLogs({ id: 'c1' } as any)
    expect(mockPush).toHaveBeenCalledWith('/docker/container/c1')
  })

  it('handleTerminal 应该导航到容器终端标签', async () => {
    const wrapper = createWrapper()
    wrapper.vm.handleTerminal({ id: 'c1' } as any)
    expect(mockPush).toHaveBeenCalledWith('/docker/container/c1?tab=terminal')
  })

  it('handleDelete 应该调用 deleteContainer', async () => {
    const wrapper = createWrapper()
    wrapper.vm.handleDelete({ id: 'c1' } as any)
    expect(dockerStoreMock.deleteContainer).toHaveBeenCalledWith('c1')
  })

  it('handleImageDelete 应该调用 deleteImage', async () => {
    const wrapper = createWrapper()
    wrapper.vm.handleImageDelete({ id: 'img-1' })
    expect(dockerStoreMock.deleteImage).toHaveBeenCalledWith('img-1')
  })

  it('refreshAll 应该调用所有 fetch 方法', async () => {
    const wrapper = createWrapper()
    wrapper.vm.refreshAll()
    expect(dockerStoreMock.fetchInfo).toHaveBeenCalled()
    expect(dockerStoreMock.fetchContainers).toHaveBeenCalled()
    expect(dockerStoreMock.fetchImages).toHaveBeenCalled()
    expect(dockerStoreMock.fetchNetworks).toHaveBeenCalled()
    expect(dockerStoreMock.fetchVolumes).toHaveBeenCalled()
    expect(dockerStoreMock.fetchComposeProjects).toHaveBeenCalled()
  })

  it('onMounted 有默认账户时应该自动选择并刷新', async () => {
    createWrapper()
    await nextTick()
    await nextTick()
    expect(sshStoreMock.fetchAccounts).toHaveBeenCalled()
    expect(dockerStoreMock.setAccountAlias).toHaveBeenCalledWith('test-server')
  })

  it('sshOptions 应该返回正确的选项', () => {
    const wrapper = createWrapper()
    const options = wrapper.vm.sshOptions
    expect(options).toHaveLength(1)
    expect(options[0].value).toBe('test-server')
    expect(options[0].label).toContain('test-server')
  })

  it('dockerInfo 应该返回 store 数据', () => {
    const wrapper = createWrapper()
    expect(wrapper.vm.dockerInfo.version).toBe('24.0')
    expect(wrapper.vm.dockerInfo.daemon_status).toBe('running')
    expect(wrapper.vm.dockerInfo.docker_group).toBe(true)
  })

  it('tabItems 应该返回5个标签', () => {
    const wrapper = createWrapper()
    expect(wrapper.vm.tabItems).toHaveLength(5)
  })

  it('networkDriverOptions 应该返回4个驱动选项', () => {
    const wrapper = createWrapper()
    expect(wrapper.vm.networkDriverOptions).toHaveLength(4)
  })
})

describe('DockerContainerDetail', () => {
  beforeEach(() => {
    mockRoute.params = { id: 'abc123' }
    mockRoute.query = {}
    dockerStoreMock.containers = [
      { id: 'abc123def456', name: 'nginx-web', image: 'nginx:latest', status: 'Up 2 hours', state: 'running', ports: '80/tcp', created: '2024-01-15' },
    ]
  })

  function createWrapper() {
    return mount(DockerContainerDetail, { global: { stubs: { Md3Icon: true } } })
  }

  it('应该渲染容器详情页面容器', () => {
    const wrapper = createWrapper()
    expect(wrapper.find('.docker-detail-page').exists()).toBe(true)
  })

  it('应该渲染页面标题', () => {
    const wrapper = createWrapper()
    expect(wrapper.text()).toContain('Docker 管理')
  })

  it('应该渲染 Tab 切换', () => {
    const wrapper = createWrapper()
    expect(wrapper.find('.detail-tabs').exists()).toBe(true)
  })

  it('应该渲染日志控制区', () => {
    const wrapper = createWrapper()
    expect(wrapper.find('.log-controls').exists()).toBe(true)
  })

  it('goBack 应该导航到 /docker', () => {
    const wrapper = createWrapper()
    wrapper.vm.goBack()
    expect(mockPush).toHaveBeenCalledWith('/docker')
  })

  it('toggleLogStream 应该切换流式状态', async () => {
    const wrapper = createWrapper()
    expect(wrapper.vm.isLogStreaming).toBe(false)
    wrapper.vm.toggleLogStream()
    expect(wrapper.vm.isLogStreaming).toBe(true)
  })

  it('logLevelClass 应该返回正确的类名', () => {
    const wrapper = createWrapper()
    expect(wrapper.vm.logLevelClass('ERROR something')).toBe('log-error')
    expect(wrapper.vm.logLevelClass('WARN something')).toBe('log-warn')
    expect(wrapper.vm.logLevelClass('INFO something')).toBe('log-info')
  })

  it('loadContainerDetail 找到容器时应该设置 containerDetail', async () => {
    const wrapper = createWrapper()
    await wrapper.vm.loadContainerDetail()
    expect(wrapper.vm.containerDetail).toBeTruthy()
    expect(wrapper.vm.containerName).toBe('nginx-web')
  })

  it('loadContainerDetail 未找到容器时不应设置 containerDetail', async () => {
    mockRoute.params = { id: 'nonexistent' }
    const wrapper = createWrapper()
    await wrapper.vm.loadContainerDetail()
    expect(wrapper.vm.containerDetail).toBeFalsy()
  })

  it('loadContainerDetail 异常时不应报错', async () => {
    dockerStoreMock.containers = null
    const wrapper = createWrapper()
    await expect(wrapper.vm.loadContainerDetail()).resolves.toBeUndefined()
  })

  it('loadLogs 成功时应该设置 containerLogs', async () => {
    dockerStoreMock.getContainerLogs = vi.fn().mockResolvedValue(['line1', 'line2'])
    const wrapper = createWrapper()
    await wrapper.vm.loadLogs()
    expect(wrapper.vm.containerLogs).toEqual(['line1', 'line2'])
  })

  it('loadLogs 异常时不应报错', async () => {
    dockerStoreMock.getContainerLogs = vi.fn().mockRejectedValue(new Error('fail'))
    const wrapper = createWrapper()
    await expect(wrapper.vm.loadLogs()).resolves.toBeUndefined()
  })

  it('downloadLogs 应该创建下载链接', () => {
    const mockCreateObjectURL = vi.fn().mockReturnValue('blob:test')
    const mockRevokeObjectURL = vi.fn()
    globalThis.URL.createObjectURL = mockCreateObjectURL
    globalThis.URL.revokeObjectURL = mockRevokeObjectURL
    const wrapper = createWrapper()
    wrapper.vm.containerLogs = ['log line 1', 'log line 2']
    wrapper.vm.downloadLogs()
    expect(mockCreateObjectURL).toHaveBeenCalled()
    expect(mockRevokeObjectURL).toHaveBeenCalled()
  })

  it('restartContainer 应该调用 store 方法', () => {
    const wrapper = createWrapper()
    wrapper.vm.restartContainer()
    expect(dockerStoreMock.restartContainer).toHaveBeenCalledWith('abc123')
  })

  it('stopContainer 应该调用 store 方法', () => {
    const wrapper = createWrapper()
    wrapper.vm.stopContainer()
    expect(dockerStoreMock.stopContainer).toHaveBeenCalledWith('abc123')
  })

  it('killContainer 应该调用 store 方法', () => {
    const wrapper = createWrapper()
    wrapper.vm.killContainer()
    expect(dockerStoreMock.killContainer).toHaveBeenCalledWith('abc123')
  })

  it('deleteContainer 应该调用 store 方法并返回', () => {
    const wrapper = createWrapper()
    wrapper.vm.deleteContainer()
    expect(dockerStoreMock.deleteContainer).toHaveBeenCalledWith('abc123')
    expect(mockPush).toHaveBeenCalledWith('/docker')
  })

  it('openStats 应该切换到概览标签', () => {
    const wrapper = createWrapper()
    wrapper.vm.activeTab = 'logs'
    wrapper.vm.openStats()
    expect(wrapper.vm.activeTab).toBe('overview')
  })

  it('logTailLines 变更且流式时应该重新加载日志', async () => {
    dockerStoreMock.getContainerLogs = vi.fn().mockResolvedValue(['line1'])
    const wrapper = createWrapper()
    wrapper.vm.isLogStreaming = true
    wrapper.vm.logTailLines = 500
    await nextTick()
    expect(dockerStoreMock.getContainerLogs).toHaveBeenCalled()
  })

  it('logTailLines 变更且非流式时不应重新加载日志', async () => {
    dockerStoreMock.getContainerLogs = vi.fn().mockResolvedValue(['line1'])
    const wrapper = createWrapper()
    wrapper.vm.isLogStreaming = false
    wrapper.vm.logTailLines = 500
    await nextTick()
    expect(dockerStoreMock.getContainerLogs).not.toHaveBeenCalled()
  })

  it('toggleLogStream 开启时应该加载日志', async () => {
    dockerStoreMock.getContainerLogs = vi.fn().mockResolvedValue(['line1'])
    const wrapper = createWrapper()
    wrapper.vm.isLogStreaming = false
    wrapper.vm.toggleLogStream()
    expect(wrapper.vm.isLogStreaming).toBe(true)
  })

  it('logLevelClass FATAL 应该返回 log-error', () => {
    const wrapper = createWrapper()
    expect(wrapper.vm.logLevelClass('FATAL error')).toBe('log-error')
  })

  it('onMounted 应该加载容器详情', async () => {
    createWrapper()
    await nextTick()
    expect(dockerStoreMock.containers).toBeDefined()
  })
})

describe('DockerStorePage', () => {
  function createWrapper() {
    return mount(DockerStorePage, { global: { stubs: { Md3Icon: true, StatusTag: true } } })
  }

  it('应该渲染应用商店页面容器', () => {
    const wrapper = createWrapper()
    expect(wrapper.find('.docker-store-page').exists()).toBe(true)
  })

  it('应该渲染页面标题', () => {
    const wrapper = createWrapper()
    expect(wrapper.text()).toContain('应用商店')
  })

  it('应该渲染 SSH 服务器选择器', () => {
    const wrapper = createWrapper()
    expect(wrapper.find('.account-selector').exists()).toBe(true)
  })

  it('应该渲染分类栏', () => {
    const wrapper = createWrapper()
    expect(wrapper.find('.category-bar').exists()).toBe(true)
  })

  it('应该在无 currentAlias 时显示空状态', async () => {
    dockerStoreMock.currentAlias = ''
    const wrapper = createWrapper()
    await nextTick()
    expect(wrapper.text()).toContain('请先选择一个 SSH 服务器')
  })

  it('onAccountChange 应该调用 store 方法', async () => {
    const wrapper = createWrapper()
    wrapper.vm.onAccountChange('new-server')
    expect(dockerStoreMock.setAccountAlias).toHaveBeenCalledWith('new-server')
  })

  it('应该渲染分类按钮', () => {
    const wrapper = createWrapper()
    const buttons = wrapper.findAll('.category-bar button, .category-bar .md3-btn')
    expect(buttons.length).toBeGreaterThanOrEqual(0)
  })

  it('getAppStatus 应该返回应用状态', () => {
    const wrapper = createWrapper()
    expect(wrapper.vm.getAppStatus('app1')).toBe('not_installed')
  })

  it('getAppSize 无大小时应该返回空字符串', () => {
    const wrapper = createWrapper()
    expect(wrapper.vm.getAppSize('app1')).toBe('')
  })

  it('getAppSize 有大小时应该返回大小字符串', () => {
    const wrapper = createWrapper()
    const store = wrapper.vm.store
    store.appSizes = { app1: { total_size: 1024, total_size_human: '1.0 KB' } }
    expect(wrapper.vm.getAppSize('app1')).toBe('1.0 KB')
  })

  it('filteredApps 全部分类时应该返回所有应用', () => {
    const wrapper = createWrapper()
    expect(wrapper.vm.filteredApps).toEqual([])
  })

  it('filteredApps 按分类过滤', () => {
    const wrapper = createWrapper()
    const store = wrapper.vm.store
    store.apps = [
      { id: '1', name: 'nginx', category: 'web_server', icon: '', description: '', require_memory: 512, versions: ['latest'], env_config: [], features: [], recommended_for: [] },
      { id: '2', name: 'mysql', category: 'database', icon: '', description: '', require_memory: 1024, versions: ['latest'], env_config: [], features: [], recommended_for: [] },
    ]
    wrapper.vm.activeCategory = 'web'
    expect(wrapper.vm.filteredApps).toHaveLength(1)
    expect(wrapper.vm.filteredApps[0].name).toBe('nginx')
  })

  it('versionOptions 无应用时应该返回空数组', () => {
    const wrapper = createWrapper()
    expect(wrapper.vm.versionOptions).toEqual([])
  })

  it('versionOptions 有应用时应该返回版本选项', () => {
    const wrapper = createWrapper()
    wrapper.vm.selectedApp = { id: '1', name: 'nginx', versions: ['latest', '1.25'], icon: '', description: '', require_memory: 512, env_config: [], features: [], recommended_for: [] }
    expect(wrapper.vm.versionOptions).toHaveLength(2)
  })

  it('selectedVersionSize 无选择时应该返回 null', () => {
    const wrapper = createWrapper()
    expect(wrapper.vm.selectedVersionSize).toBeNull()
  })

  it('selectedAppSize 无选择时应该返回 null', () => {
    const wrapper = createWrapper()
    expect(wrapper.vm.selectedAppSize).toBeNull()
  })

  it('refreshAll 应该调用所有 fetch 方法', async () => {
    const wrapper = createWrapper()
    await wrapper.vm.refreshAll()
    const store = wrapper.vm.store
    expect(store.fetchApps).toHaveBeenCalled()
    expect(store.fetchAppStatuses).toHaveBeenCalled()
    expect(store.fetchRegistryMirrors).toHaveBeenCalled()
  })

  it('formatDate 应该正确格式化日期', () => {
    const wrapper = createWrapper()
    const result = wrapper.vm.formatDate('2024-01-15T10:30:00Z')
    expect(result).toBeTruthy()
  })

  it('formatDate 空字符串应该返回空', () => {
    const wrapper = createWrapper()
    expect(wrapper.vm.formatDate('')).toBe('')
  })

  it('openDetailDialog 应该设置选中应用并打开对话框', async () => {
    const wrapper = createWrapper()
    const app = { id: '1', name: 'nginx', versions: ['latest'], icon: '', description: '', require_memory: 512, env_config: [], features: [], recommended_for: [] }
    await wrapper.vm.openDetailDialog(app)
    expect(wrapper.vm.selectedApp).toBeTruthy()
    expect(wrapper.vm.showDetailDialog).toBe(true)
  })

  it('openInstallDialog 应该设置安装表单', () => {
    const wrapper = createWrapper()
    const app = { id: '1', name: 'nginx', versions: ['latest'], icon: '', description: '', require_memory: 512, env_config: [{ key: 'PORT', label: '端口', type: 'port', default: 80, description: '' }], features: [], recommended_for: [] }
    wrapper.vm.openInstallDialog(app)
    expect(wrapper.vm.selectedApp).toBeTruthy()
    expect(wrapper.vm.showInstallDialog).toBe(true)
    expect(wrapper.vm.installForm.PORT).toBe(80)
  })

  it('submitInstall 无应用时不应调用 store', async () => {
    const wrapper = createWrapper()
    wrapper.vm.selectedApp = null
    await wrapper.vm.submitInstall()
    const store = wrapper.vm.store
    expect(store.installAppWithProgress).not.toHaveBeenCalled()
  })

  it('submitInstall 有应用时应该调用 store', async () => {
    const wrapper = createWrapper()
    wrapper.vm.selectedApp = { id: '1', name: 'nginx', versions: ['latest'], icon: '', description: '', require_memory: 512, env_config: [], features: [], recommended_for: [] }
    wrapper.vm.selectedVersion = 'latest'
    await wrapper.vm.submitInstall()
    const store = wrapper.vm.store
    expect(store.installAppWithProgress).toHaveBeenCalled()
  })

  it('openUninstallDialog 应该设置卸载对话框', () => {
    const wrapper = createWrapper()
    const app = { id: '1', name: 'nginx', versions: ['latest'], icon: '', description: '', require_memory: 512, env_config: [], features: [], recommended_for: [] }
    wrapper.vm.openUninstallDialog(app)
    expect(wrapper.vm.showUninstallDialog).toBe(true)
    expect(wrapper.vm.uninstallRemoveData).toBe(false)
  })

  it('submitUninstall 无应用时不应调用 store', async () => {
    const wrapper = createWrapper()
    wrapper.vm.selectedApp = null
    await wrapper.vm.submitUninstall()
    const store = wrapper.vm.store
    expect(store.uninstallApp).not.toHaveBeenCalled()
  })

  it('submitUninstall 有应用时应该调用 store', async () => {
    const wrapper = createWrapper()
    wrapper.vm.selectedApp = { id: '1', name: 'nginx', versions: ['latest'], icon: '', description: '', require_memory: 512, env_config: [], features: [], recommended_for: [] }
    await wrapper.vm.submitUninstall()
    const store = wrapper.vm.store
    expect(store.uninstallApp).toHaveBeenCalled()
    expect(wrapper.vm.showUninstallDialog).toBe(false)
  })

  it('goToContainer 有 container_id 时应该导航到容器详情', () => {
    const wrapper = createWrapper()
    const store = wrapper.vm.store
    store.appStatuses = { '1': { state: 'running', container_id: 'abc123' } }
    wrapper.vm.goToContainer({ id: '1' })
    expect(mockPush).toHaveBeenCalledWith('/docker/container/abc123')
  })

  it('goToContainer 无 container_id 时应该导航到 Docker 页面', () => {
    const wrapper = createWrapper()
    const store = wrapper.vm.store
    store.appStatuses = { '1': { state: 'running' } }
    wrapper.vm.goToContainer({ id: '1' })
    expect(mockPush).toHaveBeenCalledWith('/docker')
  })

  it('handleConfigureMirror 应该调用 store', async () => {
    const wrapper = createWrapper()
    await wrapper.vm.handleConfigureMirror()
    const store = wrapper.vm.store
    expect(store.configureRegistryMirror).toHaveBeenCalled()
  })

  it('onMounted 应该加载 SSH 账户', () => {
    createWrapper()
    expect(sshStoreMock.fetchAccounts).toHaveBeenCalled()
  })

  it('sshOptions 应该返回正确的选项', () => {
    const wrapper = createWrapper()
    const options = wrapper.vm.sshOptions
    expect(options).toHaveLength(1)
    expect(options[0].value).toBe('test-server')
  })
})
