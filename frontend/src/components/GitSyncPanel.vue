<template>
  <div class="git-sync-panel">
    <div class="panel-actions">
      <Md3Button size="sm" @click="showConfigDialog = true">创建同步配置</Md3Button>
      <Md3Button size="sm" @click="gitStore.fetchSyncConfigs()">刷新</Md3Button>
    </div>

    <Md3Table
      :columns="syncColumns"
      :data="gitStore.syncConfigs"
      stripe
      hover
      empty-text="暂无同步配置"
    >
      <template #mode="{ row }">
        <Md3Tag :type="modeTagType(row.mode)" size="sm">{{ modeLabel(row.mode) }}</Md3Tag>
      </template>
      <template #status="{ row }">
        <Md3Tag :type="row.status === 'active' ? 'success' : 'warning'" size="sm">
          {{ row.status === 'active' ? '运行中' : '已暂停' }}
        </Md3Tag>
      </template>
      <template #pending_updates="{ row }">
        <span v-if="row.pending_updates > 0" class="pending-badge">{{ row.pending_updates }}</span>
        <span v-else>0</span>
      </template>
      <template #actions="{ row }">
        <div class="row-actions">
          <Md3Button size="sm" @click="openEditDialog(row)">编辑</Md3Button>
          <Md3Button size="sm" variant="primary" @click="handleManualPull(row.id)">拉取</Md3Button>
          <Md3Button size="sm" variant="danger" @click="handleDeleteConfig(row.id)">删除</Md3Button>
        </div>
      </template>
    </Md3Table>

    <Md3Card v-if="selectedConfigId" class="status-card">
      <template #header>
        <span class="card-title">同步状态</span>
      </template>
      <div class="status-grid">
        <div class="status-item">
          <span class="status-label">上次同步</span>
          <span class="status-value">{{ gitStore.syncStatus.last_sync_time || '-' }}</span>
        </div>
        <div class="status-item">
          <span class="status-label">下次检查</span>
          <span class="status-value">{{ gitStore.syncStatus.next_check_time || '-' }}</span>
        </div>
        <div class="status-item">
          <span class="status-label">差异提交数</span>
          <span class="status-value">{{ gitStore.syncStatus.diff_commits }}</span>
        </div>
      </div>
    </Md3Card>

    <Md3Card v-if="gitStore.syncLogs.length > 0" class="log-card">
      <template #header>
        <span class="card-title">同步日志</span>
      </template>
      <Md3Table
        :columns="logColumns"
        :data="gitStore.syncLogs"
        stripe
        hover
        empty-text="暂无日志"
        :pagination="true"
        :page-size="10"
      >
        <template #result="{ row }">
          <Md3Tag :type="row.result === 'success' ? 'success' : 'danger'" size="sm">
            {{ row.result === 'success' ? '成功' : '失败' }}
          </Md3Tag>
        </template>
      </Md3Table>
    </Md3Card>

    <Md3Dialog v-model:visible="showConfigDialog" :title="configEditId ? '编辑同步配置' : '创建同步配置'" width="480px">
      <div class="dialog-form">
        <Md3Input v-model="configForm.repo_path" label="仓库路径" placeholder="/path/to/repo" />
        <Md3Select v-model="configForm.interval" :options="intervalOptions" label="同步间隔" placeholder="选择间隔" />
        <Md3Select v-model="configForm.mode" :options="modeOptions" label="同步模式" placeholder="选择模式" />
        <div class="switch-row">
          <span class="switch-label">自动部署</span>
          <Md3Switch v-model="configForm.auto_deploy" />
        </div>
      </div>
      <template #footer>
        <Md3Button @click="showConfigDialog = false">取消</Md3Button>
        <Md3Button variant="primary" @click="handleSaveConfig">保存</Md3Button>
      </template>
    </Md3Dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useGitIntegrationStore, type SyncConfig } from '@/stores/gitIntegrationStore'
import {
  Md3Card,
  Md3Dialog,
  Md3Input,
  Md3Select,
  Md3Switch,
  Md3Table,
  Md3Tag,
} from '@/components/md3'
import Md3Button from '@/components/Md3Button.vue'
import { Md3Message } from '@/components/md3/Md3Message'
import { Md3Confirm } from '@/components/md3/Md3Confirm'

const gitStore = useGitIntegrationStore()

const showConfigDialog = ref(false)
const configEditId = ref('')
const selectedConfigId = ref('')

const configForm = ref({
  repo_path: '',
  interval: 300,
  mode: 'auto_pull',
  auto_deploy: false,
})

const syncColumns = [
  { prop: 'repo_path', label: '仓库' },
  { prop: 'interval', label: '间隔(秒)' },
  { prop: 'mode', label: '模式' },
  { prop: 'status', label: '状态' },
  { prop: 'pending_updates', label: '待更新' },
  { prop: 'actions', label: '操作' },
]

const logColumns = [
  { prop: 'time', label: '时间' },
  { prop: 'action', label: '操作' },
  { prop: 'result', label: '结果' },
  { prop: 'summary', label: '变更摘要' },
]

const intervalOptions = [
  { label: '5 分钟', value: 300 },
  { label: '15 分钟', value: 900 },
  { label: '30 分钟', value: 1800 },
  { label: '1 小时', value: 3600 },
]

const modeOptions = [
  { label: '自动拉取', value: 'auto_pull' },
  { label: '仅通知', value: 'notify_only' },
  { label: '手动', value: 'manual' },
]

function modeTagType(mode: string) {
  if (mode === 'auto_pull') return 'success'
  if (mode === 'notify_only') return 'warning'
  return 'info'
}

function modeLabel(mode: string) {
  if (mode === 'auto_pull') return '自动拉取'
  if (mode === 'notify_only') return '仅通知'
  return '手动'
}

function openEditDialog(config: SyncConfig) {
  configEditId.value = config.id
  configForm.value = {
    repo_path: config.repo_path,
    interval: config.interval,
    mode: config.mode,
    auto_deploy: config.auto_deploy,
  }
  showConfigDialog.value = true
}

async function handleSaveConfig() {
  try {
    if (configEditId.value) {
      await gitStore.updateSyncConfig(configEditId.value, configForm.value)
      Md3Message.success('配置已更新')
    } else {
      await gitStore.createSyncConfig(configForm.value)
      Md3Message.success('配置创建成功')
    }
    showConfigDialog.value = false
    configForm.value = { repo_path: '', interval: 300, mode: 'auto_pull', auto_deploy: false }
    gitStore.fetchSyncConfigs()
  } catch {
    Md3Message.error('保存失败')
  }
}

async function handleManualPull(configId: string) {
  try {
    await gitStore.manualPull(configId)
    Md3Message.success('拉取成功')
    selectedConfigId.value = configId
    gitStore.fetchSyncStatus(configId)
    gitStore.fetchSyncLogs(configId)
  } catch {
    Md3Message.error('拉取失败')
  }
}

async function handleDeleteConfig(id: string) {
  const confirmed = await Md3Confirm.show({ title: '确认删除', message: '确认删除该同步配置？' })
  if (!confirmed) return
  try {
    await gitStore.deleteSyncConfig(id)
    Md3Message.success('已删除')
    if (selectedConfigId.value === id) {
      selectedConfigId.value = ''
    }
    gitStore.fetchSyncConfigs()
  } catch {
    Md3Message.error('删除失败')
  }
}

onMounted(() => {
  gitStore.fetchSyncConfigs()
})
</script>

<style scoped>
.panel-actions {
  display: flex;
  gap: var(--md3-space-sm);
  margin-bottom: var(--md3-space-md);
}

.row-actions {
  display: flex;
  gap: var(--md3-space-xs);
}

.pending-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 20px;
  height: 20px;
  padding: 0 6px;
  border-radius: var(--md3-shape-full);
  background: var(--md3-error);
  color: var(--md3-on-error);
  font: var(--md3-type-label-small);
}

.status-card {
  margin-top: var(--md3-space-lg);
}

.card-title {
  font: var(--md3-type-title-medium);
  color: var(--md3-on-surface);
}

.status-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--md3-space-lg);
}

.status-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.status-label {
  font: var(--md3-type-body-small);
  color: var(--md3-outline);
}

.status-value {
  font: var(--md3-type-body-medium);
  color: var(--md3-on-surface);
}

.log-card {
  margin-top: var(--md3-space-lg);
}

.dialog-form {
  display: flex;
  flex-direction: column;
  gap: var(--md3-space-md);
}

.switch-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.switch-label {
  font: var(--md3-type-body-medium);
  color: var(--md3-on-surface-variant);
}
</style>
