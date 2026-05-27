<template>
  <div class="tools">
    <el-page-header title="OpsV-Kits">
      <template #content>
        <span>工具箱</span>
      </template>
    </el-page-header>
    <el-divider />

    <el-card shadow="never" class="section-card">
      <template #header>
        <span><el-icon :size="16"><FolderOpened /></el-icon> 远程硬盘（NAS）</span>
        <div class="card-header-right">
          <el-switch
            v-model="remoteDriveEnabled"
            active-text="已启用"
            inactive-text="已关闭"
            @change="onRemoteDriveToggle"
            size="small"
            style="margin-right: 8px"
          />
          <el-tag :type="remoteDriveRunning ? 'success' : 'info'" size="small">
            {{ remoteDriveRunning ? '服务运行中' : '服务已停止' }}
          </el-tag>
        </div>
      </template>

      <div class="remote-drive-body">
        <div class="rd-section">
          <div class="rd-field">
            <span class="rd-label">WebDAV 地址：</span>
            <el-input :model-value="webdavUrl" readonly style="width: 340px" size="small">
              <template #append>
                <el-button @click="copyUrl" :icon="DocumentCopy" size="small">复制</el-button>
              </template>
            </el-input>
          </div>
          <div class="rd-field">
            <span class="rd-label">Windows 映射地址：</span>
            <el-input :model-value="windowsUrl" readonly style="width: 420px" size="small">
              <template #append>
                <el-button @click="copyWindowsUrl" :icon="DocumentCopy" size="small">复制</el-button>
              </template>
            </el-input>
          </div>
        </div>

        <el-table v-if="mounts.length > 0" :data="mounts" size="small" stripe style="width: 100%; margin-top: 12px;">
          <el-table-column prop="alias" label="远程服务器别名" width="150" />
          <el-table-column prop="hostname" label="主机地址" width="180" />
          <el-table-column prop="port" label="端口" width="70" />
          <el-table-column label="独立访问地址">
            <template #default="scope">
              <el-link type="primary" :href="scope.row.url" target="_blank">{{ scope.row.url }}</el-link>
            </template>
          </el-table-column>
          <el-table-column prop="windows_url" label="Windows 映射地址" min-width="280" />
        </el-table>

        <div v-if="remoteDriveRunning" class="rd-status">
          <el-icon><SuccessFilled /></el-icon>
          共 {{ accountCount }} 台远程主机可通过网络硬盘访问
        </div>

        <el-collapse class="rd-tutorial" accordion>
          <el-collapse-item title="📖 查看使用教程 — 如何在 Windows 中映射为网络驱动器" name="tutorial">
            <div class="tutorial-content">
              <h4>什么是远程硬盘？</h4>
              <p>远程硬盘功能通过 WebDAV 协议将远程 Linux 服务器的文件系统暴露到本地网络，您可以像操作本地硬盘一样（拖拽文件、直接编辑），无需每次通过浏览器上传/下载。</p>

              <h4>方法一：映射为 Windows 网络驱动器（推荐）</h4>
              <ol>
                <li>确保上方开关为<strong>「已启用」</strong>且状态标签显示<strong>「服务运行中」</strong></li>
                <li>打开 Windows 资源管理器（Win + E）</li>
                <li>右键左侧的<strong>「此电脑」</strong> → 选择<strong>「映射网络驱动器」</strong></li>
                <li>在弹出的窗口中：
                  <ul>
                    <li><strong>驱动器</strong>：选择一个空闲盘符（如 Z:）</li>
                    <li><strong>文件夹</strong>：优先输入 <code>{{ windowsUrl }}</code>；也可输入 <code>{{ webdavUrl }}</code></li>
                    <li>勾选<strong>「登录时重新连接」</strong></li>
                  </ul>
                </li>
                <li>点击<strong>「完成」</strong>，稍等片刻即可在网络位置中看到远程服务器的文件</li>
                <li>如果映射到某个特定服务器的根目录，请使用表格中的<strong>独立访问地址</strong></li>
              </ol>

              <h4>方法二：直接在浏览器中访问</h4>
              <ol>
                <li>复制上方 WebDAV 地址 <code>{{ webdavUrl }}</code></li>
                <li>在浏览器地址栏中打开，可见所有已配置的远程服务器列表</li>
                <li>点击任意服务器别名进入该服务器的文件系统</li>
              </ol>

              <h4>注意事项</h4>
              <ul>
                <li><strong>WebDAV 服务仅监听 <code>127.0.0.1</code></strong>（本机），其他设备无法访问，确保安全</li>
                <li>映射网络驱动器时，Windows 可能需要启用 WebDAV 支持（Win10/11 默认已支持）</li>
                <li>如果映射后长时间无响应，请在资源管理器中右键映射的驱动器 → <strong>「断开」</strong> 后重新映射</li>
                <li>文件操作（上传/下载/删除/重命名/新建文件夹）均通过 SSH/SFTP 实时同步到远程服务器</li>
                <li>远程服务器必须已在 <strong>SSH 账户管理</strong> 中正确配置</li>
                <li>如需关闭此功能，将上方开关切换为 <strong>「已关闭」</strong> 即可</li>
              </ul>
            </div>
          </el-collapse-item>
        </el-collapse>
      </div>
    </el-card>

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
import { Refresh, CircleClose, Connection, Key, Delete, FolderOpened, DocumentCopy, SuccessFilled } from '@element-plus/icons-vue'
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

const remoteDriveEnabled = ref(true)
const remoteDriveRunning = ref(false)
const webdavUrl = ref('http://127.0.0.1:8081/')
const windowsUrl = ref('\\\\127.0.0.1@8081\\DavWWWRoot\\')
const mounts = ref<any[]>([])
const accountCount = ref(0)

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

async function loadDriveStatus() {
  try {
    const res: any = await request.get('/settings')
    remoteDriveEnabled.value = res.remote_drive_enabled !== false
  } catch {}
  try {
    const status: any = await request.get('/remote-drive/status')
    remoteDriveRunning.value = status.running
    webdavUrl.value = status.webdav_url
    windowsUrl.value = status.windows_url || webdavUrl.value
    mounts.value = status.mounts || []
    accountCount.value = status.account_count
  } catch {}
}

async function onRemoteDriveToggle(val: boolean) {
  try {
    await request.put('/settings', { remote_drive_enabled: val })
    ElMessage.success(val ? '远程硬盘功能已开启' : '远程硬盘功能已关闭')
    loadDriveStatus()
  } catch {
    ElMessage.error('设置更新失败')
    remoteDriveEnabled.value = !val
  }
}

async function copyUrl() {
  try {
    await navigator.clipboard.writeText(webdavUrl.value)
    ElMessage.success('地址已复制到剪贴板')
  } catch {
    ElMessage.warning('复制失败，请手动复制')
  }
}

async function copyWindowsUrl() {
  try {
    await navigator.clipboard.writeText(windowsUrl.value)
    ElMessage.success('Windows 映射地址已复制到剪贴板')
  } catch {
    ElMessage.warning('复制失败，请手动复制')
  }
}

onMounted(async () => {
  await sshStore.fetchAccounts()
  sshAccounts.value = sshStore.accounts
  if (sshAccounts.value.length > 0) {
    selectedAlias.value = sshAccounts.value[0].alias
    loadSelinux()
    loadFirewallStatus()
  }
  loadDriveStatus()
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

.remote-drive-body { display: flex; flex-direction: column; gap: 4px; }
.rd-section { display: flex; align-items: center; flex-wrap: wrap; gap: 8px; }
.rd-field { display: flex; align-items: center; gap: 8px; }
.rd-label { font-size: 13px; color: #606266; white-space: nowrap; }
.rd-status {
  font-size: 12px; color: #67c23a; margin-top: 8px;
  display: flex; align-items: center; gap: 4px;
}
.rd-tutorial { margin-top: 12px; }
.rd-tutorial :deep(.el-collapse-item__header) {
  font-size: 13px; font-weight: 500; color: #409eff; padding-left: 4px;
}
.tutorial-content { font-size: 13px; line-height: 1.8; color: #303133; padding: 4px 0; }
.tutorial-content h4 {
  font-size: 14px; margin: 12px 0 6px; color: #303133;
}
.tutorial-content h4:first-child { margin-top: 0; }
.tutorial-content p { margin: 4px 0; color: #606266; }
.tutorial-content ol, .tutorial-content ul { margin: 4px 0; padding-left: 20px; }
.tutorial-content li { margin: 3px 0; }
.tutorial-content code {
  background: #f5f7fa; padding: 1px 6px; border-radius: 3px;
  font-size: 12px; color: #e6a23c; font-family: Consolas, monospace;
}
.tutorial-content strong { color: #303133; }
</style>
