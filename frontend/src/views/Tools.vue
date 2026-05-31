<template>
  <div class="tools">
    <Md3Card :shadow="false" class="section-card">
      <template #header>
        <span><Md3Icon name="folder-open" class="header-icon" /> 远程硬盘（NAS）</span>
        <div class="card-header-right">
          <Md3Tag type="warning" size="sm">实验性功能</Md3Tag>
          <Md3Switch
            v-model="remoteDriveEnabled"
            on-text="已启用"
            off-text="已关闭"
            @update:model-value="onRemoteDriveToggle"
          />
          <Md3Tag :type="remoteDriveRunning ? 'success' : 'info'" size="sm">
            {{ remoteDriveRunning ? '服务运行中' : '服务已停止' }}
          </Md3Tag>
        </div>
      </template>

      <div class="remote-drive-body">
        <div class="rd-section">
          <div class="rd-field">
            <span class="rd-label">WebDAV 地址：</span>
            <Md3Input :model-value="webdavUrl" readonly class="rd-input" size="sm">
              <template #suffix>
                <Md3Button @click="copyUrl" icon="content-copy" size="sm">复制</Md3Button>
              </template>
            </Md3Input>
          </div>
          <div class="rd-field">
            <span class="rd-label">Windows 映射地址：</span>
            <Md3Input :model-value="windowsUrl" readonly class="rd-input-wide" size="sm">
              <template #suffix>
                <Md3Button @click="copyWindowsUrl" icon="content-copy" size="sm">复制</Md3Button>
              </template>
            </Md3Input>
          </div>
        </div>

        <Md3Table
          v-if="mounts.length > 0"
          :columns="mountColumns"
          :data="mounts"
          stripe
          class="mounts-table"
        >
          <template #url="{ row }">
            <a class="md3-link" :href="row.url as string" target="_blank">{{ row.url as string }}</a>
          </template>
        </Md3Table>

        <div v-if="remoteDriveRunning" class="rd-status">
          <Md3Icon name="check-circle" class="rd-status-icon" />
          共 {{ accountCount }} 台远程主机可通过网络硬盘访问
          <span class="rd-auth-info">
            映射账户：<strong>{{ authUsername }}</strong> / <strong>{{ authPasswordSet ? '******' : '(SSH默认)' }}</strong>
          </span>
        </div>

        <Md3Collapse v-model="tutorialOpen" title="📖 查看使用教程 — 如何在 Windows 中映射为网络驱动器">
          <div class="tutorial-content">
            <h4>什么是远程硬盘？</h4>
            <p>远程硬盘功能通过 WebDAV 协议将远程 Linux 服务器的文件系统暴露到本地网络，您可以像操作本地硬盘一样（拖拽文件、直接编辑），无需每次通过浏览器上传/下载。</p>

            <h4>方法一：映射为 Windows 网络驱动器（推荐）</h4>
            <ol>
              <li><strong>步骤一：确保 WebClient 服务已启动</strong>
                <ul>
                  <li>按 <code>Win + R</code>，输入 <code>services.msc</code>，找到 <strong>WebClient</strong> 服务</li>
                  <li>如未运行，右键 → <strong>启动</strong>；右键 → 属性 → 启动类型改为 <strong>自动</strong></li>
                </ul>
              </li>
              <li>打开 Windows 资源管理器（Win + E）</li>
              <li>右键左侧的<strong>「此电脑」</strong> → 选择<strong>「映射网络驱动器」</strong></li>
              <li>在弹出的窗口中：
                <ul>
                  <li><strong>驱动器</strong>：选择一个空闲盘符（如 Z:）</li>
                  <li><strong>文件夹</strong>：输入 <code>{{ webdavUrl }}</code></li>
                  <li>勾选<strong>「使用其他凭据连接」</strong></li>
                  <li>勾选<strong>「登录时重新连接」</strong></li>
                </ul>
              </li>
              <li>点击<strong>「完成」</strong>，在弹出的凭据窗口中输入任意用户名和密码（推荐 <code>opsv</code> / <code>opsv</code>）</li>
              <li>稍等片刻即可在网络位置中看到远程服务器的文件</li>
            </ol>

            <h4>方法二：使用 net use 命令映射</h4>
            <ol>
              <li>以<strong>管理员身份</strong>打开命令提示符</li>
              <li>执行：<code>net use Z: {{ webdavUrl }} /user:opsv opsv /persistent:yes</code></li>
              <li>将 <code>Z:</code> 替换为实际盘符，<code>opsv/opsv</code> 为任意用户名/密码</li>
            </ol>

            <h4>方法三：直接在浏览器中访问</h4>
            <ol>
              <li>复制上方 WebDAV 地址 <code>{{ webdavUrl }}</code></li>
              <li>在浏览器地址栏中打开，可见所有已配置的远程服务器列表</li>
              <li>点击任意服务器别名进入该服务器的文件系统</li>
            </ol>

            <h4>注意事项</h4>
            <ul>
              <li><strong>必须先启动 Windows WebClient 服务</strong>（<code>services.msc</code> → WebClient → 启动）</li>
              <li>服务端已支持 NTLM + Basic 认证，Windows 可直接使用，无需修改注册表</li>
              <li>映射时<strong>必须勾选「使用其他凭据连接」</strong>，并输入任意用户名和密码</li>
              <li>Windows 默认限制 WebDAV 文件大小为 50MB，如需传输更大文件：
                <ul>
                  <li>管理员 CMD 执行 <code>reg add HKLM\SYSTEM\CurrentControlSet\Services\WebClient\Parameters /v FileSizeLimitInBytes /t REG_DWORD /d 4294967295 /f</code></li>
                  <li>然后执行 <code>net stop WebClient && net start WebClient</code></li>
                </ul>
              </li>
              <li>文件操作均通过 SSH/SFTP 实时同步到远程服务器</li>
              <li>远程服务器必须已在 <strong>SSH 账户管理</strong> 中正确配置</li>
            </ul>
          </div>
        </Md3Collapse>
      </div>
    </Md3Card>

    <Md3Card :shadow="false" class="account-card">
      <div class="account-selector">
        <span class="selector-label">目标服务器:</span>
        <Md3Select
          v-model="selectedAlias"
          :options="selectOptions"
          placeholder="选择 SSH 服务器"
          variant="outlined"
          @update:model-value="onAccountChange"
        />
      </div>
    </Md3Card>

    <template v-if="selectedAlias">
      <Md3Card :shadow="false" class="section-card">
        <template #header>
          <span><Md3Icon name="database" class="header-icon" /> 数据库管理</span>
          <Md3Tag type="info" size="sm">主机模式</Md3Tag>
        </template>
        <DbManagerPanel
          deploy-mode="host"
          :account-alias="selectedAlias"
        />
      </Md3Card>

      <Md3Card :shadow="false" class="section-card">
        <template #header>
          <span><Md3Icon name="refresh" class="header-icon" /> 系统操作</span>
        </template>
        <div class="action-grid">
          <Md3Button variant="warning" icon="refresh" @click="confirmAction('reboot')" :loading="loadingAction === 'reboot'">
            重启服务器
          </Md3Button>
          <Md3Button variant="danger" icon="close" @click="confirmAction('shutdown')" :loading="loadingAction === 'shutdown'">
            关机
          </Md3Button>
          <Md3Button icon="connection" @click="executeAction('reload_network')" :loading="loadingAction === 'reload_network'">
            重启网络
          </Md3Button>
          <Md3Button icon="key" @click="executeAction('reload_ssh')" :loading="loadingAction === 'reload_ssh'">
            重启 SSH
          </Md3Button>
          <Md3Button icon="delete" @click="executeAction('clear_cache')" :loading="loadingAction === 'clear_cache'">
            清理缓存
          </Md3Button>
          <Md3Button icon="schedule" @click="executeAction('toolkit/sync-time')" :loading="loadingAction === 'toolkit/sync-time'">
            同步系统时间
          </Md3Button>
          <Md3Button icon="edit" @click="hostnameDialogVisible = true" :loading="loadingAction === 'toolkit/hostname'">
            修改主机名
          </Md3Button>
          <Md3Button icon="language" @click="openTimezoneDialog" :loading="loadingAction === 'toolkit/timezone'">
            修改时区
          </Md3Button>
        </div>
        <Md3Divider />
        <div class="selinux-row">
          <span class="label">SELinux:</span>
          <Md3Tag
            :type="selinuxStatus === 'Enforcing' ? 'danger' : selinuxStatus === 'Permissive' ? 'warning' : 'info'"
            size="sm"
          >
            {{ selinuxStatus || '未知' }}
          </Md3Tag>
          <Md3Button size="sm" v-if="selinuxStatus === 'Enforcing'" @click="setSelinux('permissive')" :loading="loadingSelinux">
            设为 Permissive
          </Md3Button>
          <Md3Button size="sm" v-if="selinuxStatus === 'Permissive'" @click="setSelinux('enforcing')" :loading="loadingSelinux">
            设为 Enforcing
          </Md3Button>
          <Md3Button size="sm" @click="loadSelinux" :loading="loadingSelinux">刷新</Md3Button>
        </div>
      </Md3Card>

      <Md3Card :shadow="false" class="section-card">
        <template #header>
          <span><Md3Icon name="search" class="header-icon" /> 诊断工具</span>
        </template>
        <div class="action-grid">
          <Md3Button icon="people" @click="queryToolkit('logged-users')" :loading="queryLoading === 'logged-users'">
            当前登录用户
          </Md3Button>
          <Md3Button icon="schedule" @click="queryToolkit('boot-time')" :loading="queryLoading === 'boot-time'">
            系统启动时间
          </Md3Button>
          <Md3Button icon="memory" @click="queryToolkit('kernel-modules')" :loading="queryLoading === 'kernel-modules'">
            内核模块
          </Md3Button>
          <Md3Button icon="rocket-launch" @click="queryToolkit('enabled-services')" :loading="queryLoading === 'enabled-services'">
            开机自启服务
          </Md3Button>
          <Md3Button icon="dns" @click="queryToolkit('dns-config')" :loading="queryLoading === 'dns-config'">
            DNS 配置
          </Md3Button>
          <Md3Button icon="tune" @click="queryToolkit('ulimit')" :loading="queryLoading === 'ulimit'">
            资源限制
          </Md3Button>
        </div>
      </Md3Card>

      <Md3Card :shadow="false" class="section-card">
        <template #header>
          <span><Md3Icon name="cleaning-services" class="header-icon" /> 清理维护</span>
        </template>
        <div class="action-grid">
          <Md3Button icon="swap-horiz" @click="confirmSwapRefresh" :loading="loadingAction === 'swap-refresh'">
            SWAP 查看/刷新
          </Md3Button>
          <Md3Button variant="warning" icon="delete-sweep" @click="confirmCleanupKernels" :loading="loadingAction === 'cleanup-kernels'">
            清理旧内核
          </Md3Button>
          <Md3Button icon="auto-delete" @click="confirmCleanupJournal" :loading="loadingAction === 'cleanup-journal'">
            清理 Journal 日志
          </Md3Button>
          <Md3Button icon="system-update" @click="queryToolkit('check-updates')" :loading="queryLoading === 'check-updates'">
            检查系统更新
          </Md3Button>
        </div>
      </Md3Card>

      <Md3Dialog v-model:visible="resultDialogVisible" :title="resultDialogTitle" width="680px">
        <div class="result-content">
          <pre class="result-pre">{{ resultDialogContent }}</pre>
        </div>
        <template #footer>
          <Md3Button @click="resultDialogVisible = false">关闭</Md3Button>
        </template>
      </Md3Dialog>

      <Md3Dialog v-model:visible="hostnameDialogVisible" title="修改主机名" width="420px">
        <div class="dialog-form">
          <Md3Input v-model="hostnameInput" placeholder="输入新主机名" />
        </div>
        <template #footer>
          <Md3Button @click="hostnameDialogVisible = false">取消</Md3Button>
          <Md3Button variant="primary" @click="doSetHostname" :loading="loadingAction === 'set-hostname'">确定</Md3Button>
        </template>
      </Md3Dialog>

      <Md3Dialog v-model:visible="timezoneDialogVisible" title="修改时区" width="420px">
        <div class="dialog-form">
          <Md3Input v-model="timezoneInput" placeholder="如 Asia/Shanghai, UTC" />
          <div class="dialog-hint">常用: Asia/Shanghai, Asia/Tokyo, America/New_York, UTC</div>
        </div>
        <template #footer>
          <Md3Button @click="timezoneDialogVisible = false">取消</Md3Button>
          <Md3Button variant="primary" @click="doSetTimezone" :loading="loadingAction === 'set-timezone'">确定</Md3Button>
        </template>
      </Md3Dialog>

    </template>

    <Md3Empty v-else description="请先选择一个 SSH 服务器" :image-size="80" />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { Md3Message, Md3Confirm, Md3Icon } from '@/components/md3'
import Md3Button from '@/components/Md3Button.vue'
import DbManagerPanel from '@/components/DbManagerPanel.vue'
import {
  Md3PageHeader,
  Md3Divider,
  Md3Card,
  Md3Switch,
  Md3Tag,
  Md3Input,
  Md3Table,
  Md3Collapse,
  Md3Select,
  Md3Empty,
  Md3Dialog,
} from '@/components/md3'
import { useSshAccountStore } from '@/stores/sshAccountStore'
import { request } from '@/api'

const sshStore = useSshAccountStore()
const selectedAlias = ref('')
const sshAccounts = ref(sshStore.accounts)
const tutorialOpen = ref(false)

const loadingAction = ref('')
const loadingSelinux = ref(false)
const selinuxStatus = ref('')

const queryLoading = ref('')
const resultDialogVisible = ref(false)
const resultDialogTitle = ref('')
const resultDialogContent = ref('')

const hostnameDialogVisible = ref(false)
const hostnameInput = ref('')

const timezoneDialogVisible = ref(false)
const timezoneInput = ref('')

const remoteDriveEnabled = ref(false)
const remoteDriveRunning = ref(false)
const webdavUrl = ref('http://localhost:8081/')
const windowsUrl = ref('\\\\localhost@8081\\DavWWWRoot\\')
const mounts = ref<any[]>([])
const accountCount = ref(0)
const authUsername = ref('opsv')
const authPasswordSet = ref(false)

const mountColumns = [
  { prop: 'alias', label: '远程服务器别名', width: '150px' },
  { prop: 'hostname', label: '主机地址', width: '180px' },
  { prop: 'port', label: '端口', width: '70px' },
  { prop: 'url', label: '独立访问地址' },
  { prop: 'windows_url', label: 'Windows 映射地址' },
]

const selectOptions = computed(() =>
  sshAccounts.value.map(acc => ({
    label: `${acc.alias} (${acc.host})`,
    value: acc.alias,
  }))
)

const protocolOptions = [
  { label: 'TCP', value: 'tcp' },
  { label: 'UDP', value: 'udp' },
]

function onAccountChange(value: string | number | (string | number)[]) {
  const alias = String(value)
  selectedAlias.value = alias
  loadSelinux()
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
    Md3Message.success(res.message)
    await loadSelinux()
  } catch { Md3Message.error('设置失败') }
  finally { loadingSelinux.value = false }
}

async function confirmAction(action: string) {
  try {
    await Md3Confirm.show({
      title: '危险操作',
      message: action === 'reboot' ? '确定要重启远程服务器吗？' : '确定要关闭远程服务器吗？',
      confirmText: '确定',
      cancelText: '取消',
      type: 'danger',
    })
    await executeAction(action)
  } catch {}
}

async function executeAction(action: string) {
  loadingAction.value = action
  try {
    const res = await request.post<any>(`/system/${action}`, null, { params: { alias: selectedAlias.value } })
    Md3Message.success(res.message)
  } catch { Md3Message.error('操作失败') }
  finally { loadingAction.value = '' }
}

async function loadDriveStatus() {
  try {
    const status: any = await request.get('/remote-drive/status')
    remoteDriveEnabled.value = status.enabled === true
    remoteDriveRunning.value = status.running
    webdavUrl.value = status.webdav_url
    windowsUrl.value = status.windows_url || webdavUrl.value
    mounts.value = status.mounts || []
    accountCount.value = status.account_count
    authUsername.value = status.auth_username || 'opsv'
    authPasswordSet.value = status.auth_password_set || false
  } catch {}
}

async function onRemoteDriveToggle(val: boolean) {
  if (val) {
    try {
      await Md3Confirm.show({
        title: '实验性功能警告',
        message: '远程硬盘（NAS）为实验性功能，开启后会严重影响系统性能，可能造成卡顿或资源占用过高。确定要开启吗？',
        confirmText: '确定开启',
        cancelText: '取消',
        type: 'danger',
      })
    } catch {
      remoteDriveEnabled.value = false
      return
    }
  }
  try {
    await request.put('/settings', { remote_drive_enabled: val })
    Md3Message.success(val ? '远程硬盘功能已开启' : '远程硬盘功能已关闭')
    loadDriveStatus()
  } catch {
    Md3Message.error('设置更新失败')
    remoteDriveEnabled.value = !val
  }
}

async function copyUrl() {
  try {
    await navigator.clipboard.writeText(webdavUrl.value)
    Md3Message.success('地址已复制到剪贴板')
  } catch {
    Md3Message.warning('复制失败，请手动复制')
  }
}

async function copyWindowsUrl() {
  try {
    await navigator.clipboard.writeText(windowsUrl.value)
    Md3Message.success('Windows 映射地址已复制到剪贴板')
  } catch {
    Md3Message.warning('复制失败，请手动复制')
  }
}

const queryLabels: Record<string, string> = {
  'logged-users': '当前登录用户',
  'boot-time': '系统启动时间',
  'kernel-modules': '内核模块',
  'enabled-services': '开机自启服务列表',
  'dns-config': 'DNS 配置 (/etc/resolv.conf)',
  'ulimit': '系统资源限制 (ulimit -a)',
  'check-updates': '系统更新检查',
  'swap-status': 'SWAP 状态',
}

async function queryToolkit(endpoint: string) {
  queryLoading.value = endpoint
  try {
    const res = await request.get<any>(`/system/toolkit/${endpoint}`, {
      params: { alias: selectedAlias.value },
    })
    resultDialogTitle.value = queryLabels[endpoint] || endpoint
    let content = ''
    if (endpoint === 'logged-users') {
      const users = res.users || []
      if (users.length === 0) {
        content = '当前无用户登录\n'
      } else {
        users.forEach((u: any) => {
          content += `${u.user.padEnd(12)} ${u.tty.padEnd(10)} ${u.login_time.padEnd(20)} ${u.from}\n`
        })
      }
      if (res.raw) content += '\n─'.repeat(40) + '\n' + res.raw
    } else if (endpoint === 'boot-time') {
      content = `系统启动时间: ${res.boot_time || ''}\n启动后运行: ${res.since || ''}`
    } else if (endpoint === 'kernel-modules') {
      const modules = res.modules || []
      content = `共 ${res.count || 0} 个已加载内核模块 (显示前 50 个):\n\n`
      content += '模块名'.padEnd(28) + '大小'.padEnd(12) + '引用数\n'
      content += '─'.repeat(52) + '\n'
      modules.forEach((m: any) => {
        content += `${m.name.padEnd(28)} ${m.size.padEnd(12)} ${m.used_by}\n`
      })
    } else if (endpoint === 'enabled-services') {
      content = res.services || '无开机自启服务'
    } else if (endpoint === 'dns-config') {
      content = res.resolv_conf || '未获取到 DNS 配置'
    } else if (endpoint === 'ulimit') {
      content = res.ulimit || '未获取到资源限制信息'
    } else if (endpoint === 'check-updates') {
      if ((res.update_count || 0) === 0) {
        content = '系统已是最新，无可用更新'
      } else {
        content = `发现 ${res.update_count} 个可用更新:\n\n`
        const updates = res.updates || []
        updates.forEach((u: string) => { content += u + '\n' })
      }
    } else {
      content = JSON.stringify(res, null, 2)
    }
    resultDialogContent.value = content
    resultDialogVisible.value = true
  } catch (e: any) {
    Md3Message.error(e?.response?.data?.detail || '查询失败')
  } finally {
    queryLoading.value = ''
  }
}

async function doSetHostname() {
  const name = hostnameInput.value.trim()
  if (!name) { Md3Message.warning('请输入主机名'); return }
  loadingAction.value = 'toolkit/hostname'
  try {
    const res = await request.post<any>('/system/toolkit/hostname', null, {
      params: { alias: selectedAlias.value, hostname: name },
    })
    Md3Message.success(res.message)
    hostnameDialogVisible.value = false
    hostnameInput.value = ''
  } catch { Md3Message.error('修改失败') }
  finally { loadingAction.value = '' }
}

async function openTimezoneDialog() {
  timezoneDialogVisible.value = true
  try {
    const res = await request.get<any>('/system/toolkit/timezone', {
      params: { alias: selectedAlias.value },
    })
    timezoneInput.value = res.timezone || ''
  } catch {}
}

async function doSetTimezone() {
  const tz = timezoneInput.value.trim()
  if (!tz) { Md3Message.warning('请输入时区'); return }
  loadingAction.value = 'toolkit/timezone'
  try {
    const res = await request.post<any>('/system/toolkit/timezone', null, {
      params: { alias: selectedAlias.value, timezone: tz },
    })
    Md3Message.success(res.message)
    timezoneDialogVisible.value = false
  } catch { Md3Message.error('修改失败') }
  finally { loadingAction.value = '' }
}

async function confirmSwapRefresh() {
  try {
    await Md3Confirm.show({
      title: 'SWAP 操作',
      message: '将查看 SWAP 状态并刷新 SWAP 分区，确定继续？',
      confirmText: '确定',
      cancelText: '取消',
    })
  } catch { return }
  loadingAction.value = 'swap-refresh'
  try {
    const status = await request.get<any>('/system/toolkit/swap-status', {
      params: { alias: selectedAlias.value },
    })
    resultDialogTitle.value = 'SWAP 状态'
    resultDialogContent.value = (status.swapon || '无 SWAP') + '\n\n' + (status.free || '')
    resultDialogVisible.value = true

    const res = await request.post<any>('/system/toolkit/swap-refresh', null, {
      params: { alias: selectedAlias.value },
    })
    Md3Message.success(res.message)
  } catch { Md3Message.error('操作失败') }
  finally { loadingAction.value = '' }
}

async function confirmCleanupKernels() {
  try {
    await Md3Confirm.show({
      title: '清理旧内核',
      message: '将保留最新的 2 个内核版本，删除其余旧内核。确定继续？',
      confirmText: '确定清理',
      cancelText: '取消',
      type: 'danger',
    })
  } catch { return }
  loadingAction.value = 'cleanup-kernels'
  try {
    const res = await request.post<any>('/system/toolkit/cleanup-kernels', null, {
      params: { alias: selectedAlias.value },
    })
    Md3Message.success(res.message)
  } catch { Md3Message.error('清理失败') }
  finally { loadingAction.value = '' }
}

async function confirmCleanupJournal() {
  try {
    await Md3Confirm.show({
      title: '清理 Journal 日志',
      message: '将清理 7 天前的 systemd journal 日志。确定继续？',
      confirmText: '确定清理',
      cancelText: '取消',
    })
  } catch { return }
  loadingAction.value = 'cleanup-journal'
  try {
    const res = await request.post<any>('/system/toolkit/cleanup-journal', null, {
      params: { alias: selectedAlias.value, days: 7 },
    })
    Md3Message.success(res.message)
  } catch { Md3Message.error('清理失败') }
  finally { loadingAction.value = '' }
}

onMounted(async () => {
  await sshStore.fetchAccounts()
  sshAccounts.value = sshStore.accounts
  if (sshAccounts.value.length > 0) {
    selectedAlias.value = sshAccounts.value[0].alias
    loadSelinux()
  }
  loadDriveStatus()
})
</script>

<style scoped>
.tools { padding: 0; }
.header-icon { width: 16px; height: 16px; vertical-align: -3px; }
.account-card { margin-bottom: var(--md3-space-md); }
.account-selector { display: flex; align-items: center; gap: var(--md3-space-sm); }
.selector-label { font-size: 13px; color: var(--md3-on-surface-variant); white-space: nowrap; }
.section-card { margin-bottom: var(--md3-space-lg); }
.section-card :deep(.md3-card-header) {
  display: flex; align-items: center; justify-content: space-between;
  padding: var(--md3-space-md) var(--md3-space-lg); font-weight: 600; font-size: 14px;
}
.card-header-right { display: flex; align-items: center; gap: var(--md3-space-sm); }
.action-grid {
  display: flex; flex-wrap: wrap; gap: var(--md3-space-sm);
}
.selinux-row {
  display: flex; align-items: center; gap: var(--md3-space-sm); font-size: 13px;
}
.selinux-row .label { color: var(--md3-on-surface-variant); }
.remote-drive-body { display: flex; flex-direction: column; gap: var(--md3-space-xs); }
.rd-section { display: flex; align-items: center; flex-wrap: wrap; gap: var(--md3-space-sm); }
.rd-field { display: flex; align-items: center; gap: var(--md3-space-sm); }
.rd-label { font-size: 13px; color: var(--md3-on-surface-variant); white-space: nowrap; }
.rd-input { width: 340px; }
.rd-input-wide { width: 420px; }
.rd-status {
  font-size: 12px; color: var(--md3-success); margin-top: var(--md3-space-sm);
  display: flex; align-items: center; gap: var(--md3-space-xs);
}
.rd-status-icon { width: 14px; height: 14px; }
.rd-auth-info {
  margin-left: 16px; color: var(--md3-on-surface-variant);
}
.mounts-table { margin-top: 12px; width: 100%; }

.md3-link {
  color: var(--md3-primary);
  text-decoration: none;
  font-size: inherit;
}
.md3-link:hover {
  text-decoration: underline;
}

.rd-tutorial { margin-top: var(--md3-space-md); }
.tutorial-content { font-size: 13px; line-height: 1.8; color: var(--md3-on-surface); padding: var(--md3-space-xs) 0; }
.tutorial-content h4 {
  font-size: 14px; margin: var(--md3-space-md) 0 6px; color: var(--md3-on-surface);
}
.tutorial-content h4:first-child { margin-top: 0; }
.tutorial-content p { margin: var(--md3-space-xs) 0; color: var(--md3-on-surface-variant); }
.tutorial-content ol, .tutorial-content ul { margin: var(--md3-space-xs) 0; padding-left: 20px; }
.tutorial-content li { margin: 3px 0; }
.tutorial-content code {
  background: var(--md3-surface-container-low); padding: 1px 6px; border-radius: var(--md3-shape-xs);
  font-size: 12px; color: var(--md3-warning); font-family: var(--md3-font-mono);
}
.tutorial-content strong { color: var(--md3-on-surface); }

.result-content {
  max-height: 60vh;
  overflow-y: auto;
}

.result-pre {
  margin: 0;
  font-family: var(--md3-font-mono);
  font-size: 12px;
  line-height: 1.6;
  color: var(--md3-on-surface);
  white-space: pre-wrap;
  word-break: break-all;
}

.dialog-form {
  display: flex;
  flex-direction: column;
  gap: var(--md3-space-md);
}

.dialog-hint {
  font-size: 12px;
  color: var(--md3-on-surface-variant);
  line-height: 1.5;
}

</style>
