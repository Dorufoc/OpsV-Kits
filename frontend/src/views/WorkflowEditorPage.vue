<template>
  <div class="workflow-editor-page">
    <div class="editor-toolbar">
      <div class="toolbar-left">
        <Md3Button variant="text" @click="goBack"><Md3Icon name="arrow-left" />返回</Md3Button>
        <Md3Input v-model="workflowName" class="workflow-name-input" @blur="saveWorkflow" />
        <Md3Tag v-if="workflow" :type="workflow.status === 'active' ? 'success' : 'warning'" size="sm">v{{ workflow?.version || 1 }}</Md3Tag>
      </div>
      <div class="toolbar-right">
        <Md3Button size="sm" variant="text" @click="showVersions = true"><Md3Icon name="history" />版本</Md3Button>
        <Md3Button size="sm" variant="text" @click="exportWorkflow"><Md3Icon name="download" />导出</Md3Button>
        <Md3Button size="sm" variant="text" @click="importWorkflow"><Md3Icon name="upload" />导入</Md3Button>
        <Md3Button size="sm" variant="primary" @click="executeWorkflow"><Md3Icon name="play" />执行</Md3Button>
        <Md3Button v-if="isExecuting" size="sm" variant="text" @click="pauseExecution"><Md3Icon name="pause" />暂停</Md3Button>
        <Md3Button v-if="isExecuting" size="sm" variant="danger" @click="cancelExecution"><Md3Icon name="stop" />取消</Md3Button>
      </div>
    </div>

    <div class="editor-body">
      <WorkflowNodePanel @drag-start="onNodeDragStart" />

      <WorkflowCanvas
        :nodes="nodes"
        :edges="edges"
        :node-executions="canvasNodeExecutions"
        @node-click="onNodeClick"
        @node-drag="onNodeDrag"
        @node-drag-end="onNodeDragEnd"
        @edge-click="onEdgeClick"
        @canvas-click="onCanvasClick"
        @connect="onConnect"
      />

      <NodeConfigPanel
        v-if="selectedNode"
        :node="selectedNode"
        :ssh-accounts="sshAccounts"
        @update="onNodeUpdate"
        @close="selectedNode = null"
      />
    </div>

    <Md3Dialog v-model:visible="showVersions" title="版本历史" width="560px">
      <Md3Table :columns="versionColumns" :data="workflowStore.versions" stripe max-height="400" empty-text="暂无版本历史">
        <template #action="{ row }">
          <Md3Button size="sm" variant="text" @click="rollbackToVersion((row as any).version)">回滚</Md3Button>
        </template>
      </Md3Table>
    </Md3Dialog>

    <div v-if="currentExecution" class="execution-bar" :class="currentExecution.status">
      <Md3Icon :name="getExecutionIcon(currentExecution.status)" />
      <span>执行状态: {{ getExecutionStatusLabel(currentExecution.status) }}</span>
      <span v-if="currentExecution.duration_seconds">耗时: {{ currentExecution.duration_seconds.toFixed(1) }}s</span>
      <span>节点: {{ currentExecution.success_nodes }}/{{ currentExecution.total_nodes }} 成功</span>
      <Md3Progress v-if="currentExecution.status === 'running'" :percentage="executionProgress" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Md3Message, Md3Icon } from '@/components/md3'
import Md3Button from '@/components/Md3Button.vue'
import {
  Md3Tag,
  Md3Input,
  Md3Table,
  Md3Dialog,
  Md3Progress,
} from '@/components/md3'
import { useWorkflowStore } from '@/stores/workflowStore'
import { useSshAccountStore } from '@/stores/sshAccountStore'
import WorkflowCanvas from '@/components/workflow/WorkflowCanvas.vue'
import WorkflowNodePanel from '@/components/workflow/WorkflowNodePanel.vue'
import NodeConfigPanel from '@/components/workflow/NodeConfigPanel.vue'
import type { WorkflowNode, WorkflowEdge, WorkflowExecution, NodeExecution } from '@/stores/workflowStore'

const route = useRoute()
const router = useRouter()
const workflowStore = useWorkflowStore()
const sshAccountStore = useSshAccountStore()

const workflowId = computed(() => route.params.id as string)
const workflow = computed(() => workflowStore.currentWorkflow)
const workflowName = ref('')
const selectedNode = ref<WorkflowNode | null>(null)
const showVersions = ref(false)
const isExecuting = ref(false)
let pollTimer: ReturnType<typeof setInterval> | null = null

const nodes = computed<WorkflowNode[]>(() => workflow.value?.nodes || [])
const edges = computed<WorkflowEdge[]>(() => workflow.value?.edges || [])
const nodeExecutions = ref<NodeExecution[]>([])
const currentExecution = ref<WorkflowExecution | null>(null)

type CanvasNodeExecutionStatus = 'pending' | 'running' | 'success' | 'failed'
const canvasNodeExecutions = computed(() =>
  nodeExecutions.value.map(ne => ({
    node_id: ne.node_id,
    status: ne.status as CanvasNodeExecutionStatus,
  }))
)

const sshAccounts = computed(() =>
  sshAccountStore.accounts.map(a => ({ id: a.alias, name: a.alias }))
)

const executionProgress = computed(() => {
  if (!currentExecution.value || currentExecution.value.total_nodes === 0) return 0
  const completed = currentExecution.value.success_nodes + currentExecution.value.failed_nodes
  return Math.round((completed / currentExecution.value.total_nodes) * 100)
})

const versionColumns = [
  { prop: 'version', label: '版本', width: '80px' },
  { prop: 'change_note', label: '变更说明', width: '200px' },
  { prop: 'created_at', label: '创建时间', width: '180px' },
  { prop: 'action', label: '操作', width: '100px' },
]

function getExecutionIcon(status: string): string {
  const map: Record<string, string> = {
    running: 'loading',
    success: 'check-circle',
    failed: 'alert-circle',
    paused: 'pause-circle',
    cancelled: 'close-circle',
  }
  return map[status] || 'help-circle'
}

function getExecutionStatusLabel(status: string): string {
  const map: Record<string, string> = {
    running: '运行中',
    success: '已完成',
    failed: '失败',
    paused: '已暂停',
    cancelled: '已取消',
    pending: '等待中',
  }
  return map[status] || status
}

function goBack() {
  router.push({ name: 'automation' })
}

async function saveWorkflow() {
  if (!workflow.value) return
  try {
    await workflowStore.updateWorkflow(workflowId.value, { name: workflowName.value })
  } catch {
    Md3Message.error('保存工作流失败')
  }
}

async function exportWorkflow() {
  if (!workflow.value) return
  try {
    const data = await workflowStore.exportWorkflow(workflowId.value)
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${workflow.value.name || 'workflow'}.json`
    a.click()
    URL.revokeObjectURL(url)
    Md3Message.success('工作流已导出')
  } catch {
    Md3Message.error('导出失败')
  }
}

async function importWorkflow() {
  const input = document.createElement('input')
  input.type = 'file'
  input.accept = '.json'
  input.onchange = async (e) => {
    const file = (e.target as HTMLInputElement).files?.[0]
    if (!file) return
    try {
      const text = await file.text()
      const data = JSON.parse(text)
      await workflowStore.importWorkflow(data)
      Md3Message.success('工作流已导入')
    } catch {
      Md3Message.error('导入失败，请检查文件格式')
    }
  }
  input.click()
}

async function executeWorkflow() {
  if (!workflow.value) return
  try {
    const res = await workflowStore.executeWorkflow(workflowId.value, 'manual')
    isExecuting.value = true
    currentExecution.value = res
    startPolling(res.id)
    Md3Message.success('工作流已开始执行')
  } catch {
    Md3Message.error('执行工作流失败')
  }
}

async function pauseExecution() {
  if (!currentExecution.value) return
  try {
    await workflowStore.pauseExecution(currentExecution.value.id)
    Md3Message.success('执行已暂停')
  } catch {
    Md3Message.error('暂停执行失败')
  }
}

async function cancelExecution() {
  if (!currentExecution.value) return
  try {
    await workflowStore.cancelExecution(currentExecution.value.id)
    isExecuting.value = false
    stopPolling()
    Md3Message.success('执行已取消')
  } catch {
    Md3Message.error('取消执行失败')
  }
}

function startPolling(executionId: string) {
  stopPolling()
  pollTimer = setInterval(async () => {
    try {
      await workflowStore.fetchExecution(executionId)
      currentExecution.value = workflowStore.currentExecution
      if (currentExecution.value && ['success', 'failed', 'cancelled'].includes(currentExecution.value.status)) {
        isExecuting.value = false
        stopPolling()
      }
      await workflowStore.fetchNodeExecutions(executionId)
      nodeExecutions.value = workflowStore.nodeExecutions
    } catch {
      stopPolling()
    }
  }, 2000)
}

function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

async function rollbackToVersion(version: number) {
  try {
    await workflowStore.rollback(workflowId.value, version)
    await workflowStore.fetchWorkflow(workflowId.value)
    if (workflow.value) {
      workflowName.value = workflow.value.name
    }
    showVersions.value = false
    Md3Message.success(`已回滚到 v${version}`)
  } catch {
    Md3Message.error('回滚失败')
  }
}

function onNodeDragStart(nodeType: string) {
}

function onNodeClick(nodeId: string) {
  const node = nodes.value.find(n => n.id === nodeId)
  if (node) {
    selectedNode.value = node
  }
}

function onNodeDrag(nodeId: string, x: number, y: number) {
}

function onNodeDragEnd(nodeId: string, x: number, y: number) {
  if (!workflow.value) return
  const updatedNodes = nodes.value.map(n =>
    n.id === nodeId ? { ...n, position_x: x, position_y: y } : n
  )
  workflowStore.updateWorkflow(workflowId.value, { nodes: updatedNodes })
}

function onEdgeClick(edgeId: string) {
}

function onCanvasClick() {
  selectedNode.value = null
}

function onConnect(sourceNodeId: string, targetNodeId: string) {
  if (!workflow.value) return
  const newEdge = {
    id: `edge-${Date.now()}`,
    workflow_id: workflowId.value,
    source_node_id: sourceNodeId,
    target_node_id: targetNodeId,
  }
  const updatedEdges = [...edges.value, newEdge as any]
  workflowStore.updateWorkflow(workflowId.value, { edges: updatedEdges })
}

function onNodeUpdate(nodeId: string, config: Record<string, any>) {
  if (!workflow.value) return
  const updatedNodes = nodes.value.map(n =>
    n.id === nodeId ? { ...n, config } : n
  )
  workflowStore.updateWorkflow(workflowId.value, { nodes: updatedNodes })
  if (selectedNode.value?.id === nodeId) {
    selectedNode.value = { ...selectedNode.value, config }
  }
}

onMounted(async () => {
  await workflowStore.fetchWorkflow(workflowId.value)
  if (workflow.value) {
    workflowName.value = workflow.value.name
  }
  await workflowStore.fetchVersions(workflowId.value)
})

onUnmounted(() => {
  stopPolling()
})
</script>

<style scoped>
.workflow-editor-page {
  display: flex;
  flex-direction: column;
  height: 100vh;
  overflow: hidden;
  background: var(--md3-surface);
}

.editor-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--md3-space-sm) var(--md3-space-lg);
  background: var(--md3-surface-container);
  border-bottom: 1px solid var(--md3-outline-variant);
  flex-shrink: 0;
  z-index: 30;
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: var(--md3-space-sm);
}

.toolbar-right {
  display: flex;
  align-items: center;
  gap: var(--md3-space-xs);
}

.workflow-name-input {
  width: 240px;
}

.workflow-name-input :deep(.md3-input) {
  font: var(--md3-type-title-medium);
  font-weight: 600;
}

.editor-body {
  display: flex;
  flex: 1;
  overflow: hidden;
  position: relative;
}

.execution-bar {
  display: flex;
  align-items: center;
  gap: var(--md3-space-md);
  padding: var(--md3-space-sm) var(--md3-space-lg);
  background: var(--md3-surface-container);
  border-top: 1px solid var(--md3-outline-variant);
  font: var(--md3-type-body-small);
  color: var(--md3-on-surface-variant);
  flex-shrink: 0;
  z-index: 30;
}

.execution-bar.running {
  color: var(--md3-primary);
  background: var(--md3-primary-container);
}

.execution-bar.success {
  color: var(--md3-success, #4caf50);
  background: var(--md3-surface-container-low);
}

.execution-bar.failed {
  color: var(--md3-error);
  background: var(--md3-error-container);
}

.execution-bar .md3-progress {
  flex: 1;
  max-width: 200px;
}

@media (max-width: 768px) {
  .toolbar-left,
  .toolbar-right {
    flex-wrap: wrap;
    gap: var(--md3-space-xs);
  }

  .workflow-name-input {
    width: 160px;
  }
}
</style>
