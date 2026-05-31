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
export const mockPatch = vi.fn().mockResolvedValue({})

// Mock @/api/index
vi.mock('@/api/index', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/api/index')>()
  return {
    ...actual,
    request: {
      get: mockGet,
      post: mockPost,
      put: mockPut,
      delete: mockDelete,
      patch: mockPatch,
    },
  }
})

// Mock @/api (re-export from @/api/index)
vi.mock('@/api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/api/index')>()
  return {
    ...actual,
    request: {
      get: mockGet,
      post: mockPost,
      put: mockPut,
      delete: mockDelete,
      patch: mockPatch,
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
      getCronJobLogs: vi.fn(),
      listBackupPolicies: vi.fn(),
      createBackupPolicy: vi.fn(),
      updateBackupPolicy: vi.fn(),
      deleteBackupPolicy: vi.fn(),
      runBackupNow: vi.fn(),
      listBackupHistory: vi.fn(),
      downloadBackupFile: vi.fn(),
      listLogPolicies: vi.fn(),
      createLogPolicy: vi.fn(),
      updateLogPolicy: vi.fn(),
      deleteLogPolicy: vi.fn(),
      previewLogCleanup: vi.fn(),
      runLogCleanupNow: vi.fn(),
      getDiskAlert: vi.fn(),
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
      getStoreApps: vi.fn(),
      getStoreApp: vi.fn(),
      installStoreApp: vi.fn(),
      uninstallStoreApp: vi.fn(),
      getStoreAppStatus: vi.fn(),
      getRegistryMirrors: vi.fn(),
      configureRegistryMirror: vi.fn(),
    },
    dbToolkitApi: {
      listConnections: vi.fn(),
      testConnection: vi.fn(),
      executeQuery: vi.fn(),
    },
    healthApi: {
      checkHealth: vi.fn(),
    },
    securityNetworkApi: {
      getFirewallBackend: vi.fn(),
      getFirewallRules: vi.fn(),
      addPortRule: vi.fn(),
      removePortRule: vi.fn(),
      addIpRule: vi.fn(),
      removeIpRule: vi.fn(),
      getSshConfig: vi.fn(),
      changeSshPort: vi.fn(),
      togglePasswordAuth: vi.fn(),
      getSshKeys: vi.fn(),
      addSshKey: vi.fn(),
      removeSshKey: vi.fn(),
      generateSshKey: vi.fn(),
      getLoginLogs: vi.fn(),
      getFail2banStatus: vi.fn(),
      unbanIp: vi.fn(),
      getOpsAuditLogs: vi.fn(),
      runPing: vi.fn(),
      runTraceroute: vi.fn(),
      runPortScan: vi.fn(),
    },
    eventTriggerApi: {
      listSources: vi.fn(),
      getSource: vi.fn(),
      createSource: vi.fn(),
      updateSource: vi.fn(),
      deleteSource: vi.fn(),
      listRoutes: vi.fn(),
      createRoute: vi.fn(),
      updateRoute: vi.fn(),
      deleteRoute: vi.fn(),
      listLogs: vi.fn(),
      replayEvent: vi.fn(),
    },
    healthProbeApi: {
      listTargets: vi.fn(),
      getTarget: vi.fn(),
      createTarget: vi.fn(),
      updateTarget: vi.fn(),
      deleteTarget: vi.fn(),
      probeNow: vi.fn(),
      getLogs: vi.fn(),
      getStatistics: vi.fn(),
      getOverview: vi.fn(),
    },
    workflowApi: {
      list: vi.fn(),
      get: vi.fn(),
      create: vi.fn(),
      update: vi.fn(),
      delete: vi.fn(),
      validate: vi.fn(),
      saveVersion: vi.fn(),
      listVersions: vi.fn(),
      rollback: vi.fn(),
      exportWorkflow: vi.fn(),
      importWorkflow: vi.fn(),
      listTemplates: vi.fn(),
      createFromTemplate: vi.fn(),
      execute: vi.fn(),
      pauseExecution: vi.fn(),
      resumeExecution: vi.fn(),
      cancelExecution: vi.fn(),
      listExecutions: vi.fn(),
      getExecution: vi.fn(),
      listNodeExecutions: vi.fn(),
    },
    schedulerApi: {
      listTasks: vi.fn().mockResolvedValue({}),
      getTask: vi.fn().mockResolvedValue({}),
      createTask: vi.fn().mockResolvedValue({}),
      updateTask: vi.fn().mockResolvedValue({}),
      deleteTask: vi.fn().mockResolvedValue({}),
      toggleTask: vi.fn().mockResolvedValue({}),
      runTask: vi.fn().mockResolvedValue({}),
      listExecutions: vi.fn().mockResolvedValue({}),
      getExecution: vi.fn().mockResolvedValue({}),
      retryExecution: vi.fn().mockResolvedValue({}),
      getStatus: vi.fn().mockResolvedValue({}),
    },
    default: {
      get: mockGet,
      post: mockPost,
      put: mockPut,
      delete: mockDelete,
      interceptors: {
        request: { use: vi.fn(), eject: vi.fn() },
        response: { use: vi.fn(), eject: vi.fn() },
      },
    },
  }
})

// 添加 WebSocket mock 到全局
const MockWebSocket = vi.fn().mockImplementation(function(this: any) {
  this.onopen = null
  this.onmessage = null
  this.onclose = null
  this.onerror = null
  this.close = vi.fn()
  this.send = vi.fn()
  this.readyState = 1
  const self = this
  Promise.resolve().then(() => {
    if (self.onopen) self.onopen()
  })
})
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
