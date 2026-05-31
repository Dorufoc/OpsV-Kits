<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import WorkflowNode from './WorkflowNode.vue'
import WorkflowEdge from './WorkflowEdge.vue'

interface WorkflowNodeData {
  id: string
  node_type: string
  name: string
  config: Record<string, any>
  position_x: number
  position_y: number
}

interface WorkflowEdgeData {
  id: string
  source_node_id: string
  target_node_id: string
  label?: string
}

interface NodeExecution {
  node_id: string
  status: 'pending' | 'running' | 'success' | 'failed'
}

const props = withDefaults(defineProps<{
  nodes: WorkflowNodeData[]
  edges: WorkflowEdgeData[]
  nodeExecutions?: NodeExecution[]
}>(), {
  nodeExecutions: () => [],
})

const emit = defineEmits<{
  'node-click': [nodeId: string]
  'node-drag': [nodeId: string, x: number, y: number]
  'node-drag-end': [nodeId: string, x: number, y: number]
  'edge-click': [edgeId: string]
  'canvas-click': []
  'connect': [sourceNodeId: string, targetNodeId: string]
  'drop': [nodeType: string, x: number, y: number]
}>()

const zoom = ref(1)
const panX = ref(0)
const panY = ref(0)
const isPanning = ref(false)
const panStart = ref({ x: 0, y: 0 })
const panStartOffset = ref({ x: 0, y: 0 })

const connectingFrom = ref<string | null>(null)
const tempLineEnd = ref({ x: 0, y: 0 })
const isDrawingConnection = ref(false)

const selectedEdgeId = ref<string | null>(null)

const viewBox = computed(() => {
  const w = 10000
  const h = 10000
  const vw = w / zoom.value
  const vh = h / zoom.value
  const vx = (w - vw) / 2 + panX.value
  const vy = (h - vh) / 2 + panY.value
  return `${vx} ${vy} ${vw} ${vh}`
})

const executionMap = computed(() => {
  const map = new Map<string, string>()
  for (const ex of props.nodeExecutions) {
    map.set(ex.node_id, ex.status)
  }
  return map
})

function findNode(id: string): WorkflowNodeData | undefined {
  return props.nodes.find(n => n.id === id)
}

function screenToCanvas(clientX: number, clientY: number) {
  const svg = document.querySelector('.canvas-svg') as SVGSVGElement | null
  if (!svg) return { x: 0, y: 0 }
  const rect = svg.getBoundingClientRect()
  const svgX = ((clientX - rect.left) / rect.width) * 10000
  const svgY = ((clientY - rect.top) / rect.height) * 10000
  const w = 10000 / zoom.value
  const h = 10000 / zoom.value
  const vx = (10000 - w) / 2 + panX.value
  const vy = (10000 - h) / 2 + panY.value
  return {
    x: vx + (svgX / 10000) * w,
    y: vy + (svgY / 10000) * h,
  }
}

function onWheel(e: WheelEvent) {
  e.preventDefault()
  const delta = e.deltaY > 0 ? -0.1 : 0.1
  zoom.value = Math.min(3, Math.max(0.2, zoom.value + delta))
}

function onCanvasMouseDown(e: MouseEvent) {
  if (e.button === 1 || (e.button === 0 && e.altKey)) {
    isPanning.value = true
    panStart.value = { x: e.clientX, y: e.clientY }
    panStartOffset.value = { x: panX.value, y: panY.value }
    e.preventDefault()
    return
  }
  if (e.button === 0 && !isDrawingConnection.value) {
    selectedEdgeId.value = null
    emit('canvas-click')
  }
}

function onMouseMove(e: MouseEvent) {
  if (isPanning.value) {
    const dx = (e.clientX - panStart.value.x) / zoom.value
    const dy = (e.clientY - panStart.value.y) / zoom.value
    panX.value = panStartOffset.value.x - dx
    panY.value = panStartOffset.value.y - dy
  }
  if (isDrawingConnection.value && connectingFrom.value) {
    const pos = screenToCanvas(e.clientX, e.clientY)
    tempLineEnd.value = pos
  }
}

function onMouseUp(e: MouseEvent) {
  if (isPanning.value) {
    isPanning.value = false
  }
  if (isDrawingConnection.value) {
    isDrawingConnection.value = false
    connectingFrom.value = null
  }
}

function onNodeClick(nodeId: string) {
  emit('node-click', nodeId)
}

function onNodeDrag(nodeId: string, x: number, y: number) {
  emit('node-drag', nodeId, x, y)
}

function onNodeDragEnd(nodeId: string, x: number, y: number) {
  emit('node-drag-end', nodeId, x, y)
}

function onPortClick(nodeId: string, portType: 'input' | 'output') {
  if (portType === 'output') {
    connectingFrom.value = nodeId
    isDrawingConnection.value = true
  }
}

function onEdgeClick(edgeId: string) {
  selectedEdgeId.value = edgeId
  emit('edge-click', edgeId)
}

function onSvgMouseUp(e: MouseEvent) {
  if (isDrawingConnection.value && connectingFrom.value) {
    const target = (e.target as SVGElement).closest('[data-node-id]')
    if (target) {
      const targetNodeId = target.getAttribute('data-node-id')
      if (targetNodeId && targetNodeId !== connectingFrom.value) {
        emit('connect', connectingFrom.value, targetNodeId)
      }
    }
    isDrawingConnection.value = false
    connectingFrom.value = null
  }
}

function onDrop(e: DragEvent) {
  e.preventDefault()
  const nodeType = e.dataTransfer?.getData('workflow-node-type')
  if (!nodeType) return
  const pos = screenToCanvas(e.clientX, e.clientY)
  emit('drop', nodeType, pos.x, pos.y)
}

function zoomIn() {
  zoom.value = Math.min(3, zoom.value + 0.2)
}

function zoomOut() {
  zoom.value = Math.max(0.2, zoom.value - 0.2)
}

function resetView() {
  zoom.value = 1
  panX.value = 0
  panY.value = 0
}

const tempConnectionPath = computed(() => {
  if (!connectingFrom.value) return ''
  const sourceNode = findNode(connectingFrom.value)
  if (!sourceNode) return ''
  const sx = sourceNode.position_x + 180
  const sy = sourceNode.position_y + 30
  const ex = tempLineEnd.value.x
  const ey = tempLineEnd.value.y
  const dx = Math.abs(ex - sx) * 0.5
  return `M ${sx} ${sy} C ${sx + dx} ${sy}, ${ex - dx} ${ey}, ${ex} ${ey}`
})

const minimapNodes = computed(() => {
  if (props.nodes.length === 0) return []
  const xs = props.nodes.map(n => n.position_x)
  const ys = props.nodes.map(n => n.position_y)
  const minX = Math.min(...xs) - 50
  const maxX = Math.max(...xs) + 230
  const minY = Math.min(...ys) - 50
  const maxY = Math.max(...ys) + 110
  const rangeX = maxX - minX || 1
  const rangeY = maxY - minY || 1
  return props.nodes.map(n => ({
    id: n.id,
    x: ((n.position_x - minX) / rangeX) * 180 + 10,
    y: ((n.position_y - minY) / rangeY) * 130 + 10,
    w: (180 / rangeX) * 180,
    h: (60 / rangeY) * 130,
  }))
})

onMounted(() => {
  window.addEventListener('mousemove', onMouseMove)
  window.addEventListener('mouseup', onMouseUp)
})

onUnmounted(() => {
  window.removeEventListener('mousemove', onMouseMove)
  window.removeEventListener('mouseup', onMouseUp)
})
</script>

<template>
  <div
    class="workflow-canvas"
    @drop="onDrop"
    @dragover.prevent
    @wheel="onWheel"
    @mousedown="onCanvasMouseDown"
  >
    <svg
      :viewBox="viewBox"
      class="canvas-svg"
      @mouseup="onSvgMouseUp"
    >
      <defs>
        <pattern id="grid" width="20" height="20" patternUnits="userSpaceOnUse">
          <circle cx="10" cy="10" r="1" fill="var(--md3-outline-variant)" />
        </pattern>
        <marker
          id="arrowhead"
          markerWidth="10"
          markerHeight="7"
          refX="10"
          refY="3.5"
          orient="auto"
          fill="var(--md3-on-surface-variant)"
        >
          <polygon points="0 0, 10 3.5, 0 7" />
        </marker>
      </defs>
      <rect width="10000" height="10000" fill="url(#grid)" />
      <WorkflowEdge
        v-for="edge in edges"
        :key="edge.id"
        :edge="edge"
        :source-node="findNode(edge.source_node_id)!"
        :target-node="findNode(edge.target_node_id)!"
        :selected="selectedEdgeId === edge.id"
        @click="onEdgeClick"
        @delete="() => {}"
      />
      <WorkflowNode
        v-for="node in nodes"
        :key="node.id"
        :node="node"
        :execution-status="executionMap.get(node.id)"
        @click="onNodeClick"
        @drag="onNodeDrag"
        @drag-end="onNodeDragEnd"
        @port-click="onPortClick"
      />
      <path
        v-if="isDrawingConnection && connectingFrom"
        :d="tempConnectionPath"
        fill="none"
        stroke="var(--md3-primary)"
        stroke-width="2"
        stroke-dasharray="6 3"
        pointer-events="none"
      />
    </svg>
    <div class="canvas-controls">
      <button class="canvas-control-btn" @click="zoomIn">+</button>
      <button class="canvas-control-btn" @click="zoomOut">-</button>
      <button class="canvas-control-btn" @click="resetView">Reset</button>
    </div>
    <div class="canvas-minimap">
      <svg viewBox="0 0 200 150" class="minimap-svg">
        <rect
          v-for="mnode in minimapNodes"
          :key="mnode.id"
          :x="mnode.x"
          :y="mnode.y"
          :width="Math.max(mnode.w, 4)"
          :height="Math.max(mnode.h, 3)"
          rx="2"
          fill="var(--md3-primary)"
          opacity="0.5"
        />
      </svg>
    </div>
  </div>
</template>

<style scoped>
.workflow-canvas {
  position: relative;
  width: 100%;
  height: 100%;
  overflow: hidden;
  background: var(--md3-surface);
  cursor: default;
}

.canvas-svg {
  width: 100%;
  height: 100%;
  display: block;
}

.canvas-controls {
  position: absolute;
  bottom: var(--md3-space-lg);
  left: var(--md3-space-lg);
  display: flex;
  flex-direction: column;
  gap: var(--md3-space-xs);
  z-index: 10;
}

.canvas-control-btn {
  width: 32px;
  height: 32px;
  border: 1px solid var(--md3-outline-variant);
  border-radius: var(--md3-shape-xs);
  background: var(--md3-surface-container);
  color: var(--md3-on-surface);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: 600;
  transition: background-color var(--md3-motion-duration-short) var(--md3-motion-easing-standard);
}

.canvas-control-btn:hover {
  background: var(--md3-surface-container-high);
}

.canvas-minimap {
  position: absolute;
  bottom: var(--md3-space-lg);
  right: var(--md3-space-lg);
  width: 200px;
  height: 150px;
  border: 1px solid var(--md3-outline-variant);
  border-radius: var(--md3-shape-xs);
  background: var(--md3-surface-container);
  overflow: hidden;
  z-index: 10;
  opacity: 0.85;
}

.minimap-svg {
  width: 100%;
  height: 100%;
}
</style>
