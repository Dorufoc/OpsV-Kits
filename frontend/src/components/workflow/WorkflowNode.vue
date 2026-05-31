<script setup lang="ts">
import { computed, ref } from 'vue'
import { getMdiIconPath } from '@/utils/icon-map'

interface NodeData {
  id: string
  node_type: string
  name: string
  config: Record<string, any>
  position_x: number
  position_y: number
}

const props = defineProps<{
  node: NodeData
  executionStatus?: string
}>()

const emit = defineEmits<{
  click: [nodeId: string]
  'drag-start': [nodeId: string, event: MouseEvent]
  drag: [nodeId: string, x: number, y: number]
  'drag-end': [nodeId: string, x: number, y: number]
  'port-click': [nodeId: string, portType: 'input' | 'output']
}>()

const isDragging = ref(false)
const dragStart = ref({ x: 0, y: 0 })
const dragNodeStart = ref({ x: 0, y: 0 })

const NODE_WIDTH = 180
const NODE_HEIGHT = 60

const nodeColors: Record<string, { bg: string; border: string; text: string }> = {
  trigger_cron: { bg: 'var(--md3-primary-container)', border: 'var(--md3-primary)', text: 'var(--md3-on-primary-container)' },
  trigger_webhook: { bg: 'var(--md3-primary-container)', border: 'var(--md3-primary)', text: 'var(--md3-on-primary-container)' },
  trigger_event: { bg: 'var(--md3-primary-container)', border: 'var(--md3-primary)', text: 'var(--md3-on-primary-container)' },
  action_shell: { bg: 'var(--md3-tertiary-container, #d0e8d0)', border: 'var(--md3-tertiary, #2e7d32)', text: 'var(--md3-on-tertiary-container, #1b5e20)' },
  action_http: { bg: 'var(--md3-tertiary-container, #d0e8d0)', border: 'var(--md3-tertiary, #2e7d32)', text: 'var(--md3-on-tertiary-container, #1b5e20)' },
  action_script: { bg: 'var(--md3-tertiary-container, #d0e8d0)', border: 'var(--md3-tertiary, #2e7d32)', text: 'var(--md3-on-tertiary-container, #1b5e20)' },
  condition: { bg: 'var(--md3-warning-container, #ffe0b2)', border: 'var(--md3-warning, #e65100)', text: 'var(--md3-on-warning-container, #bf360c)' },
  loop: { bg: 'var(--md3-secondary-container)', border: 'var(--md3-secondary)', text: 'var(--md3-on-secondary-container)' },
  wait: { bg: 'var(--md3-surface-container-high)', border: 'var(--md3-outline)', text: 'var(--md3-on-surface-variant)' },
  notify: { bg: 'var(--md3-error-container)', border: 'var(--md3-error)', text: 'var(--md3-on-error-container)' },
  end: { bg: 'var(--md3-surface-container-highest)', border: 'var(--md3-outline-variant)', text: 'var(--md3-on-surface)' },
}

const nodeIcons: Record<string, string> = {
  trigger_cron: 'schedule',
  trigger_webhook: 'webhook',
  trigger_event: 'lightning-bolt',
  action_shell: 'console',
  action_http: 'http',
  action_script: 'code-tags',
  condition: 'source-branch',
  loop: 'repeat',
  wait: 'timer-sand',
  notify: 'bell',
  end: 'stop',
}

const colors = computed(() => {
  return nodeColors[props.node.node_type] || nodeColors.end
})

const iconPath = computed(() => {
  const iconName = nodeIcons[props.node.node_type]
  return iconName ? getMdiIconPath(iconName) : ''
})

const statusBorderColor = computed(() => {
  switch (props.executionStatus) {
    case 'success': return 'var(--md3-success, #2e7d32)'
    case 'failed': return 'var(--md3-error)'
    case 'running': return 'var(--md3-primary)'
    case 'pending': return 'var(--md3-warning, #e65100)'
    default: return ''
  }
})

function onBodyMouseDown(e: MouseEvent) {
  if ((e.target as SVGElement).classList.contains('node-port')) return
  e.stopPropagation()
  emit('click', props.node.id)
  isDragging.value = true
  dragStart.value = { x: e.clientX, y: e.clientY }
  dragNodeStart.value = { x: props.node.position_x, y: props.node.position_y }

  const onMove = (ev: MouseEvent) => {
    if (!isDragging.value) return
    const dx = (ev.clientX - dragStart.value.x)
    const dy = (ev.clientY - dragStart.value.y)
    const newX = dragNodeStart.value.x + dx
    const newY = dragNodeStart.value.y + dy
    emit('drag', props.node.id, newX, newY)
  }

  const onUp = (ev: MouseEvent) => {
    if (!isDragging.value) return
    isDragging.value = false
    const dx = (ev.clientX - dragStart.value.x)
    const dy = (ev.clientY - dragStart.value.y)
    const newX = dragNodeStart.value.x + dx
    const newY = dragNodeStart.value.y + dy
    emit('drag-end', props.node.id, newX, newY)
    window.removeEventListener('mousemove', onMove)
    window.removeEventListener('mouseup', onUp)
  }

  window.addEventListener('mousemove', onMove)
  window.addEventListener('mouseup', onUp)
}

function onPortMouseDown(e: MouseEvent, portType: 'input' | 'output') {
  e.stopPropagation()
  e.preventDefault()
  emit('port-click', props.node.id, portType)
}
</script>

<template>
  <g
    :data-node-id="node.id"
    :transform="`translate(${node.position_x}, ${node.position_y})`"
    class="workflow-node"
    @mousedown="onBodyMouseDown"
  >
    <rect
      :width="NODE_WIDTH"
      :height="NODE_HEIGHT"
      rx="12"
      ry="12"
      :fill="colors.bg"
      :stroke="statusBorderColor || colors.border"
      :stroke-width="statusBorderColor ? 2.5 : 1.5"
      class="node-body"
    />
    <g v-if="iconPath" transform="translate(12, 16)">
      <svg width="24" height="24" viewBox="0 0 24 24">
        <path :d="iconPath" :fill="colors.text" />
      </svg>
    </g>
    <text
      :x="iconPath ? 44 : 16"
      :y="NODE_HEIGHT / 2"
      :fill="colors.text"
      dominant-baseline="central"
      class="node-name"
    >
      {{ node.name }}
    </text>
    <circle
      cx="0"
      :cy="NODE_HEIGHT / 2"
      r="6"
      fill="var(--md3-surface)"
      stroke="var(--md3-outline)"
      stroke-width="1.5"
      class="node-port node-port-input"
      @mousedown="onPortMouseDown($event, 'input')"
    />
    <circle
      :cx="NODE_WIDTH"
      :cy="NODE_HEIGHT / 2"
      r="6"
      fill="var(--md3-surface)"
      stroke="var(--md3-outline)"
      stroke-width="1.5"
      class="node-port node-port-output"
      @mousedown="onPortMouseDown($event, 'output')"
    />
    <circle
      v-if="executionStatus === 'running'"
      :cx="NODE_WIDTH - 12"
      :cy="12"
      r="4"
      fill="var(--md3-primary)"
      class="node-status-dot"
    />
  </g>
</template>

<style scoped>
.workflow-node {
  cursor: grab;
}

.workflow-node:active {
  cursor: grabbing;
}

.node-body {
  transition: stroke var(--md3-motion-duration-short) var(--md3-motion-easing-standard);
}

.node-name {
  font-size: 13px;
  font-weight: 500;
  pointer-events: none;
  user-select: none;
  max-width: 120px;
  overflow: hidden;
  text-overflow: ellipsis;
}

.node-port {
  cursor: crosshair;
  transition: r var(--md3-motion-duration-short) var(--md3-motion-easing-standard),
              fill var(--md3-motion-duration-short) var(--md3-motion-easing-standard);
}

.node-port:hover {
  r: 8;
  fill: var(--md3-primary-container);
  stroke: var(--md3-primary);
}

.node-status-dot {
  animation: pulse 1.5s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.3; }
}
</style>
