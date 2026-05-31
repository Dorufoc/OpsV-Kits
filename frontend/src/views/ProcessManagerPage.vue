<template>
  <div class="process-manager-page">
    <!-- 页面头部 -->
    <Md3PageHeader title="进程管理">
      <template #subtitle>
        <span>{{ subtitleText }}</span>
      </template>
      <template #actions>
        <Md3Select
          v-model="selectedAlias"
          :options="selectOptions"
          placeholder="选择服务器"
          style="width: 200px"
          @update:model-value="onAccountChange"
        />
        <Md3Select
          v-model="refreshIntervalValue"
          :options="refreshOptions"
          placeholder="刷新频率"
          style="width: 120px"
          @update:model-value="onRefreshIntervalChange"
        />
        <Md3Button size="sm" @click="refreshAll" :disabled="!selectedAlias || streaming">
          <Md3Icon name="refresh" size="1em" />刷新
        </Md3Button>
        <Md3Button
          size="sm"
          @click="toggleStream"
          :type="streaming ? 'danger' : 'primary'"
          :disabled="!selectedAlias"
        >
          <Md3Icon name="monitor" size="1em" />{{ streaming ? '停止推送' : '实时推送' }}
        </Md3Button>
      </template>
    </Md3PageHeader>
    <Md3Divider />

    <!-- 未选择服务器状态 -->
    <template v-if="!selectedAlias">
      <div class="empty-wrapper">
        <Md3Empty description="请先选择一台服务器查看进程" />
      </div>
    </template>

    <template v-else>
      <!-- 异常告警横幅 -->
      <Md3Alert
        v-if="hasAnomalies"
        :type="anomalyType"
        :title="anomalyTitle"
        :message="anomalyDescription"
        class="anomaly-banner"
      >
        <template #title>
          <span>{{ anomalyTitle }}</span>
          <Md3Button size="sm" @click="showAnomalyOnly = !showAnomalyOnly" style="margin-left: 12px">
            {{ showAnomalyOnly ? '显示全部进程' : '仅看异常进程' }}
          </Md3Button>
        </template>
      </Md3Alert>

      <!-- 工具栏 -->
      <div class="toolbar">
        <Md3Input
          v-model="searchQuery"
          placeholder="搜索 PID / 进程名 / 用户名 / 命令"
          class="search-input"
          type="search"
        >
          <template #prefix>
            <Md3Icon name="search" size="16" class="search-icon" />
          </template>
        </Md3Input>

        <Md3Select
          v-model="statusFilterValue"
          :options="statusOptions"
          placeholder="状态筛选"
          style="width: 130px"
        />

        <Md3Select
          v-model="userFilterValue"
          :options="userOptions"
          placeholder="用户筛选"
          style="width: 130px"
        />

        <div class="sort-buttons">
          <Md3Button
            size="sm"
            :type="sortColumn === 'cpu_percent' ? 'primary' : 'default'"
            @click="toggleSort('cpu_percent')"
          >
            CPU{{ sortColumn === 'cpu_percent' ? sortArrow : '' }}
          </Md3Button>
          <Md3Button
            size="sm"
            :type="sortColumn === 'mem_percent' ? 'primary' : 'default'"
            @click="toggleSort('mem_percent')"
          >
            MEM{{ sortColumn === 'mem_percent' ? sortArrow : '' }}
          </Md3Button>
          <Md3Button
            size="sm"
            :type="sortColumn === 'pid' ? 'primary' : 'default'"
            @click="toggleSort('pid')"
          >
            PID{{ sortColumn === 'pid' ? sortArrow : '' }}
          </Md3Button>
        </div>
      </div>

      <!-- 批量操作栏 -->
      <div v-if="selectedRows.length > 0" class="batch-bar">
        <span class="batch-count">已选中 {{ selectedRows.length }} 个进程</span>
        <Md3Button size="sm" @click="doBatchKill('SIGTERM')">
          批量优雅终止 (SIGTERM)
        </Md3Button>
        <Md3Button size="sm" type="danger" @click="doBatchKill('SIGKILL')">
          批量强制结束 (SIGKILL)
        </Md3Button>
        <Md3Button size="sm" @click="clearSelection">取消选择</Md3Button>
      </div>

      <!-- 进程表格 -->
      <Md3Card class="process-table-card">
        <Md3Table
          :columns="processColumns"
          :data="displayProcesses"
          :selection="true"
          @selection-change="onSelectionChange"
          :empty-text="loading ? '正在加载进程数据...' : '未找到匹配的进程'"
          stripe
        >
          <!-- 进程名列 -->
          <template #name="{ row }">
            <span class="process-name">{{ row.name || '-' }}</span>
          </template>

          <!-- 状态列 -->
          <template #status="{ row }">
            <Md3Tag :type="statusColor(row.status as string)">
              {{ formatStatus(row.status as string) }}
            </Md3Tag>
          </template>

          <!-- CPU% 列 -->
          <template #cpu_percent="{ row }">
            <span :style="{ color: resourceColor(Number(row.cpu_percent), 'cpu'), fontWeight: 600 }">
              {{ row.cpu_percent }}%
            </span>
          </template>

          <!-- 内存% 列 -->
          <template #mem_percent="{ row }">
            <span :style="{ color: resourceColor(Number(row.mem_percent), 'mem'), fontWeight: 600 }">
              {{ row.mem_percent }}%
            </span>
          </template>

          <!-- VSZ 列 -->
          <template #vsz="{ row }">
            {{ formatBytes(Number(row.vsz)) }}
          </template>

          <!-- RSS 列 -->
          <template #rss="{ row }">
            {{ formatBytes(Number(row.rss)) }}
          </template>

          <!-- 命令列 -->
          <template #command="{ row }">
            <Md3Tooltip :content="row.command || ''" placement="top">
              <span class="command-cell">{{ row.command || '-' }}</span>
            </Md3Tooltip>
          </template>

          <!-- 操作列 -->
          <template #actions="{ row }">
            <div class="action-buttons">
              <Md3Button size="sm" variant="text" @click="showDetail(Number(row.pid))">详情</Md3Button>
              <div class="kill-dropdown">
                <Md3Button size="sm" variant="text" @click="toggleKillMenu(Number(row.pid))">
                  终止 ▼
                </Md3Button>
                <div v-if="currentKillPid === Number(row.pid)" class="kill-menu">
                  <div class="kill-menu-item" @click="doKill(Number(row.pid), 'SIGTERM')">
                    优雅终止 (SIGTERM)
                  </div>
                  <div class="kill-menu-item danger" @click="doKill(Number(row.pid), 'SIGKILL')">
                    强制结束 (SIGKILL)
                  </div>
                </div>
              </div>
              <Md3Button size="sm" variant="text" @click="showNiceDialog(Number(row.pid))">Nice</Md3Button>
            </div>
          </template>
        </Md3Table>
      </Md3Card>
    </template>

    <!-- 进程详情对话框 -->
    <Md3Dialog
      :visible="detailVisible"
      title="进程详情"
      width="800px"
      @update:visible="detailVisible = $event"
    >
      <template v-if="currentDetail">
        <div class="detail-grid">
          <div class="detail-item">
            <span class="detail-label">PID</span>
            <span class="detail-value">{{ currentDetail.pid }}</span>
          </div>
          <div class="detail-item">
            <span class="detail-label">PPID</span>
            <span class="detail-value">{{ currentDetail.ppid }}</span>
          </div>
          <div class="detail-item">
            <span class="detail-label">状态</span>
            <span class="detail-value">
              <Md3Tag :type="statusColor(currentDetail.status) as any">
                {{ formatStatus(currentDetail.status) }}
              </Md3Tag>
            </span>
          </div>
          <div class="detail-item">
            <span class="detail-label">用户</span>
            <span class="detail-value">{{ currentDetail.user }}</span>
          </div>
          <div class="detail-item">
            <span class="detail-label">CPU%</span>
            <span class="detail-value" :style="{ color: resourceColor(currentDetail.cpu_percent, 'cpu') }">
              {{ currentDetail.cpu_percent }}%
            </span>
          </div>
          <div class="detail-item">
            <span class="detail-label">内存%</span>
            <span class="detail-value" :style="{ color: resourceColor(currentDetail.mem_percent, 'mem') }">
              {{ currentDetail.mem_percent }}%
            </span>
          </div>
          <div class="detail-item">
            <span class="detail-label">VSZ</span>
            <span class="detail-value">{{ formatBytes(currentDetail.vsz) }}</span>
          </div>
          <div class="detail-item">
            <span class="detail-label">RSS</span>
            <span class="detail-value">{{ formatBytes(currentDetail.rss) }}</span>
          </div>
          <div class="detail-item">
            <span class="detail-label">运行时长</span>
            <span class="detail-value">{{ currentDetail.start_time || '-' }}</span>
          </div>
          <div class="detail-item">
            <span class="detail-label">线程数</span>
            <span class="detail-value">{{ currentDetail.thread_count || '-' }}</span>
          </div>
          <div class="detail-item">
            <span class="detail-label">文件描述符</span>
            <span class="detail-value">{{ currentDetail.fd_count || '-' }}</span>
          </div>
          <div class="detail-item">
            <span class="detail-label">Nice 值</span>
            <span class="detail-value">{{ currentDetail.nice ?? '-' }}</span>
          </div>
          <div class="detail-item full-width">
            <span class="detail-label">进程名</span>
            <span class="detail-value">{{ currentDetail.name || '-' }}</span>
          </div>
          <div class="detail-item full-width">
            <span class="detail-label">命令</span>
            <span class="detail-value command-full">{{ currentDetail.command || '-' }}</span>
          </div>
          <div class="detail-item full-width">
            <span class="detail-label">工作目录</span>
            <span class="detail-value">{{ currentDetail.cwd || '-' }}</span>
          </div>
          <div class="detail-item" v-if="currentDetail.net_connections">
            <span class="detail-label">网络连接</span>
            <span class="detail-value">{{ currentDetail.net_connections }}</span>
          </div>
          <div class="detail-item" v-if="currentDetail.cgroup">
            <span class="detail-label">Cgroup</span>
            <span class="detail-value cgroup-text">{{ currentDetail.cgroup }}</span>
          </div>
        </div>

        <!-- 环境变量 -->
        <Md3Collapse title="环境变量" v-if="currentDetail.environ && currentDetail.environ.length > 0">
          <div class="env-list">
            <div v-for="env in currentDetail.environ" :key="env" class="env-item">
              <span class="env-text">{{ env }}</span>
            </div>
          </div>
        </Md3Collapse>

        <!-- 操作按钮 -->
        <div class="detail-actions">
          <Md3Button
            v-if="currentDetail.cwd"
            size="sm"
            @click="goToFileManager(currentDetail.cwd)"
          >
            <Md3Icon name="folder-open" size="1em" />打开所在目录
          </Md3Button>
          <Md3Button
            v-if="currentDetail.service_name"
            size="sm"
            type="primary"
            @click="serviceControl(currentDetail.service_name, 'restart')"
          >
            重启服务 ({{ currentDetail.service_name }})
          </Md3Button>
          <Md3Button
            v-if="currentDetail.service_name"
            size="sm"
            type="danger"
            @click="serviceControl(currentDetail.service_name, 'stop')"
          >
            停止服务 ({{ currentDetail.service_name }})
          </Md3Button>
        </div>
      </template>

      <template #footer>
        <Md3Button size="sm" @click="detailVisible = false">关闭</Md3Button>
      </template>
    </Md3Dialog>

    <!-- Nice 值设置对话框 -->
    <Md3Dialog
      :visible="niceVisible"
      title="设置 Nice 值"
      width="500px"
      @update:visible="niceVisible = $event"
    >
      <div class="nice-dialog-content">
        <p class="nice-info">进程 PID: <strong>{{ nicePid }}</strong></p>
        <p class="nice-info" v-if="currentNiceValue !== null">
          当前 Nice 值: <strong>{{ currentNiceValue }}</strong>
        </p>
        <div class="nice-input-group">
          <label class="nice-label">Nice 值 (-20 ~ 19):</label>
          <div class="nice-slider-wrapper">
            <input
              type="range"
              v-model.number="niceValue"
              min="-20"
              max="19"
              class="nice-slider"
            />
            <div class="nice-slider-labels">
              <span>-20 (最高优先级)</span>
              <span>0</span>
              <span>19 (最低优先级)</span>
            </div>
          </div>
          <Md3Input
            v-model="niceValue"
            type="number"
            :min="-20"
            :max="19"
            class="nice-number-input"
          />
        </div>
      </div>

      <template #footer>
        <Md3Button size="sm" @click="doSetNice" type="primary">确认</Md3Button>
        <Md3Button size="sm" @click="niceVisible = false">取消</Md3Button>
      </template>
    </Md3Dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount, nextTick, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useProcessStore } from '@/stores/processStore'
import { useSshAccountStore } from '@/stores/sshAccountStore'
import {
  Md3PageHeader,
  Md3Divider,
  Md3Card,
  Md3Select,
  Md3Table,
  Md3Tag,
  Md3Empty,
  Md3Alert,
  Md3Dialog,
  Md3Collapse,
  Md3Tooltip,
  Md3Icon,
} from '@/components/md3'
import Md3Input from '@/components/md3/Md3Input.vue'
import Md3Button from '@/components/Md3Button.vue'

/** 路由与 Store */
const router = useRouter()
const processStore = useProcessStore()
const sshStore = useSshAccountStore()

/** 状态变量 */
const selectedAlias = ref('')
const refreshIntervalValue = ref<number>(0)
const detailVisible = ref(false)
const niceVisible = ref(false)
const nicePid = ref(0)
const currentNiceValue = ref<number | null>(null)
const niceValue = ref(0)
const currentDetail = ref<any>(null)
const showAnomalyOnly = ref(false)
const currentKillPid = ref<number | null>(null)

/** 本地筛选与排序状态（不依赖 store） */
const searchQuery = ref('')
const statusFilterValue = ref('')
const userFilterValue = ref('')
const sortColumn = ref('')
const sortOrder = ref<'asc' | 'desc'>('desc')
const selectedRows = ref<any[]>([])

/** 同步筛选状态到 store（如果 store 需要） */
watch([searchQuery, statusFilterValue, userFilterValue], ([q, s, u]) => {
  // 如果 processStore 支持这些属性，可以同步
  if (processStore.searchQuery !== undefined) processStore.searchQuery = q as string
  if (processStore.statusFilter !== undefined) {
    processStore.statusFilter = (s as string) ? [(s as string)] : []
  }
  if (processStore.userFilter !== undefined) processStore.userFilter = u as string
})

/** 服务器选择选项 */
const selectOptions = computed(() =>
  sshStore.accounts.map((a) => ({ label: `${a.alias} (${a.host})`, value: a.alias }))
)

/** 刷新频率选项 */
const refreshOptions = [
  { label: '1秒', value: 1000 },
  { label: '3秒', value: 3000 },
  { label: '10秒', value: 10000 },
  { label: '手动', value: 0 },
]

/** 状态筛选选项 */
const statusOptions = [
  { label: '全部', value: '' },
  { label: 'Running', value: 'running' },
  { label: 'Sleeping', value: 'sleeping' },
  { label: 'Zombie', value: 'zombie' },
  { label: 'Stopped', value: 'stopped' },
  { label: 'Idle', value: 'idle' },
]

/** 用户筛选选项 */
const userOptions = computed(() => {
  const users = processStore.uniqueUsers || []
  return [
    { label: '全部用户', value: '' },
    ...users.map((u: string) => ({ label: u, value: u })),
  ]
})

/** 页面副标题 */
const subtitleText = computed(() => {
  if (!selectedAlias.value) return ''
  const total = processStore.processes?.length || 0
  const anomalyCount = processStore.anomalies?.total_anomalies || 0
  return `${selectedAlias.value} | 共 ${total} 个进程 | ${anomalyCount} 个异常`
})

/** 异常状态 */
const hasAnomalies = computed(() => (processStore.anomalies?.total_anomalies || 0) > 0)
const anomalyType = computed(() => {
  const zombieCount = (processStore.anomalies?.zombies || []).length
  if (zombieCount > 0) return 'danger'
  return 'warning'
})
const anomalyTitle = computed(() => {
  const total = processStore.anomalies?.total_anomalies || 0
  return `检测到 ${total} 个异常进程`
})
const anomalyDescription = computed(() => {
  const zombieCount = (processStore.anomalies?.zombies || []).length
  const highCpu = (processStore.anomalies?.high_cpu || []).length
  const highMem = (processStore.anomalies?.high_mem || []).length
  return `僵尸进程: ${zombieCount} | 高CPU: ${highCpu} | 高内存: ${highMem}`
})

/** 流式推送状态 */
const streaming = computed(() => processStore.streaming)

/** 加载状态 */
const loading = computed(() => processStore.loading)

/** 表格列定义 */
const processColumns = [
  { prop: 'pid', label: 'PID', width: '80px' },
  { prop: 'ppid', label: 'PPID', width: '80px' },
  { prop: 'name', label: '进程名', width: '120px' },
  { prop: 'status', label: '状态', width: '100px' },
  { prop: 'user', label: '用户', width: '100px' },
  { prop: 'cpu_percent', label: 'CPU%', width: '90px' },
  { prop: 'mem_percent', label: 'MEM%', width: '90px' },
  { prop: 'vsz', label: 'VSZ', width: '100px' },
  { prop: 'rss', label: 'RSS', width: '100px' },
  { prop: 'thread_count', label: '线程', width: '70px' },
  { prop: 'command', label: '命令' },
  { prop: 'actions', label: '操作', width: '150px' },
]

/** 过滤和排序后的进程列表 */
const displayProcesses = computed(() => {
  let processes = processStore.filteredProcesses || processStore.processes || []

  // 搜索过滤
  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    processes = processes.filter((p: any) => {
      return (
        String(p.pid).includes(query) ||
        (p.name || '').toLowerCase().includes(query) ||
        (p.user || '').toLowerCase().includes(query) ||
        (p.command || '').toLowerCase().includes(query)
      )
    })
  }

  // 状态过滤
  if (statusFilterValue.value) {
    processes = processes.filter((p: any) => p.status === statusFilterValue.value)
  }

  // 用户过滤
  if (userFilterValue.value) {
    processes = processes.filter((p: any) => p.user === userFilterValue.value)
  }

  // 异常过滤
  if (showAnomalyOnly.value) {
    const anomalyPids = processStore.anomalyPidSet || new Set()
    processes = processes.filter((p: any) => anomalyPids.has(p.pid))
  }

  // 排序
  if (sortColumn.value) {
    const col = sortColumn.value
    const order = sortOrder.value === 'desc' ? -1 : 1
    processes = [...processes].sort((a: any, b: any) => {
      const va = a[col] ?? 0
      const vb = b[col] ?? 0
      return (va - vb) * order
    })
  }

  return processes
})

/** 排序箭头 */
const sortArrow = computed(() => {
  return sortOrder.value === 'desc' ? '↓' : '↑'
})

/**
 * 状态标签颜色映射
 */
function statusColor(status: string): 'primary' | 'success' | 'warning' | 'danger' | 'info' {
  switch (status) {
    case 'running':
      return 'success'
    case 'sleeping':
      return 'info'
    case 'zombie':
      return 'danger'
    case 'stopped':
      return 'warning'
    case 'idle':
      return 'primary'
    default:
      return 'info'
  }
}

/** 格式化状态显示文本 */
function formatStatus(status: string): string {
  if (!status) return '-'
  return status.charAt(0).toUpperCase() + status.slice(1)
}

/** CPU/内存资源颜色 */
function resourceColor(value: number, type: 'cpu' | 'mem'): string {
  const threshold1 = type === 'cpu' ? 50 : 50
  const threshold2 = type === 'cpu' ? 90 : 80
  const numValue = Number(value) || 0
  if (numValue >= threshold2) return '#ef4444'
  if (numValue >= threshold1) return '#f59e0b'
  return '#22c55e'
}

/** 格式化字节大小（KB 转可读格式） */
function formatBytes(kb: number): string {
  if (!kb && kb !== 0) return '-'
  const numKb = Number(kb) || 0
  if (numKb < 1024) return `${numKb} KB`
  if (numKb < 1024 * 1024) return `${(numKb / 1024).toFixed(1)} MB`
  return `${(numKb / (1024 * 1024)).toFixed(2)} GB`
}

/** 切换排序 */
function toggleSort(column: string) {
  if (sortColumn.value === column) {
    sortOrder.value = sortOrder.value === 'desc' ? 'asc' : 'desc'
  } else {
    sortColumn.value = column
    sortOrder.value = 'desc'
  }
}

/** 清除选择 */
function clearSelection() {
  selectedRows.value = []
  processStore.deselectAll?.()
}

/** 账户变更处理 */
async function onAccountChange(value: string | number | (string | number)[]) {
  selectedAlias.value = String(value)
  processStore.currentAlias = selectedAlias.value
  await refreshAll()
}

/** 刷新全部数据 */
async function refreshAll() {
  if (!selectedAlias.value) return
  processStore.currentAlias = selectedAlias.value
  await processStore.fetchProcessList()
  await processStore.fetchAlertConfig?.()
}

/** 刷新频率变更处理 */
function onRefreshIntervalChange(value: any) {
  const ms = Number(value)
  refreshIntervalValue.value = ms
  processStore.refreshInterval = ms
  if (ms > 0 && !processStore.streaming) {
    processStore.startAutoRefresh?.()
  } else {
    processStore.stopAutoRefresh?.()
  }
}

/** 切换流式推送 */
function toggleStream() {
  if (processStore.streaming) {
    processStore.disconnect?.()
  } else {
    processStore.connectWebSocket?.(selectedAlias.value)
  }
}

/** 显示进程详情 */
async function showDetail(pid: number) {
  const detail = await processStore.fetchProcessDetail(pid)
  currentDetail.value = detail
  detailVisible.value = true
}

/** 终止进程 */
async function doKill(pid: number, signal: string) {
  currentKillPid.value = null
  await processStore.killProcess(pid, signal)
  await refreshAll()
}

/** 批量终止进程 */
async function doBatchKill(signal: string) {
  const pids = selectedRows.value.map((r: any) => r.pid)
  if (pids.length === 0) return
  await processStore.batchKill?.(pids, signal)
  clearSelection()
  await refreshAll()
}

/** 显示 Nice 对话框 */
function showNiceDialog(pid: number) {
  nicePid.value = pid
  const proc = processStore.processes?.find((p: any) => p.pid === pid)
  currentNiceValue.value = (proc as any)?.nice ?? null
  niceValue.value = (proc as any)?.nice ?? 0
  niceVisible.value = true
}

/** 设置 Nice 值 */
async function doSetNice() {
  await processStore.setNice?.(nicePid.value, niceValue.value)
  niceVisible.value = false
  await refreshAll()
}

/** 跳转到文件管理器 */
function goToFileManager(cwd: string) {
  router.push({ path: '/file-manager', query: { path: cwd } })
  detailVisible.value = false
}

/** 服务控制 */
async function serviceControl(name: string, action: string) {
  await processStore.serviceControl?.(name, action)
  await refreshAll()
}

/** 切换终止菜单 */
function toggleKillMenu(pid: number) {
  if (currentKillPid.value === pid) {
    currentKillPid.value = null
  } else {
    currentKillPid.value = pid
    nextTick(() => {
      document.addEventListener('click', handleOutsideClick)
    })
  }
}

/** 处理外部点击关闭菜单 */
function handleOutsideClick(e: MouseEvent) {
  const target = e.target as HTMLElement
  if (!target.closest('.kill-dropdown')) {
    currentKillPid.value = null
    document.removeEventListener('click', handleOutsideClick)
  }
}

/** 选择变更处理 - Md3Table 返回行数组 */
function onSelectionChange(rows: any[]) {
  selectedRows.value = rows
  // 同步到 store（如果 store 需要）
  if (processStore.selectedPids instanceof Set) {
    processStore.selectedPids.clear()
    rows.forEach((r: any) => processStore.selectedPids.add(r.pid))
  }
}

/** 组件挂载 */
onMounted(async () => {
  await sshStore.fetchAccounts()
  const defaultAcc = sshStore.accounts.find((a) => (a as any).default)
  const firstAcc = sshStore.accounts[0]
  const alias = defaultAcc?.alias || firstAcc?.alias || ''
  if (alias) {
    selectedAlias.value = alias
    processStore.currentAlias = alias
    refreshIntervalValue.value = processStore.refreshInterval || 0
    await refreshAll()
    if (processStore.refreshInterval > 0) {
      processStore.startAutoRefresh?.()
    }
  }
})

/** 组件卸载 */
onBeforeUnmount(() => {
  processStore.disconnect?.()
  processStore.stopAutoRefresh?.()
  document.removeEventListener('click', handleOutsideClick)
})
</script>

<style scoped>
.process-manager-page {
  padding: 0;
}

.empty-wrapper {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 300px;
}

/* 异常告警横幅 */
.anomaly-banner {
  margin-top: var(--md3-space-md);
  margin-bottom: var(--md3-space-md);
}

/* 工具栏 */
.toolbar {
  display: flex;
  align-items: center;
  gap: var(--md3-space-md);
  margin-top: var(--md3-space-md);
  margin-bottom: var(--md3-space-md);
  flex-wrap: wrap;
}

.search-input {
  flex: 1;
  min-width: 200px;
  max-width: 400px;
}

.search-icon {
  width: 16px;
  height: 16px;
  color: var(--md3-on-surface-variant);
}

.sort-buttons {
  display: flex;
  gap: var(--md3-space-xs);
  margin-left: auto;
}

/* 批量操作栏 */
.batch-bar {
  display: flex;
  align-items: center;
  gap: var(--md3-space-md);
  padding: var(--md3-space-sm) var(--md3-space-lg);
  background: var(--md3-primary-container);
  border: 1px solid var(--md3-outline);
  border-radius: var(--md3-shape-md);
  margin-bottom: var(--md3-space-md);
}

.batch-count {
  font-size: 13px;
  font-weight: 600;
  color: var(--md3-on-primary-container);
}

/* 进程表格 */
.process-table-card {
  margin-top: var(--md3-space-md);
}

.process-table-card :deep(.md3-table) {
  font-size: 13px;
}

.process-name {
  font-weight: 500;
  color: var(--md3-on-surface);
}

.command-cell {
  max-width: 300px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  display: block;
  color: var(--md3-on-surface-variant);
  font-family: var(--md3-type-mono, monospace);
  font-size: 12px;
}

.action-buttons {
  display: flex;
  align-items: center;
  gap: var(--md3-space-xs);
}

/* 终止下拉菜单 */
.kill-dropdown {
  position: relative;
  display: inline-flex;
}

.kill-menu {
  position: absolute;
  top: 100%;
  right: 0;
  z-index: 100;
  background: var(--md3-surface-container);
  border: 1px solid var(--md3-outline-variant);
  border-radius: var(--md3-shape-sm);
  backdrop-filter: var(--md3-glass-blur);
  -webkit-backdrop-filter: var(--md3-glass-blur);
  min-width: 160px;
  padding: var(--md3-space-xs) 0;
}

.kill-menu-item {
  padding: var(--md3-space-sm) var(--md3-space-md);
  font-size: 13px;
  color: var(--md3-on-surface);
  cursor: pointer;
  transition: background var(--md3-motion-duration-short) var(--md3-motion-easing-standard);
}

.kill-menu-item:hover {
  background: var(--md3-surface-container-high);
}

.kill-menu-item.danger {
  color: var(--md3-error);
}

.kill-menu-item.danger:hover {
  background: var(--md3-error-container);
}

/* 详情对话框 */
.detail-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--md3-space-md);
  padding: var(--md3-space-md) 0;
}

.detail-item {
  display: flex;
  flex-direction: column;
  gap: var(--md3-space-xs);
  padding: var(--md3-space-sm) var(--md3-space-md);
  background: var(--md3-surface-container-low);
  border-radius: var(--md3-shape-sm);
}

.detail-item.full-width {
  grid-column: span 3;
}

.detail-label {
  font-size: 12px;
  color: var(--md3-on-surface-variant);
  font-weight: 500;
}

.detail-value {
  font-size: 13px;
  color: var(--md3-on-surface);
  word-break: break-all;
}

.command-full {
  font-family: var(--md3-type-mono, monospace);
  font-size: 12px;
  background: var(--md3-surface-container);
  padding: var(--md3-space-xs) var(--md3-space-sm);
  border-radius: var(--md3-shape-xs);
  overflow-x: auto;
}

.cgroup-text {
  font-family: var(--md3-type-mono, monospace);
  font-size: 11px;
  color: var(--md3-on-surface-variant);
}

/* 环境变量列表 */
.env-list {
  max-height: 300px;
  overflow-y: auto;
  padding: var(--md3-space-sm) 0;
}

.env-item {
  padding: var(--md3-space-xs) var(--md3-space-sm);
  border-bottom: 1px solid var(--md3-outline-variant);
  font-size: 12px;
  font-family: var(--md3-type-mono, monospace);
  color: var(--md3-on-surface-variant);
  word-break: break-all;
}

/* 详情操作按钮 */
.detail-actions {
  display: flex;
  gap: var(--md3-space-md);
  margin-top: var(--md3-space-lg);
  padding-top: var(--md3-space-md);
  border-top: 1px solid var(--md3-outline-variant);
  flex-wrap: wrap;
}

/* Nice 对话框 */
.nice-dialog-content {
  padding: var(--md3-space-md) 0;
}

.nice-info {
  margin: 0 0 var(--md3-space-md);
  font-size: 14px;
  color: var(--md3-on-surface-variant);
}

.nice-info strong {
  color: var(--md3-on-surface);
  font-weight: 600;
}

.nice-input-group {
  display: flex;
  flex-direction: column;
  gap: var(--md3-space-md);
}

.nice-label {
  font-size: 14px;
  font-weight: 500;
  color: var(--md3-on-surface);
}

.nice-slider-wrapper {
  display: flex;
  flex-direction: column;
  gap: var(--md3-space-xs);
}

.nice-slider {
  width: 100%;
  height: 6px;
  border-radius: 3px;
  background: linear-gradient(to right, var(--md3-primary) 0%, var(--md3-on-surface-variant) 50%, var(--md3-primary) 100%);
  outline: none;
  -webkit-appearance: none;
  appearance: none;
}

.nice-slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: var(--md3-primary);
  cursor: pointer;
  box-shadow: var(--md3-elevation-level1);
}

.nice-slider::-moz-range-thumb {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: var(--md3-primary);
  cursor: pointer;
  border: none;
  box-shadow: var(--md3-elevation-level1);
}

.nice-slider-labels {
  display: flex;
  justify-content: space-between;
  font-size: 11px;
  color: var(--md3-on-surface-variant);
}

.nice-number-input {
  width: 100px;
  align-self: flex-start;
}

/* 响应式 */
@media (max-width: 768px) {
  .toolbar {
    flex-direction: column;
    align-items: stretch;
  }

  .search-input {
    max-width: none;
  }

  .sort-buttons {
    margin-left: 0;
    justify-content: center;
  }

  .detail-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .detail-item.full-width {
    grid-column: span 2;
  }

  .batch-bar {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
