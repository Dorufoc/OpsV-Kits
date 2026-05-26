import { defineStore } from 'pinia'
import { ref } from 'vue'
import { request } from '@/api'

export interface DockerContainer {
  id: string
  name: string
  image: string
  status: string
  state: 'running' | 'exited' | 'paused' | 'created'
  ports: string
  created: string
  command?: string
  cpu_usage?: string
  memory_usage?: string
}

export interface DockerImage {
  id: string
  repository: string
  tag: string
  size: string
  created: string
  in_use: boolean
}

export interface DockerNetwork {
  id: string
  name: string
  driver: string
  scope: string
  containers: number
}

export interface DockerVolume {
  name: string
  driver: string
  mountpoint: string
  size: string
  in_use: boolean
}

export interface ComposeProject {
  name: string
  path: string
  status: string
  services: string[]
}

export interface DockerInfo {
  version: string
  daemon_status: 'running' | 'stopped'
  user_permission: string
  docker_group: boolean
}

export const useDockerStore = defineStore('docker', () => {
  const currentAlias = ref('')
  const dockerInfo = ref<DockerInfo>({
    version: '',
    daemon_status: 'stopped',
    user_permission: '',
    docker_group: false,
  })
  const containers = ref<DockerContainer[]>([])
  const images = ref<DockerImage[]>([])
  const networks = ref<DockerNetwork[]>([])
  const volumes = ref<DockerVolume[]>([])
  const composeProjects = ref<ComposeProject[]>([])
  const loading = ref(false)

  function setAccountAlias(alias: string) {
    currentAlias.value = alias
  }

  async function fetchInfo(alias?: string) {
    const a = alias || currentAlias.value
    if (!a) return
    const res = await request.get<any>('/docker/info', { params: { account_alias: a } })
    dockerInfo.value = {
      version: res.version || '',
      daemon_status: res.running ? 'running' : 'stopped',
      user_permission: res.installed ? '已安装' : '',
      docker_group: res.permissions?.in_docker_group || false,
    }
    return res
  }

  async function installDocker(alias?: string) {
    const a = alias || currentAlias.value
    return request.post('/docker/install', { account_alias: a })
  }

  async function fetchContainers(alias?: string) {
    const a = alias || currentAlias.value
    if (!a) return
    loading.value = true
    try {
      const res = await request.get<DockerContainer[]>('/docker/containers', { params: { account_alias: a } })
      containers.value = res
      return res
    } finally {
      loading.value = false
    }
  }

  async function startContainer(id: string, alias?: string) {
    const a = alias || currentAlias.value
    if (!a) return
    await request.post(`/docker/containers/${id}/start`, null, { params: { account_alias: a } })
    await fetchContainers(a)
  }

  async function stopContainer(id: string, alias?: string) {
    const a = alias || currentAlias.value
    if (!a) return
    await request.post(`/docker/containers/${id}/stop`, { account_alias: a })
    await fetchContainers(a)
  }

  async function restartContainer(id: string, alias?: string) {
    const a = alias || currentAlias.value
    if (!a) return
    await request.post(`/docker/containers/${id}/restart`, null, { params: { account_alias: a } })
    await fetchContainers(a)
  }

  async function killContainer(id: string, alias?: string) {
    const a = alias || currentAlias.value
    if (!a) return
    await request.post(`/docker/containers/${id}/kill`, null, { params: { account_alias: a } })
    await fetchContainers(a)
  }

  async function deleteContainer(id: string, alias?: string) {
    const a = alias || currentAlias.value
    if (!a) return
    await request.delete(`/docker/containers/${id}`, { params: { account_alias: a } })
    await fetchContainers(a)
  }

  async function pauseContainer(id: string, alias?: string) {
    const a = alias || currentAlias.value
    if (!a) return
    await request.post(`/docker/containers/${id}/pause`, null, { params: { account_alias: a } })
    await fetchContainers(a)
  }

  async function unpauseContainer(id: string, alias?: string) {
    const a = alias || currentAlias.value
    if (!a) return
    await request.post(`/docker/containers/${id}/unpause`, null, { params: { account_alias: a } })
    await fetchContainers(a)
  }

  async function fetchImages(alias?: string) {
    const a = alias || currentAlias.value
    if (!a) return
    const res = await request.get<DockerImage[]>('/docker/images', { params: { account_alias: a } })
    images.value = res
    return res
  }

  async function deleteImage(id: string, alias?: string) {
    const a = alias || currentAlias.value
    if (!a) return
    await request.delete(`/docker/images/${id}`, { params: { account_alias: a } })
    await fetchImages(a)
  }

  async function pullImage(params: { repository: string; tag?: string }, alias?: string) {
    const a = alias || currentAlias.value
    if (!a) return
    const res = await request.post('/docker/images/pull', { account_alias: a, image_name: params.tag ? `${params.repository}:${params.tag}` : params.repository })
    await fetchImages(a)
    return res
  }

  async function buildImage(params: { dockerfile_path: string; tag: string; context_path?: string }, alias?: string) {
    const a = alias || currentAlias.value
    if (!a) return
    const res = await request.post('/docker/images/build', {
      account_alias: a,
      tag: params.tag,
      dockerfile_path: params.dockerfile_path,
      context_path: params.context_path || params.dockerfile_path.replace(/\/[^/]+$/, ''),
    })
    await fetchImages(a)
    return res
  }

  async function pruneImages(alias?: string) {
    const a = alias || currentAlias.value
    if (!a) return
    await request.post('/docker/images/prune', null, { params: { account_alias: a } })
    await fetchImages(a)
  }

  async function fetchNetworks(alias?: string) {
    const a = alias || currentAlias.value
    if (!a) return
    const res = await request.get<DockerNetwork[]>('/docker/networks', { params: { account_alias: a } })
    networks.value = res
    return res
  }

  async function createNetwork(params: { name: string; driver?: string }, alias?: string) {
    const a = alias || currentAlias.value
    if (!a) return
    const res = await request.post('/docker/networks', { account_alias: a, ...params })
    await fetchNetworks(a)
    return res
  }

  async function deleteNetwork(id: string, alias?: string) {
    const a = alias || currentAlias.value
    if (!a) return
    await request.delete(`/docker/networks/${id}`, { params: { account_alias: a } })
    await fetchNetworks(a)
  }

  async function fetchVolumes(alias?: string) {
    const a = alias || currentAlias.value
    if (!a) return
    const res = await request.get<DockerVolume[]>('/docker/volumes', { params: { account_alias: a } })
    volumes.value = res
    return res
  }

  async function createVolume(params: { name: string }, alias?: string) {
    const a = alias || currentAlias.value
    if (!a) return
    const res = await request.post('/docker/volumes', { account_alias: a, ...params })
    await fetchVolumes(a)
    return res
  }

  async function deleteVolume(name: string, alias?: string) {
    const a = alias || currentAlias.value
    if (!a) return
    await request.delete(`/docker/volumes/${name}`, { params: { account_alias: a } })
    await fetchVolumes(a)
  }

  async function fetchComposeProjects(alias?: string) {
    const a = alias || currentAlias.value
    if (!a) return
    const res = await request.get<ComposeProject[]>('/docker/compose/projects', { params: { account_alias: a } })
    composeProjects.value = res
    return res
  }

  async function composeUp(params: { path: string; detached?: boolean }, alias?: string) {
    const a = alias || currentAlias.value
    if (!a) return
    return request.post('/docker/compose/up', { account_alias: a, project_path: params.path, detach: params.detached ?? false })
  }

  async function composeDown(params: { path: string }, alias?: string) {
    const a = alias || currentAlias.value
    if (!a) return
    return request.post('/docker/compose/down', { account_alias: a, project_path: params.path })
  }

  async function getContainerLogs(id: string, tail?: number, alias?: string) {
    const a = alias || currentAlias.value
    if (!a) return
    return request.get<string[]>(`/docker/containers/${id}/logs`, {
      params: { account_alias: a, tail },
    })
  }

  async function getContainerStats(id: string, alias?: string) {
    const a = alias || currentAlias.value
    if (!a) return
    return request.get(`/docker/containers/${id}/stats`, { params: { account_alias: a } })
  }

  async function execInContainer(id: string, command: string, alias?: string) {
    const a = alias || currentAlias.value
    if (!a) return
    return request.post(`/docker/containers/${id}/exec`, { account_alias: a, command })
  }

  return {
    currentAlias,
    dockerInfo,
    containers,
    images,
    networks,
    volumes,
    composeProjects,
    loading,
    setAccountAlias,
    fetchInfo,
    installDocker,
    fetchContainers,
    startContainer,
    stopContainer,
    restartContainer,
    killContainer,
    deleteContainer,
    pauseContainer,
    unpauseContainer,
    fetchImages,
    deleteImage,
    pullImage,
    buildImage,
    pruneImages,
    fetchNetworks,
    createNetwork,
    deleteNetwork,
    fetchVolumes,
    createVolume,
    deleteVolume,
    fetchComposeProjects,
    composeUp,
    composeDown,
    getContainerLogs,
    getContainerStats,
    execInContainer,
  }
})
