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
                <th v-for="col in result.columns" :key="col">{{ col }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(row, ri) in pageRows" :key="ri">
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
          </span>
          <div class="pagination" v-if="totalPages > 1">
            <Md3Button variant="text" size="sm" :disabled="currentPage <= 1" @click="currentPage--">上一页</Md3Button>
            <span class="page-info">{{ currentPage }} / {{ totalPages }}</span>
            <Md3Button variant="text" size="sm" :disabled="currentPage >= totalPages" @click="currentPage++">下一页</Md3Button>
          </div>
        </div>
      </template>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import type { MysqlQueryResult } from '@/types/db-toolkit'
import Md3Button from '@/components/Md3Button.vue'

const props = defineProps<{
  result: MysqlQueryResult | null
}>()

const pageSize = 50
const currentPage = ref(1)

const totalPages = computed(() => {
  if (!props.result) return 0
  return Math.max(1, Math.ceil(props.result.rows.length / pageSize))
})

const pageRows = computed(() => {
  if (!props.result) return []
  const start = (currentPage.value - 1) * pageSize
  return props.result.rows.slice(start, start + pageSize)
})
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
