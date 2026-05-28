<template>
  <div class="monitor-pie-chart" ref="chartRef" :style="{ height }"></div>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, watch, nextTick } from 'vue'
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

const colors = ['#1a73e8', '#22c55e', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4', '#ec4899', '#14b8a6']

function render() {
  if (!chartRef.value) return
  if (!chart) chart = echarts.init(chartRef.value)
  chart.setOption({
    backgroundColor: 'transparent',
    tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
    color: colors,
    series: [{
      type: 'pie',
      radius: props.donut ? ['35%', '65%'] : '70%',
      center: ['50%', '55%'],
      roseType: props.roseType ? 'radius' : undefined,
      itemStyle: { borderRadius: 4, borderColor: '#0f172a', borderWidth: 2 },
      label: { color: '#94a3b8', fontSize: 11, formatter: '{b}\n{d}%' },
      labelLine: { lineStyle: { color: '#334155' } },
      data: props.data,
    }],
  })
}

watch(() => props.data, () => nextTick(render), { deep: true })
onMounted(() => { nextTick(render); window.addEventListener('resize', () => chart?.resize()) })
onBeforeUnmount(() => { chart?.dispose(); chart = null })
</script>

<style scoped>
.monitor-pie-chart { width: 100%; }
</style>