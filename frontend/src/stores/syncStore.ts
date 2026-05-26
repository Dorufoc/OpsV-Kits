import { defineStore } from 'pinia'
import { ref } from 'vue'
import { request } from '@/api'

export type SyncStatus = 'idle' | 'scanning' | 'syncing' | 'completed' | 'error'

export interface SyncProgress {
  total: number
  transferred: number
  current_file: string
  bytes_transferred: number
  speed: string
}

export const useSyncStore = defineStore('sync', () => {
  const syncStatus = ref<SyncStatus>('idle')
  const progress = ref<SyncProgress>({
    total: 0,
    transferred: 0,
    current_file: '',
    bytes_transferred: 0,
    speed: '',
  })
  const currentTaskId = ref('')
  const syncLogs = ref<string[]>([])

  async function startSync(params: { local_path: string; remote_path: string; ssh_alias: string }) {
    syncStatus.value = 'scanning'
    syncLogs.value = []
    try {
      const res = await request.post<{ task_id: string }>('/sync/start', params)
      currentTaskId.value = res.task_id
      syncStatus.value = 'syncing'
      return res
    } catch (e) {
      syncStatus.value = 'error'
      throw e
    }
  }

  async function stopSync() {
    await request.post('/sync/stop', { task_id: currentTaskId.value })
    syncStatus.value = 'idle'
    currentTaskId.value = ''
  }

  async function getSyncStatus() {
    const res = await request.get<{ status: SyncStatus; progress: SyncProgress; logs: string[] }>(
      `/sync/status/${currentTaskId.value}`
    )
    syncStatus.value = res.status
    progress.value = res.progress
    if (res.logs) {
      syncLogs.value = res.logs
    }
    return res
  }

  function resetStatus() {
    syncStatus.value = 'idle'
    progress.value = {
      total: 0,
      transferred: 0,
      current_file: '',
      bytes_transferred: 0,
      speed: '',
    }
    currentTaskId.value = ''
    syncLogs.value = []
  }

  return {
    syncStatus,
    progress,
    currentTaskId,
    syncLogs,
    startSync,
    stopSync,
    getSyncStatus,
    resetStatus,
  }
})
