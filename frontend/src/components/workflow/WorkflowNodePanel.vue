<script setup lang="ts">
import { Md3Icon, Md3Divider } from '@/components/md3'

const emit = defineEmits<{
  'drag-start': [nodeType: string]
}>()

interface NodeTypeDef {
  type: string
  label: string
  icon: string
}

interface NodeCategory {
  name: string
  nodes: NodeTypeDef[]
}

const categories: NodeCategory[] = [
  {
    name: '触发器',
    nodes: [
      { type: 'trigger_cron', label: '定时触发', icon: 'schedule' },
      { type: 'trigger_webhook', label: 'Webhook', icon: 'webhook' },
      { type: 'trigger_event', label: '事件触发', icon: 'lightning-bolt' },
    ],
  },
  {
    name: '操作',
    nodes: [
      { type: 'action_shell', label: 'Shell 命令', icon: 'console' },
      { type: 'action_http', label: 'HTTP 请求', icon: 'http' },
      { type: 'action_script', label: '脚本执行', icon: 'code-tags' },
    ],
  },
  {
    name: '控制',
    nodes: [
      { type: 'condition', label: '条件判断', icon: 'source-branch' },
      { type: 'loop', label: '循环', icon: 'repeat' },
      { type: 'wait', label: '等待', icon: 'timer-sand' },
    ],
  },
  {
    name: '输出',
    nodes: [
      { type: 'notify', label: '通知', icon: 'bell' },
      { type: 'end', label: '结束', icon: 'stop' },
    ],
  },
]

function onDragStart(e: DragEvent, nodeType: string) {
  e.dataTransfer?.setData('workflow-node-type', nodeType)
  emit('drag-start', nodeType)
}
</script>

<template>
  <div class="workflow-node-panel">
    <div class="panel-title">节点类型</div>
    <Md3Divider />
    <div v-for="category in categories" :key="category.name" class="node-category">
      <div class="category-label">{{ category.name }}</div>
      <div class="category-nodes">
        <div
          v-for="nodeDef in category.nodes"
          :key="nodeDef.type"
          class="node-item"
          draggable="true"
          @dragstart="onDragStart($event, nodeDef.type)"
        >
          <Md3Icon :name="nodeDef.icon" :size="18" />
          <span class="node-item-label">{{ nodeDef.label }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.workflow-node-panel {
  width: 240px;
  height: 100%;
  background: var(--md3-surface-container);
  border-right: 1px solid var(--md3-outline-variant);
  display: flex;
  flex-direction: column;
  overflow-y: auto;
  flex-shrink: 0;
}

.panel-title {
  font: var(--md3-type-title-small);
  color: var(--md3-on-surface);
  padding: var(--md3-space-lg) var(--md3-space-xl) var(--md3-space-sm);
}

.node-category {
  padding: var(--md3-space-sm) var(--md3-space-lg);
}

.category-label {
  font: var(--md3-type-label-medium);
  color: var(--md3-on-surface-variant);
  padding: var(--md3-space-xs) var(--md3-space-sm);
  margin-bottom: var(--md3-space-xs);
}

.category-nodes {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.node-item {
  display: flex;
  align-items: center;
  gap: var(--md3-space-sm);
  padding: var(--md3-space-sm) var(--md3-space-md);
  border-radius: var(--md3-shape-xs);
  cursor: grab;
  transition: background-color var(--md3-motion-duration-short) var(--md3-motion-easing-standard);
  user-select: none;
}

.node-item:hover {
  background: var(--md3-surface-container-high);
}

.node-item:active {
  cursor: grabbing;
  background: var(--md3-primary-container);
}

.node-item-label {
  font: var(--md3-type-body-medium);
  color: var(--md3-on-surface);
}
</style>
