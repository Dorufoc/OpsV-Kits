<template>
  <div class="audit-log-page">
    <Md3PageHeader title="审计日志">
      <template #content>
        <span>操作审计与日志分析</span>
      </template>
    </Md3PageHeader>
    <Md3Divider />

    <Md3Tabs v-model="activeTab" :tabs="tabItems" class="page-tabs" />

    <div class="tab-content">
      <template v-if="activeTab === 'query'">
        <Md3Card :shadow="false" class="section-card">
          <template #header>
            <span><Md3Icon name="magnify" class="header-icon" /> 日志查询</span>
            <div class="card-header-right">
              <Md3Button size="sm" @click="showSaveQueryDialog = true">
                <Md3Icon name="content-save" size="1em" />保存查询
              </Md3Button>
              <Md3Select
                v-model="selectedSavedQuery"
                :options="savedQueryOptions"
                placeholder="加载已保存查询"
                style="width: 180px"
                @update:model-value="loadSavedQuery"
              />
            </div>
          </template>

          <div class="filter-bar">
            <div class="filter-field">
              <span class="filter-label">用户名</span>
              <Md3Input v-model="filters.username" placeholder="模糊匹配" class="filter-input" />
            </div>
            <div class="filter-field">
              <span class="filter-label">开始时间</span>
              <input type="datetime-local" v-model="filters.startTime" class="datetime-input" />
            </div>
            <div class="filter-field">
              <span class="filter-label">结束时间</span>
              <input type="datetime-local" v-model="filters.endTime" class="datetime-input" />
            </div>
            <div class="filter-field">
              <span class="filter-label">操作类型</span>
              <Md3Select
                v-model="filters.actionTypes"
                :options="actionTypeOptions"
                multiple
                placeholder="选择操作类型"
                class="filter-select-wide"
              />
            </div>
            <div class="filter-field">
              <span class="filter-label">模块</span>
              <Md3Select
                v-model="filters.modules"
                :options="moduleOptions"
                multiple
                placeholder="选择模块"
                class="filter-select-wide"
              />
            </div>
            <div class="filter-field">
              <span class="filter-label">状态</span>
              <Md3Select
                v-model="filters.status"
                :options="statusOptions"
                placeholder="全部"
                class="filter-select"
              />
            </div>
            <div class="filter-field">
              <span class="filter-label">关键词</span>
              <Md3Input v-model="filters.keyword" placeholder="全文搜索" class="filter-input" />
            </div>
            <div class="filter-actions">
              <Md3Button variant="primary" size="sm" @click="searchLogs" :loading="store.loading">
                <Md3Icon name="magnify" size="1em" />搜索
              </Md3Button>
              <Md3Button size="sm" @click="resetFilters">
                <Md3Icon name="refresh" size="1em" />重置
              </Md3Button>
            </div>
          </div>
        </Md3Card>

        <Md3Card :shadow="false" class="section-card">
          <template #header>
            <span><Md3Icon name="format-list-bulleted" class="header-icon" /> 日志列表</span>
            <div class="card-header-right">
              <Md3Button size="sm" @click="showExportDialog = true">
                <Md3Icon name="download" size="1em" />导出
              </Md3Button>
            </div>
          </template>

          <Md3Table
            :columns="logColumns"
            :data="pagedLogs"
            stripe
            hover
            :pagination="true"
            :page-size="pageSize"
            :page-sizes="[10, 20, 50, 100]"
            empty-text="暂无审计日志"
          >
            <template #timestamp="{ row }">
              {{ formatTimestamp(row.timestamp) }}
            </template>
            <template #action_type="{ row }">
              <div class="cell-tags">
                <Md3Tag type="info" size="sm">{{ row.action_type }}</Md3Tag>
                <Md3Tag v-if="row.sensitive" type="warning" size="sm">敏感</Md3Tag>
              </div>
            </template>
            <template #module="{ row }">
              <Md3Tag type="info" size="sm">{{ row.module }}</Md3Tag>
            </template>
            <template #status="{ row }">
              <Md3Tag :type="row.status === 'success' ? 'success' : 'danger'" size="sm">
                {{ row.status === 'success' ? '成功' : '失败' }}
              </Md3Tag>
            </template>
            <template #duration_ms="{ row }">
              {{ formatDuration(row.duration_ms) }}
            </template>
            <template #action_col="{ row }">
              <Md3Button size="sm" @click="openDetail(row)">详情</Md3Button>
            </template>
          </Md3Table>
        </Md3Card>
      </template>

      <template v-if="activeTab === 'statistics'">
        <Md3Card :shadow="false" class="section-card">
          <template #header>
            <span><Md3Icon name="chart-bar" class="header-icon" /> 统计分析</span>
            <div class="card-header-right">
              <div class="filter-field">
                <span class="filter-label">时间范围</span>
                <Md3Select v-model="statsTimeRange" :options="statsTimeRangeOptions" class="filter-select" />
              </div>
              <div class="filter-field">
                <span class="filter-label">粒度</span>
                <Md3Select v-model="statsGranularity" :options="granularityOptions" class="filter-select" />
              </div>
              <Md3Button size="sm" variant="primary" @click="refreshStatistics" :loading="store.loadingStats">
                <Md3Icon name="refresh" size="1em" />刷新
              </Md3Button>
            </div>
          </template>

          <div class="stats-grid">
            <div class="stats-card">
              <div class="stats-card-title">操作趋势</div>
              <div class="bar-chart-vertical">
                <div v-for="(item, idx) in trendData" :key="idx" class="bar-col">
                  <div class="bar-value">{{ item.count }}</div>
                  <div
                    class="bar-fill"
                    :style="{ height: trendMax > 0 ? (item.count / trendMax * 100) + '%' : '0%' }"
                  ></div>
                  <div class="bar-label">{{ item.label }}</div>
                </div>
              </div>
            </div>

            <div class="stats-card">
              <div class="stats-card-title">模块分布</div>
              <div class="bar-chart-horizontal">
                <div v-for="(item, idx) in moduleDistData" :key="idx" class="hbar-row">
                  <span class="hbar-label">{{ item.label }}</span>
                  <div class="hbar-track">
                    <div
                      class="hbar-fill"
                      :style="{ width: moduleDistMax > 0 ? (item.count / moduleDistMax * 100) + '%' : '0%' }"
                    ></div>
                  </div>
                  <span class="hbar-value">{{ item.count }}</span>
                </div>
              </div>
            </div>

            <div class="stats-card">
              <div class="stats-card-title">操作类型分布</div>
              <div class="bar-chart-horizontal">
                <div v-for="(item, idx) in actionDistData" :key="idx" class="hbar-row">
                  <span class="hbar-label">{{ item.label }}</span>
                  <div class="hbar-track">
                    <div
                      class="hbar-fill hbar-fill--secondary"
                      :style="{ width: actionDistMax > 0 ? (item.count / actionDistMax * 100) + '%' : '0%' }"
                    ></div>
                  </div>
                  <span class="hbar-value">{{ item.count }}</span>
                </div>
              </div>
            </div>

            <div class="stats-card">
              <div class="stats-card-title">用户操作排行</div>
              <div class="rank-list">
                <div v-for="(item, idx) in userRankData" :key="idx" class="rank-row">
                  <span class="rank-index">{{ idx + 1 }}</span>
                  <span class="rank-name">{{ item.label }}</span>
                  <div class="rank-track">
                    <div
                      class="rank-fill"
                      :style="{ width: userRankMax > 0 ? (item.count / userRankMax * 100) + '%' : '0%' }"
                    ></div>
                  </div>
                  <span class="rank-value">{{ item.count }}</span>
                </div>
              </div>
            </div>
          </div>
        </Md3Card>

        <Md3Card :shadow="false" class="section-card">
          <template #header>
            <span><Md3Icon name="alert-circle" class="header-icon" /> 异常检测</span>
          </template>
          <Md3Table
            :columns="anomalyColumns"
            :data="anomalies"
            stripe
            max-height="300"
            empty-text="暂无异常记录"
          >
            <template #level="{ row }">
              <Md3Tag :type="row.level === 'high' ? 'danger' : row.level === 'medium' ? 'warning' : 'info'" size="sm">
                {{ row.level === 'high' ? '高' : row.level === 'medium' ? '中' : '低' }}
              </Md3Tag>
            </template>
          </Md3Table>
        </Md3Card>
      </template>

      <template v-if="activeTab === 'archives'">
        <Md3Card :shadow="false" class="section-card">
          <template #header>
            <span><Md3Icon name="archive" class="header-icon" /> 归档管理</span>
            <div class="card-header-right">
              <Md3Button size="sm" variant="primary" @click="refreshArchives" :loading="loadingArchives">
                <Md3Icon name="refresh" size="1em" />刷新
              </Md3Button>
            </div>
          </template>
          <Md3Table
            v-if="archives.length > 0"
            :columns="archiveColumns"
            :data="archives"
            stripe
            empty-text="暂无归档文件"
          />
          <Md3Empty v-else description="暂无归档文件" :image-size="80" />
        </Md3Card>
      </template>
    </div>

    <Md3Dialog v-model:visible="showDetailDialog" title="日志详情" width="640px">
      <template v-if="detailLog">
        <div class="detail-grid">
          <div class="detail-item">
            <span class="detail-label">时间</span>
            <span class="detail-value">{{ formatTimestamp(detailLog.timestamp) }}</span>
          </div>
          <div class="detail-item">
            <span class="detail-label">用户</span>
            <span class="detail-value">{{ detailLog.username }}</span>
          </div>
          <div class="detail-item">
            <span class="detail-label">操作类型</span>
            <span class="detail-value">
              <Md3Tag type="info" size="sm">{{ detailLog.action_type }}</Md3Tag>
              <Md3Tag v-if="detailLog.sensitive" type="warning" size="sm">敏感</Md3Tag>
            </span>
          </div>
          <div class="detail-item">
            <span class="detail-label">模块</span>
            <span class="detail-value"><Md3Tag type="info" size="sm">{{ detailLog.module }}</Md3Tag></span>
          </div>
          <div class="detail-item">
            <span class="detail-label">状态</span>
            <span class="detail-value">
              <Md3Tag :type="detailLog.status === 'success' ? 'success' : 'danger'" size="sm">
                {{ detailLog.status === 'success' ? '成功' : '失败' }}
              </Md3Tag>
            </span>
          </div>
          <div class="detail-item">
            <span class="detail-label">请求路径</span>
            <span class="detail-value mono-text">{{ detailLog.request_path }}</span>
          </div>
          <div class="detail-item">
            <span class="detail-label">请求方法</span>
            <span class="detail-value">{{ detailLog.request_method }}</span>
          </div>
          <div class="detail-item">
            <span class="detail-label">来源 IP</span>
            <span class="detail-value mono-text">{{ detailLog.source_ip }}</span>
          </div>
          <div class="detail-item">
            <span class="detail-label">耗时</span>
            <span class="detail-value">{{ formatDuration(detailLog.duration_ms) }}</span>
          </div>
          <div class="detail-item">
            <span class="detail-label">User-Agent</span>
            <span class="detail-value">{{ detailLog.user_agent }}</span>
          </div>
        </div>
        <Md3Divider />
        <div class="detail-section">
          <div class="detail-section-header">
            <span class="detail-section-title">详细信息 (JSON)</span>
          </div>
          <pre class="detail-json">{{ formatDetailJson(detailLog.detail) }}</pre>
        </div>
        <div class="detail-section">
          <div class="detail-section-header">
            <span class="detail-section-title">完整性校验</span>
            <Md3Button size="sm" @click="verifyIntegrity" :loading="verifying">
              <Md3Icon name="shield-check" size="1em" />验证完整性
            </Md3Button>
          </div>
          <div v-if="integrityResult !== null" class="integrity-result">
            <Md3Tag :type="integrityResult.failed === 0 ? 'success' : 'danger'" size="md">
              {{ integrityResult.failed === 0 ? '校验通过' : `校验失败 (${integrityResult.failed}/${integrityResult.total})` }}
            </Md3Tag>
          </div>
        </div>
      </template>
      <template #footer>
        <Md3Button @click="showDetailDialog = false">关闭</Md3Button>
      </template>
    </Md3Dialog>

    <Md3Dialog v-model:visible="showExportDialog" title="导出日志" width="420px">
      <div class="dialog-form">
        <Md3Select v-model="exportFormat" :options="exportFormatOptions" label="导出格式" />
        <div v-if="exporting" class="export-progress">
          <Md3Tag type="info" size="md">导出中...</Md3Tag>
        </div>
      </div>
      <template #footer>
        <Md3Button @click="showExportDialog = false" :disabled="exporting">取消</Md3Button>
        <Md3Button variant="primary" @click="doExport" :loading="exporting">确认导出</Md3Button>
      </template>
    </Md3Dialog>

    <Md3Dialog v-model:visible="showSaveQueryDialog" title="保存查询" width="420px">
      <div class="dialog-form">
        <Md3Input v-model="saveQueryName" label="查询名称" placeholder="输入名称以保存当前查询条件" />
      </div>
      <template #footer>
        <Md3Button @click="showSaveQueryDialog = false">取消</Md3Button>
        <Md3Button variant="primary" @click="saveQuery">保存</Md3Button>
      </template>
    </Md3Dialog>
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
import { useAuditLogStore } from '@/stores/auditLogStore'

const store = useAuditLogStore()

const activeTab = ref('query')
const pageSize = ref(20)
const showDetailDialog = ref(false)
const showExportDialog = ref(false)
const showSaveQueryDialog = ref(false)
const detailLog = ref<Record<string, any> | null>(null)
const verifying = ref(false)
const integrityResult = ref<{ total: number; passed: number; failed: number; failed_ids: string[] } | null>(null)
const exporting = ref(false)
const exportFormat = ref('xlsx')
const saveQueryName = ref('')
const selectedSavedQuery = ref('')
const statsTimeRange = ref('24h')
const statsGranularity = ref('hour')
const loadingArchives = ref(false)

const filters = ref({
  username: '',
  startTime: '',
  endTime: '',
  actionTypes: [] as (string | number)[],
  modules: [] as (string | number)[],
  status: '',
  keyword: '',
})

const tabItems = computed(() => [
  { label: '日志查询', value: 'query', icon: markRaw({ template: '<Md3Icon name="magnify" size="1em" />', components: { Md3Icon } }) },
  { label: '统计分析', value: 'statistics', icon: markRaw({ template: '<Md3Icon name="chart-bar" size="1em" />', components: { Md3Icon } }) },
  { label: '归档管理', value: 'archives', icon: markRaw({ template: '<Md3Icon name="archive" size="1em" />', components: { Md3Icon } }) },
])

const logColumns = [
  { prop: 'timestamp', label: '时间', width: '170px' },
  { prop: 'username', label: '用户', width: '100px' },
  { prop: 'action_type', label: '操作类型', width: '100px' },
  { prop: 'module', label: '模块', width: '110px' },
  { prop: 'status', label: '状态', width: '80px' },
  { prop: 'request_path', label: '请求路径', width: '200px' },
  { prop: 'duration_ms', label: '耗时(ms)', width: '90px' },
  { prop: 'action_col', label: '操作', width: '80px' },
]

const actionTypeOptions = [
  { label: '创建', value: 'create' },
  { label: '更新', value: 'update' },
  { label: '删除', value: 'delete' },
  { label: '登录', value: 'login' },
  { label: '登出', value: 'logout' },
  { label: '执行', value: 'execute' },
  { label: '导出', value: 'export' },
  { label: '导入', value: 'import' },
  { label: '配置', value: 'config' },
]

const moduleOptions = [
  { label: 'SSH', value: 'ssh' },
  { label: 'Docker', value: 'docker' },
  { label: '监控', value: 'monitor' },
  { label: '进程', value: 'process' },
  { label: '安全', value: 'security' },
  { label: '设置', value: 'settings' },
  { label: '项目', value: 'project' },
  { label: '构建', value: 'build' },
  { label: '定时备份', value: 'cron-backup' },
  { label: '文件管理', value: 'file-manager' },
  { label: '数据库工具', value: 'db-toolkit' },
  { label: 'WebSSH', value: 'webssh' },
  { label: '远程驱动器', value: 'remote-drive' },
  { label: 'Vite部署', value: 'vite-deploy' },
  { label: '审计', value: 'audit' },
]

const statusOptions = [
  { label: '全部', value: '' },
  { label: '成功', value: 'success' },
  { label: '失败', value: 'failure' },
]

const exportFormatOptions = [
  { label: 'XLSX', value: 'xlsx' },
  { label: 'CSV', value: 'csv' },
  { label: 'PDF', value: 'pdf' },
]

const statsTimeRangeOptions = [
  { label: '最近1小时', value: '1h' },
  { label: '最近24小时', value: '24h' },
  { label: '最近7天', value: '7d' },
  { label: '最近30天', value: '30d' },
]

const granularityOptions = [
  { label: '小时', value: 'hour' },
  { label: '天', value: 'day' },
  { label: '周', value: 'week' },
]

const anomalyColumns = [
  { prop: 'timestamp', label: '时间', width: '170px' },
  { prop: 'username', label: '用户', width: '100px' },
  { prop: 'type', label: '异常类型', width: '140px' },
  { prop: 'level', label: '等级', width: '80px' },
  { prop: 'description', label: '描述' },
]

const archiveColumns = [
  { prop: 'filename', label: '文件名', width: '220px' },
  { prop: 'record_count', label: '记录数', width: '100px' },
  { prop: 'size', label: '大小', width: '100px' },
  { prop: 'start_time', label: '起始时间', width: '170px' },
  { prop: 'end_time', label: '结束时间', width: '170px' },
]

const pagedLogs = computed(() => store.logs)
const archives = computed(() => store.archives)
const anomalies = computed(() => store.statistics?.anomalies ?? [])

const trendData = computed(() => (store.statistics?.trend ?? []).map(d => ({ label: d.bucket, count: d.count })))
const trendMax = computed(() => Math.max(...trendData.value.map((d: { count: number }) => d.count), 1))

const moduleDistData = computed(() => (store.statistics?.module_distribution ?? []).map(d => ({ label: d.module, count: d.count })))
const moduleDistMax = computed(() => Math.max(...moduleDistData.value.map((d: { count: number }) => d.count), 1))

const actionDistData = computed(() => (store.statistics?.action_distribution ?? []).map(d => ({ label: d.action_type, count: d.count })))
const actionDistMax = computed(() => Math.max(...actionDistData.value.map((d: { count: number }) => d.count), 1))

const userRankData = computed(() => (store.statistics?.user_ranking ?? []).map(d => ({ label: d.username, count: d.count })))
const userRankMax = computed(() => Math.max(...userRankData.value.map((d: { count: number }) => d.count), 1))

const savedQueryOptions = computed(() =>
  store.savedQueries.map(q => ({ label: q.name, value: q.name }))
)

function formatTimestamp(ts: number | string) {
  if (!ts) return '-'
  return new Date(ts).toLocaleString('zh-CN')
}

function formatDuration(ms: number | undefined) {
  if (ms === undefined || ms === null) return '-'
  return Number(ms).toFixed(1)
}

function formatDetailJson(detail: any) {
  if (!detail) return '-'
  try {
    return JSON.stringify(typeof detail === 'string' ? JSON.parse(detail) : detail, null, 2)
  } catch {
    return String(detail)
  }
}

async function searchLogs() {
  try {
    await store.queryLogs({
      username: filters.value.username || undefined,
      time_start: filters.value.startTime || undefined,
      time_end: filters.value.endTime || undefined,
      action_types: filters.value.actionTypes.length ? filters.value.actionTypes as string[] : undefined,
      modules: filters.value.modules.length ? filters.value.modules as string[] : undefined,
      status: filters.value.status || undefined,
      keyword: filters.value.keyword || undefined,
      page: 1,
      page_size: pageSize.value,
    })
  } catch {
    Md3Message.error('查询失败')
  }
}

function resetFilters() {
  filters.value = {
    username: '',
    startTime: '',
    endTime: '',
    actionTypes: [],
    modules: [],
    status: '',
    keyword: '',
  }
  searchLogs()
}

function openDetail(row: Record<string, any>) {
  detailLog.value = row
  integrityResult.value = null
  showDetailDialog.value = true
}

async function verifyIntegrity() {
  if (!detailLog.value) return
  verifying.value = true
  try {
    const result = await store.verifyIntegrity(detailLog.value.id)
    integrityResult.value = result
  } catch {
    integrityResult.value = { total: 0, passed: 0, failed: 1, failed_ids: [] }
    Md3Message.error('校验失败')
  } finally {
    verifying.value = false
  }
}

async function doExport() {
  exporting.value = true
  try {
    await store.exportLogs({
      username: filters.value.username || undefined,
      time_start: filters.value.startTime || undefined,
      time_end: filters.value.endTime || undefined,
      action_types: filters.value.actionTypes.length ? filters.value.actionTypes as string[] : undefined,
      modules: filters.value.modules.length ? filters.value.modules as string[] : undefined,
      status: filters.value.status || undefined,
      keyword: filters.value.keyword || undefined,
      page: 1,
      page_size: pageSize.value,
    }, exportFormat.value)
    Md3Message.success('导出成功')
    showExportDialog.value = false
  } catch {
    Md3Message.error('导出失败')
  } finally {
    exporting.value = false
  }
}

function saveQuery() {
  if (!saveQueryName.value.trim()) {
    Md3Message.warning('请输入查询名称')
    return
  }
  store.saveQuery(saveQueryName.value.trim(), {
    username: filters.value.username || undefined,
    time_start: filters.value.startTime || undefined,
    time_end: filters.value.endTime || undefined,
    action_types: filters.value.actionTypes.length ? filters.value.actionTypes as string[] : undefined,
    modules: filters.value.modules.length ? filters.value.modules as string[] : undefined,
    status: filters.value.status || undefined,
    keyword: filters.value.keyword || undefined,
    page: 1,
    page_size: pageSize.value,
  })
  Md3Message.success('查询已保存')
  saveQueryName.value = ''
  showSaveQueryDialog.value = false
}

function loadSavedQuery(name: string | number | (string | number)[]) {
  const queryName = String(name)
  const query = store.savedQueries.find(q => q.name === queryName)
  if (query) {
    filters.value = {
      username: query.params.username ?? '',
      startTime: query.params.time_start ?? '',
      endTime: query.params.time_end ?? '',
      actionTypes: query.params.action_types ?? [],
      modules: query.params.modules ?? [],
      status: query.params.status ?? '',
      keyword: query.params.keyword ?? '',
    }
    searchLogs()
  }
}

async function refreshStatistics() {
  try {
    await store.loadStatistics(undefined, statsTimeRange.value, statsGranularity.value)
  } catch {
    Md3Message.error('加载统计数据失败')
  }
}

async function refreshArchives() {
  loadingArchives.value = true
  try {
    await store.loadArchives()
  } catch {
    Md3Message.error('加载归档列表失败')
  } finally {
    loadingArchives.value = false
  }
}

watch(activeTab, (tab) => {
  if (tab === 'query') {
    searchLogs()
  } else if (tab === 'statistics') {
    refreshStatistics()
  } else if (tab === 'archives') {
    refreshArchives()
  }
})

onMounted(() => {
  searchLogs()
})
</script>

<style scoped>
.audit-log-page {
  padding: 0;
}

.header-icon {
  width: 16px;
  height: 16px;
  vertical-align: -3px;
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

.filter-input {
  width: 160px;
}

.filter-select {
  width: 130px;
}

.filter-select-wide {
  width: 200px;
}

.datetime-input {
  width: 200px;
  height: 48px;
  padding: 0 var(--md3-space-md);
  border: 1px solid var(--md3-outline);
  border-radius: var(--md3-shape-xs);
  background: var(--md3-surface);
  color: var(--md3-on-surface);
  font: var(--md3-type-body-medium);
  outline: none;
  transition: border-color var(--md3-motion-duration-short) var(--md3-motion-easing-standard);
}

.datetime-input:focus {
  border-color: var(--md3-primary);
  box-shadow: inset 0 0 0 1px var(--md3-primary);
}

.filter-actions {
  display: flex;
  align-items: center;
  gap: var(--md3-space-xs);
  padding-bottom: 1px;
}

.cell-tags {
  display: flex;
  align-items: center;
  gap: 4px;
}

.mono-text {
  font-family: var(--md3-font-mono);
  font-size: 12px;
}

.stats-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--md3-space-lg);
}

.stats-card {
  display: flex;
  flex-direction: column;
  gap: var(--md3-space-md);
}

.stats-card-title {
  font-weight: 600;
  font-size: 13px;
  color: var(--md3-on-surface-variant);
}

.bar-chart-vertical {
  display: flex;
  align-items: flex-end;
  gap: var(--md3-space-xs);
  height: 180px;
  padding: var(--md3-space-sm) 0;
}

.bar-col {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--md3-space-xs);
  height: 100%;
  justify-content: flex-end;
}

.bar-fill {
  width: 100%;
  max-width: 36px;
  min-height: 2px;
  background: var(--md3-primary);
  border-radius: var(--md3-shape-xs) var(--md3-shape-xs) 0 0;
  transition: height var(--md3-motion-duration-medium) var(--md3-motion-easing-standard);
}

.bar-value {
  font: var(--md3-type-label-small);
  color: var(--md3-on-surface-variant);
}

.bar-label {
  font: var(--md3-type-label-small);
  color: var(--md3-on-surface-variant);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 48px;
  text-align: center;
}

.bar-chart-horizontal {
  display: flex;
  flex-direction: column;
  gap: var(--md3-space-sm);
}

.hbar-row {
  display: flex;
  align-items: center;
  gap: var(--md3-space-sm);
}

.hbar-label {
  font: var(--md3-type-body-small);
  color: var(--md3-on-surface-variant);
  min-width: 60px;
  text-align: right;
  white-space: nowrap;
}

.hbar-track {
  flex: 1;
  height: 16px;
  background: var(--md3-surface-container);
  border-radius: var(--md3-shape-full);
  overflow: hidden;
}

.hbar-fill {
  height: 100%;
  background: var(--md3-primary);
  border-radius: var(--md3-shape-full);
  transition: width var(--md3-motion-duration-medium) var(--md3-motion-easing-standard);
  min-width: 2px;
}

.hbar-fill--secondary {
  background: var(--md3-tertiary);
}

.hbar-value {
  font: var(--md3-type-label-small);
  color: var(--md3-on-surface);
  min-width: 36px;
}

.rank-list {
  display: flex;
  flex-direction: column;
  gap: var(--md3-space-sm);
}

.rank-row {
  display: flex;
  align-items: center;
  gap: var(--md3-space-sm);
}

.rank-index {
  font: var(--md3-type-label-small);
  color: var(--md3-on-surface-variant);
  min-width: 20px;
  text-align: center;
}

.rank-name {
  font: var(--md3-type-body-small);
  color: var(--md3-on-surface);
  min-width: 60px;
}

.rank-track {
  flex: 1;
  height: 14px;
  background: var(--md3-surface-container);
  border-radius: var(--md3-shape-full);
  overflow: hidden;
}

.rank-fill {
  height: 100%;
  background: var(--md3-secondary);
  border-radius: var(--md3-shape-full);
  transition: width var(--md3-motion-duration-medium) var(--md3-motion-easing-standard);
  min-width: 2px;
}

.rank-value {
  font: var(--md3-type-label-small);
  color: var(--md3-on-surface);
  min-width: 36px;
}

.detail-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--md3-space-md);
}

.detail-item {
  display: flex;
  flex-direction: column;
  gap: var(--md3-space-xs);
}

.detail-label {
  font-size: 12px;
  color: var(--md3-on-surface-variant);
}

.detail-value {
  font: var(--md3-type-body-medium);
  color: var(--md3-on-surface);
  display: flex;
  align-items: center;
  gap: 4px;
}

.detail-section {
  margin-top: var(--md3-space-md);
}

.detail-section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--md3-space-sm);
}

.detail-section-title {
  font-weight: 600;
  font-size: 13px;
  color: var(--md3-on-surface-variant);
}

.detail-json {
  margin: 0;
  padding: var(--md3-space-md);
  background: var(--md3-surface-container-low);
  border-radius: var(--md3-shape-xs);
  font-family: var(--md3-font-mono);
  font-size: 12px;
  line-height: 1.6;
  color: var(--md3-on-surface);
  white-space: pre-wrap;
  word-break: break-all;
  max-height: 300px;
  overflow-y: auto;
}

.integrity-result {
  margin-top: var(--md3-space-sm);
}

.dialog-form {
  display: flex;
  flex-direction: column;
  gap: var(--md3-space-md);
}

.export-progress {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--md3-space-md);
}
</style>
