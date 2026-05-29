<template>
  <Md3Dialog
    :visible="visible"
    @update:visible="$emit('update:visible', $event)"
    :title="`执行日志 - ${jobName}`"
    width="800px"
  >
    <div class="execution-log-content">
      <Md3Table
        :columns="columns"
        :data="logs"
        border
        stripe
        empty-text="暂无执行日志"
      >
        <template #executed_at="{ row, value }">
          {{ formatDateTime(value as any) }}
        </template>
        <template #status="{ row, value }">
          <Md3Tag :type="value === 'success' ? 'success' : 'danger'" size="sm">
            {{ value === 'success' ? '成功' : '失败' }}
          </Md3Tag>
        </template>
        <template #exit_code="{ row, value }">
          {{ value ?? '-' }}
        </template>
        <template #duration="{ row, value }">
          {{ formatDuration(value as any) }}
        </template>
        <template #output_summary="{ row }">
          <div class="output-summary-cell">
            <span class="output-summary-text">{{ truncateOutput((row as any).output, 60) }}</span>
            <Md3Button variant="text" size="sm" @click="toggleDetail((row as any))">
              {{ expandedRows.has((row as any).id) ? '收起' : '查看详情' }}
            </Md3Button>
          </div>
        </template>
      </Md3Table>

      <div
        v-for="row in expandedLogs"
        :key="row.id"
        class="log-detail-panel"
      >
        <div class="log-detail-header">
          <span>输出详情 — {{ formatDateTime(row.executed_at) }}</span>
          <Md3Button variant="text" size="sm" @click="toggleDetail(row)">收起</Md3Button>
        </div>
        <pre class="log-detail-pre">{{ row.output || '(无输出)' }}</pre>
      </div>
    </div>

    <template #footer>
      <Md3Button variant="text" @click="$emit('update:visible', false)">关闭</Md3Button>
    </template>
  </Md3Dialog>
</template>

<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import { Md3Dialog, Md3Table, Md3Tag } from '@/components/md3'
import Md3Button from '@/components/Md3Button.vue'
import { cronBackupApi } from '@/api'

const props = defineProps<{
  visible: boolean
  jobId: string
  jobName: string
  alias: string
}>()

const emit = defineEmits<{
  'update:visible': [value: boolean]
}>()

const logs = ref<any[]>([])
const loading = ref(false)
const expandedRows = ref<Set<string>>(new Set())

const columns = [
  { prop: 'executed_at', label: '执行时间', width: '160px' },
  { prop: 'status', label: '状态', width: '80px' },
  { prop: 'exit_code', label: '退出码', width: '80px' },
  { prop: 'duration', label: '耗时', width: '90px' },
  { prop: 'output_summary', label: '输出摘要' },
]

const expandedLogs = computed(() => {
  return logs.value.filter((row) => expandedRows.value.has(row.id))
})

function toggleDetail(row: any) {
  if (expandedRows.value.has(row.id)) {
    expandedRows.value.delete(row.id)
  } else {
    expandedRows.value.add(row.id)
  }
}

function formatDateTime(value: string | undefined): string {
  if (!value) return '-'
  const d = new Date(value)
  if (isNaN(d.getTime())) return value
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
}

function formatDuration(value: number | undefined): string {
  if (value == null || isNaN(value)) return '-'
  return `${value.toFixed(2)}s`
}

function truncateOutput(value: string | undefined, maxLength: number): string {
  if (!value) return '(无输出)'
  if (value.length <= maxLength) return value
  return value.slice(0, maxLength) + '...'
}

async function fetchLogs() {
  if (!props.jobId || !props.alias) return
  loading.value = true
  try {
    const res = await cronBackupApi.getCronJobLogs(props.jobId, props.alias, 50)
    logs.value = res.items || []
  } catch (e) {
    logs.value = []
  } finally {
    loading.value = false
  }
}

watch(
  () => props.visible,
  (val) => {
    if (val) {
      expandedRows.value.clear()
      fetchLogs()
    }
  }
)
</script>

<style scoped>
.execution-log-content {
  display: flex;
  flex-direction: column;
  gap: var(--md3-space-md);
  max-height: 60vh;
  overflow-y: auto;
}

.output-summary-cell {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--md3-space-sm);
}

.output-summary-text {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--md3-on-surface-variant);
}

.log-detail-panel {
  border: 1px solid var(--md3-outline-variant);
  border-radius: var(--md3-shape-md);
  overflow: hidden;
}

.log-detail-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--md3-space-sm) var(--md3-space-md);
  background: var(--md3-surface-container);
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--md3-on-surface-variant);
}

.log-detail-pre {
  margin: 0;
  padding: var(--md3-space-md);
  background: var(--md3-surface);
  color: var(--md3-on-surface);
  font-size: 0.8125rem;
  line-height: 1.5;
  white-space: pre-wrap;
  word-break: break-word;
  max-height: 300px;
  overflow-y: auto;
}
</style>
