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
let themeObserver: MutationObserver | null = null

function getChartColors() {
  const styles = getComputedStyle(document.documentElement)
  return {
    primary: styles.getPropertyValue('--md3-chart-primary').trim() || '#1a73e8',
    success: styles.getPropertyValue('--md3-chart-success').trim() || '#22c55e',
    warning: styles.getPropertyValue('--md3-chart-warning').trim() || '#f59e0b',
    danger: styles.getPropertyValue('--md3-chart-danger').trim() || '#ef4444',
    gaugeBg: styles.getPropertyValue('--md3-chart-gauge-bg').trim() || '#1e293b',
    gaugeText: styles.getPropertyValue('--md3-chart-gauge-text').trim() || '#e2e8f0',
    gaugeSubtitle: styles.getPropertyValue('--md3-chart-gauge-subtitle').trim() || '#94a3b8',
  }
}

function colorFor(v: number, colors: ReturnType<typeof getChartColors>) {
  return v > 90 ? colors.danger : v > 75 ? colors.warning : colors.success
}

function render() {
  if (!chartRef.value) return
  if (!chart) chart = echarts.init(chartRef.value)
  const colors = getChartColors()
  chart.setOption({
    backgroundColor: 'transparent',
    series: [{
      type: 'gauge', center: ['50%', '60%'], radius: '90%',
      min: props.min, max: props.max, startAngle: 220, endAngle: -40,
      title: { offsetCenter: [0, '80%'], fontSize: 12, color: colors.gaugeSubtitle },
      detail: { formatter: `{value}${props.unit}`, fontSize: 18, fontWeight: 700, color: colors.gaugeText, offsetCenter: [0, '40%'] },
      axisLine: { lineStyle: { width: 12, color: [[1, colors.gaugeBg]] } },
      progress: { show: true, width: 12, itemStyle: { color: colorFor(props.value, colors) } },
      axisTick: { show: false }, splitLine: { show: false },
      axisLabel: { show: false },
      pointer: { show: false },
      data: [{ value: props.value, name: props.title }],
    }],
  })
}

function setupThemeObserver() {
  if (themeObserver) return
  themeObserver = new MutationObserver(() => render())
  themeObserver.observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] })
}

watch(() => props.value, () => nextTick(render))
onMounted(() => { nextTick(render); window.addEventListener('resize', () => chart?.resize()); setupThemeObserver() })
onBeforeUnmount(() => { chart?.dispose(); chart = null; themeObserver?.disconnect(); themeObserver = null })
</script>

<style scoped>
.monitor-gauge-chart { width: 100%; }
</style>