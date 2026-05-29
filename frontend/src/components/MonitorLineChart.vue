<template>
  <div class="monitor-line-chart" ref="chartRef" :style="{ height }"></div>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, watch, nextTick } from 'vue'
import * as echarts from 'echarts'

const props = withDefaults(defineProps<{
  data: { time: number; value: number }[]
  title?: string
  color?: string
  height?: string
  yAxisName?: string
  smooth?: boolean
  area?: boolean
}>(), {
  title: '',
  color: '#1a73e8',
  height: '200px',
  yAxisName: '',
  smooth: true,
  area: true,
})

const chartRef = ref<HTMLDivElement>()
let chart: echarts.ECharts | null = null
let themeObserver: MutationObserver | null = null

function getChartColors() {
  const styles = getComputedStyle(document.documentElement)
  return {
    primary: styles.getPropertyValue('--md3-chart-primary').trim() || '#1a73e8',
    gridLine: styles.getPropertyValue('--md3-chart-grid-line').trim() || 'rgba(0, 0, 0, 0.06)',
    axisLabel: styles.getPropertyValue('--md3-chart-axis-label').trim() || '#94a3b8',
    axisLine: styles.getPropertyValue('--md3-chart-axis-line').trim() || '#cbd5e1',
    text: styles.getPropertyValue('--md3-chart-text').trim() || '#64748b',
  }
}

function formatTime(ts: number) {
  const d = new Date(ts * 1000)
  return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}:${String(d.getSeconds()).padStart(2, '0')}`
}

function render() {
  if (!chartRef.value) return
  if (!chart) chart = echarts.init(chartRef.value)
  const colors = getChartColors()
  const lineColor = props.color || colors.primary
  const xData = props.data.map(d => formatTime(d.time))
  const yData = props.data.map(d => d.value)
  chart.setOption({
    backgroundColor: 'transparent',
    tooltip: { trigger: 'axis', formatter: (params: any) => {
      const p = params[0]
      return `${p.axisValue}<br/>${p.seriesName}: ${p.value}`
    }},
    grid: { left: 50, right: 16, top: 32, bottom: 20 },
    xAxis: { type: 'category', data: xData, axisLabel: { fontSize: 10, color: colors.axisLabel }, axisLine: { lineStyle: { color: colors.axisLine } } },
    yAxis: { type: 'value', name: props.yAxisName, nameTextStyle: { fontSize: 10, color: colors.axisLabel }, axisLabel: { fontSize: 10, color: colors.axisLabel }, splitLine: { lineStyle: { color: colors.gridLine, type: 'dashed' } } },
    series: [{
      type: 'line', data: yData, name: props.title || '', smooth: props.smooth,
      symbol: 'none', lineStyle: { width: 2, color: lineColor },
      areaStyle: props.area ? { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [{ offset: 0, color: lineColor + '40' }, { offset: 1, color: lineColor + '05' }]) } : undefined,
    }],
  })
}

function setupThemeObserver() {
  if (themeObserver) return
  themeObserver = new MutationObserver(() => render())
  themeObserver.observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] })
}

watch(() => props.data, () => nextTick(render), { deep: true })

onMounted(() => { nextTick(render); window.addEventListener('resize', () => chart?.resize()); setupThemeObserver() })
onBeforeUnmount(() => { chart?.dispose(); chart = null; themeObserver?.disconnect(); themeObserver = null })
</script>

<style scoped>
.monitor-line-chart { width: 100%; }
</style>