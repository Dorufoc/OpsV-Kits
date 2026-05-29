<script setup lang="ts">
import { ref, computed, watch } from 'vue'

const props = defineProps<{
  modelValue: string
}>()

const emit = defineEmits<{
  'update:modelValue': [value: string]
}>()

const presets = [
  { label: '每分钟', value: '* * * * *' },
  { label: '每小时', value: '0 * * * *' },
  { label: '每天', value: '0 0 * * *' },
  { label: '每周', value: '0 0 * * 0' },
  { label: '每月', value: '0 0 1 * *' },
]

const weekLabels = ['日', '一', '二', '三', '四', '五', '六']

const sections = [
  { label: '分钟', min: 0, max: 59, cols: 6, rows: 10 },
  { label: '小时', min: 0, max: 23, cols: 6, rows: 4 },
  { label: '日', min: 1, max: 31, cols: 7, rows: 5 },
  { label: '月', min: 1, max: 12, cols: 6, rows: 2 },
  { label: '周几', min: 0, max: 6, cols: 7, rows: 1 },
]

function parseCronField(field: string, min: number, max: number): number[] {
  if (field === '*') {
    const arr: number[] = []
    for (let i = min; i <= max; i++) arr.push(i)
    return arr
  }
  const values = new Set<number>()
  const parts = field.split(',')
  for (const part of parts) {
    if (part.includes('/')) {
      const [range, stepStr] = part.split('/')
      const step = parseInt(stepStr, 10)
      let start = min
      let end = max
      if (range !== '*') {
        const [s, e] = range.split('-').map(Number)
        start = s
        end = e
      }
      for (let i = start; i <= end; i += step) {
        values.add(i)
      }
    } else if (part.includes('-')) {
      const [s, e] = part.split('-').map(Number)
      for (let i = s; i <= e; i++) {
        values.add(i)
      }
    } else if (part !== '') {
      values.add(parseInt(part, 10))
    }
  }
  return Array.from(values).sort((a, b) => a - b)
}

function buildCronField(values: number[], min: number, max: number): string {
  const total = max - min + 1
  if (values.length === total) return '*'
  if (values.length === 0) return '*'

  // Try to find contiguous ranges
  const ranges: string[] = []
  let i = 0
  while (i < values.length) {
    let j = i
    while (j + 1 < values.length && values[j + 1] === values[j] + 1) {
      j++
    }
    if (j - i >= 2) {
      ranges.push(`${values[i]}-${values[j]}`)
    } else if (j - i === 1) {
      ranges.push(String(values[i]))
      ranges.push(String(values[j]))
    } else {
      ranges.push(String(values[i]))
    }
    i = j + 1
  }
  return ranges.join(',')
}

function parseCron(expr: string): number[][] {
  const parts = expr.trim().split(/\s+/)
  if (parts.length !== 5) {
    return sections.map(s => {
      const arr: number[] = []
      for (let i = s.min; i <= s.max; i++) arr.push(i)
      return arr
    })
  }
  return parts.map((part, idx) => parseCronField(part, sections[idx].min, sections[idx].max))
}

function buildCron(selections: number[][]): string {
  return selections.map((vals, idx) => buildCronField(vals, sections[idx].min, sections[idx].max)).join(' ')
}

const selections = ref<number[][]>(parseCron(props.modelValue))
const rawExpr = ref(props.modelValue)

watch(() => props.modelValue, (val) => {
  rawExpr.value = val
  selections.value = parseCron(val)
})

watch(selections, (vals) => {
  const expr = buildCron(vals)
  rawExpr.value = expr
  emit('update:modelValue', expr)
}, { deep: true })

function toggleValue(sectionIdx: number, value: number) {
  const arr = selections.value[sectionIdx]
  const pos = arr.indexOf(value)
  if (pos >= 0) {
    arr.splice(pos, 1)
  } else {
    arr.push(value)
    arr.sort((a, b) => a - b)
  }
}

function applyPreset(value: string) {
  rawExpr.value = value
  selections.value = parseCron(value)
  emit('update:modelValue', value)
}

function onRawInput(e: Event) {
  const target = e.target as HTMLInputElement
  const val = target.value.trim()
  rawExpr.value = val
  selections.value = parseCron(val)
  emit('update:modelValue', buildCron(selections.value))
}

function describeCron(expr: string): string {
  const parts = expr.trim().split(/\s+/)
  if (parts.length !== 5) return '无效的 Cron 表达式'

  const [min, hour, day, month, week] = parts

  if (expr === '* * * * *') return '每分钟执行'
  if (expr === '0 * * * *') return '每小时的第0分钟执行'
  if (expr === '0 0 * * *') return '每天凌晨0点执行'
  if (expr === '0 0 * * 0') return '每周日凌晨0点执行'
  if (expr === '0 0 1 * *') return '每月1日凌晨0点执行'

  let desc = ''

  if (month !== '*') {
    desc += `${month}月 `
  }
  if (day !== '*') {
    desc += `${day}日 `
  }
  if (week !== '*') {
    const weekVals = parseCronField(week, 0, 6)
    const weekNames = weekVals.map(v => `周${weekLabels[v]}`)
    desc += `${weekNames.join('、')} `
  }

  if (hour === '*' && min === '*') {
    desc += '每小时每分钟'
  } else if (hour === '*') {
    desc += `每小时的第${min}分钟`
  } else if (min === '*') {
    desc += `${hour}点的每分钟`
  } else {
    desc += `${hour}点${min}分`
  }

  desc += '执行'
  return desc
}

const description = computed(() => describeCron(rawExpr.value))
</script>

<template>
  <div class="cron-picker">
    <div class="presets">
      <button
        v-for="preset in presets"
        :key="preset.value"
        class="preset-btn"
        :class="{ active: rawExpr === preset.value }"
        @click="applyPreset(preset.value)"
      >
        {{ preset.label }}
      </button>
    </div>

    <div class="sections">
      <div
        v-for="(section, sIdx) in sections"
        :key="section.label"
        class="section"
      >
        <div class="section-label">{{ section.label }}</div>
        <div
          class="grid"
          :style="{
            gridTemplateColumns: `repeat(${section.cols}, 1fr)`,
            gridTemplateRows: `repeat(${section.rows}, 1fr)`
          }"
        >
          <button
            v-for="val in (section.max - section.min + 1)"
            :key="val"
            class="value-btn"
            :class="{ selected: selections[sIdx].includes(section.min + val - 1) }"
            @click="toggleValue(sIdx, section.min + val - 1)"
          >
            {{ sIdx === 4 ? weekLabels[section.min + val - 1] : section.min + val - 1 }}
          </button>
        </div>
      </div>
    </div>

    <div class="bottom">
      <input
        class="raw-input"
        :value="rawExpr"
        @input="onRawInput"
        placeholder="* * * * *"
      />
      <div class="description">{{ description }}</div>
    </div>
  </div>
</template>

<style scoped>
.cron-picker {
  --md3-primary: #6750a4;
  --md3-on-primary: #ffffff;
  --md3-surface-container: #f3edf7;
  --md3-on-surface: #1d1b20;
  --md3-on-surface-variant: #49454f;
  --md3-outline: #79747e;
  --md3-shape-sm: 8px;

  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 16px;
  color: var(--md3-on-surface);
  font-size: 14px;
  max-width: 480px;
}

.presets {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.preset-btn {
  padding: 6px 14px;
  border: 1px solid var(--md3-outline);
  border-radius: var(--md3-shape-sm);
  background: transparent;
  color: var(--md3-on-surface);
  cursor: pointer;
  font-size: 13px;
  transition: background 0.15s, color 0.15s, border-color 0.15s;
}

.preset-btn:hover {
  background: var(--md3-surface-container);
}

.preset-btn.active {
  background: var(--md3-primary);
  color: var(--md3-on-primary);
  border-color: var(--md3-primary);
}

.sections {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.section {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.section-label {
  font-weight: 600;
  font-size: 13px;
  color: var(--md3-on-surface-variant);
}

.grid {
  display: grid;
  gap: 4px;
}

.value-btn {
  padding: 4px 0;
  border: 1px solid var(--md3-outline);
  border-radius: var(--md3-shape-sm);
  background: transparent;
  color: var(--md3-on-surface);
  cursor: pointer;
  font-size: 12px;
  min-width: 28px;
  transition: background 0.15s, color 0.15s, border-color 0.15s;
}

.value-btn:hover {
  background: var(--md3-surface-container);
}

.value-btn.selected {
  background: var(--md3-primary);
  color: var(--md3-on-primary);
  border-color: var(--md3-primary);
}

.bottom {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-top: 4px;
}

.raw-input {
  padding: 8px 12px;
  border: 1px solid var(--md3-outline);
  border-radius: var(--md3-shape-sm);
  background: transparent;
  color: var(--md3-on-surface);
  font-size: 14px;
  font-family: monospace;
  outline: none;
}

.raw-input:focus {
  border-color: var(--md3-primary);
}

.description {
  font-size: 13px;
  color: var(--md3-on-surface-variant);
  min-height: 18px;
}
</style>
