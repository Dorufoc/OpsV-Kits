import { defineStore } from 'pinia'
import { ref } from 'vue'
import { request } from '@/api'

export interface WebSshSession {
  id: string
  alias: string
  host: string
  port: number
  username: string
  status: 'connecting' | 'online' | 'offline'
  connected_at?: string
}

export interface HistoryRecord {
  session_id: string
  account_alias?: string
  host: string
  port: number
  username: string
  disconnected_at: string
}

export interface ConnectConfig {
  account_alias?: string
  host?: string
  port?: number
  username?: string
  auth_type?: 'password' | 'key' | 'agent'
  password?: string
  private_key?: string
  key_passphrase?: string
  totp_code?: string
}

export const useWebsshStore = defineStore('webssh', () => {
  const sessions = ref<WebSshSession[]>([])
  const historyRecords = ref<HistoryRecord[]>([])
  const activeSessionId = ref('')
  const loading = ref(false)

  async function listSessions() {
    loading.value = true
    try {
      const res: any = await request.get('/webssh/sessions')
      const rawSessions = res.sessions || res || []
      sessions.value = rawSessions.map((s: any) => ({
        id: s.session_id || s.id,
        alias: s.account_alias || s.alias || '',
        host: s.host,
        port: s.port,
        username: s.username,
        status: s.status === 'connected' ? 'online' : s.status === 'disconnected' ? 'offline' : s.status || 'offline',
        connected_at: s.connected_at || s.created_at,
      }))
      return sessions.value
    } finally {
      loading.value = false
    }
  }

  async function fetchHistory() {
    try {
      const res: any = await request.get('/webssh/sessions/history')
      historyRecords.value = (res.sessions || []).map((s: any) => ({
        session_id: s.session_id,
        account_alias: s.account_alias,
        host: s.host,
        port: s.port,
        username: s.username,
        disconnected_at: s.disconnected_at,
      }))
    } catch {}
  }

  async function connect(config: ConnectConfig) {
    const res: any = await request.post('/webssh/connect', config)
    const s = res.session || res
    const session: WebSshSession = {
      id: s.session_id || s.id,
      alias: s.account_alias || s.alias || '',
      host: s.host,
      port: s.port,
      username: s.username,
      status: 'online',
    }
    sessions.value.push(session)
    activeSessionId.value = session.id
    return session
  }

  async function disconnect(sessionId?: string) {
    const id = sessionId || activeSessionId.value
    await request.post('/webssh/disconnect', { session_id: id })
    sessions.value = sessions.value.filter(s => s.id !== id)
    if (activeSessionId.value === id) {
      activeSessionId.value = sessions.value[0]?.id || ''
    }
    await fetchHistory()
  }

  function setActiveSession(sessionId: string) {
    activeSessionId.value = sessionId
  }

  async function resizeTerminal(sessionId: string, cols: number, rows: number) {
    await request.post('/webssh/resize', { session_id: sessionId, width: cols, height: rows })
  }

  async function sendCommand(sessionId: string, command: string) {
    return request.post('/webssh/command', { session_id: sessionId, command })
  }

  async function getHistory(sessionId: string) {
    return request.get<string[]>(`/webssh/history/${sessionId}`)
  }

  return {
    sessions,
    historyRecords,
    activeSessionId,
    loading,
    listSessions,
    fetchHistory,
    connect,
    disconnect,
    setActiveSession,
    resizeTerminal,
    sendCommand,
    getHistory,
  }
})
