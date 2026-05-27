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
  let pollTimer: ReturnType<typeof setInterval> | null = null
  let logCallback: ((text: string) => void) | null = null
  let lastSyncMessage = ''

  function setLogCallback(cb: (text: string) => void) {
    logCallback = cb
  }

  async function startSync(params: { local_path: string; remote_path: string; account_alias: string }) {
    syncStatus.value = 'scanning'
    syncLogs.value = []
    try {
      const res = await request.post<{ sync_id: string }>('/sync/start', params)
      currentTaskId.value = res.sync_id
      syncStatus.value = 'syncing'
      startPolling()
      return res
    } catch (e) {
      syncStatus.value = 'error'
      throw e
    }
  }

  function startPolling() {
    stopPolling()
    pollTimer = setInterval(async () => {
      if (!currentTaskId.value) return
      try {
        const res = await request.get<any>(`/sync/status/${currentTaskId.value}`)
        syncStatus.value = res.status || 'syncing'

        if (res.phase === 'scanning') {
          syncStatus.value = 'scanning'
        }

        if (res.progress !== undefined) {
          const msg = res.message || res.phase || ''
          if (msg && msg !== lastSyncMessage) {
            if (logCallback) {
              let coloredMsg = msg
              if (msg.startsWith('新增:')) {
                coloredMsg = `\x1b[32m${msg}\x1b[0m`
              } else if (msg.startsWith('修改:')) {
                coloredMsg = `\x1b[33m${msg}\x1b[0m`
              } else if (msg.startsWith('删除:')) {
                coloredMsg = `\x1b[31m${msg}\x1b[0m`
              }
              logCallback(`\r\n${coloredMsg}`)
            }
          }
          lastSyncMessage = msg

          progress.value = {
            total: Math.round((res.progress || 0) * 100),
            transferred: Math.round((res.progress || 0) * 100),
            current_file: msg,
            bytes_transferred: 0,
            speed: '',
          }
        }

        if (res.status === 'completed') {
          stopPolling()
          const isNoop = res.message && res.message.includes('无需同步')
          progress.value.total = 100
          progress.value.transferred = isNoop ? 0 : 100
          progress.value.current_file = res.message || '同步完成'
          if (logCallback) {
            logCallback(`\r\n\x1b[32m${res.message || '同步完成'}\x1b[0m`)
            if (res.remote_path) {
              logCallback(`\r\n\x1b[36m同步目录: ${res.remote_path}\x1b[0m`)
            }
            if (res.diff_tree) {
              logCallback(`\r\n${res.diff_tree}\r\n`)
            }
            if (res.tree && !isNoop) {
              logCallback(`\r\n\x1b[36m远程目录结构:\x1b[0m\r\n${res.tree}\r\n`)
            }
            logCallback('\r\n')
          }
        } else if (res.status === 'failed') {
          stopPolling()
          progress.value.current_file = res.error || '同步失败'
          if (logCallback) logCallback(`\r\n\x1b[31m同步失败: ${res.error || ''}\x1b[0m\r\n`)
        } else if (res.status === 'stopped') {
          stopPolling()
        }
      } catch {
        if (syncStatus.value === 'idle') return
        stopPolling()
      }
    }, 1000)
  }

  function stopPolling() {
    if (pollTimer !== null) {
      clearInterval(pollTimer)
      pollTimer = null
    }
  }

  async function stopSync() {
    try {
      await request.post('/sync/stop', { sync_id: currentTaskId.value })
    } catch (e) {
      if (logCallback) logCallback(`\r\n\x1b[33m停止同步请求发送失败\x1b[0m\r\n`)
    }
    stopPolling()
    syncStatus.value = 'idle'
    currentTaskId.value = ''
  }

  async function getSyncStatus() {
    if (!currentTaskId.value) return
    try {
      const res = await request.get<any>(`/sync/status/${currentTaskId.value}`)
      syncStatus.value = res.status || 'syncing'
      if (res.progress !== undefined) {
        progress.value = {
          total: Math.round((res.progress || 0) * 100),
          transferred: Math.round((res.progress || 0) * 100),
          current_file: res.message || res.phase || '',
          bytes_transferred: 0,
          speed: '',
        }
      }
      return res
    } catch {
      stopPolling()
      throw new Error('获取状态失败')
    }
  }

  function resetStatus() {
    stopPolling()
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
    setLogCallback,
    startSync,
    stopSync,
    getSyncStatus,
    resetStatus,
  }
})
