<template>
  <div class="security-network-page">
    <Md3PageHeader title="安全与网络">
      <template #content>
        <span>安全管理与网络诊断</span>
      </template>
    </Md3PageHeader>
    <Md3Divider />

    <Md3Card class="account-card">
      <div class="account-selector">
        <span class="selector-label">目标服务器:</span>
        <Md3Select
          v-model="selectedAlias"
          :options="sshOptions"
          placeholder="选择 SSH 服务器"
          style="width: 280px"
          @update:model-value="onAccountChange"
        />
      </div>
    </Md3Card>

    <template v-if="selectedAlias">
      <Md3Tabs v-model="activeTab" :tabs="tabItems" class="page-tabs" />

      <div class="tab-content">
        <!-- 防火墙 -->
        <template v-if="activeTab === 'firewall'">
          <Md3Card :shadow="false" class="section-card">
            <template #header>
              <span><Md3Icon name="shield" class="header-icon" /> 防火墙状态</span>
              <div class="card-header-right">
                <Md3Tag :type="firewallBackend?.running ? 'success' : 'danger'" size="sm">
                  {{ firewallBackend?.running ? '运行中' : '已停止' }}
                </Md3Tag>
                <Md3Tag type="info" size="sm">
                  {{ firewallBackend?.backend || '未知' }}
                </Md3Tag>
                <Md3Button size="sm" @click="refreshFirewall" :loading="store.loadingFirewall">
                  <Md3Icon name="refresh" size="1em" />刷新
                </Md3Button>
              </div>
            </template>

            <div class="firewall-section">
              <div class="section-title">端口规则</div>
              <div class="rule-form">
                <div class="form-field">
                  <span class="field-label">端口</span>
                  <Md3Input v-model.number="newPort" placeholder="如 8080" type="number" class="port-input" />
                </div>
                <div class="form-field">
                  <span class="field-label">协议</span>
                  <Md3Select v-model="newProtocol" :options="protocolOptions" class="protocol-select" />
                </div>
                <div class="form-field">
                  <span class="field-label">动作</span>
                  <Md3Select v-model="newAction" :options="actionOptions" class="action-select" />
                </div>
                <Md3Button variant="primary" @click="addPortRule" :loading="store.loadingFirewall">
                  添加端口规则
                </Md3Button>
              </div>

              <Md3Table
                :columns="portRuleColumns"
                :data="portRules"
                stripe
                max-height="240"
                empty-text="暂无端口规则"
              >
                <template #action="{ row }">
                  <Md3Button icon="delete" size="sm" variant="danger" @click="removePortRule(row)">删除</Md3Button>
                </template>
              </Md3Table>
            </div>

            <Md3Divider />

            <div class="firewall-section">
              <div class="section-title">IP 规则</div>
              <div class="rule-form">
                <div class="form-field">
                  <span class="field-label">IP 地址</span>
                  <Md3Input v-model="newIp" placeholder="如 192.168.1.1" class="ip-input" />
                </div>
                <div class="form-field">
                  <span class="field-label">动作</span>
                  <Md3Select v-model="newIpAction" :options="actionOptions" class="action-select" />
                </div>
                <div class="form-field">
                  <span class="field-label">备注</span>
                  <Md3Input v-model="newIpRemark" placeholder="可选备注" class="remark-input" />
                </div>
                <Md3Button variant="primary" @click="addIpRule" :loading="store.loadingFirewall">
                  添加 IP 规则
                </Md3Button>
              </div>

              <Md3Table
                :columns="ipRuleColumns"
                :data="ipRules"
                stripe
                max-height="240"
                empty-text="暂无 IP 规则"
              >
                <template #action="{ row }">
                  <Md3Button icon="delete" size="sm" variant="danger" @click="removeIpRule(row)">删除</Md3Button>
                </template>
              </Md3Table>
            </div>
          </Md3Card>
        </template>

        <!-- SSH 安全 -->
        <template v-if="activeTab === 'ssh'">
          <Md3Card :shadow="false" class="section-card">
            <template #header>
              <span><Md3Icon name="key" class="header-icon" /> SSH 配置</span>
            </template>

            <div class="ssh-config-grid">
              <div class="config-item">
                <span class="config-label">当前端口</span>
                <Md3Tag type="primary" size="md">{{ sshConfig?.port || '-' }}</Md3Tag>
              </div>
              <div class="config-item">
                <span class="config-label">密码认证</span>
                <Md3Tag :type="sshConfig?.password_auth ? 'success' : 'danger'" size="md">
                  {{ sshConfig?.password_auth ? '已启用' : '已禁用' }}
                </Md3Tag>
              </div>
              <div class="config-item">
                <span class="config-label">Root 登录</span>
                <Md3Tag :type="sshConfig?.root_login ? 'warning' : 'info'" size="md">
                  {{ sshConfig?.root_login ? '允许' : '禁止' }}
                </Md3Tag>
              </div>
              <div class="config-item">
                <span class="config-label">公钥认证</span>
                <Md3Tag :type="sshConfig?.pubkey_auth ? 'success' : 'danger'" size="md">
                  {{ sshConfig?.pubkey_auth ? '已启用' : '已禁用' }}
                </Md3Tag>
              </div>
            </div>

            <Md3Divider />

            <div class="ssh-actions">
              <div class="ssh-action-row">
                <span class="action-label">修改 SSH 端口</span>
                <Md3Input v-model.number="sshPortInput" type="number" placeholder="新端口" class="port-input" />
                <Md3Button variant="primary" size="sm" @click="confirmChangeSshPort">修改</Md3Button>
              </div>
              <div class="ssh-action-row">
                <span class="action-label">密码认证</span>
                <Md3Switch
                  v-model="passwordAuthToggle"
                  on-text="开"
                  off-text="关"
                  @update:model-value="onPasswordAuthToggle"
                />
              </div>
            </div>
          </Md3Card>

          <Md3Card :shadow="false" class="section-card">
            <template #header>
              <span><Md3Icon name="lock" class="header-icon" /> 授权公钥</span>
              <div class="card-header-right">
                <Md3Button size="sm" @click="showAddKeyDialog = true">
                  <Md3Icon name="plus" size="1em" />添加
                </Md3Button>
                <Md3Button size="sm" variant="primary" @click="showGenerateKeyDialog = true">
                  <Md3Icon name="key" size="1em" />生成
                </Md3Button>
              </div>
            </template>

            <Md3Table
              :columns="sshKeyColumns"
              :data="sshKeys"
              stripe
              max-height="320"
              empty-text="暂无授权公钥"
            >
              <template #fingerprint="{ row }">
                <span class="mono-text">{{ row.fingerprint }}</span>
              </template>
              <template #action="{ row }">
                <Md3Button icon="delete" size="sm" variant="danger" @click="removeSshKey(row)">删除</Md3Button>
              </template>
            </Md3Table>
          </Md3Card>

          <Md3Dialog v-model:visible="showAddKeyDialog" title="添加公钥" width="520px">
            <Md3Input v-model="newPublicKey" label="公钥内容" placeholder="ssh-rsa / ssh-ed25519 ..." />
            <template #footer>
              <Md3Button @click="showAddKeyDialog = false">取消</Md3Button>
              <Md3Button variant="primary" @click="addSshKey">添加</Md3Button>
            </template>
          </Md3Dialog>

          <Md3Dialog v-model:visible="showGenerateKeyDialog" title="生成 SSH 密钥对" width="420px">
            <div class="dialog-form">
              <Md3Select v-model="keyAlgorithm" :options="algorithmOptions" label="算法" />
              <Md3Input v-model.number="keyBits" label="位数" type="number" />
              <Md3Input v-model="keyComment" label="注释" placeholder="可选" />
            </div>
            <template #footer>
              <Md3Button @click="showGenerateKeyDialog = false">取消</Md3Button>
              <Md3Button variant="primary" @click="generateSshKey">生成</Md3Button>
            </template>
          </Md3Dialog>
        </template>

        <!-- 安全审计 -->
        <template v-if="activeTab === 'audit'">
          <Md3Card :shadow="false" class="section-card">
            <template #header>
              <span><Md3Icon name="file-document" class="header-icon" /> 登录日志</span>
              <div class="card-header-right">
                <Md3Button size="sm" @click="refreshLoginLogs" :loading="store.loadingLogs">
                  <Md3Icon name="refresh" size="1em" />刷新
                </Md3Button>
              </div>
            </template>

            <div class="filter-bar">
              <div class="filter-field">
                <span class="filter-label">时间范围</span>
                <Md3Select v-model="logTimeFilter" :options="timeFilterOptions" class="filter-select" />
              </div>
              <div class="filter-field">
                <span class="filter-label">结果</span>
                <Md3Select v-model="logStatusFilter" :options="statusFilterOptions" class="filter-select" />
              </div>
              <div class="filter-field">
                <span class="filter-label">IP 地址</span>
                <Md3Input v-model="logIpFilter" placeholder="筛选 IP" class="filter-input" />
              </div>
              <Md3Button size="sm" @click="applyLogFilters">筛选</Md3Button>
            </div>

            <Md3Table
              :columns="loginLogColumns"
              :data="loginLogs"
              stripe
              max-height="320"
              empty-text="暂无登录日志"
            >
              <template #status="{ row }">
                <Md3Tag :type="row.status === 'success' ? 'success' : 'danger'" size="sm">
                  {{ row.status === 'success' ? '成功' : '失败' }}
                </Md3Tag>
              </template>
            </Md3Table>
          </Md3Card>

          <Md3Card :shadow="false" class="section-card">
            <template #header>
              <span><Md3Icon name="ban" class="header-icon" /> Fail2ban</span>
            </template>

            <div class="fail2ban-status">
              <div class="status-row">
                <span class="status-label">运行状态</span>
                <Md3Tag :type="fail2banStatus?.running ? 'success' : 'danger'" size="md">
                  {{ fail2banStatus?.running ? '运行中' : '未运行' }}
                </Md3Tag>
                <Md3Button v-if="!fail2banStatus?.running" size="sm" variant="primary" @click="installFail2ban">
                  安装/启动
                </Md3Button>
              </div>
              <div class="status-row" v-if="fail2banStatus?.jails?.length">
                <span class="status-label">监控 Jail</span>
                <Md3Tag v-for="jail in fail2banStatus.jails" :key="jail" type="info" size="sm" class="jail-tag">
                  {{ jail }}
                </Md3Tag>
              </div>
            </div>

            <Md3Divider />

            <div class="section-title">已封禁 IP</div>
            <Md3Table
              :columns="bannedIpColumns"
              :data="bannedIpRows"
              stripe
              max-height="240"
              empty-text="暂无封禁 IP"
            >
              <template #action="{ row }">
                <Md3Button size="sm" variant="warning" @click="unbanIp(row)">解封</Md3Button>
              </template>
            </Md3Table>
          </Md3Card>

          <Md3Card :shadow="false" class="section-card">
            <template #header>
              <span><Md3Icon name="clipboard-list" class="header-icon" /> 操作审计日志</span>
              <div class="card-header-right">
                <Md3Button size="sm" @click="refreshAuditWidget" :loading="auditStore.loading">
                  <Md3Icon name="refresh" size="1em" />刷新
                </Md3Button>
                <Md3Button size="sm" variant="primary" @click="goToAuditLog">
                  <Md3Icon name="arrow-right" size="1em" />查看全部
                </Md3Button>
              </div>
            </template>

            <div v-if="recentAuditLogs.length === 0" class="audit-widget-empty">暂无审计日志</div>
            <div v-else class="audit-widget-list">
              <div v-for="log in recentAuditLogs" :key="log.id" class="audit-widget-item">
                <span class="audit-widget-time">{{ formatAuditTime(log.timestamp) }}</span>
                <Md3Tag :type="log.status === 'success' ? 'success' : 'danger'" size="sm">{{ log.status === 'success' ? '成功' : '失败' }}</Md3Tag>
                <span class="audit-widget-user">{{ log.username }}</span>
                <span class="audit-widget-action">{{ log.action_type }}</span>
                <span class="audit-widget-module">{{ log.module }}</span>
              </div>
            </div>
          </Md3Card>
        </template>

        <!-- 网络工具 -->
        <template v-if="activeTab === 'network'">
          <Md3Card :shadow="false" class="section-card">
            <template #header>
              <span><Md3Icon name="signal" class="header-icon" /> Ping</span>
            </template>

            <div class="tool-form">
              <Md3Input v-model="pingTarget" placeholder="目标主机/IP，如 baidu.com" class="tool-input" />
              <Md3Button variant="primary" @click="runPing" :loading="store.loadingNetwork">
                <Md3Icon name="play" size="1em" />执行
              </Md3Button>
            </div>

            <div class="output-area" v-if="pingOutput">
              <pre class="output-pre">{{ pingOutput }}</pre>
            </div>

            <div class="stats-row" v-if="pingStats">
              <Md3Tag type="info" size="sm">发送: {{ pingStats.transmitted }}</Md3Tag>
              <Md3Tag type="info" size="sm">接收: {{ pingStats.received }}</Md3Tag>
              <Md3Tag type="info" size="sm">丢包: {{ pingStats.loss }}%</Md3Tag>
              <Md3Tag type="info" size="sm">最小: {{ pingStats.min }}ms</Md3Tag>
              <Md3Tag type="info" size="sm">平均: {{ pingStats.avg }}ms</Md3Tag>
              <Md3Tag type="info" size="sm">最大: {{ pingStats.max }}ms</Md3Tag>
            </div>
          </Md3Card>

          <Md3Card :shadow="false" class="section-card">
            <template #header>
              <span><Md3Icon name="map-marker-path" class="header-icon" /> TraceRoute</span>
            </template>

            <div class="tool-form">
              <Md3Input v-model="tracerouteTarget" placeholder="目标主机/IP，如 baidu.com" class="tool-input" />
              <Md3Button variant="primary" @click="runTraceroute" :loading="store.loadingNetwork">
                <Md3Icon name="play" size="1em" />执行
              </Md3Button>
            </div>

            <Md3Table
              v-if="tracerouteHops.length > 0"
              :columns="tracerouteColumns"
              :data="tracerouteHops"
              stripe
              max-height="400"
            />
            <div class="output-area" v-else-if="tracerouteRaw">
              <pre class="output-pre">{{ tracerouteRaw }}</pre>
            </div>
          </Md3Card>

          <Md3Card :shadow="false" class="section-card">
            <template #header>
              <span><Md3Icon name="radar" class="header-icon" /> 端口扫描</span>
            </template>

            <div class="tool-form">
              <Md3Input v-model="scanTarget" placeholder="目标主机/IP" class="tool-input" />
              <Md3Input v-model="scanPortRange" placeholder="端口范围，如 1-1000 或 22,80,443" class="tool-input" />
              <Md3Button variant="primary" @click="runPortScan" :loading="store.loadingNetwork">
                <Md3Icon name="play" size="1em" />扫描
              </Md3Button>
            </div>

            <Md3Table
              v-if="scanResults.length > 0"
              :columns="scanColumns"
              :data="scanResults"
              stripe
              max-height="400"
            />
            <div class="output-area" v-else-if="scanRaw">
              <pre class="output-pre">{{ scanRaw }}</pre>
            </div>
          </Md3Card>
        </template>
      </div>
    </template>

    <Md3Empty v-else description="请先选择一个 SSH 服务器" :image-size="80" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch, markRaw } from 'vue'
import { Md3Message, Md3Icon } from '@/components/md3'
import Md3Button from '@/components/Md3Button.vue'
import {
  Md3PageHeader,
  Md3Divider,
  Md3Card,
  Md3Tag,
  Md3Input,
  Md3Table,
  Md3Tabs,
  Md3Select,
  Md3Switch,
  Md3Empty,
  Md3Dialog,
} from '@/components/md3'
import { Md3Confirm } from '@/components/md3/Md3Confirm'
import { useSecurityNetworkStore } from '@/stores/securityNetworkStore'
import { useSshAccountStore } from '@/stores/sshAccountStore'
import { useDockerStore } from '@/stores/dockerStore'
import { useAuditLogStore } from '@/stores/auditLogStore'
import { useRouter } from 'vue-router'
import type { LoginLogEntry, OpsAuditLogEntry } from '@/api'

const store = useSecurityNetworkStore()
const sshStore = useSshAccountStore()
const dockerStore = useDockerStore()
const auditStore = useAuditLogStore()
const router = useRouter()

const selectedAlias = ref('')
const activeTab = ref('firewall')

const newPort = ref<number | ''>('')
const newProtocol = ref('tcp')
const newAction = ref('allow')
const newIp = ref('')
const newIpAction = ref('allow')
const newIpRemark = ref('')

const sshPortInput = ref<number | ''>('')
const passwordAuthToggle = ref(false)

const showAddKeyDialog = ref(false)
const showGenerateKeyDialog = ref(false)
const newPublicKey = ref('')
const keyAlgorithm = ref('ed25519')
const keyBits = ref(256)
const keyComment = ref('')

const logTimeFilter = ref('all')
const logStatusFilter = ref('all')
const logIpFilter = ref('')

const pingTarget = ref('')
const pingOutput = ref('')
const pingStats = ref<Record<string, string | number> | null>(null)

const tracerouteTarget = ref('')
const tracerouteHops = ref<Record<string, any>[]>([])
const tracerouteRaw = ref('')

const scanTarget = ref('')
const scanPortRange = ref('')
const scanResults = ref<Record<string, any>[]>([])
const scanRaw = ref('')

const tabItems = computed(() => [
  { label: '防火墙', value: 'firewall', icon: markRaw({ template: '<Md3Icon name="shield" size="1em" />', components: { Md3Icon } }) },
  { label: 'SSH 安全', value: 'ssh', icon: markRaw({ template: '<Md3Icon name="key" size="1em" />', components: { Md3Icon } }) },
  { label: '安全审计', value: 'audit', icon: markRaw({ template: '<Md3Icon name="clipboard-list" size="1em" />', components: { Md3Icon } }) },
  { label: '网络工具', value: 'network', icon: markRaw({ template: '<Md3Icon name="connection" size="1em" />', components: { Md3Icon } }) },
])

const sshOptions = computed(() =>
  sshStore.accounts.map(acc => ({
    label: `${acc.alias} (${acc.host})`,
    value: acc.alias,
  }))
)

const protocolOptions = [
  { label: 'TCP', value: 'tcp' },
  { label: 'UDP', value: 'udp' },
  { label: 'TCP/UDP', value: 'tcp/udp' },
]

const actionOptions = [
  { label: '允许', value: 'allow' },
  { label: '拒绝', value: 'deny' },
  { label: '丢弃', value: 'reject' },
]

const algorithmOptions = [
  { label: 'ED25519', value: 'ed25519' },
  { label: 'RSA', value: 'rsa' },
  { label: 'ECDSA', value: 'ecdsa' },
]

const timeFilterOptions = [
  { label: '全部', value: 'all' },
  { label: '最近1小时', value: '1h' },
  { label: '最近24小时', value: '24h' },
  { label: '最近7天', value: '7d' },
]

const statusFilterOptions = [
  { label: '全部', value: 'all' },
  { label: '成功', value: 'success' },
  { label: '失败', value: 'failed' },
]

const portRuleColumns = [
  { prop: 'port', label: '端口', width: '80px' },
  { prop: 'protocol', label: '协议', width: '90px' },
  { prop: 'action', label: '动作', width: '80px' },
  { prop: 'zone', label: '区域', width: '100px' },
  { prop: 'remark', label: '备注' },
  { prop: 'action_col', label: '操作', width: '90px' },
]

const ipRuleColumns = [
  { prop: 'source', label: 'IP 地址', width: '140px' },
  { prop: 'action', label: '动作', width: '80px' },
  { prop: 'remark', label: '备注' },
  { prop: 'action_col', label: '操作', width: '90px' },
]

const sshKeyColumns = [
  { prop: 'type', label: '类型', width: '100px' },
  { prop: 'bits', label: '位数', width: '80px' },
  { prop: 'fingerprint', label: '指纹' },
  { prop: 'comment', label: '注释', width: '180px' },
  { prop: 'action_col', label: '操作', width: '90px' },
]

const loginLogColumns = [
  { prop: 'time', label: '时间', width: '160px' },
  { prop: 'user', label: '用户', width: '100px' },
  { prop: 'ip', label: 'IP 地址', width: '140px' },
  { prop: 'status', label: '结果', width: '80px' },
  { prop: 'method', label: '方式', width: '100px' },
]

const bannedIpColumns = [
  { prop: 'ip', label: 'IP 地址', width: '160px' },
  { prop: 'jail', label: 'Jail', width: '140px' },
  { prop: 'action_col', label: '操作', width: '90px' },
]

const opsAuditColumns = [
  { prop: 'time', label: '时间', width: '160px' },
  { prop: 'user', label: '用户', width: '100px' },
  { prop: 'action', label: '操作', width: '120px' },
  { prop: 'target', label: '目标', width: '160px' },
  { prop: 'detail', label: '详情' },
  { prop: 'ip', label: '来源 IP', width: '130px' },
]

const tracerouteColumns = [
  { prop: 'hop', label: '跳数', width: '60px' },
  { prop: 'host', label: '主机' },
  { prop: 'ip', label: 'IP', width: '140px' },
  { prop: 'rtt1', label: 'RTT1', width: '90px' },
  { prop: 'rtt2', label: 'RTT2', width: '90px' },
  { prop: 'rtt3', label: 'RTT3', width: '90px' },
]

const scanColumns = [
  { prop: 'port', label: '端口', width: '80px' },
  { prop: 'state', label: '状态', width: '100px' },
  { prop: 'service', label: '服务' },
]

const firewallBackend = computed(() => store.firewallBackend)
const portRules = computed(() =>
  store.firewallRules
    .filter(r => r.port !== undefined)
    .map(r => ({ ...r, action_col: '' }))
)
const ipRules = computed(() =>
  store.firewallRules
    .filter(r => r.source !== undefined)
    .map(r => ({ ...r, action_col: '' }))
)

const sshConfig = computed(() => store.sshConfig)
const sshKeys = computed(() => store.sshKeys.map(k => ({ ...k, action_col: '' })))

const loginLogs = computed(() => store.loginLogs)
const fail2banStatus = computed(() => store.fail2banStatus)
const bannedIpRows = computed(() => {
  const rows: { ip: string; jail: string; action_col: string }[] = []
  if (store.fail2banStatus?.banned_ips) {
    Object.entries(store.fail2banStatus.banned_ips).forEach(([jail, ips]) => {
      ips.forEach(ip => rows.push({ ip, jail, action_col: '' }))
    })
  }
  return rows
})
const opsAuditLogs = computed(() => store.opsAuditLogs)
const recentAuditLogs = computed(() => auditStore.logs.slice(0, 5))

watch(() => store.sshConfig, (cfg) => {
  if (cfg) {
    passwordAuthToggle.value = cfg.password_auth
  }
}, { immediate: true })

function onAccountChange(value: string | number | (string | number)[]) {
  const alias = String(value)
  selectedAlias.value = alias
  dockerStore.setAccountAlias(alias)
  refreshTabData()
}

function refreshTabData() {
  if (activeTab.value === 'firewall') {
    refreshFirewall()
  } else if (activeTab.value === 'ssh') {
    refreshSsh()
  } else if (activeTab.value === 'audit') {
    refreshAudit()
  }
}

watch(activeTab, () => {
  refreshTabData()
})

async function refreshFirewall() {
  await store.loadFirewallBackend()
  await store.loadFirewallRules()
}

async function refreshSsh() {
  await store.loadSshConfig()
  await store.loadSshKeys()
}

async function refreshAudit() {
  await store.loadLoginLogs()
  await store.loadFail2banStatus()
  await store.loadOpsAuditLogs()
  refreshAuditWidget()
}

async function addPortRule() {
  const port = Number(newPort.value)
  if (!port || port < 1 || port > 65535) {
    Md3Message.warning('请输入有效端口 (1-65535)')
    return
  }
  try {
    await store.addPortRule(port, newProtocol.value, newAction.value)
    Md3Message.success('端口规则已添加')
    newPort.value = ''
  } catch {
    Md3Message.error('添加失败')
  }
}

async function removePortRule(row: Record<string, unknown>) {
  try {
    const confirmed = await Md3Confirm.show({
      title: '确认删除',
      message: `确定删除端口规则 ${row.port}/${row.protocol || 'tcp'} 吗？`,
      type: 'danger',
    })
    if (!confirmed) return
    await store.removePortRule(Number(row.port) || 0, String(row.protocol || 'tcp'), String(row.action))
    Md3Message.success('规则已删除')
  } catch {
    Md3Message.error('删除失败')
  }
}

async function addIpRule() {
  if (!newIp.value) {
    Md3Message.warning('请输入 IP 地址')
    return
  }
  try {
    await store.addIpRule(newIp.value, newIpAction.value, newIpRemark.value || undefined)
    Md3Message.success('IP 规则已添加')
    newIp.value = ''
    newIpRemark.value = ''
  } catch {
    Md3Message.error('添加失败')
  }
}

async function removeIpRule(row: Record<string, unknown>) {
  try {
    const confirmed = await Md3Confirm.show({
      title: '确认删除',
      message: `确定删除 IP 规则 ${row.source} 吗？`,
      type: 'danger',
    })
    if (!confirmed) return
    await store.removeIpRule(String(row.source || ''), String(row.action))
    Md3Message.success('规则已删除')
  } catch {
    Md3Message.error('删除失败')
  }
}

async function confirmChangeSshPort() {
  const port = Number(sshPortInput.value)
  if (!port || port < 1 || port > 65535) {
    Md3Message.warning('请输入有效端口 (1-65535)')
    return
  }
  try {
    const confirmed = await Md3Confirm.show({
      title: '危险操作',
      message: `确定将 SSH 端口修改为 ${port} 吗？修改后需要使用新端口连接。`,
      confirmText: '确定修改',
      cancelText: '取消',
      type: 'danger',
    })
    if (!confirmed) return
    await store.changeSshPort(port)
    Md3Message.success('SSH 端口已修改')
    sshPortInput.value = ''
  } catch {
    Md3Message.error('修改失败')
  }
}

async function onPasswordAuthToggle(val: boolean) {
  try {
    const confirmed = await Md3Confirm.show({
      title: '确认操作',
      message: `确定${val ? '启用' : '禁用'}密码认证吗？`,
      type: val ? 'default' : 'danger',
    })
    if (!confirmed) {
      passwordAuthToggle.value = !val
      return
    }
    await store.togglePasswordAuth(val)
    Md3Message.success(`密码认证已${val ? '启用' : '禁用'}`)
  } catch {
    passwordAuthToggle.value = !val
    Md3Message.error('操作失败')
  }
}

async function addSshKey() {
  if (!newPublicKey.value.trim()) {
    Md3Message.warning('请输入公钥内容')
    return
  }
  try {
    await store.addSshKey(newPublicKey.value.trim())
    Md3Message.success('公钥已添加')
    newPublicKey.value = ''
    showAddKeyDialog.value = false
  } catch {
    Md3Message.error('添加失败')
  }
}

async function removeSshKey(row: Record<string, unknown>) {
  try {
    const confirmed = await Md3Confirm.show({
      title: '确认删除',
      message: `确定删除公钥 ${row.comment || row.fingerprint} 吗？`,
      type: 'danger',
    })
    if (!confirmed) return
    await store.removeSshKey(String(row.fingerprint))
    Md3Message.success('公钥已删除')
  } catch {
    Md3Message.error('删除失败')
  }
}

async function generateSshKey() {
  try {
    await store.generateSshKey(keyAlgorithm.value, keyBits.value || undefined, keyComment.value || undefined)
    Md3Message.success('密钥对已生成')
    showGenerateKeyDialog.value = false
    keyComment.value = ''
  } catch {
    Md3Message.error('生成失败')
  }
}

async function applyLogFilters() {
  const filters: Record<string, any> = {}
  if (logTimeFilter.value !== 'all') filters.time_range = logTimeFilter.value
  if (logStatusFilter.value !== 'all') filters.status = logStatusFilter.value
  if (logIpFilter.value) filters.ip = logIpFilter.value
  await store.loadLoginLogs(filters)
}

async function refreshLoginLogs() {
  await applyLogFilters()
}

async function refreshOpsAuditLogs() {
  await store.loadOpsAuditLogs()
}

function refreshAuditWidget() {
  auditStore.loadRecentLogs(5)
}

function goToAuditLog() {
  router.push('/audit-log')
}

function formatAuditTime(ts: string) {
  return new Date(ts).toLocaleString('zh-CN')
}

async function installFail2ban() {
  try {
    const confirmed = await Md3Confirm.show({
      title: '安装 Fail2ban',
      message: '确定安装并启动 Fail2ban 吗？',
    })
    if (!confirmed) return
    Md3Message.info('安装功能待后端实现')
  } catch {}
}

async function unbanIp(row: Record<string, unknown>) {
  try {
    const confirmed = await Md3Confirm.show({
      title: '确认解封',
      message: `确定解封 IP ${row.ip} 吗？`,
    })
    if (!confirmed) return
    await store.unbanIp(String(row.ip), String(row.jail))
    Md3Message.success('IP 已解封')
  } catch {
    Md3Message.error('解封失败')
  }
}

function parsePingStats(output: string) {
  const stats: Record<string, string | number> = {}
  const transmittedMatch = output.match(/(\d+) packets transmitted/)
  const receivedMatch = output.match(/(\d+) received/)
  const lossMatch = output.match(/(\d+)% packet loss/)
  const rttMatch = output.match(/rtt min\/avg\/max\/mdev = ([\d.]+)\/([\d.]+)\/([\d.]+)\/([\d.]+)/)
  if (transmittedMatch) stats.transmitted = transmittedMatch[1]
  if (receivedMatch) stats.received = receivedMatch[1]
  if (lossMatch) stats.loss = lossMatch[1]
  if (rttMatch) {
    stats.min = rttMatch[1]
    stats.avg = rttMatch[2]
    stats.max = rttMatch[3]
  }
  return stats
}

function parseTraceroute(output: string) {
  const hops: Record<string, any>[] = []
  const lines = output.split('\n')
  lines.forEach(line => {
    const match = line.match(/^\s*(\d+)\s+([\w\-.]+)\s*\(([\d.]+)\)\s+([\d.]+)\s*ms\s*([\d.]+)?\s*ms?\s*([\d.]+)?\s*ms?/)
    if (match) {
      hops.push({
        hop: match[1],
        host: match[2],
        ip: match[3],
        rtt1: match[4] + ' ms',
        rtt2: match[5] ? match[5] + ' ms' : '-',
        rtt3: match[6] ? match[6] + ' ms' : '-',
      })
    } else {
      const simple = line.match(/^\s*(\d+)\s+([\d.]+)\s+([\d.]+)\s*ms/)
      if (simple) {
        hops.push({
          hop: simple[1],
          host: simple[2],
          ip: simple[2],
          rtt1: simple[3] + ' ms',
          rtt2: '-',
          rtt3: '-',
        })
      }
    }
  })
  return hops
}

function parsePortScan(output: string) {
  const results: Record<string, any>[] = []
  const lines = output.split('\n')
  lines.forEach(line => {
    const match = line.match(/(\d+)\/(tcp|udp)\s+(open|closed|filtered)\s+(\S+)/)
    if (match) {
      results.push({
        port: match[1] + '/' + match[2],
        state: match[3],
        service: match[4],
      })
    }
  })
  return results
}

async function runPing() {
  if (!pingTarget.value.trim()) {
    Md3Message.warning('请输入目标地址')
    return
  }
  pingOutput.value = ''
  pingStats.value = null
  try {
    const res = await store.runPing(pingTarget.value.trim())
    if (res) {
      pingOutput.value = res.output || res.error || ''
      if (res.output) {
        pingStats.value = parsePingStats(res.output)
      }
    }
  } catch {
    Md3Message.error('执行失败')
  }
}

async function runTraceroute() {
  if (!tracerouteTarget.value.trim()) {
    Md3Message.warning('请输入目标地址')
    return
  }
  tracerouteHops.value = []
  tracerouteRaw.value = ''
  try {
    const res = await store.runTraceroute(tracerouteTarget.value.trim())
    if (res) {
      const output = res.output || res.error || ''
      const hops = parseTraceroute(output)
      if (hops.length > 0) {
        tracerouteHops.value = hops
      } else {
        tracerouteRaw.value = output
      }
    }
  } catch {
    Md3Message.error('执行失败')
  }
}

async function runPortScan() {
  if (!scanTarget.value.trim()) {
    Md3Message.warning('请输入目标地址')
    return
  }
  if (!scanPortRange.value.trim()) {
    Md3Message.warning('请输入端口范围')
    return
  }
  scanResults.value = []
  scanRaw.value = ''
  try {
    const res = await store.runPortScan(scanTarget.value.trim(), scanPortRange.value.trim())
    if (res) {
      const output = res.output || res.error || ''
      const results = parsePortScan(output)
      if (results.length > 0) {
        scanResults.value = results
      } else {
        scanRaw.value = output
      }
    }
  } catch {
    Md3Message.error('执行失败')
  }
}

onMounted(async () => {
  await sshStore.fetchAccounts()
  const defaultAcc = sshStore.accounts.find(a => a.default)
  const firstAcc = sshStore.accounts[0]
  const alias = defaultAcc?.alias || firstAcc?.alias || ''
  if (alias) {
    selectedAlias.value = alias
    dockerStore.setAccountAlias(alias)
    refreshTabData()
  }
})
</script>

<style scoped>
.security-network-page {
  padding: 0;
}

.header-icon {
  width: 16px;
  height: 16px;
  vertical-align: -3px;
}

.account-card {
  margin-bottom: var(--md3-space-md);
}

.account-selector {
  display: flex;
  align-items: center;
  gap: var(--md3-space-sm);
}

.selector-label {
  font: var(--md3-type-body-medium);
  color: var(--md3-on-surface-variant);
  white-space: nowrap;
}

.page-tabs {
  margin-top: var(--md3-space-sm);
  margin-bottom: var(--md3-space-lg);
}

.tab-content {
  margin-top: var(--md3-space-md);
}

.section-card {
  margin-bottom: var(--md3-space-lg);
}

.section-card :deep(.md3-card-header) {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--md3-space-md) var(--md3-space-lg);
  font-weight: 600;
  font-size: 14px;
}

.card-header-right {
  display: flex;
  align-items: center;
  gap: var(--md3-space-sm);
}

.section-title {
  font-weight: 600;
  font-size: 13px;
  color: var(--md3-on-surface-variant);
  margin-bottom: var(--md3-space-sm);
}

.firewall-section {
  display: flex;
  flex-direction: column;
  gap: var(--md3-space-md);
}

.rule-form {
  display: flex;
  align-items: flex-end;
  gap: var(--md3-space-sm);
  flex-wrap: wrap;
}

.form-field {
  display: flex;
  flex-direction: column;
  gap: var(--md3-space-xs);
}

.field-label {
  font-size: 12px;
  color: var(--md3-on-surface-variant);
}

.port-input {
  width: 100px;
}

.protocol-select {
  width: 100px;
}

.action-select {
  width: 100px;
}

.ip-input {
  width: 160px;
}

.remark-input {
  width: 200px;
}

.ssh-config-grid {
  display: flex;
  gap: var(--md3-space-xl);
  flex-wrap: wrap;
}

.config-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
}

.config-label {
  color: var(--md3-on-surface-variant);
  white-space: nowrap;
}

.ssh-actions {
  display: flex;
  flex-direction: column;
  gap: var(--md3-space-md);
}

.ssh-action-row {
  display: flex;
  align-items: center;
  gap: var(--md3-space-sm);
  flex-wrap: wrap;
}

.action-label {
  font-size: 13px;
  color: var(--md3-on-surface-variant);
  min-width: 100px;
}

.mono-text {
  font-family: var(--md3-font-mono);
  font-size: 12px;
}

.dialog-form {
  display: flex;
  flex-direction: column;
  gap: var(--md3-space-md);
}

.filter-bar {
  display: flex;
  align-items: flex-end;
  gap: var(--md3-space-sm);
  flex-wrap: wrap;
  margin-bottom: var(--md3-space-md);
}

.filter-field {
  display: flex;
  flex-direction: column;
  gap: var(--md3-space-xs);
}

.filter-label {
  font-size: 12px;
  color: var(--md3-on-surface-variant);
}

.filter-select {
  width: 130px;
}

.filter-input {
  width: 160px;
}

.fail2ban-status {
  display: flex;
  flex-direction: column;
  gap: var(--md3-space-sm);
  margin-bottom: var(--md3-space-md);
}

.status-row {
  display: flex;
  align-items: center;
  gap: var(--md3-space-sm);
  flex-wrap: wrap;
}

.status-label {
  font-size: 13px;
  color: var(--md3-on-surface-variant);
  min-width: 80px;
}

.jail-tag {
  margin-right: 4px;
}

.tool-form {
  display: flex;
  align-items: flex-end;
  gap: var(--md3-space-sm);
  flex-wrap: wrap;
  margin-bottom: var(--md3-space-md);
}

.tool-input {
  min-width: 200px;
  flex: 1;
}

.output-area {
  background: var(--md3-surface-container-low);
  border-radius: var(--md3-shape-xs);
  padding: var(--md3-space-md);
  margin-top: var(--md3-space-sm);
}

.output-pre {
  margin: 0;
  font-family: var(--md3-font-mono);
  font-size: 12px;
  line-height: 1.6;
  color: var(--md3-on-surface);
  white-space: pre-wrap;
  word-break: break-all;
  max-height: 360px;
  overflow-y: auto;
}

.stats-row {
  display: flex;
  gap: var(--md3-space-sm);
  margin-top: var(--md3-space-md);
  flex-wrap: wrap;
}

.audit-widget-empty {
  text-align: center;
  color: var(--md3-on-surface-variant);
  padding: var(--md3-space-xl) 0;
  font-size: 14px;
}
.audit-widget-list {
  display: flex;
  flex-direction: column;
  gap: var(--md3-space-xs);
}
.audit-widget-item {
  display: flex;
  align-items: center;
  gap: var(--md3-space-sm);
  font-size: 13px;
  padding: var(--md3-space-xs) 0;
  border-bottom: 1px solid var(--md3-outline-variant);
}
.audit-widget-item:last-child {
  border-bottom: none;
}
.audit-widget-time {
  color: var(--md3-on-surface-variant);
  font-size: 12px;
  min-width: 140px;
}
.audit-widget-user {
  min-width: 60px;
}
.audit-widget-action {
  color: var(--md3-primary);
  min-width: 70px;
}
.audit-widget-module {
  color: var(--md3-on-surface-variant);
}
</style>
