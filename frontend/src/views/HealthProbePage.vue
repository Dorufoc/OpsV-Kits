<template>
  <div class="health-probe-page">
    <Md3PageHeader title="健康检查">
      <template #subtitle>
        <span>服务拨测与可用性监控</span>
      </template>
      <template #actions>
        <Md3Button size="sm" type="primary" @click="openCreateDialog">
          <Md3Icon name="plus" size="1em" />新增探测
        </Md3Button>
        <Md3Button size="sm" @click="refreshAll" :disabled="store.loading">
          <Md3Icon name="refresh" size="1em" />刷新
        </Md3Button>
      </template>
    </Md3PageHeader>
    <Md3Divider />

    <div v-if="store.loading && !store.targets.length" class="loading-state">
      <Md3Icon name="loading" size="24" class="is-loading icon-lg" />
      <span>加载中...</span>
    </div>

    <template v-else>
      <div class="overview-cards" v-if="store.overview">
        <div class="overview-card">
          <div class="overview-value">{{ store.overview.total_targets }}</div>
          <div class="overview-label">探测目标</div>
        </div>
        <div class="overview-card overview-card--success">
          <div class="overview-value">{{ store.overview.available_count }}</div>
          <div class="overview-label">可用</div>
        </div>
        <div class="overview-card overview-card--danger">
          <div class="overview-value">{{ store.overview.unavailable_count }}</div>
          <div class="overview-label">不可用</div>
        </div>
        <div class="overview-card overview-card--muted">
          <div class="overview-value">{{ store.overview.unknown_count }}</div>
          <div class="overview-label">未知</div>
        </div>
      </div>

      <Md3Empty v-if="!store.targets.length" description="暂无探测目标，点击「新增探测」添加" />

      <div class="target-grid" v-else>
        <div
          v-for="target in store.targets"
          :key="target.id"
          class="target-card"
          :class="{ 'target-card--unavailable': target.current_status === 'unavailable' }"
          @click="openDetail(target)"
        >
          <div class="target-card-header">
            <div class="target-card-name">
              <span class="status-dot" :class="`status-dot--${target.current_status}`"></span>
              {{ target.name }}
            </div>
            <Md3Tag :type="probeTypeTagType(target.probe_type)" size="sm">
              {{ target.probe_type.toUpperCase() }}
            </Md3Tag>
          </div>
          <div class="target-card-target">{{ target.target }}</div>
          <div class="target-card-meta">
            <span v-if="target.last_probe_time">
              {{ formatTime(target.last_probe_time) }}
            </span>
            <span v-else class="text-muted">未探测</span>
            <Md3Switch
              :modelValue="target.enabled"
              @update:modelValue="(v: boolean) => toggleTarget(target.id, v)"
              @click.stop
            />
          </div>
          <div class="target-card-stats" v-if="targetStats[target.id]">
            <div class="stat-item">
              <span class="stat-label">可用率</span>
              <span class="stat-value" :class="getUptimeClass(targetStats[target.id]?.uptime_percent ?? 0)">
                {{ (targetStats[target.id]?.uptime_percent ?? 0).toFixed(1) }}%
              </span>
            </div>
            <div class="stat-item">
              <span class="stat-label">响应</span>
              <span class="stat-value">
                {{ targetStats[target.id]?.avg_response_time_ms != null ? targetStats[target.id]!.avg_response_time_ms!.toFixed(0) + 'ms' : '-' }}
              </span>
            </div>
          </div>
          <div class="target-card-actions" @click.stop>
            <Md3Button size="sm" @click="handleProbeNow(target.id)" :loading="store.probing">
              <Md3Icon name="play" size="1em" />探测
            </Md3Button>
            <Md3Button size="sm" @click="openEditDialog(target)">
              <Md3Icon name="edit" size="1em" />编辑
            </Md3Button>
            <Md3Button size="sm" type="danger" @click="handleDelete(target.id, target.name)">
              <Md3Icon name="delete" size="1em" />
            </Md3Button>
          </div>
        </div>
      </div>
    </template>

    <Md3Dialog v-model:visible="dialogVisible" :title="dialogMode === 'create' ? '新增探测目标' : '编辑探测目标'" width="560px">
      <div class="form-grid">
        <Md3Input v-model="formData.name" label="目标名称" placeholder="如：生产环境 API" />
        <Md3Select
          v-model="formData.probe_type"
          :options="probeTypeOptions"
          label="探测类型"
          placeholder="选择探测类型"
        />
        <Md3Input v-model="formData.target" label="目标地址" :placeholder="targetPlaceholder" />
        <Md3Input v-model.number="formData.interval_seconds" label="探测频率（秒）" type="number" :min="10" />
        <Md3Input v-model.number="formData.timeout_seconds" label="超时时间（秒）" type="number" :min="1" />
        <Md3Input v-model.number="formData.failure_threshold" label="连续失败阈值" type="number" :min="1" />
        <Md3Input v-model.number="formData.recovery_threshold" label="连续成功恢复阈值" type="number" :min="1" />
      </div>

      <template v-if="formData.probe_type === 'http'">
        <Md3Divider />
        <div class="form-section-title">HTTP 配置</div>
        <div class="form-grid">
          <Md3Input v-model="httpForm.method" label="HTTP 方法" placeholder="GET" />
          <Md3Input v-model="httpForm.status_codes_str" label="期望状态码" placeholder="200,201,204" />
          <Md3Input v-model="httpForm.content_match" label="内容匹配正则" placeholder="可选，如 &quot;status&quot;:&quot;ok&quot;" />
          <div class="form-row">
            <label class="form-label">跟随重定向</label>
            <Md3Switch v-model="httpForm.follow_redirects" />
          </div>
        </div>
      </template>

      <template #footer>
        <Md3Button size="sm" @click="dialogVisible = false">取消</Md3Button>
        <Md3Button size="sm" type="primary" @click="handleSubmit" :loading="submitting">
          {{ dialogMode === 'create' ? '创建' : '保存' }}
        </Md3Button>
      </template>
    </Md3Dialog>

    <Md3Dialog v-model:visible="detailVisible" :title="detailTarget?.name ?? '探测详情'" width="900px" :fullscreen="true">
      <template v-if="detailTarget">
        <div class="detail-header">
          <div class="detail-info">
            <span class="status-dot" :class="`status-dot--${detailTarget.current_status}`"></span>
            <Md3Tag :type="probeTypeTagType(detailTarget.probe_type)" size="sm">{{ detailTarget.probe_type.toUpperCase() }}</Md3Tag>
            <span class="detail-target-addr">{{ detailTarget.target }}</span>
            <Md3Tag :type="detailTarget.enabled ? 'success' : 'danger'" size="sm">{{ detailTarget.enabled ? '已启用' : '已禁用' }}</Md3Tag>
          </div>
          <Md3Button size="sm" type="primary" @click="handleProbeNow(detailTarget.id)" :loading="store.probing">
            <Md3Icon name="play" size="1em" />立即探测
          </Md3Button>
        </div>

        <div class="detail-stats" v-if="detailStats">
          <div class="detail-stat-card">
            <div class="detail-stat-value" :class="getUptimeClass(detailStats.uptime_percent)">
              {{ detailStats.uptime_percent.toFixed(1) }}%
            </div>
            <div class="detail-stat-label">可用率</div>
          </div>
          <div class="detail-stat-card">
            <div class="detail-stat-value">{{ detailStats.avg_response_time_ms?.toFixed(0) ?? '-' }}ms</div>
            <div class="detail-stat-label">平均响应</div>
          </div>
          <div class="detail-stat-card">
            <div class="detail-stat-value">{{ detailStats.max_response_time_ms?.toFixed(0) ?? '-' }}ms</div>
            <div class="detail-stat-label">最大响应</div>
          </div>
          <div class="detail-stat-card">
            <div class="detail-stat-value">{{ detailStats.min_response_time_ms?.toFixed(0) ?? '-' }}ms</div>
            <div class="detail-stat-label">最小响应</div>
          </div>
          <div class="detail-stat-card">
            <div class="detail-stat-value">{{ detailStats.total_probes }}</div>
            <div class="detail-stat-label">总探测</div>
          </div>
          <div class="detail-stat-card">
            <div class="detail-stat-value text-success">{{ detailStats.success_count }}</div>
            <div class="detail-stat-label">成功</div>
          </div>
          <div class="detail-stat-card">
            <div class="detail-stat-value text-danger">{{ detailStats.failure_count }}</div>
            <div class="detail-stat-label">失败</div>
          </div>
        </div>

        <div class="detail-time-range">
          <label class="form-label">统计范围</label>
          <Md3Select v-model="statsHours" :options="statsHoursOptions" @update:model-value="loadDetailStats" />
        </div>

        <Md3Divider />

        <div class="detail-logs">
          <div class="detail-logs-header">
            <span class="detail-logs-title">探测日志</span>
            <Md3Select v-model="logFilter" :options="logFilterOptions" @update:model-value="loadDetailLogs" style="width: 120px" />
          </div>
          <Md3Table
            :columns="logColumns"
            :data="detailLogs"
            :pagination="true"
            :pageSize="15"
            :stripe="true"
            :hover="true"
            :border="true"
            emptyText="暂无探测日志"
          >
            <template #timestamp="{ row }">
              {{ formatTime(row.timestamp) }}
            </template>
            <template #success="{ row }">
              <Md3Tag :type="row.success ? 'success' : 'danger'" size="sm">
                {{ row.success ? '成功' : '失败' }}
              </Md3Tag>
            </template>
            <template #response_time_ms="{ row }">
              {{ row.response_time_ms != null ? row.response_time_ms.toFixed(1) + 'ms' : '-' }}
            </template>
            <template #status_code="{ row }">
              {{ row.status_code ?? '-' }}
            </template>
            <template #error_message="{ row }">
              <span v-if="row.error_message" class="text-danger" :title="row.error_message">
                {{ row.error_message.length > 40 ? row.error_message.slice(0, 40) + '...' : row.error_message }}
              </span>
              <span v-else>-</span>
            </template>
            <template #content_matched="{ row }">
              <span v-if="row.content_matched === null">-</span>
              <Md3Tag v-else :type="row.content_matched ? 'success' : 'warning'" size="sm">
                {{ row.content_matched ? '匹配' : '不匹配' }}
              </Md3Tag>
            </template>
          </Md3Table>
        </div>
      </template>
    </Md3Dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { useHealthProbeStore } from '@/stores/healthProbeStore'
import type { ProbeTarget, ProbeTargetCreate, ProbeStatistics, ProbeResult } from '@/api'
import { Md3Icon } from '@/components/md3'

const store = useHealthProbeStore()

const targetStats = ref<Record<string, ProbeStatistics | null>>({})
const dialogVisible = ref(false)
const dialogMode = ref<'create' | 'edit'>('create')
const editingId = ref('')
const submitting = ref(false)
const detailVisible = ref(false)
const detailTarget = ref<ProbeTarget | null>(null)
const detailStats = ref<ProbeStatistics | null>(null)
const detailLogs = ref<ProbeResult[]>([])
const statsHours = ref(24)
const logFilter = ref<string>('all')

const formData = reactive({
  name: '',
  probe_type: 'http' as 'http' | 'tcp' | 'icmp',
  target: '',
  interval_seconds: 60,
  timeout_seconds: 10,
  failure_threshold: 3,
  recovery_threshold: 2,
})

const httpForm = reactive({
  method: 'GET',
  status_codes_str: '200',
  content_match: '',
  follow_redirects: true,
})

const probeTypeOptions = [
  { label: 'HTTP', value: 'http' },
  { label: 'TCP', value: 'tcp' },
  { label: 'ICMP', value: 'icmp' },
]

const statsHoursOptions = [
  { label: '最近 1 小时', value: 1 },
  { label: '最近 6 小时', value: 6 },
  { label: '最近 24 小时', value: 24 },
  { label: '最近 7 天', value: 168 },
  { label: '最近 30 天', value: 720 },
]

const logFilterOptions = [
  { label: '全部', value: 'all' },
  { label: '成功', value: 'success' },
  { label: '失败', value: 'failure' },
]

const logColumns = [
  { prop: 'timestamp', label: '时间', width: '170px' },
  { prop: 'success', label: '状态', width: '70px' },
  { prop: 'response_time_ms', label: '响应时间', width: '100px' },
  { prop: 'status_code', label: '状态码', width: '80px' },
  { prop: 'content_matched', label: '内容匹配', width: '90px' },
  { prop: 'error_message', label: '错误信息' },
]

const targetPlaceholder = computed(() => {
  switch (formData.probe_type) {
    case 'http': return 'https://example.com/health'
    case 'tcp': return 'db.example.com:3306'
    case 'icmp': return '10.0.0.1'
  }
})

function probeTypeTagType(type: string) {
  switch (type) {
    case 'http': return 'primary'
    case 'tcp': return 'warning'
    case 'icmp': return 'info'
    default: return 'info'
  }
}

function getUptimeClass(percent: number) {
  if (percent >= 99) return 'text-success'
  if (percent >= 95) return 'text-warning'
  return 'text-danger'
}

function formatTime(ts: string | undefined) {
  if (!ts) return '-'
  const d = new Date(ts)
  const pad = (n: number) => n.toString().padStart(2, '0')
  return `${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
}

async function refreshAll() {
  await store.fetchOverview()
  for (const t of store.targets) {
    try {
      targetStats.value[t.id] = await store.fetchStatistics(t.id, 24)
    } catch {
      targetStats.value[t.id] = null
    }
  }
}

function openCreateDialog() {
  dialogMode.value = 'create'
  formData.name = ''
  formData.probe_type = 'http'
  formData.target = ''
  formData.interval_seconds = 60
  formData.timeout_seconds = 10
  formData.failure_threshold = 3
  formData.recovery_threshold = 2
  httpForm.method = 'GET'
  httpForm.status_codes_str = '200'
  httpForm.content_match = ''
  httpForm.follow_redirects = true
  dialogVisible.value = true
}

function openEditDialog(target: ProbeTarget) {
  dialogMode.value = 'edit'
  editingId.value = target.id
  formData.name = target.name
  formData.probe_type = target.probe_type
  formData.target = target.target
  formData.interval_seconds = target.interval_seconds
  formData.timeout_seconds = target.timeout_seconds
  formData.failure_threshold = target.failure_threshold
  formData.recovery_threshold = target.recovery_threshold
  if (target.http_config) {
    httpForm.method = target.http_config.method || 'GET'
    httpForm.status_codes_str = (target.http_config.expected_status_codes || [200]).join(',')
    httpForm.content_match = target.http_config.content_match || ''
    httpForm.follow_redirects = target.http_config.follow_redirects !== false
  } else {
    httpForm.method = 'GET'
    httpForm.status_codes_str = '200'
    httpForm.content_match = ''
    httpForm.follow_redirects = true
  }
  dialogVisible.value = true
}

async function handleSubmit() {
  if (!formData.name || !formData.target) return
  submitting.value = true
  try {
    const payload: ProbeTargetCreate = {
      name: formData.name,
      probe_type: formData.probe_type,
      target: formData.target,
      interval_seconds: formData.interval_seconds,
      timeout_seconds: formData.timeout_seconds,
      failure_threshold: formData.failure_threshold,
      recovery_threshold: formData.recovery_threshold,
    }
    if (formData.probe_type === 'http') {
      payload.http_config = {
        method: httpForm.method || 'GET',
        expected_status_codes: httpForm.status_codes_str.split(',').map(s => parseInt(s.trim())).filter(n => !isNaN(n)),
        content_match: httpForm.content_match || undefined,
        follow_redirects: httpForm.follow_redirects,
      }
    }
    if (dialogMode.value === 'create') {
      await store.createTarget(payload)
    } else {
      await store.updateTarget(editingId.value, payload)
    }
    dialogVisible.value = false
    await refreshAll()
  } finally {
    submitting.value = false
  }
}

async function toggleTarget(id: string, enabled: boolean) {
  await store.updateTarget(id, { enabled })
  await refreshAll()
}

async function handleProbeNow(id: string) {
  const result = await store.probeNow(id)
  if (result) {
    try {
      targetStats.value[id] = await store.fetchStatistics(id, 24)
    } catch { /* ignore */ }
    if (detailVisible.value && detailTarget.value?.id === id) {
      await loadDetailStats(statsHours.value)
      await loadDetailLogs()
    }
  }
}

async function handleDelete(id: string, name: string) {
  if (!confirm(`确定删除探测目标「${name}」？此操作将同时删除所有探测日志。`)) return
  await store.deleteTarget(id)
  delete targetStats.value[id]
  await refreshAll()
}

async function openDetail(target: ProbeTarget) {
  detailTarget.value = target
  detailVisible.value = true
  await loadDetailStats(statsHours.value)
  await loadDetailLogs()
}

async function loadDetailStats(hours: number) {
  if (!detailTarget.value) return
  try {
    detailStats.value = await store.fetchStatistics(detailTarget.value.id, hours)
  } catch {
    detailStats.value = null
  }
}

async function loadDetailLogs() {
  if (!detailTarget.value) return
  try {
    const successFilter = logFilter.value === 'success' ? true : logFilter.value === 'failure' ? false : undefined
    const result = await store.fetchLogs(detailTarget.value.id, { limit: 200, success: successFilter })
    detailLogs.value = result.items
  } catch {
    detailLogs.value = []
  }
}

onMounted(() => {
  refreshAll()
})
</script>

<style scoped>
.health-probe-page {
  padding: var(--md3-space-lg);
}

.loading-state {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--md3-space-sm);
  padding: var(--md3-space-3xl);
  color: var(--md3-on-surface-variant);
}

.overview-cards {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--md3-space-md);
  margin-bottom: var(--md3-space-lg);
}

.overview-card {
  background: var(--md3-surface-container);
  border-radius: var(--md3-shape-lg);
  padding: var(--md3-space-lg);
  text-align: center;
  border: 1px solid var(--md3-outline-variant);
}

.overview-card--success .overview-value { color: var(--md3-success); }
.overview-card--danger .overview-value { color: var(--md3-error); }
.overview-card--muted .overview-value { color: var(--md3-on-surface-variant); }

.overview-value {
  font: var(--md3-type-display-small);
  color: var(--md3-on-surface);
  margin-bottom: var(--md3-space-xs);
}

.overview-label {
  font: var(--md3-type-label-medium);
  color: var(--md3-on-surface-variant);
}

.target-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: var(--md3-space-md);
}

.target-card {
  background: var(--md3-surface-container);
  border-radius: var(--md3-shape-lg);
  padding: var(--md3-space-lg);
  border: 1px solid var(--md3-outline-variant);
  cursor: pointer;
  transition: border-color var(--md3-motion-duration-short) var(--md3-motion-easing-standard);
}

.target-card:hover {
  border-color: var(--md3-primary);
}

.target-card--unavailable {
  border-left: 3px solid var(--md3-error);
}

.target-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--md3-space-sm);
}

.target-card-name {
  display: flex;
  align-items: center;
  gap: var(--md3-space-sm);
  font: var(--md3-type-title-medium);
  color: var(--md3-on-surface);
}

.target-card-target {
  font: var(--md3-type-body-small);
  color: var(--md3-on-surface-variant);
  margin-bottom: var(--md3-space-sm);
  word-break: break-all;
}

.target-card-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font: var(--md3-type-body-small);
  color: var(--md3-on-surface-variant);
  margin-bottom: var(--md3-space-sm);
}

.target-card-stats {
  display: flex;
  gap: var(--md3-space-lg);
  margin-bottom: var(--md3-space-sm);
  padding: var(--md3-space-sm) 0;
  border-top: 1px solid var(--md3-outline-variant);
}

.stat-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.stat-label {
  font: var(--md3-type-label-small);
  color: var(--md3-on-surface-variant);
}

.stat-value {
  font: var(--md3-type-title-small);
  color: var(--md3-on-surface);
}

.target-card-actions {
  display: flex;
  gap: var(--md3-space-xs);
  padding-top: var(--md3-space-sm);
  border-top: 1px solid var(--md3-outline-variant);
}

.status-dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.status-dot--available { background: var(--md3-success); }
.status-dot--unavailable { background: var(--md3-error); }
.status-dot--unknown { background: var(--md3-outline); }

.text-success { color: var(--md3-success); }
.text-warning { color: var(--md3-warning); }
.text-danger { color: var(--md3-error); }
.text-muted { color: var(--md3-on-surface-variant); }

.form-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--md3-space-md);
}

.form-section-title {
  font: var(--md3-type-title-small);
  color: var(--md3-on-surface);
  margin: var(--md3-space-sm) 0;
}

.form-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--md3-space-sm) 0;
}

.form-label {
  font: var(--md3-type-label-medium);
  color: var(--md3-on-surface-variant);
}

.detail-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--md3-space-md);
}

.detail-info {
  display: flex;
  align-items: center;
  gap: var(--md3-space-sm);
}

.detail-target-addr {
  font: var(--md3-type-body-medium);
  color: var(--md3-on-surface-variant);
}

.detail-stats {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: var(--md3-space-sm);
  margin-bottom: var(--md3-space-md);
}

.detail-stat-card {
  background: var(--md3-surface-container-high);
  border-radius: var(--md3-shape-md);
  padding: var(--md3-space-sm);
  text-align: center;
}

.detail-stat-value {
  font: var(--md3-type-headline-small);
  color: var(--md3-on-surface);
}

.detail-stat-label {
  font: var(--md3-type-label-small);
  color: var(--md3-on-surface-variant);
}

.detail-time-range {
  display: flex;
  align-items: center;
  gap: var(--md3-space-sm);
  margin-bottom: var(--md3-space-md);
}

.detail-logs-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--md3-space-sm);
}

.detail-logs-title {
  font: var(--md3-type-title-small);
  color: var(--md3-on-surface);
}

.detail-logs {
  margin-top: var(--md3-space-md);
}
</style>
