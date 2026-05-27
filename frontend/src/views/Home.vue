<template>
  <div class="home">
    <template v-if="!loading && !accountsExist">
      <el-empty description="OpsV-Kits 欢迎您" :image-size="200">
        <template #image>
          <div class="welcome-icon">
            <el-icon :size="80" color="#409eff"><Connection /></el-icon>
          </div>
        </template>
        <p class="welcome-text">开始使用前，请先配置您的第一个 SSH 远程服务器</p>
        <el-button type="primary" size="large" @click="dialogVisible = true">
          <el-icon><Plus /></el-icon> 添加 SSH 服务器
        </el-button>
      </el-empty>
    </template>

    <template v-else>
      <el-page-header title="OpsV-Kits">
        <template #content>
          <span>控制台</span>
        </template>
        <template #extra>
          <el-button size="small" @click="dashboardAlias = ''; loadDashboard()" :disabled="!dashboardAlias">
            <el-icon><Refresh /></el-icon> 刷新
          </el-button>
        </template>
      </el-page-header>
      <el-divider />

      <div class="stats-row">
        <el-card shadow="hover" class="stat-card" @click="$router.push('/ssh-accounts')">
          <div class="stat-value">{{ sshStore.accounts.length }}</div>
          <div class="stat-label">SSH 账户</div>
        </el-card>
        <el-card shadow="hover" class="stat-card" @click="$router.push('/docker')">
          <div class="stat-value">{{ dockerStore.containers.length }}</div>
          <div class="stat-label">Docker 容器</div>
        </el-card>
        <el-card shadow="hover" class="stat-card" @click="$router.push('/project')">
          <div class="stat-value">1</div>
          <div class="stat-label">一键部署</div>
        </el-card>
        <el-card shadow="hover" class="stat-card" @click="$router.push('/webssh')">
          <div class="stat-value">{{ websshStore.sessions.length }}</div>
          <div class="stat-label">终端会话</div>
        </el-card>
        <el-card shadow="hover" class="stat-card" @click="$router.push('/vscode')">
          <div class="stat-value"><el-icon :size="24"><Edit /></el-icon></div>
          <div class="stat-label">在线 IDE</div>
        </el-card>
      </div>

      <el-card shadow="never" class="dashboard-card">
        <template #header>
          <div class="dashboard-header">
            <span><el-icon><Monitor /></el-icon> 设备总览</span>
            <el-select v-model="dashboardAlias" placeholder="选择服务器" size="small" style="width: 200px" @change="loadDashboard">
              <el-option v-for="acc in sshStore.accounts" :key="acc.alias" :label="`${acc.alias} (${acc.host})`" :value="acc.alias" />
            </el-select>
          </div>
        </template>

        <div v-if="!dashboardAlias" class="select-hint">
          请选择一台服务器查看监控信息
        </div>

        <div v-else-if="dashboardLoading" class="loading-hint">
          <el-icon class="is-loading" :size="20"><Loading /></el-icon> 加载中...
        </div>

        <template v-else>
          <el-row :gutter="16">
            <el-col :span="12">
              <div class="info-section">
                <div class="info-title"><el-icon><InfoFilled /></el-icon> 系统信息</div>
                <div class="info-grid">
                  <div class="info-item"><span class="info-label">主机名</span><span class="info-value">{{ sysInfo.hostname || '-' }}</span></div>
                  <div class="info-item"><span class="info-label">操作系统</span><span class="info-value">{{ sysInfo.os || '-' }}</span></div>
                  <div class="info-item"><span class="info-label">内核版本</span><span class="info-value">{{ sysInfo.kernel || '-' }}</span></div>
                  <div class="info-item"><span class="info-label">运行时间</span><span class="info-value">{{ sysInfo.uptime || '-' }}</span></div>
                </div>
              </div>
            </el-col>
            <el-col :span="12">
              <div class="info-section">
                <div class="info-title"><el-icon><Cpu /></el-icon> CPU</div>
                <div class="info-grid">
                  <div class="info-item"><span class="info-label">核心数</span><span class="info-value">{{ perf.cpu_cores || '-' }}</span></div>
                  <div class="info-item"><span class="info-label">型号</span><span class="info-value" style="font-size: 12px">{{ perf.cpu_model || '-' }}</span></div>
                  <div class="info-item"><span class="info-label">负载</span><span class="info-value">{{ perf.loadavg || '-' }}</span></div>
                </div>
              </div>
            </el-col>
          </el-row>

          <el-row :gutter="16" style="margin-top: 16px">
            <el-col :span="12">
              <div class="info-section">
                <div class="info-title"><el-icon><Coin /></el-icon> 内存</div>
                <div class="progress-block" v-if="perf.memory">
                  <div class="progress-header">
                    <span>使用率 {{ perf.memory.usage_percent }}%</span>
                    <span>{{ formatBytes(perf.memory.used) }} / {{ formatBytes(perf.memory.total) }}</span>
                  </div>
                  <el-progress :percentage="perf.memory.usage_percent" :color="memColor(perf.memory.usage_percent)" />
                </div>
                <div v-else class="no-data">暂无数据</div>
              </div>
            </el-col>
            <el-col :span="12">
              <div class="info-section">
                <div class="info-title"><el-icon><Folder /></el-icon> 磁盘 (根分区)</div>
                <div class="progress-block" v-if="perf.disk">
                  <div class="progress-header">
                    <span>使用率 {{ perf.disk.usage_percent }}%</span>
                    <span>{{ formatBytes(perf.disk.used) }} / {{ formatBytes(perf.disk.total) }}</span>
                  </div>
                  <el-progress :percentage="perf.disk.usage_percent" :color="diskColor(perf.disk.usage_percent)" />
                </div>
                <div v-else class="no-data">暂无数据</div>
              </div>
            </el-col>
          </el-row>

          <div class="info-section" style="margin-top: 16px" v-if="disks.length > 0">
            <div class="info-title"><el-icon><FolderOpened /></el-icon> 挂载点详情</div>
            <el-table :data="disks" size="small" stripe>
              <el-table-column prop="mount" label="挂载点" min-width="140" />
              <el-table-column prop="filesystem" label="设备" min-width="120" />
              <el-table-column label="已用" width="100">
                <template #default="{ row }">{{ formatBytes(row.used) }}</template>
              </el-table-column>
              <el-table-column label="总量" width="100">
                <template #default="{ row }">{{ formatBytes(row.size) }}</template>
              </el-table-column>
              <el-table-column label="使用率" width="140">
                <template #default="{ row }">
                  <el-progress :percentage="row.usage_percent" :color="diskColor(row.usage_percent)" :stroke-width="14" />
                </template>
              </el-table-column>
            </el-table>
          </div>
        </template>
      </el-card>
    </template>

    <el-dialog
      v-model="dialogVisible"
      title="首次配置 — 添加 SSH 服务器"
      width="520px"
      top="8vh"
      :close-on-click-modal="false"
      :close-on-press-escape="false"
      :show-close="accountsExist"
    >
      <el-alert
        type="info"
        :closable="false"
        show-icon
        title="第一次使用 OpsV-Kits"
        description="请添加一个远程 Linux 服务器的 SSH 连接信息，之后可以随时在 SSH 账户管理中修改。"
        style="margin-bottom: 20px"
      />
      <el-form ref="formRef" :model="form" :rules="rules" label-width="100px" label-position="left" @submit.prevent="handleSave">
        <el-form-item label="账户别名" prop="alias">
          <el-input v-model="form.alias" placeholder="例如：生产环境、测试服务器" />
        </el-form-item>
        <el-form-item label="主机地址" prop="host">
          <el-input v-model="form.host" placeholder="192.168.1.100">
            <template #append>
              <el-input v-model.number="form.port" style="width: 80px" placeholder="22" />
            </template>
          </el-input>
        </el-form-item>
        <el-form-item label="用户名" prop="username">
          <el-input v-model="form.username" placeholder="root" />
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input v-model="form.password" type="password" show-password placeholder="SSH 登录密码" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="handleTest" :loading="testing" :disabled="!formValid">
          <el-icon><Connection /></el-icon> 测试连接
        </el-button>
        <el-button type="primary" @click="handleSave" :loading="saving">
          <el-icon><Check /></el-icon> 保存并开始使用
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { Plus, Check, Connection, Refresh, Monitor, InfoFilled, Cpu, Coin, Folder, FolderOpened, Loading, Edit } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { useSshAccountStore } from '@/stores/sshAccountStore'
import { useDockerStore } from '@/stores/dockerStore'
import { useWebsshStore } from '@/stores/websshStore'
import { request } from '@/api'

const sshStore = useSshAccountStore()
const dockerStore = useDockerStore()
const websshStore = useWebsshStore()

const formRef = ref<FormInstance>()
const dialogVisible = ref(false)
const accountsExist = ref(true)
const loading = ref(true)
const saving = ref(false)
const testing = ref(false)
const testResult = ref<{ success: boolean; message: string } | null>(null)

const form = ref({
  alias: '默认服务器', host: '', port: 22, username: 'root', password: '',
})

const rules: FormRules = {
  alias: [{ required: true, message: '请输入账户别名', trigger: 'blur' }],
  host: [{ required: true, message: '请输入主机地址', trigger: 'blur' }],
  port: [{ required: true, type: 'integer', min: 1, max: 65535, message: '端口范围 1-65535', trigger: 'blur' }],
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
}

const formValid = computed(() => form.value.alias && form.value.host && form.value.username && form.value.password)

const dashboardAlias = ref('')
const dashboardLoading = ref(false)
const sysInfo = ref<any>({})
const perf = ref<any>({})
const disks = ref<any[]>([])

function formatBytes(bytes: number): string {
  if (!bytes || bytes <= 0) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(1024))
  return (bytes / Math.pow(1024, i)).toFixed(1) + ' ' + units[i]
}

function memColor(pct: number) { return pct > 90 ? '#f56c6c' : pct > 70 ? '#e6a23c' : '#67c23a' }
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
    try {
      const res = await request.get<{ exists: boolean }>('/accounts/exists')
      accountsExist.value = res.exists
      if (!res.exists) dialogVisible.value = true
    } catch {
      accountsExist.value = false
      dialogVisible.value = true
    }
  }
  loading.value = false
}

async function handleTest() {
  testing.value = true
  try {
    const payload = { alias: form.value.alias, host: form.value.host, port: form.value.port, username: form.value.username, auth_type: 'password', password: form.value.password }
    const tempRes = await request.post('/accounts', payload)
    await request.post(`/accounts/${tempRes.alias}/test`)
    await request.delete(`/accounts/${tempRes.alias}`)
    ElMessage.success('连接测试成功')
    testResult.value = { success: true, message: '连接成功' }
  } catch (e: any) {
    const msg = e?.response?.data?.detail || e?.message || '连接失败'
    ElMessage.error(msg)
    testResult.value = { success: false, message: msg }
  } finally { testing.value = false }
}

async function handleSave() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  saving.value = true
  try {
    await sshStore.createAccount({ alias: form.value.alias, host: form.value.host, port: form.value.port, username: form.value.username, auth_type: 'password', password: form.value.password, default: true })
    ElMessage.success(`SSH 账户「${form.value.alias}」已添加`)
    dialogVisible.value = false
    accountsExist.value = true
    await sshStore.fetchAccounts()
    dashboardAlias.value = form.value.alias
    loadDashboard()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '保存失败')
  } finally { saving.value = false }
}

onMounted(() => { checkFirstLaunch() })
</script>

<style scoped>
.home { padding: 16px 0; }
.welcome-icon { display: flex; justify-content: center; align-items: center; margin-bottom: 8px; }
.welcome-text { color: #909399; font-size: 15px; margin: 0 0 24px 0; }
.stats-row { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 16px; margin-top: 8px; }
.stat-card { cursor: pointer; transition: transform 0.15s; text-align: center; }
.stat-card:hover { transform: translateY(-2px); }
.stat-value { font-size: 32px; font-weight: 700; color: #409eff; line-height: 1.2; }
.stat-label { font-size: 14px; color: #909399; margin-top: 4px; }
.dashboard-card { margin-top: 20px; }
.dashboard-header { display: flex; align-items: center; justify-content: space-between; }
.select-hint, .loading-hint { text-align: center; color: #909399; padding: 40px 0; font-size: 14px; }
.info-section { background: #fafafa; border-radius: 6px; padding: 12px 16px; }
.info-title { font-size: 13px; font-weight: 600; color: #303133; margin-bottom: 10px; display: flex; align-items: center; gap: 4px; }
.info-grid { display: flex; flex-direction: column; gap: 6px; }
.info-item { display: flex; justify-content: space-between; font-size: 13px; }
.info-label { color: #909399; white-space: nowrap; }
.info-value { color: #303133; text-align: right; word-break: break-all; }
.progress-block { padding: 4px 0; }
.progress-header { display: flex; justify-content: space-between; font-size: 12px; color: #606266; margin-bottom: 4px; }
.no-data { color: #c0c4cc; font-size: 13px; padding: 8px 0; }
</style>
