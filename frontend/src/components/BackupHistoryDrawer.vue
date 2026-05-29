<template>
  <Md3Dialog
    :visible="visible"
    :title="`备份历史 - ${policyName}`"
    width="700px"
    @update:visible="emit('update:visible', $event)"
  >
    <Md3Table
      :columns="columns"
      :data="historyList"
      empty-text="暂无备份记录"
      border
      hover
    >
      <template #created_at="{ row }">
        {{ formatDateTime((row as any).created_at) }}
      </template>
      <template #file_size="{ row }">
        {{ formatBytes((row as any).file_size) }}
      </template>
      <template #storage_location="{ row }">
        {{ (row as any).storage_type === 'local' ? '本地' : (row as any).storage_type === 's3' ? 'S3' : (row as any).storage_type }}
      </template>
      <template #status="{ row }">
        <Md3Tag :type="statusTagType((row as any).status)" size="sm">
          {{ statusLabel((row as any).status) }}
        </Md3Tag>
      </template>
      <template #action="{ row }">
        <Md3Button
          v-if="(row as any).status === 'success' && (row as any).storage_type === 'local' && (row as any).file_path"
          variant="text"
          size="sm"
          @click="handleDownload(row)"
        >
          下载
        </Md3Button>
        <span v-else class="action-placeholder">—</span>
      </template>
    </Md3Table>

    <template #footer>
      <Md3Button variant="text" @click="emit('update:visible', false)">关闭</Md3Button>
    </template>
  </Md3Dialog>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { Md3Dialog, Md3Table, Md3Tag } from '@/components/md3'
import Md3Button from '@/components/Md3Button.vue'
import { cronBackupApi } from '@/api'

const props = defineProps<{
  visible: boolean
  policyId: string
  policyName: string
  alias: string
}>()

const emit = defineEmits<{
  'update:visible': [value: boolean]
}>()

const historyList = ref<any[]>([])
const loading = ref(false)

const columns = [
  { prop: 'created_at', label: '备份时间', width: '160px' },
  { prop: 'file_size', label: '文件大小', width: '100px' },
  { prop: 'storage_location', label: '存储位置', width: '100px' },
  { prop: 'status', label: '状态', width: '90px' },
  { prop: 'action', label: '操作', width: '80px' },
]

function statusTagType(status: string): 'success' | 'danger' | 'primary' | 'info' {
  switch (status) {
    case 'success':
      return 'success'
    case 'failed':
      return 'danger'
    case 'running':
      return 'primary'
    default:
      return 'info'
  }
}

function statusLabel(status: string): string {
  switch (status) {
    case 'success':
      return '成功'
    case 'failed':
      return '失败'
    case 'running':
      return '进行中'
    default:
      return status
  }
}

function formatBytes(bytes: number | null | undefined): string {
  if (bytes == null || bytes === 0) return '-'
  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  let i = 0
  let size = bytes
  while (size >= 1024 && i < units.length - 1) {
    size /= 1024
    i++
  }
  return `${size.toFixed(2)} ${units[i]}`
}

function formatDateTime(value: string | null | undefined): string {
  if (!value) return '-'
  const d = new Date(value)
  if (isNaN(d.getTime())) return value
  const pad = (n: number) => n.toString().padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
}

async function fetchHistory() {
  if (!props.alias || !props.policyId) return
  loading.value = true
  try {
    const res = await cronBackupApi.listBackupHistory(props.alias, props.policyId)
    historyList.value = res.items || []
  } catch (err) {
    historyList.value = []
  } finally {
    loading.value = false
  }
}

async function handleDownload(row: any) {
  if (!row.id || !row.file_path) return
  try {
    const blob = await cronBackupApi.downloadBackupFile(row.id, props.alias, row.file_path)
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    const filename = row.file_path.split(/[\\/]/).pop() || 'backup'
    a.download = filename
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    window.URL.revokeObjectURL(url)
  } catch (err) {
    console.error('下载备份文件失败', err)
  }
}

watch(
  () => props.visible,
  (val) => {
    if (val) {
      fetchHistory()
    } else {
      historyList.value = []
    }
  }
)
</script>

<style scoped>
.action-placeholder {
  color: var(--md3-on-surface-variant);
  font-size: 13px;
}
</style>
