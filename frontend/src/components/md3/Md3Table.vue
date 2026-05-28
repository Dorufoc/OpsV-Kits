<template>
  <div class="md3-table-wrapper">
    <div class="md3-table-container" :class="{ 'md3-table--border': border }">
      <table class="md3-table" :class="{ 'md3-table--stripe': stripe, 'md3-table--hover': hover }">
        <thead>
          <tr>
            <th v-if="selection" class="md3-table-cell md3-table-cell--selection">
              <input
                type="checkbox"
                :checked="isAllSelected"
                class="md3-table-select-all"
                @change="toggleSelectAll"
              />
            </th>
            <th
              v-for="col in columns"
              :key="col.prop"
              class="md3-table-cell md3-table-header"
              :style="col.width ? { width: col.width, minWidth: col.width } : {}"
            >
              {{ col.label }}
            </th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="(row, idx) in pageData"
            :key="idx"
            class="md3-table-row"
            :class="{
              'md3-table-row--selected': isRowSelected(row),
            }"
          >
            <td v-if="selection" class="md3-table-cell md3-table-cell--selection">
              <input
                type="checkbox"
                :checked="isRowSelected(row)"
                class="md3-table-select"
                @change="toggleRowSelection(row)"
              />
            </td>
            <td
              v-for="col in columns"
              :key="col.prop"
              class="md3-table-cell md3-table-body"
            >
              <slot
                :name="col.prop"
                :row="row"
                :column="col"
                :index="idx"
                :value="row[col.prop]"
              >
                {{ row[col.prop] }}
              </slot>
            </td>
          </tr>
          <tr v-if="pageData.length === 0">
            <td :colspan="selection ? columns.length + 1 : columns.length" class="md3-table-empty">
              {{ emptyText }}
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    <div v-if="pagination && data.length > pageSize" class="md3-table-pagination">
      <button
        class="md3-table-pagination-btn"
        :disabled="currentPage === 1"
        @click="currentPage--"
      >
        ‹
      </button>
      <span class="md3-table-pagination-info">
        {{ (currentPage - 1) * pageSize + 1 }}-{{ Math.min(currentPage * pageSize, data.length) }} / {{ data.length }}
      </span>
      <button
        class="md3-table-pagination-btn"
        :disabled="currentPage >= totalPages"
        @click="currentPage++"
      >
        ›
      </button>
      <select
        v-model="pageSize"
        class="md3-table-page-size"
        @change="currentPage = 1"
      >
        <option v-for="size in pageSizes" :key="size" :value="size">{{ size }} / page</option>
      </select>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'

interface Column {
  prop: string
  label: string
  width?: string
}

const props = withDefaults(defineProps<{
  columns: Column[]
  data: Record<string, unknown>[]
  stripe?: boolean
  border?: boolean
  hover?: boolean
  selection?: boolean
  pagination?: boolean
  pageSize?: number
  pageSizes?: number[]
  emptyText?: string
}>(), {
  stripe: false,
  border: false,
  hover: true,
  selection: false,
  pagination: false,
  pageSize: 10,
  pageSizes: () => [10, 20, 50, 100],
  emptyText: 'No data available',
})

const emit = defineEmits<{
  'selection-change': [rows: Record<string, unknown>[]]
}>()

const currentPage = ref(1)
const pageSize = ref(props.pageSize)
const selectedRows = ref<Record<string, unknown>[]>([])

const totalPages = computed(() => Math.ceil(props.data.length / pageSize.value))

const pageData = computed(() => {
  if (!props.pagination) return props.data
  const start = (currentPage.value - 1) * pageSize.value
  return props.data.slice(start, start + pageSize.value)
})

const isAllSelected = computed(() => {
  return pageData.value.length > 0 && pageData.value.every(row => isRowSelected(row))
})

function isRowSelected(row: Record<string, unknown>): boolean {
  return selectedRows.value.includes(row)
}

function toggleRowSelection(row: Record<string, unknown>) {
  const idx = selectedRows.value.indexOf(row)
  if (idx === -1) {
    selectedRows.value.push(row)
  } else {
    selectedRows.value.splice(idx, 1)
  }
  emit('selection-change', selectedRows.value)
}

function toggleSelectAll() {
  if (isAllSelected.value) {
    selectedRows.value = []
  } else {
    selectedRows.value = [...pageData.value]
  }
  emit('selection-change', selectedRows.value)
}
</script>

<style scoped>
.md3-table-wrapper {
  width: 100%;
  overflow-x: auto;
}

.md3-table-container {
  border-radius: var(--md3-shape-md);
  overflow: hidden;
}

.md3-table--border {
  border: 1px solid var(--md3-outline-variant);
}

.md3-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.875rem;
  line-height: 1.25rem;
}

/* ===== Header ===== */
.md3-table-header {
  font-weight: 500;
  color: var(--md3-on-surface-variant);
  text-align: left;
  padding: var(--md3-space-md) var(--md3-space-lg);
  border-bottom: 1px solid var(--md3-outline-variant);
  white-space: nowrap;
  background: var(--md3-surface-container);
}

/* ===== Body ===== */
.md3-table-body {
  padding: var(--md3-space-md) var(--md3-space-lg);
  color: var(--md3-on-surface);
  border-bottom: 1px solid var(--md3-outline-variant);
}

/* ===== Row ===== */
.md3-table-row {
  transition: background-color var(--md3-motion-duration-short) var(--md3-motion-easing-standard);
}

.md3-table--hover .md3-table-row:hover {
  background: var(--md3-surface-container-low);
}

.md3-table--stripe .md3-table-row:nth-child(even) {
  background: var(--md3-surface-container);
}

.md3-table-row--selected {
  background: var(--md3-primary-container) !important;
}

/* ===== Selection ===== */
.md3-table-cell--selection {
  width: 40px;
  text-align: center;
}

.md3-table-select,
.md3-table-select-all {
  cursor: pointer;
  width: 16px;
  height: 16px;
  accent-color: var(--md3-primary);
}

/* ===== Empty ===== */
.md3-table-empty {
  text-align: center;
  padding: var(--md3-space-3xl) var(--md3-space-lg);
  color: var(--md3-on-surface-variant);
  opacity: 0.7;
}

/* ===== Pagination ===== */
.md3-table-pagination {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: var(--md3-space-sm);
  padding: var(--md3-space-md) 0;
}

.md3-table-pagination-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border: 1px solid var(--md3-outline-variant);
  background: var(--md3-surface);
  color: var(--md3-on-surface);
  cursor: pointer;
  border-radius: var(--md3-shape-full);
  font-size: 1rem;
  transition: background-color var(--md3-motion-duration-short) var(--md3-motion-easing-standard);
}

.md3-table-pagination-btn:hover:not(:disabled) {
  background: var(--md3-surface-container-high);
}

.md3-table-pagination-btn:disabled {
  opacity: 0.38;
  cursor: not-allowed;
}

.md3-table-pagination-info {
  font-size: 0.75rem;
  color: var(--md3-on-surface-variant);
}

.md3-table-page-size {
  border: 1px solid var(--md3-outline-variant);
  background: var(--md3-surface);
  color: var(--md3-on-surface);
  padding: 4px 8px;
  border-radius: var(--md3-shape-xs);
  font-size: 0.75rem;
  outline: none;
}

.md3-table-page-size:focus {
  border-color: var(--md3-primary);
}
</style>
