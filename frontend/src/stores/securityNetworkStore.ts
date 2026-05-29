import { defineStore } from 'pinia'
import { ref } from 'vue'
import {
  securityNetworkApi,
  type FirewallBackend,
  type FirewallRule,
  type SshConfig,
  type SshKey,
  type LoginLogEntry,
  type Fail2banStatus,
  type OpsAuditLogEntry,
  type NetworkOutput,
} from '@/api'
import { useDockerStore } from './dockerStore'

export const useSecurityNetworkStore = defineStore('securityNetwork', () => {
  const dockerStore = useDockerStore()

  const firewallBackend = ref<FirewallBackend | null>(null)
  const firewallRules = ref<FirewallRule[]>([])
  const sshConfig = ref<SshConfig | null>(null)
  const sshKeys = ref<SshKey[]>([])
  const loginLogs = ref<LoginLogEntry[]>([])
  const fail2banStatus = ref<Fail2banStatus | null>(null)
  const bannedIps = ref<string[]>([])
  const opsAuditLogs = ref<OpsAuditLogEntry[]>([])
  const networkOutput = ref<NetworkOutput | null>(null)

  const loading = ref(false)
  const loadingFirewall = ref(false)
  const loadingSsh = ref(false)
  const loadingLogs = ref(false)
  const loadingNetwork = ref(false)

  async function loadFirewallBackend() {
    const alias = dockerStore.currentAlias
    if (!alias) return
    loadingFirewall.value = true
    try {
      const res = await securityNetworkApi.getFirewallBackend(alias)
      firewallBackend.value = res
      return res
    } finally {
      loadingFirewall.value = false
    }
  }

  async function loadFirewallRules() {
    const alias = dockerStore.currentAlias
    if (!alias) return
    loadingFirewall.value = true
    try {
      const res = await securityNetworkApi.getFirewallRules(alias)
      firewallRules.value = res
      return res
    } finally {
      loadingFirewall.value = false
    }
  }

  async function addPortRule(
    port: number,
    protocol: string,
    action: string,
    zone?: string,
    permanent?: boolean
  ) {
    const alias = dockerStore.currentAlias
    if (!alias) return
    const res = await securityNetworkApi.addPortRule(alias, port, protocol, action, zone, permanent)
    await loadFirewallRules()
    return res
  }

  async function removePortRule(port: number, protocol: string, action: string, zone?: string) {
    const alias = dockerStore.currentAlias
    if (!alias) return
    const res = await securityNetworkApi.removePortRule(alias, port, protocol, action, zone)
    await loadFirewallRules()
    return res
  }

  async function addIpRule(ip: string, action: string, remark?: string) {
    const alias = dockerStore.currentAlias
    if (!alias) return
    const res = await securityNetworkApi.addIpRule(alias, ip, action, remark)
    await loadFirewallRules()
    return res
  }

  async function removeIpRule(ip: string, action: string) {
    const alias = dockerStore.currentAlias
    if (!alias) return
    const res = await securityNetworkApi.removeIpRule(alias, ip, action)
    await loadFirewallRules()
    return res
  }

  async function loadSshConfig() {
    const alias = dockerStore.currentAlias
    if (!alias) return
    loadingSsh.value = true
    try {
      const res = await securityNetworkApi.getSshConfig(alias)
      sshConfig.value = res
      return res
    } finally {
      loadingSsh.value = false
    }
  }

  async function changeSshPort(port: number) {
    const alias = dockerStore.currentAlias
    if (!alias) return
    const res = await securityNetworkApi.changeSshPort(alias, port)
    await loadSshConfig()
    return res
  }

  async function togglePasswordAuth(enabled: boolean) {
    const alias = dockerStore.currentAlias
    if (!alias) return
    const res = await securityNetworkApi.togglePasswordAuth(alias, enabled)
    await loadSshConfig()
    return res
  }

  async function loadSshKeys() {
    const alias = dockerStore.currentAlias
    if (!alias) return
    loadingSsh.value = true
    try {
      const res = await securityNetworkApi.getSshKeys(alias)
      sshKeys.value = res
      return res
    } finally {
      loadingSsh.value = false
    }
  }

  async function addSshKey(publicKey: string) {
    const alias = dockerStore.currentAlias
    if (!alias) return
    const res = await securityNetworkApi.addSshKey(alias, publicKey)
    await loadSshKeys()
    return res
  }

  async function removeSshKey(fingerprintOrComment: string) {
    const alias = dockerStore.currentAlias
    if (!alias) return
    const res = await securityNetworkApi.removeSshKey(alias, fingerprintOrComment)
    await loadSshKeys()
    return res
  }

  async function generateSshKey(algorithm: string, bits?: number, comment?: string) {
    const alias = dockerStore.currentAlias
    if (!alias) return
    const res = await securityNetworkApi.generateSshKey(alias, algorithm, bits, comment)
    await loadSshKeys()
    return res
  }

  async function loadLoginLogs(filters?: Record<string, any>) {
    const alias = dockerStore.currentAlias
    if (!alias) return
    loadingLogs.value = true
    try {
      const res = await securityNetworkApi.getLoginLogs(alias, filters)
      loginLogs.value = res
      return res
    } finally {
      loadingLogs.value = false
    }
  }

  async function loadFail2banStatus() {
    const alias = dockerStore.currentAlias
    if (!alias) return
    loadingLogs.value = true
    try {
      const res = await securityNetworkApi.getFail2banStatus(alias)
      fail2banStatus.value = res
      const ips: string[] = []
      if (res.banned_ips) {
        Object.values(res.banned_ips).forEach((jailIps: any) => {
          ips.push(...jailIps)
        })
      }
      bannedIps.value = ips
      return res
    } finally {
      loadingLogs.value = false
    }
  }

  async function unbanIp(ip: string, jail?: string) {
    const alias = dockerStore.currentAlias
    if (!alias) return
    const res = await securityNetworkApi.unbanIp(alias, ip, jail)
    await loadFail2banStatus()
    return res
  }

  async function loadOpsAuditLogs(filters?: Record<string, any>) {
    loadingLogs.value = true
    try {
      const res = await securityNetworkApi.getOpsAuditLogs(filters)
      opsAuditLogs.value = res
      return res
    } finally {
      loadingLogs.value = false
    }
  }

  async function runPing(target: string) {
    const alias = dockerStore.currentAlias
    if (!alias) return
    loadingNetwork.value = true
    try {
      const res = await securityNetworkApi.runPing(alias, target)
      networkOutput.value = res
      return res
    } finally {
      loadingNetwork.value = false
    }
  }

  async function runTraceroute(target: string) {
    const alias = dockerStore.currentAlias
    if (!alias) return
    loadingNetwork.value = true
    try {
      const res = await securityNetworkApi.runTraceroute(alias, target)
      networkOutput.value = res
      return res
    } finally {
      loadingNetwork.value = false
    }
  }

  async function runPortScan(target: string, portRange: string) {
    const alias = dockerStore.currentAlias
    if (!alias) return
    loadingNetwork.value = true
    try {
      const res = await securityNetworkApi.runPortScan(alias, target, portRange)
      networkOutput.value = res
      return res
    } finally {
      loadingNetwork.value = false
    }
  }

  return {
    firewallBackend,
    firewallRules,
    sshConfig,
    sshKeys,
    loginLogs,
    fail2banStatus,
    bannedIps,
    opsAuditLogs,
    networkOutput,
    loading,
    loadingFirewall,
    loadingSsh,
    loadingLogs,
    loadingNetwork,
    loadFirewallBackend,
    loadFirewallRules,
    addPortRule,
    removePortRule,
    addIpRule,
    removeIpRule,
    loadSshConfig,
    changeSshPort,
    togglePasswordAuth,
    loadSshKeys,
    addSshKey,
    removeSshKey,
    generateSshKey,
    loadLoginLogs,
    loadFail2banStatus,
    unbanIp,
    loadOpsAuditLogs,
    runPing,
    runTraceroute,
    runPortScan,
  }
})
