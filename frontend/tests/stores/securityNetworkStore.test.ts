import { describe, it, expect, vi, beforeEach } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useSecurityNetworkStore } from '@/stores/securityNetworkStore'
import { useDockerStore } from '@/stores/dockerStore'
import * as api from '@/api'

describe('SecurityNetwork Store', () => {
  let dockerStore: ReturnType<typeof useDockerStore>

  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    dockerStore = useDockerStore()
    dockerStore.setAccountAlias('test-server')
  })

  describe('状态初始化', () => {
    it('应该正确初始化 firewallBackend 为 null', () => {
      const store = useSecurityNetworkStore()
      expect(store.firewallBackend).toBeNull()
    })

    it('应该正确初始化 firewallRules 为空数组', () => {
      const store = useSecurityNetworkStore()
      expect(store.firewallRules).toEqual([])
    })

    it('应该正确初始化 sshConfig 为 null', () => {
      const store = useSecurityNetworkStore()
      expect(store.sshConfig).toBeNull()
    })

    it('应该正确初始化 sshKeys 为空数组', () => {
      const store = useSecurityNetworkStore()
      expect(store.sshKeys).toEqual([])
    })

    it('应该正确初始化 loginLogs 为空数组', () => {
      const store = useSecurityNetworkStore()
      expect(store.loginLogs).toEqual([])
    })

    it('应该正确初始化 fail2banStatus 为 null', () => {
      const store = useSecurityNetworkStore()
      expect(store.fail2banStatus).toBeNull()
    })

    it('应该正确初始化 bannedIps 为空数组', () => {
      const store = useSecurityNetworkStore()
      expect(store.bannedIps).toEqual([])
    })

    it('应该正确初始化 opsAuditLogs 为空数组', () => {
      const store = useSecurityNetworkStore()
      expect(store.opsAuditLogs).toEqual([])
    })

    it('应该正确初始化 networkOutput 为 null', () => {
      const store = useSecurityNetworkStore()
      expect(store.networkOutput).toBeNull()
    })

    it('应该正确初始化 loading 为 false', () => {
      const store = useSecurityNetworkStore()
      expect(store.loading).toBe(false)
    })

    it('应该正确初始化 loadingFirewall 为 false', () => {
      const store = useSecurityNetworkStore()
      expect(store.loadingFirewall).toBe(false)
    })

    it('应该正确初始化 loadingSsh 为 false', () => {
      const store = useSecurityNetworkStore()
      expect(store.loadingSsh).toBe(false)
    })

    it('应该正确初始化 loadingLogs 为 false', () => {
      const store = useSecurityNetworkStore()
      expect(store.loadingLogs).toBe(false)
    })

    it('应该正确初始化 loadingNetwork 为 false', () => {
      const store = useSecurityNetworkStore()
      expect(store.loadingNetwork).toBe(false)
    })
  })

  describe('loadFirewallBackend', () => {
    it('应该获取防火墙后端信息', async () => {
      const mockBackend = { backend: 'firewalld' as const, running: true }
      vi.mocked(api.securityNetworkApi.getFirewallBackend).mockResolvedValue(mockBackend as any)

      const store = useSecurityNetworkStore()
      const result = await store.loadFirewallBackend()

      expect(store.firewallBackend).toEqual(mockBackend)
      expect(result).toEqual(mockBackend)
    })

    it('请求期间 loadingFirewall 应该为 true', async () => {
      vi.mocked(api.securityNetworkApi.getFirewallBackend).mockImplementation(async () => {
        const store = useSecurityNetworkStore()
        expect(store.loadingFirewall).toBe(true)
        return { backend: 'ufw', running: true }
      })

      const store = useSecurityNetworkStore()
      await store.loadFirewallBackend()
      expect(store.loadingFirewall).toBe(false)
    })

    it('请求失败时 loadingFirewall 应该恢复为 false', async () => {
      vi.mocked(api.securityNetworkApi.getFirewallBackend).mockRejectedValue(new Error('Network error'))

      const store = useSecurityNetworkStore()
      await expect(store.loadFirewallBackend()).rejects.toThrow()
      expect(store.loadingFirewall).toBe(false)
    })

    it('当没有 alias 时应该直接返回', async () => {
      dockerStore.setAccountAlias('')
      const store = useSecurityNetworkStore()
      const result = await store.loadFirewallBackend()
      expect(result).toBeUndefined()
    })
  })

  describe('loadFirewallRules', () => {
    it('应该获取防火墙规则列表', async () => {
      const mockRules = [{ port: 80, protocol: 'tcp' as const, action: 'allow' as const }]
      vi.mocked(api.securityNetworkApi.getFirewallRules).mockResolvedValue(mockRules as any)

      const store = useSecurityNetworkStore()
      const result = await store.loadFirewallRules()

      expect(store.firewallRules).toEqual(mockRules)
    })

    it('请求期间 loadingFirewall 应该为 true', async () => {
      vi.mocked(api.securityNetworkApi.getFirewallRules).mockImplementation(async () => {
        const store = useSecurityNetworkStore()
        expect(store.loadingFirewall).toBe(true)
        return []
      })

      const store = useSecurityNetworkStore()
      await store.loadFirewallRules()
      expect(store.loadingFirewall).toBe(false)
    })
  })

  describe('addPortRule', () => {
    it('应该添加端口规则并刷新规则列表', async () => {
      vi.mocked(api.securityNetworkApi.addPortRule).mockResolvedValue({ success: true } as any)
      vi.mocked(api.securityNetworkApi.getFirewallRules).mockResolvedValue([] as any)

      const store = useSecurityNetworkStore()
      await store.addPortRule(8080, 'tcp', 'allow')

      expect(api.securityNetworkApi.addPortRule).toHaveBeenCalledWith('test-server', 8080, 'tcp', 'allow', undefined, undefined)
      expect(api.securityNetworkApi.getFirewallRules).toHaveBeenCalledWith('test-server')
    })

    it('应该支持 zone 和 permanent 参数', async () => {
      vi.mocked(api.securityNetworkApi.addPortRule).mockResolvedValue({} as any)
      vi.mocked(api.securityNetworkApi.getFirewallRules).mockResolvedValue([] as any)

      const store = useSecurityNetworkStore()
      await store.addPortRule(443, 'tcp', 'allow', 'public', true)

      expect(api.securityNetworkApi.addPortRule).toHaveBeenCalledWith('test-server', 443, 'tcp', 'allow', 'public', true)
    })

    it('当没有 alias 时应该直接返回', async () => {
      dockerStore.setAccountAlias('')
      const store = useSecurityNetworkStore()
      const result = await store.addPortRule(8080, 'tcp', 'allow')
      expect(result).toBeUndefined()
    })
  })

  describe('removePortRule', () => {
    it('应该删除端口规则并刷新规则列表', async () => {
      vi.mocked(api.securityNetworkApi.removePortRule).mockResolvedValue({} as any)
      vi.mocked(api.securityNetworkApi.getFirewallRules).mockResolvedValue([] as any)

      const store = useSecurityNetworkStore()
      await store.removePortRule(8080, 'tcp', 'allow')

      expect(api.securityNetworkApi.removePortRule).toHaveBeenCalledWith('test-server', 8080, 'tcp', 'allow', undefined)
    })
  })

  describe('addIpRule', () => {
    it('应该添加 IP 规则并刷新规则列表', async () => {
      vi.mocked(api.securityNetworkApi.addIpRule).mockResolvedValue({} as any)
      vi.mocked(api.securityNetworkApi.getFirewallRules).mockResolvedValue([] as any)

      const store = useSecurityNetworkStore()
      await store.addIpRule('192.168.1.1', 'deny', '恶意 IP')

      expect(api.securityNetworkApi.addIpRule).toHaveBeenCalledWith('test-server', '192.168.1.1', 'deny', '恶意 IP')
    })
  })

  describe('removeIpRule', () => {
    it('应该删除 IP 规则并刷新规则列表', async () => {
      vi.mocked(api.securityNetworkApi.removeIpRule).mockResolvedValue({} as any)
      vi.mocked(api.securityNetworkApi.getFirewallRules).mockResolvedValue([] as any)

      const store = useSecurityNetworkStore()
      await store.removeIpRule('192.168.1.1', 'deny')

      expect(api.securityNetworkApi.removeIpRule).toHaveBeenCalledWith('test-server', '192.168.1.1', 'deny')
    })
  })

  describe('loadSshConfig', () => {
    it('应该获取 SSH 配置', async () => {
      const mockConfig = { port: 22, password_auth: true, root_login: false, pubkey_auth: true }
      vi.mocked(api.securityNetworkApi.getSshConfig).mockResolvedValue(mockConfig as any)

      const store = useSecurityNetworkStore()
      const result = await store.loadSshConfig()

      expect(store.sshConfig).toEqual(mockConfig)
    })

    it('请求期间 loadingSsh 应该为 true', async () => {
      vi.mocked(api.securityNetworkApi.getSshConfig).mockImplementation(async () => {
        const store = useSecurityNetworkStore()
        expect(store.loadingSsh).toBe(true)
        return { port: 22, password_auth: true, root_login: false, pubkey_auth: true }
      })

      const store = useSecurityNetworkStore()
      await store.loadSshConfig()
      expect(store.loadingSsh).toBe(false)
    })
  })

  describe('changeSshPort', () => {
    it('应该修改 SSH 端口并刷新配置', async () => {
      vi.mocked(api.securityNetworkApi.changeSshPort).mockResolvedValue({} as any)
      vi.mocked(api.securityNetworkApi.getSshConfig).mockResolvedValue({ port: 2222, password_auth: true, root_login: false, pubkey_auth: true } as any)

      const store = useSecurityNetworkStore()
      await store.changeSshPort(2222)

      expect(api.securityNetworkApi.changeSshPort).toHaveBeenCalledWith('test-server', 2222)
      expect(api.securityNetworkApi.getSshConfig).toHaveBeenCalledWith('test-server')
    })
  })

  describe('togglePasswordAuth', () => {
    it('应该切换密码认证并刷新配置', async () => {
      vi.mocked(api.securityNetworkApi.togglePasswordAuth).mockResolvedValue({} as any)
      vi.mocked(api.securityNetworkApi.getSshConfig).mockResolvedValue({ port: 22, password_auth: false, root_login: false, pubkey_auth: true } as any)

      const store = useSecurityNetworkStore()
      await store.togglePasswordAuth(false)

      expect(api.securityNetworkApi.togglePasswordAuth).toHaveBeenCalledWith('test-server', false)
    })
  })

  describe('loadSshKeys', () => {
    it('应该获取 SSH 密钥列表', async () => {
      const mockKeys = [{ fingerprint: 'fp1', comment: 'user@host', type: 'RSA', bits: 2048 }]
      vi.mocked(api.securityNetworkApi.getSshKeys).mockResolvedValue(mockKeys as any)

      const store = useSecurityNetworkStore()
      const result = await store.loadSshKeys()

      expect(store.sshKeys).toEqual(mockKeys)
    })

    it('请求期间 loadingSsh 应该为 true', async () => {
      vi.mocked(api.securityNetworkApi.getSshKeys).mockImplementation(async () => {
        const store = useSecurityNetworkStore()
        expect(store.loadingSsh).toBe(true)
        return []
      })

      const store = useSecurityNetworkStore()
      await store.loadSshKeys()
      expect(store.loadingSsh).toBe(false)
    })
  })

  describe('addSshKey', () => {
    it('应该添加 SSH 密钥并刷新列表', async () => {
      vi.mocked(api.securityNetworkApi.addSshKey).mockResolvedValue({} as any)
      vi.mocked(api.securityNetworkApi.getSshKeys).mockResolvedValue([] as any)

      const store = useSecurityNetworkStore()
      await store.addSshKey('ssh-rsa AAAA...')

      expect(api.securityNetworkApi.addSshKey).toHaveBeenCalledWith('test-server', 'ssh-rsa AAAA...')
    })
  })

  describe('removeSshKey', () => {
    it('应该删除 SSH 密钥并刷新列表', async () => {
      vi.mocked(api.securityNetworkApi.removeSshKey).mockResolvedValue({} as any)
      vi.mocked(api.securityNetworkApi.getSshKeys).mockResolvedValue([] as any)

      const store = useSecurityNetworkStore()
      await store.removeSshKey('fp1')

      expect(api.securityNetworkApi.removeSshKey).toHaveBeenCalledWith('test-server', 'fp1')
    })
  })

  describe('generateSshKey', () => {
    it('应该生成 SSH 密钥并刷新列表', async () => {
      vi.mocked(api.securityNetworkApi.generateSshKey).mockResolvedValue({} as any)
      vi.mocked(api.securityNetworkApi.getSshKeys).mockResolvedValue([] as any)

      const store = useSecurityNetworkStore()
      await store.generateSshKey('ed25519')

      expect(api.securityNetworkApi.generateSshKey).toHaveBeenCalledWith('test-server', 'ed25519', undefined, undefined)
    })

    it('应该支持 bits 和 comment 参数', async () => {
      vi.mocked(api.securityNetworkApi.generateSshKey).mockResolvedValue({} as any)
      vi.mocked(api.securityNetworkApi.getSshKeys).mockResolvedValue([] as any)

      const store = useSecurityNetworkStore()
      await store.generateSshKey('rsa', 4096, 'deploy@server')

      expect(api.securityNetworkApi.generateSshKey).toHaveBeenCalledWith('test-server', 'rsa', 4096, 'deploy@server')
    })
  })

  describe('loadLoginLogs', () => {
    it('应该获取登录日志', async () => {
      const mockLogs = [{ time: '2024-01-01', user: 'root', ip: '192.168.1.1', status: 'success' as const, method: 'password' }]
      vi.mocked(api.securityNetworkApi.getLoginLogs).mockResolvedValue(mockLogs as any)

      const store = useSecurityNetworkStore()
      const result = await store.loadLoginLogs()

      expect(store.loginLogs).toEqual(mockLogs)
    })

    it('应该支持筛选参数', async () => {
      vi.mocked(api.securityNetworkApi.getLoginLogs).mockResolvedValue([] as any)

      const store = useSecurityNetworkStore()
      await store.loadLoginLogs({ user: 'root' })

      expect(api.securityNetworkApi.getLoginLogs).toHaveBeenCalledWith('test-server', { user: 'root' })
    })

    it('请求期间 loadingLogs 应该为 true', async () => {
      vi.mocked(api.securityNetworkApi.getLoginLogs).mockImplementation(async () => {
        const store = useSecurityNetworkStore()
        expect(store.loadingLogs).toBe(true)
        return []
      })

      const store = useSecurityNetworkStore()
      await store.loadLoginLogs()
      expect(store.loadingLogs).toBe(false)
    })
  })

  describe('loadFail2banStatus', () => {
    it('应该获取 Fail2ban 状态', async () => {
      const mockStatus = { running: true, jails: ['sshd'], banned_ips: { sshd: ['1.2.3.4', '5.6.7.8'] } }
      vi.mocked(api.securityNetworkApi.getFail2banStatus).mockResolvedValue(mockStatus as any)

      const store = useSecurityNetworkStore()
      const result = await store.loadFail2banStatus()

      expect(store.fail2banStatus).toEqual(mockStatus)
      expect(store.bannedIps).toEqual(['1.2.3.4', '5.6.7.8'])
    })

    it('应该正确提取多个 jail 的 banned IPs', async () => {
      const mockStatus = { running: true, jails: ['sshd', 'nginx'], banned_ips: { sshd: ['1.2.3.4'], nginx: ['10.0.0.1', '10.0.0.2'] } }
      vi.mocked(api.securityNetworkApi.getFail2banStatus).mockResolvedValue(mockStatus as any)

      const store = useSecurityNetworkStore()
      await store.loadFail2banStatus()

      expect(store.bannedIps).toEqual(['1.2.3.4', '10.0.0.1', '10.0.0.2'])
    })

    it('没有 banned_ips 时应该设为空数组', async () => {
      const mockStatus = { running: true, jails: [], banned_ips: {} }
      vi.mocked(api.securityNetworkApi.getFail2banStatus).mockResolvedValue(mockStatus as any)

      const store = useSecurityNetworkStore()
      await store.loadFail2banStatus()

      expect(store.bannedIps).toEqual([])
    })

    it('请求期间 loadingLogs 应该为 true', async () => {
      vi.mocked(api.securityNetworkApi.getFail2banStatus).mockImplementation(async () => {
        const store = useSecurityNetworkStore()
        expect(store.loadingLogs).toBe(true)
        return { running: true, jails: [], banned_ips: {} }
      })

      const store = useSecurityNetworkStore()
      await store.loadFail2banStatus()
      expect(store.loadingLogs).toBe(false)
    })
  })

  describe('unbanIp', () => {
    it('应该解封 IP 并刷新状态', async () => {
      vi.mocked(api.securityNetworkApi.unbanIp).mockResolvedValue({} as any)
      vi.mocked(api.securityNetworkApi.getFail2banStatus).mockResolvedValue({ running: true, jails: [], banned_ips: {} } as any)

      const store = useSecurityNetworkStore()
      await store.unbanIp('1.2.3.4')

      expect(api.securityNetworkApi.unbanIp).toHaveBeenCalledWith('test-server', '1.2.3.4', undefined)
    })

    it('应该支持 jail 参数', async () => {
      vi.mocked(api.securityNetworkApi.unbanIp).mockResolvedValue({} as any)
      vi.mocked(api.securityNetworkApi.getFail2banStatus).mockResolvedValue({ running: true, jails: [], banned_ips: {} } as any)

      const store = useSecurityNetworkStore()
      await store.unbanIp('1.2.3.4', 'sshd')

      expect(api.securityNetworkApi.unbanIp).toHaveBeenCalledWith('test-server', '1.2.3.4', 'sshd')
    })
  })

  describe('loadOpsAuditLogs', () => {
    it('应该获取运维审计日志', async () => {
      const mockLogs = [{ id: '1', time: '2024-01-01', user: 'admin', action: 'login', target: 'server' }]
      vi.mocked(api.securityNetworkApi.getOpsAuditLogs).mockResolvedValue(mockLogs as any)

      const store = useSecurityNetworkStore()
      const result = await store.loadOpsAuditLogs()

      expect(store.opsAuditLogs).toEqual(mockLogs)
    })

    it('应该支持筛选参数', async () => {
      vi.mocked(api.securityNetworkApi.getOpsAuditLogs).mockResolvedValue([] as any)

      const store = useSecurityNetworkStore()
      await store.loadOpsAuditLogs({ user: 'admin' })

      expect(api.securityNetworkApi.getOpsAuditLogs).toHaveBeenCalledWith({ user: 'admin' })
    })

    it('请求期间 loadingLogs 应该为 true', async () => {
      vi.mocked(api.securityNetworkApi.getOpsAuditLogs).mockImplementation(async () => {
        const store = useSecurityNetworkStore()
        expect(store.loadingLogs).toBe(true)
        return []
      })

      const store = useSecurityNetworkStore()
      await store.loadOpsAuditLogs()
      expect(store.loadingLogs).toBe(false)
    })

    it('请求失败时 loadingLogs 应该恢复为 false', async () => {
      vi.mocked(api.securityNetworkApi.getOpsAuditLogs).mockRejectedValue(new Error('Error'))

      const store = useSecurityNetworkStore()
      await expect(store.loadOpsAuditLogs()).rejects.toThrow()
      expect(store.loadingLogs).toBe(false)
    })
  })

  describe('runPing', () => {
    it('应该执行 ping 测试', async () => {
      const mockOutput = { output: 'PING 8.8.8.8: 64 bytes', error: undefined, exit_code: 0 }
      vi.mocked(api.securityNetworkApi.runPing).mockResolvedValue(mockOutput as any)

      const store = useSecurityNetworkStore()
      const result = await store.runPing('8.8.8.8')

      expect(store.networkOutput).toEqual(mockOutput)
    })

    it('请求期间 loadingNetwork 应该为 true', async () => {
      vi.mocked(api.securityNetworkApi.runPing).mockImplementation(async () => {
        const store = useSecurityNetworkStore()
        expect(store.loadingNetwork).toBe(true)
        return { output: '', exit_code: 0 }
      })

      const store = useSecurityNetworkStore()
      await store.runPing('8.8.8.8')
      expect(store.loadingNetwork).toBe(false)
    })

    it('当没有 alias 时应该直接返回', async () => {
      dockerStore.setAccountAlias('')
      const store = useSecurityNetworkStore()
      const result = await store.runPing('8.8.8.8')
      expect(result).toBeUndefined()
    })
  })

  describe('runTraceroute', () => {
    it('应该执行 traceroute 测试', async () => {
      const mockOutput = { output: 'traceroute to 8.8.8.8', error: undefined, exit_code: 0 }
      vi.mocked(api.securityNetworkApi.runTraceroute).mockResolvedValue(mockOutput as any)

      const store = useSecurityNetworkStore()
      const result = await store.runTraceroute('8.8.8.8')

      expect(store.networkOutput).toEqual(mockOutput)
      expect(api.securityNetworkApi.runTraceroute).toHaveBeenCalledWith('test-server', '8.8.8.8')
    })
  })

  describe('runPortScan', () => {
    it('应该执行端口扫描', async () => {
      const mockOutput = { output: 'PORT    STATE\n80/tcp  open', error: undefined, exit_code: 0 }
      vi.mocked(api.securityNetworkApi.runPortScan).mockResolvedValue(mockOutput as any)

      const store = useSecurityNetworkStore()
      const result = await store.runPortScan('192.168.1.1', '1-1000')

      expect(store.networkOutput).toEqual(mockOutput)
      expect(api.securityNetworkApi.runPortScan).toHaveBeenCalledWith('test-server', '192.168.1.1', '1-1000')
    })

    it('请求期间 loadingNetwork 应该为 true', async () => {
      vi.mocked(api.securityNetworkApi.runPortScan).mockImplementation(async () => {
        const store = useSecurityNetworkStore()
        expect(store.loadingNetwork).toBe(true)
        return { output: '', exit_code: 0 }
      })

      const store = useSecurityNetworkStore()
      await store.runPortScan('192.168.1.1', '1-1000')
      expect(store.loadingNetwork).toBe(false)
    })
  })
})
