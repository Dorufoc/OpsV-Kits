import { defineStore } from 'pinia'
import { ref } from 'vue'
import { request } from '@/api'
import { useDockerStore } from './dockerStore'

export interface StoreAppEnvConfig {
  key: string
  label: string
  type: 'string' | 'int' | 'password' | 'port'
  default?: string | number
  required?: boolean
  description?: string
}

export interface StoreApp {
  id: string
  name: string
  icon: string
  description: string
  category: string
  require_memory: number
  versions: string[]
  features: string[]
  recommended_for: string[]
  env_config: StoreAppEnvConfig[]
}

export interface AppSizeComponent {
  type: 'image' | 'container' | 'volume' | 'data_dir'
  name: string
  size: number
  size_human: string
  id?: string
  path?: string
  mountpoint?: string
}

export interface AppSizeInfo {
  app_id: string
  image_size: number
  image_size_human: string
  container_size: number
  container_size_human: string
  volume_size: number
  volume_size_human: string
  data_dir_size: number
  data_dir_size_human: string
  total_size: number
  total_size_human: string
  components: AppSizeComponent[]
}

export interface ImageVersionSize {
  version: string
  size: number
  size_human: string
  compressed_size: number
  compressed_size_human: string
  architecture: string
  os: string
  last_updated: string
  status: string
}

export interface ImageVersionSizes {
  app_id: string
  image_name: string | null
  versions: ImageVersionSize[]
  total_versions: number
  message?: string
}

export interface StoreAppStatus {
  app_id: string
  state: 'not_installed' | 'installing' | 'running' | 'stopped' | 'error'
  container_id?: string
  container_name?: string
  error_message?: string
}

export interface RegistryMirror {
  enabled: boolean
  urls: string[]
}

export interface InstallFormData {
  [key: string]: any
}

export interface InstallProgress {
  type: 'stage' | 'pull_progress' | 'pull_complete' | 'log' | 'complete' | 'error'
  stage?: string
  progress_percent?: number
  message?: string
  image?: string
  layer?: string
  action?: string
  current?: number
  total?: number
  success?: boolean
}

export const useDockerStoreStore = defineStore('dockerStore', () => {
  const dockerStore = useDockerStore()

  const apps = ref<StoreApp[]>([])
  const currentApp = ref<StoreApp | null>(null)
  const appStatuses = ref<Record<string, StoreAppStatus>>({})
  const appSizes = ref<Record<string, AppSizeInfo>>({})
  const imageVersionSizes = ref<Record<string, ImageVersionSizes>>({})
  const registryMirror = ref<RegistryMirror>({ enabled: false, urls: [] })
  const loading = ref(false)
  const installing = ref(false)
  const uninstalling = ref(false)
  const sizeLoading = ref<Record<string, boolean>>({})
  const versionSizeLoading = ref<Record<string, boolean>>({})

  // 安装进度相关状态
  const installProgress = ref<Record<string, InstallProgress>>({})
  const installProgressPercent = ref<Record<string, number>>({})
  const installProgressMessage = ref<Record<string, string>>({})

  async function fetchApps(category?: string) {
    const account_alias = dockerStore.currentAlias
    if (!account_alias) return
    loading.value = true
    try {
      const params: Record<string, any> = { account_alias }
      if (category) {
        params.category = category
      }
      const res = await request.get<StoreApp[]>('/docker-store/apps', { params })
      console.log('[DockerStore] fetchApps success:', res?.length || 0, 'apps')
      apps.value = res || []
      return res
    } catch (error) {
      console.error('[DockerStore] fetchApps error:', error)
      apps.value = []
      return []
    } finally {
      loading.value = false
    }
  }

  async function getApp(appId: string) {
    const account_alias = dockerStore.currentAlias
    if (!account_alias) return
    loading.value = true
    try {
      const res = await request.get<StoreApp>(`/docker-store/apps/${appId}`, {
        params: { account_alias },
      })
      currentApp.value = res
      return res
    } finally {
      loading.value = false
    }
  }

  async function installApp(appId: string, formData: InstallFormData) {
    const account_alias = dockerStore.currentAlias
    if (!account_alias) return
    installing.value = true
    try {
      const res = await request.post(`/docker-store/install/${appId}`, {
        account_alias,
        ...formData,
      })
      await fetchAppStatuses()
      return res
    } finally {
      installing.value = false
    }
  }

  function installAppWithProgress(
    appId: string,
    formData: InstallFormData,
  ): Promise<{ success: boolean; message?: string }> {
    return new Promise((resolve, reject) => {
      const account_alias = dockerStore.currentAlias
      if (!account_alias) {
        reject(new Error('未选择 SSH 服务器'))
        return
      }

      installing.value = true
      installProgress.value[appId] = { type: 'stage', stage: 'prepare', message: '正在连接...' }
      installProgressPercent.value[appId] = 0
      installProgressMessage.value[appId] = '正在准备安装...'

      // 设置应用状态为 installing
      appStatuses.value[appId] = {
        ...appStatuses.value[appId],
        app_id: appId,
        state: 'installing',
      }

      const wsUrl = `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/api/docker-store/ws/install/${appId}`
      const ws = new WebSocket(wsUrl)

      let heartbeatTimer: ReturnType<typeof setInterval> | null = null

      ws.onopen = () => {
        // 发送安装参数
        ws.send(JSON.stringify({
          account_alias,
          user_config: formData,
        }))

        // 心跳保活
        heartbeatTimer = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: 'ping' }))
          }
        }, 30000)
      }

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data) as InstallProgress
          installProgress.value[appId] = data

          if (data.type === 'stage') {
            installProgressMessage.value[appId] = data.message || ''
            if (data.stage === 'prepare') {
              installProgressPercent.value[appId] = 5
            } else if (data.stage === 'download') {
              installProgressPercent.value[appId] = 10
            } else if (data.stage === 'start') {
              installProgressPercent.value[appId] = 90
            }
          } else if (data.type === 'pull_progress') {
            if (data.progress_percent !== undefined && data.progress_percent >= 0) {
              // 下载阶段占 10% ~ 80%
              installProgressPercent.value[appId] = 10 + Math.min(data.progress_percent, 100) * 0.7
            }
            installProgressMessage.value[appId] = data.message || '正在下载镜像...'
          } else if (data.type === 'pull_complete') {
            installProgressMessage.value[appId] = data.message || '镜像下载完成'
            installProgressPercent.value[appId] = 80
          } else if (data.type === 'complete') {
            installProgressPercent.value[appId] = 100
            installProgressMessage.value[appId] = data.message || '安装完成'
            appStatuses.value[appId] = {
              ...appStatuses.value[appId],
              app_id: appId,
              state: 'running',
            }
            if (heartbeatTimer) clearInterval(heartbeatTimer)
            ws.close()
            installing.value = false
            resolve({ success: data.success ?? true, message: data.message })
          } else if (data.type === 'error') {
            installProgressMessage.value[appId] = data.message || '安装失败'
            appStatuses.value[appId] = {
              ...appStatuses.value[appId],
              app_id: appId,
              state: 'not_installed',
            }
            if (heartbeatTimer) clearInterval(heartbeatTimer)
            ws.close()
            installing.value = false
            reject(new Error(data.message || '安装失败'))
          }
        } catch {
          // 忽略非 JSON 消息
        }
      }

      ws.onerror = (err) => {
        if (heartbeatTimer) clearInterval(heartbeatTimer)
        installing.value = false
        appStatuses.value[appId] = {
          ...appStatuses.value[appId],
          app_id: appId,
          state: 'not_installed',
        }
        reject(new Error('WebSocket 连接失败'))
      }

      ws.onclose = () => {
        if (heartbeatTimer) clearInterval(heartbeatTimer)
        installing.value = false
      }
    })
  }

  async function uninstallApp(appId: string, purgeData: boolean = false) {
    const account_alias = dockerStore.currentAlias
    if (!account_alias) return
    uninstalling.value = true
    try {
      const res = await request.post(`/docker-store/uninstall/${appId}`, {
        account_alias,
        purge_data: purgeData,
      })
      delete appStatuses.value[appId]
      return res
    } finally {
      uninstalling.value = false
    }
  }

  async function fetchAppStatus(appId: string) {
    const account_alias = dockerStore.currentAlias
    if (!account_alias) return
    const res = await request.get<StoreAppStatus>(`/docker-store/status/${appId}`, {
      params: { account_alias },
    })
    appStatuses.value[appId] = res
    return res
  }

  async function fetchAppStatuses() {
    const account_alias = dockerStore.currentAlias
    if (!account_alias) return
    try {
      const res = await request.get<StoreAppStatus[]>('/docker-store/status', {
        params: { account_alias },
      })
      const map: Record<string, StoreAppStatus> = {}
      res.forEach(s => {
        map[s.app_id] = s
      })
      appStatuses.value = map
      return res
    } catch {
      return []
    }
  }

  async function fetchAppSize(appId: string) {
    const account_alias = dockerStore.currentAlias
    if (!account_alias) return
    sizeLoading.value[appId] = true
    try {
      const res = await request.get<AppSizeInfo>(`/docker-store/size/${appId}`, {
        params: { account_alias },
      })
      appSizes.value[appId] = res
      return res
    } catch (error) {
      console.error('[DockerStore] fetchAppSize error:', error)
    } finally {
      sizeLoading.value[appId] = false
    }
  }

  async function fetchImageVersionSizes(appId: string) {
    versionSizeLoading.value[appId] = true
    try {
      const res = await request.get<ImageVersionSizes>(`/docker-store/image-sizes/${appId}`)
      imageVersionSizes.value[appId] = res
      return res
    } catch (error) {
      console.error('[DockerStore] fetchImageVersionSizes error:', error)
    } finally {
      versionSizeLoading.value[appId] = false
    }
  }

  async function fetchRegistryMirrors() {
    const account_alias = dockerStore.currentAlias
    if (!account_alias) return
    try {
      const res = await request.get<any>('/docker-store/registry-mirrors', {
        params: { account_alias },
      })
      const mirrors = res?.mirrors || []
      registryMirror.value = { enabled: mirrors.length > 0, urls: mirrors }
      return res
    } catch {
      registryMirror.value = { enabled: false, urls: [] }
    }
  }

  async function configureRegistryMirror(mirrorUrl: string) {
    const account_alias = dockerStore.currentAlias
    if (!account_alias) return
    const res = await request.post('/docker-store/registry-mirrors', {
      account_alias,
      mirror_url: mirrorUrl,
    })
    await fetchRegistryMirrors()
    return res
  }

  return {
    apps,
    currentApp,
    appStatuses,
    appSizes,
    imageVersionSizes,
    registryMirror,
    loading,
    installing,
    uninstalling,
    sizeLoading,
    versionSizeLoading,
    installProgress,
    installProgressPercent,
    installProgressMessage,
    fetchApps,
    getApp,
    installApp,
    installAppWithProgress,
    uninstallApp,
    fetchAppStatus,
    fetchAppStatuses,
    fetchAppSize,
    fetchImageVersionSizes,
    fetchRegistryMirrors,
    configureRegistryMirror,
  }
})
