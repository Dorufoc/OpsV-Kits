<template>
  <div class="log-analysis-page">
    <Md3PageHeader title="日志聚合分析">
      <template #subtitle>
        <span>轻量级日志采集、搜索与告警</span>
      </template>
      <template #actions>
        <Md3Input v-model="globalKeyword" placeholder="全局搜索..." style="width: 220px" @keyup.enter="onGlobalSearch" />
        <Md3Button size="sm" :type="realtimeConnected ? 'danger' : 'primary'" @click="toggleRealtime">
          <Md3Icon name="monitor" size="1em" />{{ realtimeConnected ? '断开推送' : '实时推送' }}
        </Md3Button>
      </template>
    </Md3PageHeader>
    <Md3Divider />

    <Md3Tabs v-model="activeTab" :tabs="tabItems" class="log-tabs" />

    <div v-if="activeTab === 'search'" class="tab-panel">
      <div class="filter-bar">
        <Md3Select v-model="filterLevel" :options="levelOptions" placeholder="日志级别" style="width: 140px" clearable />
        <Md3Input v-model="filterSource" placeholder="来源" style="width: 160px" />
        <Md3Select v-model="filterTimeRange" :options="timeRangeOptions" placeholder="时间范围" style="width: 160px" />
        <Md3Button size="sm" type="primary" @click="onSearch" :loading="loading">搜索</Md3Button>
      </div>

      <Md3Card class="log-card">
        <div v-if="searchResult.items.length === 0" style="padding: 24px">
          <Md3Empty description="暂无日志数据，请调整搜索条件" />
        </div>
        <div v-else class="log-list">
          <div
            v-for="log in searchResult.items"
            :key="log.id"
            class="log-row"
            :class="{ 'log-row--expanded': expandedLogId === log.id }"
            @click="toggleLogExpand(log.id)"
          >
            <div class="log-row-main">
              <span class="log-timestamp">{{ formatTimestamp(log.timestamp) }}</span>
              <Md3Tag :type="levelTagType(log.level)" size="sm">{{ log.level }}</Md3Tag>
              <span class="log-source">{{ log.source }}</span>
              <span class="log-message" :title="log.message">{{ truncate(log.message, 120) }}</span>
            </div>
            <div v-if="expandedLogId === log.id" class="log-row-detail">
              <div class="log-detail-section">
                <span class="log-detail-label">完整内容</span>
                <pre class="log-detail-content">{{ log.content || log.message }}</pre>
              </div>
              <div v-if="log.structured" class="log-detail-section">
                <span class="log-detail-label">结构化数据</span>
                <pre class="log-detail-content">{{ JSON.stringify(log.structured, null, 2) }}</pre>
              </div>
              <div v-if="log.tags?.length" class="log-detail-section">
                <span class="log-detail-label">标签</span>
                <div class="log-detail-tags">
                  <Md3Tag v-for="tag in log.tags" :key="tag" size="sm" type="info">{{ tag }}</Md3Tag>
                </div>
              </div>
            </div>
          </div>
        </div>
        <div v-if="searchResult.total > searchResult.pageSize" class="log-pagination">
          <Md3Button size="sm" :disabled="searchResult.page <= 1" @click="onPageChange(searchResult.page - 1)">上一页</Md3Button>
          <span class="log-pagination-info">{{ searchResult.page }} / {{ totalPages }} ({{ searchResult.total }} 条)</span>
          <Md3Button size="sm" :disabled="searchResult.page >= totalPages" @click="onPageChange(searchResult.page + 1)">下一页</Md3Button>
        </div>
      </Md3Card>
    </div>

    <div v-if="activeTab === 'realtime'" class="tab-panel">
      <div class="filter-bar">
        <Md3Select v-model="realtimeFilterLevel" :options="levelOptions" placeholder="过滤级别" style="width: 140px" clearable />
        <Md3Input v-model="realtimeFilterSource" placeholder="来源过滤" style="width: 160px" />
        <Md3Button v-if="!realtimeConnected" size="sm" type="primary" @click="store.connectRealtime()">连接</Md3Button>
        <Md3Button v-else size="sm" type="danger" @click="store.disconnectRealtime()">断开</Md3Button>
        <Md3Button size="sm" @click="realtimeLogs = []">清空</Md3Button>
        <span v-if="realtimeConnected" class="realtime-indicator">
          <span class="realtime-dot"></span>实时接收中
        </span>
      </div>

      <Md3Card class="log-card realtime-card">
        <div v-if="filteredRealtimeLogs.length === 0" style="padding: 24px">
          <Md3Empty description="暂无实时日志，请点击连接按钮" />
        </div>
        <div v-else class="log-list realtime-list" ref="realtimeListRef">
          <div v-for="log in filteredRealtimeLogs" :key="log.id" class="log-row log-row--realtime">
            <div class="log-row-main">
              <span class="log-timestamp">{{ formatTimestamp(log.timestamp) }}</span>
              <Md3Tag :type="levelTagType(log.level)" size="sm">{{ log.level }}</Md3Tag>
              <span class="log-source">{{ log.source }}</span>
              <span class="log-message" :title="log.message">{{ truncate(log.message, 200) }}</span>
            </div>
          </div>
        </div>
      </Md3Card>
    </div>

    <div v-if="activeTab === 'visualization'" class="tab-panel">
      <div class="filter-bar">
        <Md3Select v-model="vizTimeRange" :options="vizTimeRangeOptions" placeholder="时间范围" style="width: 160px" @update:model-value="onVizTimeRangeChange" />
      </div>
      <div class="grid-12 gap-12">
        <div class="span-16">
          <Md3Card class="chart-card">
            <template #header><span class="card-title">日志趋势</span></template>
            <MonitorLineChart :data="trendSeries" color="#1a73e8" yAxisName="条" height="320px" />
          </Md3Card>
        </div>
        <div class="span-8">
          <Md3Card class="chart-card">
            <template #header><span class="card-title">日志级别分布</span></template>
            <MonitorPieChart :data="aggregation.levelDistribution" height="200px" />
          </Md3Card>
          <Md3Card class="chart-card mt-12">
            <template #header><span class="card-title">来源排行</span></template>
            <MonitorLineChart :data="sourceRankSeries" color="#8b5cf6" yAxisName="条" height="200px" :area="false" />
          </Md3Card>
        </div>
      </div>
    </div>

    <div v-if="activeTab === 'alerts'" class="tab-panel">
      <div class="grid-12 gap-12">
        <div class="span-24">
          <Md3Card class="chart-card">
            <template #header>
              <div class="card-header-row">
                <span class="card-title">告警规则</span>
                <Md3Button size="sm" type="primary" @click="openAlertRuleDialog()">添加规则</Md3Button>
              </div>
            </template>
            <Md3Table :columns="alertRuleColumns" :data="alertRules" stripe hover>
              <template #matchPattern="{ row }">
                {{ patternLabel(row.matchPattern) }}
              </template>
              <template #pattern="{ row }">
                <code class="pattern-code">{{ row.pattern }}</code>
              </template>
              <template #timeWindow="{ row }">{{ row.timeWindow }}s</template>
              <template #threshold="{ row }">{{ row.threshold }} 次</template>
              <template #enabled="{ row }">
                <Md3Switch :model-value="row.enabled" @update:model-value="onToggleAlertRule(row.id, $event)" />
              </template>
              <template #actions="{ row }">
                <div class="action-btns">
                  <Md3Button size="sm" variant="text" @click="openAlertRuleDialog(row)">编辑</Md3Button>
                  <Md3Button size="sm" variant="text" type="danger" @click="onDeleteAlertRule(row.id)">删除</Md3Button>
                </div>
              </template>
            </Md3Table>
          </Md3Card>
        </div>
      </div>
      <div class="grid-12 gap-12 mt-12">
        <div class="span-24">
          <Md3Card class="chart-card">
            <template #header><span class="card-title">最近告警事件</span></template>
            <Md3Table :columns="alertEventColumns" :data="alertEvents" stripe hover>
              <template #triggeredAt="{ row }">{{ formatTimestamp(row.triggeredAt) }}</template>
              <template #level="{ row }">
                <Md3Tag :type="levelTagType(row.level)" size="sm">{{ row.level }}</Md3Tag>
              </template>
              <template #notified="{ row }">
                <Md3Tag :type="row.notified ? 'success' : 'warning'" size="sm">{{ row.notified ? '已通知' : '未通知' }}</Md3Tag>
              </template>
            </Md3Table>
          </Md3Card>
        </div>
      </div>

      <Md3Dialog v-model:visible="alertRuleDialogVisible" :title="editingAlertRule ? '编辑告警规则' : '添加告警规则'" width="520px">
        <div class="dialog-form">
          <div class="form-row">
            <Md3Input v-model="alertRuleForm.name" label="规则名称" placeholder="输入规则名称" />
          </div>
          <div class="form-row">
            <Md3Select v-model="alertRuleForm.matchPattern" :options="patternOptions" label="匹配模式" placeholder="选择匹配模式" />
          </div>
          <div class="form-row">
            <Md3Input v-model="alertRuleForm.pattern" label="模式内容" placeholder="输入匹配内容" />
          </div>
          <div class="form-row form-row--2col">
            <Md3Input v-model="alertRuleForm.timeWindow" label="时间窗口(秒)" type="number" />
            <Md3Input v-model="alertRuleForm.threshold" label="阈值(次)" type="number" />
          </div>
          <div class="form-row">
            <Md3Select v-model="alertRuleForm.level" :options="levelOptions" label="日志级别" placeholder="选择级别" clearable />
          </div>
        </div>
        <template #footer>
          <Md3Button size="sm" @click="alertRuleDialogVisible = false">取消</Md3Button>
          <Md3Button size="sm" type="primary" @click="onSaveAlertRule" :loading="savingAlertRule">保存</Md3Button>
        </template>
      </Md3Dialog>
    </div>

    <div v-if="activeTab === 'sources'" class="tab-panel">
      <Md3Card class="chart-card">
        <template #header>
          <div class="card-header-row">
            <span class="card-title">采集源管理</span>
            <Md3Button size="sm" type="primary" @click="openSourceDialog()">添加采集源</Md3Button>
          </div>
        </template>
        <Md3Table :columns="sourceColumns" :data="sources" stripe hover>
          <template #type="{ row }">
            <Md3Tag :type="sourceTypeTagType(row.type)" size="sm">{{ row.type }}</Md3Tag>
          </template>
          <template #path="{ row }">
            {{ row.path || row.container || (row.host ? `${row.host}:${row.port}` : '-') }}
          </template>
          <template #status="{ row }">
            <Md3Tag :type="sourceStatusTagType(row.status)" size="sm">{{ sourceStatusLabel(row.status) }}</Md3Tag>
          </template>
          <template #actions="{ row }">
            <div class="action-btns">
              <Md3Button v-if="row.status !== 'running'" size="sm" variant="text" type="success" @click="onStartSource(row.id)">启动</Md3Button>
              <Md3Button v-if="row.status === 'running'" size="sm" variant="text" type="warning" @click="onStopSource(row.id)">停止</Md3Button>
              <Md3Button size="sm" variant="text" type="danger" @click="onDeleteSource(row.id)">删除</Md3Button>
            </div>
          </template>
        </Md3Table>
      </Md3Card>

      <Md3Dialog v-model:visible="sourceDialogVisible" title="添加采集源" width="520px">
        <div class="dialog-form">
          <div class="form-row">
            <Md3Select v-model="sourceForm.type" :options="sourceTypeOptions" label="类型" placeholder="选择采集源类型" />
          </div>
          <div class="form-row">
            <Md3Input v-model="sourceForm.alias" label="别名" placeholder="输入采集源别名" />
          </div>
          <div v-if="sourceForm.type === 'file'" class="form-row">
            <Md3Input v-model="sourceForm.path" label="文件路径" placeholder="如 /var/log/app.log" />
          </div>
          <div v-if="sourceForm.type === 'docker'" class="form-row">
            <Md3Input v-model="sourceForm.container" label="容器名称" placeholder="输入容器名称或ID" />
          </div>
          <div v-if="sourceForm.type === 'tcp' || sourceForm.type === 'udp'" class="form-row form-row--2col">
            <Md3Input v-model="sourceForm.host" label="主机地址" placeholder="如 127.0.0.1" />
            <Md3Input v-model="sourceForm.port" label="端口" type="number" placeholder="如 514" />
          </div>
          <div v-if="sourceForm.type === 'system'" class="form-row">
            <Md3Input v-model="sourceForm.path" label="系统日志路径" placeholder="如 /var/log/syslog" />
          </div>
        </div>
        <template #footer>
          <Md3Button size="sm" @click="sourceDialogVisible = false">取消</Md3Button>
          <Md3Button size="sm" type="primary" @click="onSaveSource" :loading="savingSource">保存</Md3Button>
        </template>
      </Md3Dialog>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount, watch, nextTick, markRaw } from 'vue'
import { Md3Icon } from '@/components/md3'
import {
  Md3PageHeader, Md3Divider, Md3Card, Md3Select, Md3Tabs, Md3Table,
  Md3Tag, Md3Switch, Md3Empty, Md3Dialog, Md3Input,
} from '@/components/md3'
import Md3Button from '@/components/Md3Button.vue'
import MonitorLineChart from '@/components/MonitorLineChart.vue'
import MonitorPieChart from '@/components/MonitorPieChart.vue'
import { useLogAnalysisStore } from '@/stores/logAnalysisStore'
import type { LogLevel, AlertRule, LogFilter } from '@/stores/logAnalysisStore'

const store = useLogAnalysisStore()

const activeTab = ref('search')
const globalKeyword = ref('')
const expandedLogId = ref<string | null>(null)

const filterLevel = ref<LogLevel | ''>('')
const filterSource = ref('')
const filterTimeRange = ref('1h')
const realtimeFilterLevel = ref<LogLevel | ''>('')
const realtimeFilterSource = ref('')
const vizTimeRange = ref('1h')

const alertRuleDialogVisible = ref(false)
const editingAlertRule = ref<AlertRule | null>(null)
const savingAlertRule = ref(false)
const alertRuleForm = ref({
  name: '',
  matchPattern: 'contains' as 'contains' | 'regex' | 'exact',
  pattern: '',
  timeWindow: 60,
  threshold: 10,
  level: '' as LogLevel | '',
})

const sourceDialogVisible = ref(false)
const savingSource = ref(false)
const sourceForm = ref({
  type: 'file' as 'system' | 'docker' | 'tcp' | 'udp' | 'file',
  alias: '',
  path: '',
  container: '',
  host: '',
  port: 514,
})

const realtimeListRef = ref<HTMLElement>()

const tabItems = [
  { label: '日志搜索', value: 'search', icon: markRaw({ template: '<Md3Icon name="search" size="1em" />', components: { Md3Icon } }) },
  { label: '实时日志', value: 'realtime', icon: markRaw({ template: '<Md3Icon name="monitor" size="1em" />', components: { Md3Icon } }) },
  { label: '可视化', value: 'visualization', icon: markRaw({ template: '<Md3Icon name="chart" size="1em" />', components: { Md3Icon } }) },
  { label: '告警管理', value: 'alerts', icon: markRaw({ template: '<Md3Icon name="alert" size="1em" />', components: { Md3Icon } }) },
  { label: '采集源', value: 'sources', icon: markRaw({ template: '<Md3Icon name="folder" size="1em" />', components: { Md3Icon } }) },
]

const levelOptions = [
  { label: 'DEBUG', value: 'DEBUG' },
  { label: 'INFO', value: 'INFO' },
  { label: 'WARN', value: 'WARN' },
  { label: 'ERROR', value: 'ERROR' },
  { label: 'CRITICAL', value: 'CRITICAL' },
]

const timeRangeOptions = [
  { label: '最近 1 小时', value: '1h' },
  { label: '最近 6 小时', value: '6h' },
  { label: '最近 24 小时', value: '24h' },
  { label: '最近 7 天', value: '7d' },
]

const vizTimeRangeOptions = [
  { label: '最近 1 小时', value: '1h' },
  { label: '最近 6 小时', value: '6h' },
  { label: '最近 24 小时', value: '24h' },
  { label: '最近 7 天', value: '7d' },
]

const patternOptions = [
  { label: '包含', value: 'contains' },
  { label: '正则匹配', value: 'regex' },
  { label: '精确匹配', value: 'exact' },
]

const sourceTypeOptions = [
  { label: '系统日志', value: 'system' },
  { label: 'Docker 容器', value: 'docker' },
  { label: 'TCP', value: 'tcp' },
  { label: 'UDP', value: 'udp' },
  { label: '文件', value: 'file' },
]

const alertRuleColumns = [
  { prop: 'name', label: '名称' },
  { prop: 'matchPattern', label: '匹配模式' },
  { prop: 'pattern', label: '模式内容' },
  { prop: 'timeWindow', label: '时间窗口' },
  { prop: 'threshold', label: '阈值' },
  { prop: 'enabled', label: '状态' },
  { prop: 'actions', label: '操作', width: '140px' },
]

const alertEventColumns = [
  { prop: 'ruleName', label: '规则名称' },
  { prop: 'level', label: '级别' },
  { prop: 'triggeredAt', label: '触发时间' },
  { prop: 'matchCount', label: '匹配次数' },
  { prop: 'notified', label: '通知状态' },
]

const sourceColumns = [
  { prop: 'type', label: '类型' },
  { prop: 'alias', label: '别名' },
  { prop: 'path', label: '路径/容器/端口' },
  { prop: 'status', label: '状态' },
  { prop: 'actions', label: '操作', width: '160px' },
]

const searchResult = computed(() => store.searchResult)
const realtimeLogs = computed(() => store.realtimeLogs)
const realtimeConnected = computed(() => store.realtimeConnected)
const aggregation = computed(() => store.aggregation)
const alertRules = computed(() => store.alertRules)
const alertEvents = computed(() => store.alertEvents)
const sources = computed(() => store.sources)
const loading = computed(() => store.loading)

const totalPages = computed(() => Math.ceil(searchResult.value.total / searchResult.value.pageSize))

const filteredRealtimeLogs = computed(() => {
  let logs = realtimeLogs.value
  if (realtimeFilterLevel.value) {
    logs = logs.filter(l => l.level === realtimeFilterLevel.value)
  }
  if (realtimeFilterSource.value) {
    const q = realtimeFilterSource.value.toLowerCase()
    logs = logs.filter(l => l.source.toLowerCase().includes(q))
  }
  return logs
})

const trendSeries = computed(() =>
  aggregation.value.trend.map(t => ({ time: t.time, value: t.value }))
)

const sourceRankSeries = computed(() =>
  aggregation.value.sourceRanking.map(s => ({ time: 0, value: s.value, ...s }))
)

function levelTagType(level: LogLevel): 'info' | 'primary' | 'warning' | 'danger' {
  switch (level) {
    case 'DEBUG': return 'info'
    case 'INFO': return 'primary'
    case 'WARN': return 'warning'
    case 'ERROR': return 'danger'
    case 'CRITICAL': return 'danger'
    default: return 'info'
  }
}

function formatTimestamp(ts: number): string {
  const d = new Date(ts * 1000)
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
}

function truncate(str: string, len: number): string {
  if (!str) return ''
  return str.length > len ? str.slice(0, len) + '...' : str
}

function patternLabel(p: string): string {
  switch (p) {
    case 'contains': return '包含'
    case 'regex': return '正则匹配'
    case 'exact': return '精确匹配'
    default: return p
  }
}

function sourceTypeTagType(type: string): 'info' | 'primary' | 'success' | 'warning' | 'danger' {
  switch (type) {
    case 'system': return 'info'
    case 'docker': return 'primary'
    case 'tcp': return 'success'
    case 'udp': return 'warning'
    case 'file': return 'info'
    default: return 'info'
  }
}

function sourceStatusTagType(status: string): 'success' | 'info' | 'danger' {
  switch (status) {
    case 'running': return 'success'
    case 'stopped': return 'info'
    case 'error': return 'danger'
    default: return 'info'
  }
}

function sourceStatusLabel(status: string): string {
  switch (status) {
    case 'running': return '运行中'
    case 'stopped': return '已停止'
    case 'error': return '异常'
    default: return status
  }
}

function toggleLogExpand(id: string) {
  expandedLogId.value = expandedLogId.value === id ? null : id
}

function toggleRealtime() {
  if (realtimeConnected.value) {
    store.disconnectRealtime()
  } else {
    store.connectRealtime()
  }
}

function onGlobalSearch() {
  activeTab.value = 'search'
  onSearch()
}

function onSearch() {
  const filter: LogFilter = {
    level: filterLevel.value || undefined,
    source: filterSource.value || undefined,
    keyword: globalKeyword.value || undefined,
    page: 1,
  }
  if (filterTimeRange.value) {
    const now = Date.now() / 1000
    const rangeMap: Record<string, number> = { '1h': 3600, '6h': 21600, '24h': 86400, '7d': 604800 }
    const offset = rangeMap[filterTimeRange.value] || 3600
    filter.startTime = String(now - offset)
    filter.endTime = String(now)
  }
  store.searchLogs(filter)
}

function onPageChange(page: number) {
  const filter: LogFilter = {
    level: filterLevel.value || undefined,
    source: filterSource.value || undefined,
    keyword: globalKeyword.value || undefined,
    page,
  }
  store.searchLogs(filter)
}

function onVizTimeRangeChange() {
  store.fetchAggregation(vizTimeRange.value)
}

function openAlertRuleDialog(rule?: AlertRule) {
  if (rule) {
    editingAlertRule.value = rule
    alertRuleForm.value = {
      name: rule.name,
      matchPattern: rule.matchPattern,
      pattern: rule.pattern,
      timeWindow: rule.timeWindow,
      threshold: rule.threshold,
      level: rule.level || '',
    }
  } else {
    editingAlertRule.value = null
    alertRuleForm.value = {
      name: '',
      matchPattern: 'contains',
      pattern: '',
      timeWindow: 60,
      threshold: 10,
      level: '',
    }
  }
  alertRuleDialogVisible.value = true
}

async function onSaveAlertRule() {
  savingAlertRule.value = true
  try {
    if (editingAlertRule.value) {
      await store.updateAlertRule(editingAlertRule.value.id, { ...alertRuleForm.value })
    } else {
      await store.createAlertRule({ ...alertRuleForm.value, enabled: true } as any)
    }
    alertRuleDialogVisible.value = false
  } finally {
    savingAlertRule.value = false
  }
}

async function onDeleteAlertRule(id: string) {
  await store.deleteAlertRule(id)
}

async function onToggleAlertRule(id: string, enabled: boolean) {
  await store.toggleAlertRule(id, enabled)
}

function openSourceDialog() {
  sourceForm.value = {
    type: 'file',
    alias: '',
    path: '',
    container: '',
    host: '',
    port: 514,
  }
  sourceDialogVisible.value = true
}

async function onSaveSource() {
  savingSource.value = true
  try {
    await store.createSource({ ...sourceForm.value } as any)
    sourceDialogVisible.value = false
  } finally {
    savingSource.value = false
  }
}

async function onStartSource(id: string) {
  await store.startSource(id)
}

async function onStopSource(id: string) {
  await store.stopSource(id)
}

async function onDeleteSource(id: string) {
  await store.deleteSource(id)
}

watch(realtimeLogs, () => {
  nextTick(() => {
    if (realtimeListRef.value) {
      realtimeListRef.value.scrollTop = 0
    }
  })
})

watch(activeTab, (tab) => {
  if (tab === 'search' && searchResult.value.items.length === 0) {
    store.searchLogs()
  } else if (tab === 'visualization') {
    store.fetchAggregation(vizTimeRange.value)
  } else if (tab === 'alerts') {
    store.fetchAlertRules()
    store.fetchAlertEvents()
  } else if (tab === 'sources') {
    store.fetchSources()
  }
})

onMounted(() => {
  store.searchLogs()
})

onBeforeUnmount(() => {
  store.disconnectRealtime()
})
</script>

<style scoped>
.log-analysis-page {
  padding: 0;
}

.log-tabs {
  margin-bottom: var(--md3-space-lg);
}

.tab-panel {
  min-height: 200px;
}

.filter-bar {
  display: flex;
  align-items: center;
  gap: var(--md3-space-sm);
  margin-bottom: var(--md3-space-md);
  flex-wrap: wrap;
}

.log-card {
  margin-bottom: 0;
}

.log-card :deep(.md3-card-body) {
  padding: 0;
}

.log-list {
  max-height: 600px;
  overflow-y: auto;
}

.realtime-list {
  max-height: 700px;
}

.log-row {
  padding: var(--md3-space-sm) var(--md3-space-lg);
  border-bottom: 1px solid var(--md3-outline-variant);
  cursor: pointer;
  transition: background-color var(--md3-motion-duration-short) var(--md3-motion-easing-standard);
}

.log-row:hover {
  background: var(--md3-surface-container-low);
}

.log-row--realtime {
  cursor: default;
}

.log-row--expanded {
  background: var(--md3-surface-container-low);
}

.log-row-main {
  display: flex;
  align-items: center;
  gap: var(--md3-space-sm);
  min-height: 32px;
}

.log-timestamp {
  font: var(--md3-type-label-small);
  color: var(--md3-on-surface-variant);
  white-space: nowrap;
  flex-shrink: 0;
  width: 150px;
}

.log-source {
  font: var(--md3-type-label-small);
  color: var(--md3-primary);
  white-space: nowrap;
  flex-shrink: 0;
  max-width: 120px;
  overflow: hidden;
  text-overflow: ellipsis;
}

.log-message {
  font: var(--md3-type-body-small);
  color: var(--md3-on-surface);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
  min-width: 0;
}

.log-row-detail {
  padding: var(--md3-space-sm) 0 var(--md3-space-sm) 0;
  display: flex;
  flex-direction: column;
  gap: var(--md3-space-sm);
}

.log-detail-section {
  display: flex;
  flex-direction: column;
  gap: var(--md3-space-xs);
}

.log-detail-label {
  font: var(--md3-type-label-small);
  color: var(--md3-on-surface-variant);
  font-weight: 600;
}

.log-detail-content {
  margin: 0;
  padding: var(--md3-space-sm) var(--md3-space-md);
  background: var(--md3-surface-container);
  border-radius: var(--md3-shape-sm);
  font: var(--md3-type-body-small);
  color: var(--md3-on-surface);
  white-space: pre-wrap;
  word-break: break-all;
  max-height: 300px;
  overflow-y: auto;
}

.log-detail-tags {
  display: flex;
  flex-wrap: wrap;
  gap: var(--md3-space-xs);
}

.log-pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--md3-space-md);
  padding: var(--md3-space-md) var(--md3-space-lg);
  border-top: 1px solid var(--md3-outline-variant);
}

.log-pagination-info {
  font: var(--md3-type-body-small);
  color: var(--md3-on-surface-variant);
}

.realtime-indicator {
  display: flex;
  align-items: center;
  gap: var(--md3-space-xs);
  font: var(--md3-type-label-small);
  color: var(--md3-success);
}

.realtime-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--md3-success);
  animation: pulse-dot 1.5s ease-in-out infinite;
}

@keyframes pulse-dot {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.3; }
}

.grid-12 {
  display: grid;
  grid-template-columns: repeat(12, 1fr);
}

.gap-12 {
  gap: var(--md3-space-md);
}

.mt-12 {
  margin-top: var(--md3-space-md);
}

.span-8 {
  grid-column: span 4;
}

.span-16 {
  grid-column: span 8;
}

.span-24 {
  grid-column: span 12;
}

.chart-card {
  margin-bottom: 0;
}

.chart-card :deep(.md3-card-header) {
  padding-bottom: var(--md3-space-xs);
}

.card-title {
  display: flex;
  align-items: center;
  gap: var(--md3-space-xs);
  font-size: 13px;
  font-weight: 600;
  color: var(--md3-on-surface);
}

.card-header-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
}

.pattern-code {
  font-family: monospace;
  font-size: 12px;
  background: var(--md3-surface-container);
  padding: 2px 6px;
  border-radius: var(--md3-shape-xs);
  color: var(--md3-on-surface);
}

.action-btns {
  display: flex;
  gap: var(--md3-space-xs);
}

.dialog-form {
  display: flex;
  flex-direction: column;
  gap: var(--md3-space-md);
}

.form-row {
  display: flex;
  gap: var(--md3-space-md);
}

.form-row--2col > * {
  flex: 1;
}

.realtime-card :deep(.md3-card-body) {
  padding: 0;
}
</style>
