<template>
  <div class="monitor-pie-chart" ref="chartRef" :style="{ height }"></div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount, watch, nextTick } from 'vue'
import * as echarts from 'echarts'

const props = withDefaults(defineProps<{
  data: { name: string; value: number }[]
  title?: string
  height?: string
  roseType?: boolean
  donut?: boolean
}>(), {
  data: () => [], title: '', height: '240px', roseType: false, donut: true,
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
    info: styles.getPropertyValue('--md3-chart-info').trim() || '#8b5cf6',
    text: styles.getPropertyValue('--md3-chart-text').trim() || '#94a3b8',
    pieBorder: styles.getPropertyValue('--md3-chart-pie-border').trim() || '#0f172a',
    pieLabelLine: styles.getPropertyValue('--md3-chart-axis-line').trim() || '#334155',
  }
}

const colors = computed(() => {
  const c = getChartColors()
  return [c.primary, c.success, c.warning, c.danger, c.info, '#06b6d4', '#ec4899', '#14b8a6']
})

function render() {
  if (!chartRef.value) return
  if (!chart) chart = echarts.init(chartRef.value)
  const c = getChartColors()
  chart.setOption({
    backgroundColor: 'transparent',
    tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
    color: colors.value,
    series: [{
      type: 'pie',
      radius: props.donut ? ['35%', '65%'] : '70%',
      center: ['50%', '55%'],
      roseType: props.roseType ? 'radius' : undefined,
      itemStyle: { borderRadius: 4, borderColor: c.pieBorder, borderWidth: 2 },
      label: { color: c.text, fontSize: 11, formatter: '{b}\n{d}%' },
      labelLine: { lineStyle: { color: c.pieLabelLine } },
      data: props.data,
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
.monitor-pie-chart { width: 100%; }
</style>