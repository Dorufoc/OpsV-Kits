import { vi } from 'vitest'

// Mock axios 模块
vi.mock('axios', () => ({
  default: {
    create: () => ({
      get: vi.fn().mockResolvedValue({}),
      post: vi.fn().mockResolvedValue({}),
      put: vi.fn().mockResolvedValue({}),
      delete: vi.fn().mockResolvedValue({}),
      interceptors: {
        request: { use: vi.fn(), eject: vi.fn() },
        response: { use: vi.fn(), eject: vi.fn() },
      },
    }),
  },
}))

// 为 request 对象创建可被 spy 的方法
export const mockGet = vi.fn().mockResolvedValue({})
export const mockPost = vi.fn().mockResolvedValue({})
export const mockPut = vi.fn().mockResolvedValue({})
export const mockDelete = vi.fn().mockResolvedValue({})

// Mock @/api/index
vi.mock('@/api/index', () => ({
  // request 对象 - store 通过 import { request } from '@/api' 使用
  request: {
    get: mockGet,
    post: mockPost,
    put: mockPut,
    delete: mockDelete,
  },
  dockerApi: {
    getInfo: vi.fn(),
    listContainers: vi.fn(),
    listImages: vi.fn(),
    listNetworks: vi.fn(),
    listVolumes: vi.fn(),
  },
  sshAccountApi: {
    listAccounts: vi.fn(),
    createAccount: vi.fn(),
    updateAccount: vi.fn(),
    deleteAccount: vi.fn(),
    testConnection: vi.fn(),
  },
  monitorApi: {
    getSnapshot: vi.fn(),
    getCpu: vi.fn(),
    getMemory: vi.fn(),
    getDisks: vi.fn(),
    getNetwork: vi.fn(),
    getLoad: vi.fn(),
    getProcesses: vi.fn(),
    getDocker: vi.fn(),
  },
  processApi: {
    listProcesses: vi.fn(),
    killProcess: vi.fn(),
    setNice: vi.fn(),
    serviceControl: vi.fn(),
  },
  projectApi: {
    listProjects: vi.fn(),
    createProject: vi.fn(),
    updateProject: vi.fn(),
    deleteProject: vi.fn(),
    deployProject: vi.fn(),
  },
  syncApi: {
    startSync: vi.fn(),
    stopSync: vi.fn(),
    getSyncStatus: vi.fn(),
  },
  fileManagerApi: {
    listFiles: vi.fn(),
    uploadFile: vi.fn(),
    downloadFile: vi.fn(),
    deleteFile: vi.fn(),
    createDirectory: vi.fn(),
  },
  settingsApi: {
    getSettings: vi.fn(),
    updateSettings: vi.fn(),
  },
  buildApi: {
    buildProject: vi.fn(),
    getBuildStatus: vi.fn(),
    cancelBuild: vi.fn(),
  },
  viteDeployApi: {
    checkEnvironment: vi.fn(),
    setupNode: vi.fn(),
    installDeps: vi.fn(),
    build: vi.fn(),
    deployNginx: vi.fn(),
    fullDeploy: vi.fn(),
    getTaskStatus: vi.fn(),
    getTaskHistory: vi.fn(),
  },
  cronBackupApi: {
    listCronJobs: vi.fn(),
    createCronJob: vi.fn(),
    updateCronJob: vi.fn(),
    deleteCronJob: vi.fn(),
    listBackupPolicies: vi.fn(),
    createBackupPolicy: vi.fn(),
    runBackupNow: vi.fn(),
    listBackupHistory: vi.fn(),
  },
  securityApi: {
    listFirewallRules: vi.fn(),
    addFirewallPort: vi.fn(),
    deleteFirewallPort: vi.fn(),
    getSshConfig: vi.fn(),
    setSshPort: vi.fn(),
    listAuditLogs: vi.fn(),
    runPing: vi.fn(),
  },
  portApi: {
    listPorts: vi.fn(),
    checkPort: vi.fn(),
    killByPort: vi.fn(),
  },
  remoteDriveApi: {
    getStatus: vi.fn(),
  },
  websshApi: {
    listSessions: vi.fn(),
    connect: vi.fn(),
    disconnect: vi.fn(),
    sendCommand: vi.fn(),
  },
  dockerStoreApi: {
    listApps: vi.fn(),
    getAppDetail: vi.fn(),
    installApp: vi.fn(),
    uninstallApp: vi.fn(),
    getAppStatus: vi.fn(),
  },
  dbToolkitApi: {
    listConnections: vi.fn(),
    testConnection: vi.fn(),
    executeQuery: vi.fn(),
  },
  healthApi: {
    checkHealth: vi.fn(),
  },
}))

// 添加 WebSocket mock 到全局
const MockWebSocket = vi.fn().mockImplementation(() => ({
  onopen: null,
  onmessage: null,
  onclose: null,
  onerror: null,
  close: vi.fn(),
  send: vi.fn(),
  readyState: 1, // WebSocket.OPEN
}))
;(MockWebSocket as any).CONNECTING = 0
;(MockWebSocket as any).OPEN = 1
;(MockWebSocket as any).CLOSING = 2
;(MockWebSocket as any).CLOSED = 3

vi.stubGlobal('WebSocket', MockWebSocket)

global.window = global.window || {}
global.document = global.document || {
  querySelector: () => null,
  getElementById: () => null,
}
