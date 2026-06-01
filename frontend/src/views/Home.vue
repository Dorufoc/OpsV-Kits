<template>
  <div class="home">
    <template v-if="!loading && !accountsExist">
      <Md3Empty description="未配置 SSH 服务器，请先添加 SSH 账户">
        <template #image>
          <div class="welcome-icon">
            <Md3Icon name="connection" class="icon-welcome" />
          </div>
        </template>
        <template #title>OpsV-Kits 功能不可用</template>
        <template #action>
          <Md3Button variant="primary" size="lg" :icon="Plus" @click="goToSshAccounts">
            前往 SSH 账户管理
          </Md3Button>
        </template>
      </Md3Empty>
    </template>

    <template v-else>
      <div class="stats-row">
        <Md3Card shadow hoverable class="stat-card" @click="$router.push('/ssh-accounts')">
          <Md3Icon name="account" class="stat-icon" />
          <div class="stat-value">{{ sshStore.accounts.length }}</div>
          <div class="stat-label">SSH 账户</div>
        </Md3Card>
        <Md3Card shadow hoverable class="stat-card" @click="$router.push('/docker')">
          <Md3Icon name="box" class="stat-icon" />
          <div class="stat-value">{{ dockerStore.containers.length }}</div>
          <div class="stat-label">Docker 容器</div>
        </Md3Card>
        <Md3Card shadow hoverable class="stat-card" @click="$router.push('/project')">
          <Md3Icon name="rocket" class="stat-icon" />
          <div class="stat-value">1</div>
          <div class="stat-label">一键部署</div>
        </Md3Card>
        <Md3Card shadow hoverable class="stat-card" @click="$router.push('/webssh')">
          <Md3Icon name="terminal" class="stat-icon" />
          <div class="stat-value">{{ websshStore.sessions.length }}</div>
          <div class="stat-label">终端会话</div>
        </Md3Card>
      </div>

      <Md3Card shadow class="dashboard-card">
        <template #header>
          <div class="dashboard-header">
            <span><Md3Icon name="monitor" class="icon-inline" /> 设备总览</span>
            <Md3Select
              v-model="dashboardAlias"
              :options="selectOptions"
              placeholder="选择服务器"
              style="width: 200px"
              @update:modelValue="loadDashboard"
            />
          </div>
        </template>

        <div v-if="!dashboardAlias" class="select-hint">
          请选择一台服务器查看监控信息
        </div>

        <div v-else-if="dashboardLoading" class="loading-hint">
            <Md3Icon name="loading" class="icon-loading" /> 加载中...
          </div>

        <template v-else>
          <div class="dashboard-grid">
            <div class="info-section">
              <div class="info-title"><Md3Icon name="information" class="icon-inline" /> 系统信息</div>
              <div class="info-grid">
                <div class="info-item"><span class="info-label">主机名</span><span class="info-value">{{ sysInfo.hostname || '-' }}</span></div>
                <div class="info-item"><span class="info-label">操作系统</span><span class="info-value">{{ sysInfo.os || '-' }}</span></div>
                <div class="info-item"><span class="info-label">内核版本</span><span class="info-value">{{ sysInfo.kernel || '-' }}</span></div>
                <div class="info-item"><span class="info-label">运行时间</span><span class="info-value">{{ sysInfo.uptime || '-' }}</span></div>
              </div>
            </div>
            <div class="info-section">
              <div class="info-title"><Md3Icon name="cpu" class="icon-inline" /> CPU</div>
              <div class="info-grid">
                <div class="info-item"><span class="info-label">核心数</span><span class="info-value">{{ perf.cpu_cores || '-' }}</span></div>
                <div class="info-item"><span class="info-label">型号</span><span class="info-value" style="font-size: 12px">{{ perf.cpu_model || '-' }}</span></div>
                <div class="info-item"><span class="info-label">负载</span><span class="info-value">{{ perf.loadavg || '-' }}</span></div>
              </div>
            </div>
            <div class="info-section">
              <div class="info-title"><component :is="Coin" class="icon-inline" /> 内存</div>
              <div class="progress-block" v-if="perf.memory">
                <div class="progress-header">
                  <span>使用率 {{ perf.memory.usage_percent }}%</span>
                  <span>{{ formatBytes(perf.memory.used) }} / {{ formatBytes(perf.memory.total) }}</span>
                </div>
                <Md3Progress :percentage="perf.memory.usage_percent" :color="memColor(perf.memory.usage_percent)" />
              </div>
              <div v-else class="no-data">暂无数据</div>
            </div>
            <div class="info-section">
              <div class="info-title"><component :is="Folder" class="icon-inline" /> 磁盘 (根分区)</div>
              <div class="progress-block" v-if="perf.disk">
                <div class="progress-header">
                  <span>使用率 {{ perf.disk.usage_percent }}%</span>
                  <span>{{ formatBytes(perf.disk.used) }} / {{ formatBytes(perf.disk.total) }}</span>
                </div>
                <Md3Progress :percentage="perf.disk.usage_percent" :color="diskColor(perf.disk.usage_percent)" />
              </div>
              <div v-else class="no-data">暂无数据</div>
            </div>
          </div>

          <div class="info-section" style="margin-top: 16px" v-if="disks.length > 0">
            <div class="info-title"><component :is="FolderOpened" class="icon-inline" /> 挂载点详情</div>
            <Md3Table :columns="diskColumns" :data="disks" stripe>
              <template #mount="{ row }">{{ row.mount }}</template>
              <template #filesystem="{ row }">{{ row.filesystem }}</template>
              <template #used="{ row }">{{ formatBytes(row.used as number) }}</template>
              <template #size="{ row }">{{ formatBytes(row.size as number) }}</template>
              <template #usage_percent="{ row }">
                <Md3Progress :percentage="row.usage_percent as number" :color="diskColor(row.usage_percent as number)" />
              </template>
            </Md3Table>
          </div>
        </template>
      </Md3Card>
    </template>

    <Md3Dialog
      v-model:visible="dialogVisible"
      title="首次配置 — 添加 SSH 服务器"
      width="520px"
      :closable="true"
      :close-on-mask-click="false"
      :close-on-esc="false"
      @update:visible="handleDialogClose"
    >
      <Md3Alert
        type="info"
        title="第一次使用 OpsV-Kits"
        message="请添加一个远程 Linux 服务器的 SSH 连接信息，之后可以随时在 SSH 账户管理中修改。"
        style="margin-bottom: 20px"
      />
      <div ref="formRef"></div>
      <div class="dialog-form">
        <div class="form-item">
          <label>账户别名</label>
          <Md3Input v-model="form.alias" placeholder="例如：生产环境、测试服务器" :error="formErrors.alias" />
        </div>
        <div class="form-item">
          <label>主机地址</label>
          <div class="host-input">
            <Md3Input v-model="form.host" placeholder="192.168.1.100" :error="formErrors.host" />
            <Md3Input v-model.number="form.port" type="number" placeholder="22" class="port-input" :error="formErrors.port" />
          </div>
        </div>
        <div class="form-item">
          <label>用户名</label>
          <Md3Input v-model="form.username" placeholder="root" :error="formErrors.username" />
        </div>
        <div class="form-item">
          <label>密码</label>
          <Md3Input v-model="form.password" type="password" placeholder="SSH 登录密码" :error="formErrors.password" />
        </div>
      </div>
      <template #footer>
        <Md3Button :icon="Connection" @click="handleTest" :loading="testing" :disabled="!formValid">
          测试连接
        </Md3Button>
        <Md3Button variant="primary" :icon="Check" @click="handleSave" :loading="saving">
          保存并开始使用
        </Md3Button>
      </template>
    </Md3Dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, h, defineComponent } from 'vue'
import { useRouter } from 'vue-router'
import { Md3Icon, Md3Empty, Md3PageHeader, Md3Divider, Md3Card, Md3Select, Md3Progress, Md3Table, Md3Dialog, Md3Alert, Md3Input, Md3Message } from '@/components/md3'
import { Md3Confirm } from '@/components/md3/Md3Confirm'
import Md3Button from '@/components/Md3Button.vue'
import { useSshAccountStore } from '@/stores/sshAccountStore'
import { useDockerStore } from '@/stores/dockerStore'
import { useWebsshStore } from '@/stores/websshStore'
import { request } from '@/api'

const STORAGE_KEY = 'opskits_ssh_dismissed'

const createIcon = (name: string) => defineComponent(() => () => h(Md3Icon, { name }))

const Plus = createIcon('plus')
const Check = createIcon('check')
const Connection = createIcon('connection')
const Refresh = createIcon('refresh')
const Coin = createIcon('coin')
const Folder = createIcon('folder')
const FolderOpened = createIcon('folder-open')
const Account = createIcon('account')
const Container = createIcon('box')
const Rocket = createIcon('rocket')
const Terminal = createIcon('terminal')

const sshStore = useSshAccountStore()
const dockerStore = useDockerStore()
const websshStore = useWebsshStore()
const router = useRouter()

const formRef = ref<HTMLElement>()
const dialogVisible = ref(false)
const accountsExist = ref(true)
const loading = ref(true)
const saving = ref(false)
const testing = ref(false)
const testResult = ref<{ success: boolean; message: string } | null>(null)
const formErrors = ref({ alias: '', host: '', port: '', username: '', password: '' })
const sshDismissed = ref(false)

const form = ref({
  alias: '默认服务器', host: '', port: 22, username: 'root', password: '',
})

const formValid = computed(() => form.value.alias && form.value.host && form.value.username && form.value.password)

const selectOptions = computed(() =>
  sshStore.accounts.map(acc => ({ label: `${acc.alias} (${acc.host})`, value: acc.alias }))
)

const dashboardAlias = ref('')
const dashboardLoading = ref(false)
const sysInfo = ref<any>({})
const perf = ref<any>({})
const disks = ref<any[]>([])

function ensurePerfData() {
  if (!perf.value.memory) {
    perf.value.memory = { total: 0, used: 0, available: 0, usage_percent: 0 }
  }
  if (!perf.value.disk) {
    perf.value.disk = { total: 0, used: 0, available: 0, usage_percent: 0 }
  }
}

const diskColumns = [
  { prop: 'mount', label: '挂载点' },
  { prop: 'filesystem', label: '设备' },
  { prop: 'used', label: '已用' },
  { prop: 'size', label: '总量' },
  { prop: 'usage_percent', label: '使用率' },
]

function formatBytes(bytes: number): string {
  if (!bytes || bytes <= 0) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(1024))
  return (bytes / Math.pow(1024, i)).toFixed(1) + ' ' + units[i]
}

function memColor(pct: number) { return pct > 90 ? '#b3261e' : pct > 70 ? '#f9a825' : '#1b7d3a' }
function diskColor(pct: number) { return memColor(pct) }

async function loadDashboard() {
  if (!dashboardAlias.value) return
  dashboardLoading.value = true
  try {
    const [sysRes, perfRes, disksRes] = await Promise.all([
      request.get<any>('/system/info', { params: { alias: dashboardAlias.value } }),
      request.get<any>('/system/performance', { params: { alias: dashboardAlias.value } }),
      request.get<any>('/system/disks', { params: { alias: dashboardAlias.value } }),
    ])
    sysInfo.value = sysRes
    perf.value = perfRes
    ensurePerfData()
    disks.value = disksRes.disks || []
  } catch {}
  finally { dashboardLoading.value = false }
}

async function checkFirstLaunch() {
  loading.value = true
  try {
    await sshStore.fetchAccounts()
  } catch {}
  if (sshStore.accounts.length > 0) {
    accountsExist.value = true
    dialogVisible.value = false
    const defaultAcc = sshStore.accounts.find(a => a.default)
    dashboardAlias.value = defaultAcc?.alias || sshStore.accounts[0]?.alias || ''
    if (dashboardAlias.value) loadDashboard()
  } else {
    let exists = false
    for (let attempt = 0; attempt < 3; attempt++) {
      try {
        const res = await request.get<{ exists: boolean }>('/accounts/exists')
        exists = res.exists
        break
      } catch {
        if (attempt < 2) {
          await new Promise(r => setTimeout(r, 1000))
        }
      }
    }
    accountsExist.value = exists
    const dismissed = localStorage.getItem(STORAGE_KEY) === 'true'
    sshDismissed.value = dismissed
    if (!exists && !dismissed) dialogVisible.value = true
  }
  loading.value = false
}

async function handleDialogClose(visible: boolean) {
  if (visible) return
  
  if (!accountsExist.value && !sshDismissed.value) {
    const confirmed = await Md3Confirm.show({
      title: '关闭配置',
      message: '关闭后将无法使用任何功能。如需登录，请重启前后端服务或前往SSH账户管理单独添加用户。',
      confirmText: '关闭',
      cancelText: '继续配置',
      type: 'warning',
    })
    
    if (!confirmed) {
      dialogVisible.value = true
      return
    }
    
    sshDismissed.value = true
    localStorage.setItem(STORAGE_KEY, 'true')
  }
  
  dialogVisible.value = false
}

function validateForm() {
  formErrors.value = { alias: '', host: '', port: '', username: '', password: '' }
  let valid = true
  if (!form.value.alias) { formErrors.value.alias = '请输入账户别名'; valid = false }
  if (!form.value.host) { formErrors.value.host = '请输入主机地址'; valid = false }
  if (!form.value.port || form.value.port < 1 || form.value.port > 65535) { formErrors.value.port = '端口范围 1-65535'; valid = false }
  if (!form.value.username) { formErrors.value.username = '请输入用户名'; valid = false }
  if (!form.value.password) { formErrors.value.password = '请输入密码'; valid = false }
  return valid
}

async function handleTest() {
  if (!validateForm()) return
  testing.value = true
  try {
    const payload = { alias: form.value.alias, host: form.value.host, port: form.value.port, username: form.value.username, auth_type: 'password', password: form.value.password }
    const tempRes = await request.post('/accounts', payload)
    await request.post(`/accounts/${tempRes.alias}/test`)
    await request.delete(`/accounts/${tempRes.alias}`)
    Md3Message.success('连接测试成功')
    testResult.value = { success: true, message: '连接成功' }
  } catch (e: any) {
    const msg = e?.response?.data?.detail || e?.message || '连接失败'
    Md3Message.error(msg)
    testResult.value = { success: false, message: msg }
  } finally { testing.value = false }
}

async function handleSave() {
  if (!validateForm()) return
  saving.value = true
  try {
    await sshStore.createAccount({ alias: form.value.alias, host: form.value.host, port: form.value.port, username: form.value.username, auth_type: 'password', password: form.value.password, default: true })
    Md3Message.success(`SSH 账户「${form.value.alias}」已添加`)
    dialogVisible.value = false
    accountsExist.value = true
    sshDismissed.value = false
    localStorage.removeItem(STORAGE_KEY)
    await sshStore.fetchAccounts()
    dashboardAlias.value = form.value.alias
    loadDashboard()
  } catch (e: any) {
    Md3Message.error(e?.response?.data?.detail || '保存失败')
  } finally { saving.value = false }
}

function goToSshAccounts() {
  router.push('/ssh-accounts')
}

onMounted(() => { checkFirstLaunch() })
</script>

<style scoped>
.home { padding: var(--md3-space-lg) 0; }
.welcome-icon { display: flex; justify-content: center; align-items: center; margin-bottom: var(--md3-space-sm); }
.icon-welcome { width: 80px; height: 80px; color: var(--ov-primary, #1a73e8); }
.icon-inline { width: 16px; height: 16px; flex-shrink: 0; }
.icon-loading { width: 20px; height: 20px; vertical-align: middle; animation: icon-spin 1s linear infinite; }
@keyframes icon-spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
.stats-row { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: var(--md3-space-lg); margin-top: var(--md3-space-sm); }
.stat-card { cursor: pointer; text-align: center; display: flex; flex-direction: column; align-items: center; gap: var(--md3-space-sm); }
.stat-card :deep(.md3-card-body) { padding: var(--md3-space-xl) var(--md3-space-lg); display: flex; flex-direction: column; align-items: center; width: 100%; }
.stat-icon { width: 36px; height: 36px; color: var(--md3-primary); margin-bottom: var(--md3-space-sm); }
.stat-value { font-size: 32px; font-weight: 700; color: var(--md3-primary); line-height: 1.2; }
.stat-label { font-size: 14px; color: var(--md3-on-surface-variant); margin-top: var(--md3-space-xs); }
.dashboard-card { margin-top: var(--md3-space-xl); }
.dashboard-header { display: flex; align-items: center; justify-content: space-between; gap: var(--md3-space-md); }
.select-hint, .loading-hint { text-align: center; color: var(--md3-on-surface-variant); padding: var(--md3-space-3xl) 0; font-size: 14px; }
.dashboard-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 16px; }
.info-section { background: var(--md3-glass-bg); backdrop-filter: var(--md3-glass-blur); -webkit-backdrop-filter: var(--md3-glass-blur); border: 1px solid var(--md3-glass-border); border-radius: var(--md3-shape-sm); padding: var(--md3-space-md) var(--md3-space-lg); transition: border-color var(--md3-motion-duration-medium) var(--md3-motion-easing-standard); }
.info-section:hover { border-color: var(--md3-card-border-hover); }
.info-title { font-size: 13px; font-weight: 600; color: var(--md3-on-surface); margin-bottom: var(--md3-space-sm); display: flex; align-items: center; gap: var(--md3-space-xs); }
.info-grid { display: flex; flex-direction: column; gap: 6px; }
.info-item { display: flex; justify-content: space-between; font-size: 13px; }
.info-label { color: var(--md3-on-surface-variant); white-space: nowrap; }
.info-value { color: var(--md3-on-surface); text-align: right; word-break: break-all; }
.progress-block { padding: var(--md3-space-xs) 0; }
.progress-header { display: flex; justify-content: space-between; font-size: 12px; color: var(--md3-on-surface-variant); margin-bottom: var(--md3-space-xs); }
.no-data { color: var(--md3-outline-variant); font-size: 13px; padding: var(--md3-space-sm) 0; }

.dialog-form { display: flex; flex-direction: column; gap: var(--md3-space-lg); }
.form-item { display: flex; flex-direction: column; gap: var(--md3-space-xs); }
.form-item label { font-size: 14px; font-weight: 500; color: var(--md3-on-surface); }
.host-input { display: flex; gap: 0; }
.host-input .md3-input-wrapper { flex: 1; }
.port-input { max-width: 80px; }
</style>
