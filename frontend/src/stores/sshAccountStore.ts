import { defineStore } from 'pinia'
import { ref } from 'vue'
import { request } from '@/api'

export interface SshAccount {
  alias: string
  host: string
  port: number
  username: string
  auth_type: 'password' | 'key' | 'agent'
  password?: string
  private_key?: string
  key_passphrase?: string
  group?: string
  default?: boolean
  status?: 'online' | 'offline' | 'unknown'
  last_connected?: string
  workplace_path?: string
}

export interface SshGroup {
  name: string
  accounts: string[]
}

export const useSshAccountStore = defineStore('sshAccount', () => {
  const accounts = ref<SshAccount[]>([])
  const groups = ref<SshGroup[]>([])
  const defaultAlias = ref('')
  const loading = ref(false)

  async function fetchAccounts() {
    loading.value = true
    try {
      const res = await request.get<SshAccount[]>('/accounts')
      accounts.value = res
      const defaultAcc = accounts.value.find(a => a.default)
      if (defaultAcc) {
        defaultAlias.value = defaultAcc.alias
      }
    } finally {
      loading.value = false
    }
  }

  async function createAccount(data: SshAccount) {
    const res = await request.post<SshAccount>('/accounts', data)
    accounts.value.push(res)
    return res
  }

  async function updateAccount(alias: string, data: Partial<SshAccount>) {
    const res = await request.put<SshAccount>(`/accounts/${alias}`, data)
    const index = accounts.value.findIndex(a => a.alias === alias)
    if (index !== -1) {
      accounts.value[index] = res
    }
    return res
  }

  async function deleteAccount(alias: string) {
    await request.delete(`/accounts/${alias}`)
    accounts.value = accounts.value.filter(a => a.alias !== alias)
    if (defaultAlias.value === alias) {
      defaultAlias.value = ''
    }
  }

  async function testConnection(alias: string) {
    const res = await request.post<{ success: boolean; message: string }>(`/accounts/${alias}/test`)
    const account = accounts.value.find(a => a.alias === alias)
    if (account) {
      account.status = res.success ? 'online' : 'offline'
    }
    return res
  }

  async function setDefault(alias: string) {
    await request.post(`/accounts/${alias}/default`)
    accounts.value.forEach(a => {
      a.default = a.alias === alias
    })
    defaultAlias.value = alias
  }

  async function fetchGroups() {
    const res = await request.get<SshGroup[]>('/accounts/groups')
    groups.value = res
  }

  return {
    accounts,
    groups,
    defaultAlias,
    loading,
    fetchAccounts,
    createAccount,
    updateAccount,
    deleteAccount,
    testConnection,
    setDefault,
    fetchGroups,
  }
})
