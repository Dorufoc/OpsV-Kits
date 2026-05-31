<script setup lang="ts">
import { computed } from 'vue'

interface NodeData {
  id: string
  node_type: string
  name: string
  config: Record<string, any>
  position_x: number
  position_y: number
}

interface EdgeData {
  id: string
  source_node_id: string
  target_node_id: string
  label?: string
}

const props = defineProps<{
  edge: EdgeData
  sourceNode: NodeData
  targetNode: NodeData
  selected?: boolean
}>()

const emit = defineEmits<{
  click: [edgeId: string]
  delete: [edgeId: string]
}>()

const NODE_WIDTH = 180
const NODE_HEIGHT = 60

const path = computed(() => {
  if (!props.sourceNode || !props.targetNode) return ''
  const sx = props.sourceNode.position_x + NODE_WIDTH
  const sy = props.sourceNode.position_y + NODE_HEIGHT / 2
  const ex = props.targetNode.position_x
  const ey = props.targetNode.position_y + NODE_HEIGHT / 2
  const dx = Math.abs(ex - sx) * 0.5
  return `M ${sx} ${sy} C ${sx + dx} ${sy}, ${ex - dx} ${ey}, ${ex} ${ey}`
})

const labelPosition = computed(() => {
  if (!props.sourceNode || !props.targetNode) return { x: 0, y: 0 }
  const sx = props.sourceNode.position_x + NODE_WIDTH
  const sy = props.sourceNode.position_y + NODE_HEIGHT / 2
  const ex = props.targetNode.position_x
  const ey = props.targetNode.position_y + NODE_HEIGHT / 2
  return {
    x: (sx + ex) / 2,
    y: (sy + ey) / 2 - 10,
  }
})

const deletePosition = computed(() => {
  if (!props.sourceNode || !props.targetNode) return { x: 0, y: 0 }
  const sx = props.sourceNode.position_x + NODE_WIDTH
  const sy = props.sourceNode.position_y + NODE_HEIGHT / 2
  const ex = props.targetNode.position_x
  const ey = props.targetNode.position_y + NODE_HEIGHT / 2
  return {
    x: (sx + ex) / 2,
    y: (sy + ey) / 2 + 12,
  }
})

function onClick(e: MouseEvent) {
  e.stopPropagation()
  emit('click', props.edge.id)
}

function onDelete(e: MouseEvent) {
  e.stopPropagation()
  emit('delete', props.edge.id)
}
</script>

<template>
  <g class="workflow-edge" @click="onClick">
    <path
      :d="path"
      fill="none"
      :stroke="selected ? 'var(--md3-primary)' : 'var(--md3-on-surface-variant)'"
      :stroke-width="selected ? 2.5 : 1.5"
      :stroke-dasharray="selected ? undefined : undefined"
      marker-end="url(#arrowhead)"
      class="edge-path"
    />
    <path
      :d="path"
      fill="none"
      stroke="transparent"
      stroke-width="12"
      class="edge-hitbox"
    />
    <text
      v-if="edge.label"
      :x="labelPosition.x"
      :y="labelPosition.y"
      text-anchor="middle"
      dominant-baseline="central"
      class="edge-label"
    >
      {{ edge.label }}
    </text>
    <g
      v-if="selected"
      :transform="`translate(${deletePosition.x}, ${deletePosition.y})`"
      @click="onDelete"
    >
      <circle r="10" fill="var(--md3-error-container)" class="edge-delete-btn" />
      <text
        text-anchor="middle"
        dominant-baseline="central"
        fill="var(--md3-error)"
        font-size="12"
        font-weight="bold"
        pointer-events="none"
      >
        ×
      </text>
    </g>
  </g>
</template>

<style scoped>
.workflow-edge {
  cursor: pointer;
}

.edge-path {
  transition: stroke var(--md3-motion-duration-short) var(--md3-motion-easing-standard),
              stroke-width var(--md3-motion-duration-short) var(--md3-motion-easing-standard);
}

.edge-hitbox {
  pointer-events: stroke;
  cursor: pointer;
}

.edge-label {
  font-size: 11px;
  fill: var(--md3-on-surface-variant);
  pointer-events: none;
  user-select: none;
}

.edge-delete-btn {
  cursor: pointer;
  transition: r var(--md3-motion-duration-short) var(--md3-motion-easing-standard);
}

.edge-delete-btn:hover {
  r: 12;
}
</style>
