<template>
  <div class="automation-page">
    <Md3PageHeader title="任务调度与自动化">
      <template #subtitle>
        <span>工作流编排、定时任务调度与事件驱动自动化</span>
      </template>
    </Md3PageHeader>
    <Md3Divider />

    <div class="metrics-row">
      <div class="metric-card" v-for="metric in metrics" :key="metric.label">
        <div class="metric-value" :style="{ color: metric.color }">{{ metric.value }}</div>
        <div class="metric-label">{{ metric.label }}</div>
      </div>
    </div>

    <Md3Tabs v-model="activeTab" :tabs="tabItems" class="page-tabs" />

    <div class="tab-content">
      <template v-if="activeTab === 'workflow'">
        <Md3Card :shadow="false" class="section-card">
          <template #header>
            <span><Md3Icon name="source-branch" class="header-icon" /> 工作流列表</span>
            <div class="card-header-right">
              <Md3Input v-model="workflowSearch" placeholder="搜索工作流" class="search-input" type="search">
                <template #prefix><Md3Icon name="search" size="16" /></template>
              </Md3Input>
              <Md3Button size="sm" variant="primary" @click="showTemplateGallery = true">
                <Md3Icon name="plus" size="1em" />从模板创建
              </Md3Button>
              <Md3Button size="sm" variant="primary" @click="createNewWorkflow">
                <Md3Icon name="plus" size="1em" />新建工作流
              </Md3Button>
            </div>
          </template>
          <Md3Table :columns="workflowColumns" :data="filteredWorkflows" stripe max-height="480" empty-text="暂无工作流">
            <template #status="{ row }">
              <Md3Tag :type="(row as any).status === 'active' ? 'success' : (row as any).status === 'draft' ? 'warning' : 'info'" size="sm">
                {{ (row as any).status === 'active' ? '活跃' : (row as any).status === 'draft' ? '草稿' : '归档' }}
              </Md3Tag>
            </template>
            <template #version="{ row }">v{{ (row as any).version }}</template>
            <template #nodes_count="{ row }">{{ (row as any).nodes?.length || 0 }}</template>
            <template #action="{ row }">
              <div class="action-buttons">
                <Md3Button size="sm" variant="text" @click="editWorkflow((row as any))">编辑</Md3Button>
                <Md3Button size="sm" variant="text" @click="executeWorkflow((row as any))">执行</Md3Button>
                <Md3Button size="sm" variant="danger" @click="deleteWorkflow((row as any))">删除</Md3Button>
              </div>
            </template>
          </Md3Table>
        </Md3Card>
      </template>

      <template v-if="activeTab === 'scheduler'">
        <Md3Card :shadow="false" class="section-card">
          <template #header>
            <span><Md3Icon name="schedule" class="header-icon" /> 定时任务</span>
            <div class="card-header-right">
              <Md3Button size="sm" variant="primary" @click="showTaskDialog = true">
                <Md3Icon name="plus" size="1em" />新建任务
              </Md3Button>
            </div>
          </template>
          <Md3Table :columns="taskColumns" :data="schedulerStore.tasks" stripe max-height="480" empty-text="暂无定时任务">
            <template #status="{ row }">
              <Md3Switch :model-value="(row as any).status === 'enabled'" @update:model-value="toggleTask((row as any), $event)" />
            </template>
            <template #priority="{ row }">
              <Md3Tag :type="(row as any).priority === 'high' ? 'danger' : (row as any).priority === 'medium' ? 'warning' : 'info'" size="sm">
                {{ (row as any).priority === 'high' ? '高' : (row as any).priority === 'medium' ? '中' : '低' }}
              </Md3Tag>
            </template>
            <template #last_run="{ row }">
              <span :class="{ 'text-danger': (row as any).last_run_status === 'failed' }">
                {{ (row as any).last_run_at || '-' }}
              </span>
            </template>
            <template #action="{ row }">
              <div class="action-buttons">
                <Md3Button size="sm" variant="text" @click="runTaskNow((row as any))">立即执行</Md3Button>
                <Md3Button size="sm" variant="text" @click="editTask((row as any))">编辑</Md3Button>
                <Md3Button size="sm" variant="danger" @click="deleteTask((row as any))">删除</Md3Button>
              </div>
            </template>
          </Md3Table>
        </Md3Card>
      </template>

      <template v-if="activeTab === 'event'">
        <Md3Card :shadow="false" class="section-card">
          <template #header>
            <span><Md3Icon name="lightning-bolt" class="header-icon" /> 事件源</span>
            <div class="card-header-right">
              <Md3Button size="sm" variant="primary" @click="showSourceDialog = true">
                <Md3Icon name="plus" size="1em" />新建事件源
              </Md3Button>
            </div>
          </template>
          <Md3Table :columns="sourceColumns" :data="eventTriggerStore.sources" stripe max-height="300" empty-text="暂无事件源">
            <template #source_type="{ row }">
              <Md3Tag :type="getSourceTypeTag((row as any).source_type)" size="sm">
                {{ getSourceTypeLabel((row as any).source_type) }}
              </Md3Tag>
            </template>
            <template #webhook_url="{ row }">
              <code v-if="(row as any).webhook_url" class="webhook-url" @click="copyWebhookUrl((row as any).webhook_url)">{{ (row as any).webhook_url }}</code>
              <span v-else>-</span>
            </template>
            <template #status="{ row }">
              <Md3Switch :model-value="(row as any).status === 'enabled'" @update:model-value="toggleSource((row as any), $event)" />
            </template>
            <template #action="{ row }">
              <div class="action-buttons">
                <Md3Button size="sm" variant="text" @click="editSource((row as any))">编辑</Md3Button>
                <Md3Button size="sm" variant="text" @click="showRoutes((row as any))">路由</Md3Button>
                <Md3Button size="sm" variant="danger" @click="deleteSource((row as any))">删除</Md3Button>
              </div>
            </template>
          </Md3Table>
        </Md3Card>

        <Md3Card :shadow="false" class="section-card" style="margin-top: 16px">
          <template #header>
            <span><Md3Icon name="text-box-outline" class="header-icon" /> 事件日志</span>
            <div class="card-header-right">
              <Md3Select v-model="logFilter" :options="logFilterOptions" placeholder="筛选状态" style="width: 140px" @update:model-value="fetchEventLogs" />
            </div>
          </template>
          <Md3Table :columns="logColumns" :data="eventTriggerStore.eventLogs" stripe max-height="300" empty-text="暂无事件日志">
            <template #status="{ row }">
              <Md3Tag :type="getEventStatusTag((row as any).status)" size="sm">{{ (row as any).status }}</Md3Tag>
            </template>
            <template #action="{ row }">
              <Md3Button size="sm" variant="text" @click="replayEvent((row as any))">回放</Md3Button>
            </template>
          </Md3Table>
        </Md3Card>
      </template>
    </div>

    <WorkflowTemplateGallery v-if="showTemplateGallery" :templates="workflowStore.templates" @select="createFromTemplate" @close="showTemplateGallery = false" />

    <Md3Dialog v-model:visible="showTaskDialog" :title="editingTask ? '编辑定时任务' : '新建定时任务'" width="640px">
      <div class="dialog-form">
        <Md3Input v-model="taskForm.name" label="任务名称" />
        <Md3Input v-model="taskForm.cron_expression" label="Cron 表达式" />
        <Md3Select v-model="taskForm.priority" :options="priorityOptions" label="优先级" />
        <Md3Input v-model="taskForm.command" label="执行命令" />
        <Md3Input v-model.number="taskForm.timeout_seconds" label="超时时间（秒）" type="number" />
        <Md3Input v-model.number="taskForm.max_concurrent" label="最大并发数" type="number" />
        <div class="form-row">
          <Md3Input v-model.number="taskForm.retry_policy.max_retries" label="最大重试次数" type="number" />
          <Md3Select v-model="taskForm.retry_policy.strategy" :options="retryStrategyOptions" label="重试策略" />
          <Md3Input v-model.number="taskForm.retry_policy.interval_seconds" label="重试间隔（秒）" type="number" />
        </div>
      </div>
      <template #footer>
        <Md3Button variant="text" @click="showTaskDialog = false">取消</Md3Button>
        <Md3Button variant="primary" @click="saveTask">保存</Md3Button>
      </template>
    </Md3Dialog>

    <Md3Dialog v-model:visible="showSourceDialog" :title="editingSource ? '编辑事件源' : '新建事件源'" width="560px">
      <div class="dialog-form">
        <Md3Input v-model="sourceForm.name" label="事件源名称" />
        <Md3Select v-model="sourceForm.source_type" :options="sourceTypeOptions" label="事件源类型" />
        <Md3Input v-model="sourceForm.description" label="描述" />
        <Md3Input v-if="sourceForm.source_type === 'file_watch'" v-model="sourceForm.config.path" label="监控路径" />
        <Md3Input v-if="sourceForm.source_type === 'system_metric'" v-model="sourceForm.config.metric" label="指标名称" />
        <Md3Input v-if="sourceForm.source_type === 'system_metric'" v-model.number="sourceForm.config.threshold" label="阈值" type="number" />
      </div>
      <template #footer>
        <Md3Button variant="text" @click="showSourceDialog = false">取消</Md3Button>
        <Md3Button variant="primary" @click="saveSource">保存</Md3Button>
      </template>
    </Md3Dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, markRaw } from 'vue'
import { useRouter } from 'vue-router'
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
  Md3Dialog,
} from '@/components/md3'
import { Md3Confirm } from '@/components/md3/Md3Confirm'
import { useWorkflowStore } from '@/stores/workflowStore'
import { useSchedulerStore } from '@/stores/schedulerStore'
import { useEventTriggerStore } from '@/stores/eventTriggerStore'
import WorkflowTemplateGallery from '@/components/workflow/WorkflowTemplateGallery.vue'
import type { Workflow } from '@/stores/workflowStore'
import type { ScheduledTask } from '@/stores/schedulerStore'
import type { EventSource } from '@/stores/eventTriggerStore'

const router = useRouter()
const workflowStore = useWorkflowStore()
const schedulerStore = useSchedulerStore()
const eventTriggerStore = useEventTriggerStore()

const activeTab = ref('workflow')
const workflowSearch = ref('')
const showTemplateGallery = ref(false)
const showTaskDialog = ref(false)
const showSourceDialog = ref(false)
const editingTask = ref<ScheduledTask | null>(null)
const editingSource = ref<EventSource | null>(null)
const logFilter = ref('')

const tabItems = computed(() => [
  { label: '工作流', value: 'workflow', icon: markRaw({ template: '<Md3Icon name="source-branch" size="1em" />', components: { Md3Icon } }) },
  { label: '定时任务', value: 'scheduler', icon: markRaw({ template: '<Md3Icon name="schedule" size="1em" />', components: { Md3Icon } }) },
  { label: '事件触发', value: 'event', icon: markRaw({ template: '<Md3Icon name="lightning-bolt" size="1em" />', components: { Md3Icon } }) },
])

const metrics = computed(() => [
  { label: '活跃工作流', value: workflowStore.activeWorkflowCount, color: 'var(--md3-primary)' },
  { label: '运行中执行', value: workflowStore.runningExecutionCount, color: 'var(--md3-tertiary)' },
  { label: '已启用任务', value: schedulerStore.enabledTaskCount, color: 'var(--md3-secondary)' },
  { label: '今日成功', value: schedulerStore.todaySuccessCount, color: 'var(--md3-success, #4caf50)' },
  { label: '今日失败', value: schedulerStore.todayFailedCount, color: 'var(--md3-error)' },
  { label: '事件源', value: eventTriggerStore.sources.length, color: 'var(--md3-on-surface-variant)' },
])

const workflowColumns = [
  { prop: 'name', label: '名称', width: '200px' },
  { prop: 'status', label: '状态', width: '80px' },
  { prop: 'version', label: '版本', width: '70px' },
  { prop: 'nodes_count', label: '节点数', width: '80px' },
  { prop: 'updated_at', label: '更新时间', width: '180px' },
  { prop: 'action', label: '操作', width: '200px' },
]

const taskColumns = [
  { prop: 'name', label: '任务名称', width: '180px' },
  { prop: 'cron_expression', label: 'Cron', width: '120px' },
  { prop: 'priority', label: '优先级', width: '80px' },
  { prop: 'status', label: '启用', width: '70px' },
  { prop: 'last_run', label: '上次执行', width: '180px' },
  { prop: 'next_run_at', label: '下次执行', width: '180px' },
  { prop: 'action', label: '操作', width: '220px' },
]

const sourceColumns = [
  { prop: 'name', label: '名称', width: '160px' },
  { prop: 'source_type', label: '类型', width: '100px' },
  { prop: 'webhook_url', label: 'Webhook', width: '240px' },
  { prop: 'event_count', label: '事件数', width: '80px' },
  { prop: 'status', label: '启用', width: '70px' },
  { prop: 'action', label: '操作', width: '200px' },
]

const logColumns = [
  { prop: 'source_name', label: '事件源', width: '120px' },
  { prop: 'event_type', label: '类型', width: '120px' },
  { prop: 'status', label: '状态', width: '80px' },
  { prop: 'received_at', label: '接收时间', width: '180px' },
  { prop: 'action', label: '操作', width: '80px' },
]

const priorityOptions = [
  { label: '高', value: 'high' },
  { label: '中', value: 'medium' },
  { label: '低', value: 'low' },
]

const retryStrategyOptions = [
  { label: '固定间隔', value: 'fixed' },
  { label: '指数退避', value: 'exponential' },
]

const sourceTypeOptions = [
  { label: 'Webhook', value: 'webhook' },
  { label: '文件监控', value: 'file_watch' },
  { label: '系统指标', value: 'system_metric' },
  { label: '定时轮询', value: 'polling' },
]

const logFilterOptions = [
  { label: '全部', value: '' },
  { label: '已处理', value: 'processed' },
  { label: '已过滤', value: 'filtered' },
  { label: '失败', value: 'failed' },
]

const filteredWorkflows = computed(() => {
  if (!workflowSearch.value) return workflowStore.workflows
  const q = workflowSearch.value.toLowerCase()
  return workflowStore.workflows.filter(w => w.name.toLowerCase().includes(q))
})

const defaultTaskForm = () => ({
  name: '',
  cron_expression: '',
  priority: 'medium',
  command: '',
  timeout_seconds: 300,
  max_concurrent: 1,
  retry_policy: {
    max_retries: 0,
    strategy: 'fixed',
    interval_seconds: 60,
  },
})

const taskForm = ref(defaultTaskForm())

const defaultSourceForm = () => ({
  name: '',
  source_type: 'webhook',
  description: '',
  config: {} as Record<string, any>,
})

const sourceForm = ref(defaultSourceForm())

function getSourceTypeTag(type: string): 'primary' | 'success' | 'warning' | 'info' {
  const map: Record<string, 'primary' | 'success' | 'warning' | 'info'> = {
    webhook: 'primary',
    file_watch: 'success',
    system_metric: 'warning',
    polling: 'info',
  }
  return map[type] || 'info'
}

function getSourceTypeLabel(type: string): string {
  const map: Record<string, string> = {
    webhook: 'Webhook',
    file_watch: '文件监控',
    system_metric: '系统指标',
    polling: '定时轮询',
  }
  return map[type] || type
}

function getEventStatusTag(status: string): 'success' | 'danger' | 'warning' | 'info' {
  const map: Record<string, 'success' | 'danger' | 'warning' | 'info'> = {
    processed: 'success',
    failed: 'danger',
    filtered: 'warning',
    pending: 'info',
  }
  return map[status] || 'info'
}

async function createNewWorkflow() {
  try {
    const wf = await workflowStore.createWorkflow({ name: '未命名工作流', status: 'draft' })
    Md3Message.success('工作流已创建')
    router.push({ name: 'workflow-editor', params: { id: wf.id } })
  } catch {
    Md3Message.error('创建工作流失败')
  }
}

async function createFromTemplate(templateId: string) {
  try {
    const wf = await workflowStore.createFromTemplate(templateId, '从模板创建')
    showTemplateGallery.value = false
    Md3Message.success('工作流已从模板创建')
    router.push({ name: 'workflow-editor', params: { id: wf.id } })
  } catch {
    Md3Message.error('从模板创建失败')
  }
}

function editWorkflow(row: any) {
  router.push({ name: 'workflow-editor', params: { id: row.id } })
}

async function executeWorkflow(row: any) {
  try {
    await workflowStore.executeWorkflow(row.id, 'manual')
    Md3Message.success(`工作流「${row.name}」已开始执行`)
  } catch {
    Md3Message.error('执行工作流失败')
  }
}

async function deleteWorkflow(row: any) {
  const confirmed = await Md3Confirm.show({ title: '确认删除', message: `确定要删除工作流「${row.name}」吗？此操作不可撤销。` })
  if (!confirmed) return
  try {
    await workflowStore.deleteWorkflow(row.id)
    Md3Message.success('工作流已删除')
  } catch {
    Md3Message.error('删除工作流失败')
  }
}

async function toggleTask(row: any, enabled: boolean) {
  try {
    await schedulerStore.toggleTask(row.id, enabled)
    Md3Message.success(enabled ? '任务已启用' : '任务已禁用')
  } catch {
    Md3Message.error('切换任务状态失败')
  }
}

async function runTaskNow(row: any) {
  try {
    await schedulerStore.runTaskNow(row.id)
    Md3Message.success(`任务「${row.name}」已触发执行`)
  } catch {
    Md3Message.error('执行任务失败')
  }
}

function editTask(row: any) {
  editingTask.value = row
  taskForm.value = {
    name: row.name,
    cron_expression: row.cron_expression,
    priority: row.priority,
    command: row.command || '',
    timeout_seconds: row.timeout_seconds,
    max_concurrent: row.max_concurrent,
    retry_policy: { ...row.retry_policy },
  }
  showTaskDialog.value = true
}

async function deleteTask(row: any) {
  const confirmed = await Md3Confirm.show({ title: '确认删除', message: `确定要删除任务「${row.name}」吗？` })
  if (!confirmed) return
  try {
    await schedulerStore.deleteTask(row.id)
    Md3Message.success('任务已删除')
  } catch {
    Md3Message.error('删除任务失败')
  }
}

async function saveTask() {
  try {
    if (editingTask.value) {
      await schedulerStore.updateTask(editingTask.value.id, taskForm.value)
      Md3Message.success('任务已更新')
    } else {
      await schedulerStore.createTask(taskForm.value)
      Md3Message.success('任务已创建')
    }
    showTaskDialog.value = false
    editingTask.value = null
    taskForm.value = defaultTaskForm()
  } catch {
    Md3Message.error('保存任务失败')
  }
}

async function toggleSource(row: any, enabled: boolean) {
  try {
    await eventTriggerStore.updateSource(row.id, { status: enabled ? 'enabled' : 'disabled' })
    Md3Message.success(enabled ? '事件源已启用' : '事件源已禁用')
  } catch {
    Md3Message.error('切换事件源状态失败')
  }
}

function editSource(row: any) {
  editingSource.value = row
  sourceForm.value = {
    name: row.name,
    source_type: row.source_type,
    description: row.description || '',
    config: { ...row.config },
  }
  showSourceDialog.value = true
}

function showRoutes(row: any) {
  Md3Message.info(`事件源「${row.name}」的路由管理功能开发中`)
}

async function deleteSource(row: any) {
  const confirmed = await Md3Confirm.show({ title: '确认删除', message: `确定要删除事件源「${row.name}」吗？` })
  if (!confirmed) return
  try {
    await eventTriggerStore.deleteSource(row.id)
    Md3Message.success('事件源已删除')
  } catch {
    Md3Message.error('删除事件源失败')
  }
}

async function saveSource() {
  try {
    if (editingSource.value) {
      await eventTriggerStore.updateSource(editingSource.value.id, sourceForm.value)
      Md3Message.success('事件源已更新')
    } else {
      await eventTriggerStore.createSource(sourceForm.value)
      Md3Message.success('事件源已创建')
    }
    showSourceDialog.value = false
    editingSource.value = null
    sourceForm.value = defaultSourceForm()
  } catch {
    Md3Message.error('保存事件源失败')
  }
}

async function replayEvent(row: any) {
  try {
    await eventTriggerStore.replayEvent(row.id)
    Md3Message.success('事件已回放')
  } catch {
    Md3Message.error('回放事件失败')
  }
}

function copyWebhookUrl(url: string) {
  navigator.clipboard.writeText(url).then(() => {
    Md3Message.success('Webhook URL 已复制')
  }).catch(() => {
    Md3Message.error('复制失败')
  })
}

function fetchEventLogs() {
  eventTriggerStore.fetchEventLogs(undefined, undefined, logFilter.value || undefined)
}

onMounted(async () => {
  await Promise.all([
    workflowStore.fetchWorkflows(),
    workflowStore.fetchTemplates(),
    schedulerStore.fetchTasks(),
    eventTriggerStore.fetchSources(),
    eventTriggerStore.fetchEventLogs(),
  ])
})
</script>

<style scoped>
.automation-page {
  padding: var(--md3-space-lg);
}

.metrics-row {
  display: flex;
  gap: var(--md3-space-md);
  margin: var(--md3-space-md) 0;
  flex-wrap: wrap;
}

.metric-card {
  flex: 1;
  min-width: 140px;
  padding: var(--md3-space-lg) var(--md3-space-xl);
  background: var(--md3-surface-container-low);
  border-radius: var(--md3-shape-md);
  border: 1px solid var(--md3-outline-variant);
  text-align: center;
}

.metric-value {
  font: var(--md3-type-headline-medium);
  font-weight: 600;
  line-height: 1.2;
}

.metric-label {
  font: var(--md3-type-body-small);
  color: var(--md3-on-surface-variant);
  margin-top: var(--md3-space-xs);
}

.page-tabs {
  margin-bottom: var(--md3-space-md);
}

.tab-content {
  min-height: 400px;
}

.section-card {
  margin-bottom: var(--md3-space-md);
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

.search-input {
  width: 200px;
}

.header-icon {
  margin-right: var(--md3-space-xs);
  vertical-align: middle;
}

.action-buttons {
  display: flex;
  align-items: center;
  gap: var(--md3-space-xs);
  flex-wrap: wrap;
}

.dialog-form {
  display: flex;
  flex-direction: column;
  gap: var(--md3-space-md);
}

.form-row {
  display: flex;
  align-items: flex-end;
  gap: var(--md3-space-sm);
}

.webhook-url {
  font: var(--md3-type-body-small);
  color: var(--md3-primary);
  cursor: pointer;
  word-break: break-all;
  background: var(--md3-surface-container-low);
  padding: 2px 6px;
  border-radius: var(--md3-shape-xs);
}

.webhook-url:hover {
  text-decoration: underline;
}

.text-danger {
  color: var(--md3-error);
}

@media (max-width: 768px) {
  .card-header-right {
    flex-direction: column;
    align-items: stretch;
    gap: var(--md3-space-xs);
  }

  .search-input {
    width: 100%;
  }

  .form-row {
    flex-direction: column;
    align-items: stretch;
  }

  .action-buttons {
    flex-direction: column;
    align-items: stretch;
  }

  .metrics-row {
    flex-direction: column;
  }
}
</style>
