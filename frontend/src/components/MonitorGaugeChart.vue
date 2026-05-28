<template>
  <div class="monitor-gauge-chart" ref="chartRef" :style="{ height }"></div>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, watch, nextTick } from 'vue'
import * as echarts from 'echarts'

const props = withDefaults(defineProps<{
  value: number
  title?: string
  unit?: string
  height?: string
  min?: number
  max?: number
}>(), {
  value: 0, title: '', unit: '%', height: '180px', min: 0, max: 100,
})

const chartRef = ref<HTMLDivElement>()
let chart: echarts.ECharts | null = null

function colorFor(v: number) { return v > 90 ? '#ef4444' : v > 75 ? '#f59e0b' : '#22c55e' }

function render() {
  if (!chartRef.value) return
  if (!chart) chart = echarts.init(chartRef.value)
  chart.setOption({
    backgroundColor: 'transparent',
    series: [{
      type: 'gauge', center: ['50%', '60%'], radius: '90%',
      min: props.min, max: props.max, startAngle: 220, endAngle: -40,
      title: { offsetCenter: [0, '80%'], fontSize: 12, color: '#94a3b8' },
      detail: { formatter: `{value}${props.unit}`, fontSize: 18, fontWeight: 700, color: '#e2e8f0', offsetCenter: [0, '40%'] },
      axisLine: { lineStyle: { width: 12, color: [[1, '#1e293b']] } },
      progress: { show: true, width: 12, itemStyle: { color: colorFor(props.value) } },
      axisTick: { show: false }, splitLine: { show: false },
      axisLabel: { show: false },
      pointer: { show: false },
      data: [{ value: props.value, name: props.title }],
    }],
  })
}

watch(() => props.value, () => nextTick(render))
onMounted(() => { nextTick(render); window.addEventListener('resize', () => chart?.resize()) })
onBeforeUnmount(() => { chart?.dispose(); chart = null })
</script>

<style scoped>
.monitor-gauge-chart { width: 100%; }
</style>