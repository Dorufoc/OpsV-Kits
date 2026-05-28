<template>
  <div class="monitor-heatmap" ref="chartRef" :style="{ height }"></div>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, watch, nextTick } from 'vue'
import * as echarts from 'echarts'

const props = withDefaults(defineProps<{
  data: { name: string; value: number }[]
  title?: string
  height?: string
}>(), {
  data: () => [], title: '', height: '200px',
})

const chartRef = ref<HTMLDivElement>()
let chart: echarts.ECharts | null = null

function colorFor(v: number) {
  if (v >= 90) return '#ef4444'
  if (v >= 70) return '#f59e0b'
  if (v >= 50) return '#eab308'
  if (v >= 30) return '#22c55e'
  return '#1a73e8'
}

function render() {
  if (!chartRef.value) return
  if (!chart) chart = echarts.init(chartRef.value)
  chart.setOption({
    backgroundColor: 'transparent',
    title: props.title ? { text: props.title, left: 'center', textStyle: { fontSize: 13, color: '#e2e8f0' } } : undefined,
    tooltip: { formatter: (p: any) => `${p.name}: ${p.value}%` },
    grid: { left: 8, right: 8, top: props.title ? 36 : 8, bottom: 8 },
    xAxis: { show: false },
    yAxis: { show: false },
    series: [{
      type: 'custom',
      renderItem: (params: any, api: any) => {
        const idx = params.dataIndex
        const item = props.data[idx]
        const cols = Math.min(6, props.data.length)
        const rows = Math.ceil(props.data.length / cols)
        const cellW = api.size([1, 0])[0] / cols
        const cellH = api.size([0, 1])[1] / rows
        const col = idx % cols
        const row = Math.floor(idx / cols)
        const x = api.coord([col, row])[0]
        const y = api.coord([col, row])[1]
        const w = cellW * 0.85
        const h = cellH * 0.85
        return {
          type: 'group',
          children: [
            { type: 'rect', shape: { x: x - w / 2, y: y - h / 2, width: w, height: h }, style: { fill: colorFor(item.value), rx: 4 } },
            { type: 'text', shape: { x: x, y: y - 6 }, style: { text: item.name, textAlign: 'center', fill: '#fff', fontSize: 11, fontWeight: 600 } },
            { type: 'text', shape: { x: x, y: y + 10 }, style: { text: `${item.value}%`, textAlign: 'center', fill: 'rgba(255,255,255,0.7)', fontSize: 10 } },
          ],
        }
      },
      data: props.data,
    }],
  })
}

watch(() => props.data, () => nextTick(render), { deep: true })
onMounted(() => { nextTick(render); window.addEventListener('resize', () => chart?.resize()) })
onBeforeUnmount(() => { chart?.dispose(); chart = null })
</script>

<style scoped>
.monitor-heatmap { width: 100%; }
</style>