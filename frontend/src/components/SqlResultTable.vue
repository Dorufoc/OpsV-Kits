<template>
  <div class="sql-result-table" v-if="result">
    <div v-if="result.error" class="result-error">
      {{ result.error }}
    </div>
    <template v-else>
      <div v-if="result.columns.length === 0" class="result-empty">
        查询结果为空
      </div>
      <template v-else>
        <div class="table-container">
          <table class="result-table">
            <thead>
              <tr>
                <th class="checkbox-col">
                  <Md3Checkbox :model-value="isAllSelected" :indeterminate="isPartialSelected" @update:model-value="toggleSelectAll" />
                </th>
                <th v-for="col in result.columns" :key="col" class="sortable-header" @click="toggleSort(col)">
                  {{ col }}
                  <span v-if="sortColumn === col" class="sort-indicator">
                    {{ sortDirection === 'asc' ? '↑' : '↓' }}
                  </span>
                </th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(row, ri) in pageRows" :key="ri">
                <td class="checkbox-col">
                  <Md3Checkbox :model-value="selectedRows.has(ri + (currentPage - 1) * pageSize)" @update:model-value="toggleRow(ri + (currentPage - 1) * pageSize)" />
                </td>
                <td v-for="(cell, ci) in row" :key="ci" :class="{ 'null-cell': cell === null }">
                  {{ cell === null ? 'NULL' : cell }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <div class="table-footer">
          <span class="row-info">
            共 {{ result.total_count }} 行
            <template v-if="result.truncated">（已截断，仅展示前 1000 行）</template>
            <template v-if="selectedRows.size > 0"> · 已选 {{ selectedRows.size }} 行</template>
          </span>
          <div class="footer-actions">
            <Md3Button variant="text" size="sm" @click="exportCsv" :disabled="!result?.rows?.length">
              <Md3Icon name="download" size="14" />导出 CSV
            </Md3Button>
            <div class="pagination" v-if="totalPages > 1">
              <Md3Button variant="text" size="sm" :disabled="currentPage <= 1" @click="currentPage--">上一页</Md3Button>
              <span class="page-info">{{ currentPage }} / {{ totalPages }}</span>
              <Md3Button variant="text" size="sm" :disabled="currentPage >= totalPages" @click="currentPage++">下一页</Md3Button>
            </div>
          </div>
        </div>
      </template>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import type { MysqlQueryResult } from '@/types/db-toolkit'
import Md3Button from '@/components/Md3Button.vue'
import { Md3Checkbox, Md3Icon } from '@/components/md3'

const props = defineProps<{
  result: MysqlQueryResult | null
}>()

const emit = defineEmits<{
  'selection-change': [indices: number[]]
}>()

const pageSize = 50
const currentPage = ref(1)
const sortColumn = ref<string | null>(null)
const sortDirection = ref<'asc' | 'desc'>('asc')
const selectedRows = ref<Set<number>>(new Set())

watch(() => props.result, () => {
  currentPage.value = 1
  sortColumn.value = null
  sortDirection.value = 'asc'
  selectedRows.value = new Set()
  emit('selection-change', [])
})

function toggleSort(col: string) {
  if (sortColumn.value === col) {
    sortDirection.value = sortDirection.value === 'asc' ? 'desc' : 'asc'
  } else {
    sortColumn.value = col
    sortDirection.value = 'asc'
  }
}

const sortedRows = computed(() => {
  if (!props.result || !sortColumn.value) return props.result?.rows ?? []
  const colIndex = props.result.columns.indexOf(sortColumn.value)
  if (colIndex === -1) return props.result.rows
  const sorted = [...props.result.rows].sort((a, b) => {
    const va = a[colIndex] ?? ''
    const vb = b[colIndex] ?? ''
    const cmp = String(va).localeCompare(String(vb), undefined, { numeric: true })
    return sortDirection.value === 'asc' ? cmp : -cmp
  })
  return sorted
})

const totalPages = computed(() => {
  if (!props.result) return 0
  return Math.max(1, Math.ceil(props.result.rows.length / pageSize))
})

const pageRows = computed(() => {
  if (!props.result) return []
  const start = (currentPage.value - 1) * pageSize
  return sortedRows.value.slice(start, start + pageSize)
})

const isAllSelected = computed(() => {
  if (!props.result || props.result.rows.length === 0) return false
  const start = (currentPage.value - 1) * pageSize
  const end = Math.min(start + pageSize, props.result.rows.length)
  for (let i = start; i < end; i++) {
    if (!selectedRows.value.has(i)) return false
  }
  return true
})

const isPartialSelected = computed(() => {
  if (!props.result || props.result.rows.length === 0) return false
  const start = (currentPage.value - 1) * pageSize
  const end = Math.min(start + pageSize, props.result.rows.length)
  let hasSelected = false
  let hasUnselected = false
  for (let i = start; i < end; i++) {
    if (selectedRows.value.has(i)) {
      hasSelected = true
    } else {
      hasUnselected = true
    }
    if (hasSelected && hasUnselected) return true
  }
  return false
})

function toggleSelectAll() {
  if (!props.result) return
  const start = (currentPage.value - 1) * pageSize
  const end = Math.min(start + pageSize, props.result.rows.length)
  if (isAllSelected.value) {
    const newSet = new Set(selectedRows.value)
    for (let i = start; i < end; i++) {
      newSet.delete(i)
    }
    selectedRows.value = newSet
  } else {
    const newSet = new Set(selectedRows.value)
    for (let i = start; i < end; i++) {
      newSet.add(i)
    }
    selectedRows.value = newSet
  }
  emit('selection-change', [...selectedRows.value])
}

function toggleRow(index: number) {
  const newSet = new Set(selectedRows.value)
  if (newSet.has(index)) {
    newSet.delete(index)
  } else {
    newSet.add(index)
  }
  selectedRows.value = newSet
  emit('selection-change', [...selectedRows.value])
}

function exportCsv() {
  if (!props.result) return
  const headers = props.result.columns.join(',')
  const rows = props.result.rows.map(row =>
    row.map(cell => {
      if (cell === null) return ''
      const str = String(cell)
      if (str.includes(',') || str.includes('"') || str.includes('\n')) {
        return '"' + str.replace(/"/g, '""') + '"'
      }
      return str
    }).join(',')
  )
  const csv = '\uFEFF' + headers + '\n' + rows.join('\n')
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = 'query_result.csv'
  a.click()
  URL.revokeObjectURL(url)
}
</script>

<style scoped>
.sql-result-table {
  display: flex;
  flex-direction: column;
  gap: var(--md3-space-sm);
}

.result-error {
  padding: var(--md3-space-sm);
  background: rgba(244, 67, 54, 0.1);
  color: #f44336;
  border-radius: var(--md3-shape-xs);
  font-size: 13px;
  font-family: var(--md3-font-mono);
}

.result-empty {
  padding: var(--md3-space-lg);
  text-align: center;
  color: var(--md3-on-surface-variant);
  font-size: 13px;
}

.table-container {
  overflow-x: auto;
  max-height: 400px;
  overflow-y: auto;
}

.result-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
  font-family: var(--md3-font-mono);
}

.result-table th {
  position: sticky;
  top: 0;
  background: var(--md3-surface-container-high);
  padding: var(--md3-space-xs) var(--md3-space-sm);
  text-align: left;
  font-weight: 600;
  color: var(--md3-on-surface);
  border-bottom: 1px solid var(--md3-glass-border);
}

.sortable-header {
  cursor: pointer;
  user-select: none;
  white-space: nowrap;
}

.sortable-header:hover {
  color: var(--md3-primary);
}

.sort-indicator {
  margin-left: 2px;
  font-size: 11px;
  color: var(--md3-primary);
}

.checkbox-col {
  width: 36px;
  min-width: 36px;
  text-align: center;
  padding: var(--md3-space-xs) !important;
}

.result-table td {
  padding: var(--md3-space-xs) var(--md3-space-sm);
  color: var(--md3-on-surface);
  border-bottom: 1px solid var(--md3-glass-border);
  white-space: nowrap;
  max-width: 300px;
  overflow: hidden;
  text-overflow: ellipsis;
}

.null-cell {
  color: var(--md3-on-surface-variant);
  font-style: italic;
}

.table-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-top: var(--md3-space-xs);
}

.footer-actions {
  display: flex;
  align-items: center;
  gap: var(--md3-space-sm);
}

.row-info {
  font-size: 12px;
  color: var(--md3-on-surface-variant);
}

.pagination {
  display: flex;
  align-items: center;
  gap: var(--md3-space-xs);
}

.page-info {
  font-size: 12px;
  color: var(--md3-on-surface);
}
</style>
