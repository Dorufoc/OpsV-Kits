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

export const useDockerStoreStore = defineStore('dockerStore', () => {
  const dockerStore = useDockerStore()

  const apps = ref<StoreApp[]>([])
  const currentApp = ref<StoreApp | null>(null)
  const appStatuses = ref<Record<string, StoreAppStatus>>({})
  const registryMirror = ref<RegistryMirror>({ enabled: false, urls: [] })
  const loading = ref(false)
  const installing = ref(false)
  const uninstalling = ref(false)

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
    registryMirror,
    loading,
    installing,
    uninstalling,
    fetchApps,
    getApp,
    installApp,
    uninstallApp,
    fetchAppStatus,
    fetchAppStatuses,
    fetchRegistryMirrors,
    configureRegistryMirror,
  }
})
