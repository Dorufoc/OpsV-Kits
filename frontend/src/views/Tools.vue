<template>
  <div class="tools">
    <el-page-header title="OpsV-Kits">
      <template #content>
        <span>工具箱</span>
      </template>
    </el-page-header>
    <el-divider />

    <el-card shadow="never" class="account-card">
      <div class="account-selector">
        <span class="selector-label">目标服务器:</span>
        <el-select v-model="selectedAlias" placeholder="选择 SSH 服务器" style="width: 260px" @change="onAccountChange">
          <el-option v-for="acc in sshAccounts" :key="acc.alias" :label="`${acc.alias} (${acc.host})`" :value="acc.alias" />
        </el-select>
      </div>
    </el-card>

    <template v-if="selectedAlias">
      <el-card shadow="never" class="section-card">
        <template #header>
          <span><el-icon :size="16"><Refresh /></el-icon> 系统操作</span>
        </template>
        <div class="action-grid">
          <el-button type="warning" @click="confirmAction('reboot')" :loading="loadingAction === 'reboot'">
            <el-icon><Refresh /></el-icon> 重启服务器
          </el-button>
          <el-button type="danger" @click="confirmAction('shutdown')" :loading="loadingAction === 'shutdown'">
            <el-icon><CircleClose /></el-icon> 关机
          </el-button>
          <el-button @click="executeAction('reload_network')" :loading="loadingAction === 'reload_network'">
            <el-icon><Connection /></el-icon> 重启网络
          </el-button>
          <el-button @click="executeAction('reload_ssh')" :loading="loadingAction === 'reload_ssh'">
            <el-icon><Key /></el-icon> 重启 SSH
          </el-button>
          <el-button @click="executeAction('clear_cache')" :loading="loadingAction === 'clear_cache'">
            <el-icon><Delete /></el-icon> 清理缓存
          </el-button>
        </div>
        <el-divider />
        <div class="selinux-row">
          <span class="label">SELinux:</span>
          <el-tag :type="selinuxStatus === 'Enforcing' ? 'danger' : selinuxStatus === 'Permissive' ? 'warning' : 'info'" size="small">
            {{ selinuxStatus || '未知' }}
          </el-tag>
          <el-button size="small" v-if="selinuxStatus === 'Enforcing'" @click="setSelinux('permissive')" :loading="loadingSelinux">
            设为 Permissive
          </el-button>
          <el-button size="small" v-if="selinuxStatus === 'Permissive'" @click="setSelinux('enforcing')" :loading="loadingSelinux">
            设为 Enforcing
          </el-button>
          <el-button size="small" @click="loadSelinux" :loading="loadingSelinux">刷新</el-button>
        </div>
      </el-card>

      <el-card shadow="never" class="section-card">
        <template #header>
          <span><el-icon :size="16"><Connection /></el-icon> 防火墙配置 (firewalld)</span>
          <div class="card-header-right">
            <el-tag :type="firewallActive ? 'success' : 'danger'" size="small">
              {{ firewallActive ? '运行中' : '已停止' }}
            </el-tag>
            <el-button size="small" :type="firewallActive ? 'danger' : 'success'" @click="toggleFirewall">
              {{ firewallActive ? '关闭防火墙' : '开启防火墙' }}
            </el-button>
          </div>
        </template>

        <div class="firewall-actions">
          <el-form :inline="true" size="small" @submit.prevent>
            <el-form-item label="端口">
              <el-input v-model.number="newPort" placeholder="如 8080" style="width: 100px" type="number" />
            </el-form-item>
            <el-form-item label="协议">
              <el-select v-model="newProtocol" style="width: 80px">
                <el-option label="TCP" value="tcp" />
                <el-option label="UDP" value="udp" />
              </el-select>
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="addPortRule" :loading="loadingPort">添加端口规则</el-button>
            </el-form-item>
          </el-form>

          <el-table :data="firewallRules" size="small" stripe max-height="240">
            <el-table-column prop="type" label="类型" width="80" />
            <el-table-column prop="value" label="规则内容" min-width="160" />
            <el-table-column prop="zone" label="区域" width="100" />
            <el-table-column label="操作" width="80">
              <template #default="{ row }">
                <el-button size="small" text type="danger" @click="removeRule(row)">
                  <el-icon><Delete /></el-icon>
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </el-card>
    </template>

    <el-empty v-else description="请先选择一个 SSH 服务器" :image-size="80" />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Refresh, CircleClose, Connection, Key, Delete } from '@element-plus/icons-vue'
import { useSshAccountStore } from '@/stores/sshAccountStore'
import { request } from '@/api'

const sshStore = useSshAccountStore()
const selectedAlias = ref('')
const sshAccounts = ref(sshStore.accounts)

const loadingAction = ref('')
const loadingSelinux = ref(false)
const selinuxStatus = ref('')

const firewallActive = ref(false)
const firewallRules = ref<any[]>([])
const newPort = ref(8080)
const newProtocol = ref('tcp')
const loadingPort = ref(false)

function onAccountChange(alias: string) {
  selectedAlias.value = alias
  loadSelinux()
  loadFirewallStatus()
}

async function loadSelinux() {
  if (!selectedAlias.value) return
  loadingSelinux.value = true
  try {
    const res = await request.get<any>('/system/selinux', { params: { alias: selectedAlias.value } })
    selinuxStatus.value = res.status || ''
  } catch { selinuxStatus.value = '未知' }
  finally { loadingSelinux.value = false }
}

async function setSelinux(mode: string) {
  loadingSelinux.value = true
  try {
    const res = await request.post<any>('/system/selinux', null, { params: { alias: selectedAlias.value, mode } })
    ElMessage.success(res.message)
    await loadSelinux()
  } catch { ElMessage.error('设置失败') }
  finally { loadingSelinux.value = false }
}

async function confirmAction(action: string) {
  try {
    await ElMessageBox.confirm(
      action === 'reboot' ? '确定要重启远程服务器吗？' : '确定要关闭远程服务器吗？',
      '危险操作', { confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning' }
    )
    await executeAction(action)
  } catch {}
}

async function executeAction(action: string) {
  loadingAction.value = action
  try {
    const res = await request.post<any>(`/system/${action}`, null, { params: { alias: selectedAlias.value } })
    ElMessage.success(res.message)
  } catch { ElMessage.error('操作失败') }
  finally { loadingAction.value = '' }
}

async function loadFirewallStatus() {
  if (!selectedAlias.value) return
  try {
    const res = await request.get<any>('/system/firewall/status', { params: { alias: selectedAlias.value } })
    firewallActive.value = res.active || false
    if (res.installed) {
      const rulesRes = await request.get<any>('/system/firewall/rules', { params: { alias: selectedAlias.value } })
      firewallRules.value = rulesRes.rules || []
    }
  } catch {}
}

async function toggleFirewall() {
  try {
    const res = await request.post<any>('/system/firewall/set', null, {
      params: { alias: selectedAlias.value, enable: !firewallActive.value }
    })
    ElMessage.success(res.message)
    await loadFirewallStatus()
  } catch { ElMessage.error('操作失败') }
}

async function addPortRule() {
  if (!newPort.value || newPort.value < 1 || newPort.value > 65535) {
    ElMessage.warning('请输入有效端口 (1-65535)')
    return
  }
  loadingPort.value = true
  try {
    const res = await request.post<any>('/system/firewall/port', null, {
      params: { alias: selectedAlias.value, port: newPort.value, protocol: newProtocol.value }
    })
    ElMessage.success(res.message)
    await loadFirewallStatus()
  } catch { ElMessage.error('添加失败') }
  finally { loadingPort.value = false }
}

async function removeRule(row: any) {
  try {
    if (row.type === 'port') {
      const parts = row.value.split('/')
      const port = parseInt(parts[0])
      const proto = parts[1] || 'tcp'
      await request.delete('/system/firewall/port', {
        params: { alias: selectedAlias.value, port, protocol: proto }
      })
    } else if (row.type === 'service') {
      await request.delete('/system/firewall/service', {
        params: { alias: selectedAlias.value, service: row.value }
      })
    }
    ElMessage.success('规则已删除')
    await loadFirewallStatus()
  } catch { ElMessage.error('删除失败') }
}

onMounted(async () => {
  await sshStore.fetchAccounts()
  sshAccounts.value = sshStore.accounts
  if (sshAccounts.value.length > 0) {
    selectedAlias.value = sshAccounts.value[0].alias
    loadSelinux()
    loadFirewallStatus()
  }
})
</script>

<style scoped>
.tools { padding: 0; }
.account-card { margin-bottom: 12px; }
.account-selector { display: flex; align-items: center; gap: 8px; }
.selector-label { font-size: 13px; color: #606266; white-space: nowrap; }
.section-card { margin-bottom: 16px; }
.section-card :deep(.el-card__header) {
  display: flex; align-items: center; justify-content: space-between;
  padding: 12px 16px; font-weight: 600; font-size: 14px;
}
.card-header-right { display: flex; align-items: center; gap: 8px; }
.action-grid {
  display: flex; flex-wrap: wrap; gap: 8px;
}
.selinux-row {
  display: flex; align-items: center; gap: 8px; font-size: 13px;
}
.selinux-row .label { color: #909399; }
.firewall-actions { display: flex; flex-direction: column; gap: 12px; }
</style>
