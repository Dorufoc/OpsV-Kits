<template>
  <div class="data-editor">
    <div class="editor-toolbar">
      <span class="table-label">{{ tableName }}</span>
      <div class="toolbar-actions">
        <Md3Button variant="primary" size="sm" @click="showAddRow = true">
          <Md3Icon name="plus" size="14" />新增行
        </Md3Button>
        <Md3Button variant="danger" size="sm" :disabled="selectedRows.size === 0" @click="deleteSelectedRows">
          <Md3Icon name="delete" size="14" />删除选中 ({{ selectedRows.size }})
        </Md3Button>
        <Md3Button size="sm" @click="refreshData">
          <Md3Icon name="refresh" size="14" />刷新
        </Md3Button>
      </div>
    </div>

    <div class="data-table-container" v-if="queryResult">
      <div v-if="queryResult.error" class="data-error">{{ queryResult.error }}</div>
      <template v-else>
        <table class="data-table">
          <thead>
            <tr>
              <th class="checkbox-col">
                <Md3Checkbox :model-value="allSelected" @update:model-value="toggleSelectAll" />
              </th>
              <th v-for="col in queryResult.columns" :key="col">{{ col }}</th>
              <th class="action-col">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(row, ri) in pagedRows" :key="ri" :class="{ 'row-selected': selectedRows.has(ri) }">
              <td class="checkbox-col">
                <Md3Checkbox :model-value="selectedRows.has(ri)" @update:model-value="toggleRow(ri)" />
              </td>
              <td v-for="(cell, ci) in row" :key="ci"
                  :class="{ 'null-cell': cell === null, 'editing': editingCell?.row === ri && editingCell?.col === ci }"
                  @dblclick="startEdit(ri, ci, cell)">
                <template v-if="editingCell?.row === ri && editingCell?.col === ci">
                  <input v-model="editValue" class="cell-input"
                         @keydown.enter="confirmEdit" @keydown.escape="cancelEdit" @blur="confirmEdit" />
                </template>
                <template v-else>{{ cell === null ? 'NULL' : cell }}</template>
              </td>
              <td class="action-col">
                <Md3Button variant="text" size="sm" @click="startEditRow(ri)">
                  <Md3Icon name="pencil" size="12" />
                </Md3Button>
              </td>
            </tr>
          </tbody>
        </table>

        <div class="data-footer">
          <span class="row-info">共 {{ queryResult.total_count }} 行</span>
          <div class="pagination" v-if="totalPages > 1">
            <Md3Button variant="text" size="sm" :disabled="currentPage <= 1" @click="goPage(currentPage - 1)">上一页</Md3Button>
            <span class="page-info">{{ currentPage }} / {{ totalPages }}</span>
            <Md3Button variant="text" size="sm" :disabled="currentPage >= totalPages" @click="goPage(currentPage + 1)">下一页</Md3Button>
          </div>
        </div>
      </template>
    </div>

    <Md3Empty v-else-if="!loading" description="暂无数据" />
    <Md3Progress v-else />

    <DataRowForm
      v-if="showAddRow"
      :account-alias="accountAlias"
      :container-id="containerId"
      :table-name="tableName"
      @close="showAddRow = false"
      @inserted="onRowInserted"
    />

    <Md3Dialog :visible="editConfirmVisible" @close="editConfirmVisible = false">
      <template #header>确认修改</template>
      <div class="edit-confirm-content">
        <p>将执行以下 SQL：</p>
        <pre class="edit-sql">{{ editSql }}</pre>
      </div>
      <template #footer>
        <Md3Button variant="text" @click="editConfirmVisible = false">取消</Md3Button>
        <Md3Button variant="primary" @click="executeEdit">确认执行</Md3Button>
      </template>
    </Md3Dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick, onMounted } from 'vue'
import { useDbToolkitStore } from '@/stores/dbToolkitStore'
import type { MysqlQueryResult } from '@/types/db-toolkit'
import Md3Button from '@/components/Md3Button.vue'
import { Md3Checkbox, Md3Dialog, Md3Empty, Md3Progress, Md3Icon, Md3Confirm, Md3Message } from '@/components/md3'
import DataRowForm from '@/components/DataRowForm.vue'

const props = defineProps<{
  accountAlias: string
  containerId?: string
  tableName: string
}>()

const store = useDbToolkitStore()
const queryResult = ref<MysqlQueryResult | null>(null)
const loading = ref(false)
const selectedRows = ref<Set<number>>(new Set())
const editingCell = ref<{ row: number; col: number } | null>(null)
const editValue = ref('')
const editConfirmVisible = ref(false)
const editSql = ref('')
const showAddRow = ref(false)
const currentPage = ref(1)
const pageSize = 50

const totalPages = computed(() => {
  if (!queryResult.value) return 0
  return Math.max(1, Math.ceil(queryResult.value.total_count / pageSize))
})

const pagedRows = computed(() => {
  if (!queryResult.value) return []
  return queryResult.value.rows
})

const allSelected = computed(() => {
  return pagedRows.value.length > 0 && pagedRows.value.every((_, i) => selectedRows.value.has(i))
})

async function loadData() {
  loading.value = true
  selectedRows.value = new Set()
  editingCell.value = null
  try {
    const offset = (currentPage.value - 1) * pageSize
    const sql = `SELECT * FROM \`${props.tableName}\` LIMIT ${pageSize} OFFSET ${offset}`
    queryResult.value = await store.executeMysqlQuery(props.accountAlias, props.containerId, sql)
  } catch (e: any) {
    queryResult.value = null
    Md3Message.error(e?.response?.data?.detail || e?.message || '加载数据失败')
  } finally {
    loading.value = false
  }
}

function refreshData() {
  loadData()
}

function goPage(page: number) {
  currentPage.value = page
  loadData()
}

function startEdit(ri: number, ci: number, cell: string | null) {
  editingCell.value = { row: ri, col: ci }
  editValue.value = cell === null ? '' : String(cell)
  nextTick(() => {
    const input = document.querySelector('.cell-input') as HTMLInputElement
    input?.focus()
    input?.select()
  })
}

function confirmEdit() {
  if (!editingCell.value || !queryResult.value) return
  const { row, col } = editingCell.value
  const originalCell = pagedRows.value[row]?.[col]
  const newValue = editValue.value
  if (originalCell === newValue || (originalCell === null && newValue === '')) {
    editingCell.value = null
    return
  }
  const sql = buildUpdateSql(row, col, newValue)
  editSql.value = sql
  editConfirmVisible.value = true
  editingCell.value = null
}

function cancelEdit() {
  editingCell.value = null
}

function startEditRow(ri: number) {
  if (!queryResult.value || queryResult.value.columns.length <= 1) return
  startEdit(ri, 1, pagedRows.value[ri]?.[1] ?? null)
}

function buildUpdateSql(rowIndex: number, colIndex: number, newValue: string): string {
  const col = queryResult.value!.columns[colIndex]
  const row = pagedRows.value[rowIndex]
  const idCol = queryResult.value!.columns[0]
  const idVal = row[0]
  const val = newValue === '' ? 'NULL' : `'${newValue.replace(/'/g, "\\'")}'`
  return `UPDATE \`${props.tableName}\` SET \`${col}\` = ${val} WHERE \`${idCol}\` = '${idVal}'`
}

async function executeEdit() {
  try {
    const result = await store.executeMysqlQuery(props.accountAlias, props.containerId, editSql.value)
    if (result.error) {
      Md3Message.error(result.error)
    } else {
      Md3Message.success('修改成功')
      loadData()
    }
  } catch (e: any) {
    Md3Message.error(e?.response?.data?.detail || e?.message || '修改失败')
  } finally {
    editConfirmVisible.value = false
  }
}

async function deleteSelectedRows() {
  if (!queryResult.value || selectedRows.value.size === 0) return
  const idCol = queryResult.value.columns[0]
  const ids = Array.from(selectedRows.value)
    .map(i => pagedRows.value[i]?.[0])
    .filter(v => v !== undefined && v !== null)
  if (ids.length === 0) return
  const sql = `DELETE FROM \`${props.tableName}\` WHERE \`${idCol}\` IN (${ids.map(v => `'${v}'`).join(', ')})`

  const confirmed = await Md3Confirm.show({
    title: '删除确认',
    message: `确定要删除选中的 ${selectedRows.value.size} 行数据吗？此操作不可恢复。`,
    confirmText: '确认删除',
    cancelText: '取消',
    type: 'danger',
  })

  if (!confirmed) return

  try {
    const result = await store.executeMysqlQuery(props.accountAlias, props.containerId, sql)
    if (result.error) {
      Md3Message.error(result.error)
    } else {
      Md3Message.success('删除成功')
      loadData()
    }
  } catch (e: any) {
    Md3Message.error(e?.response?.data?.detail || e?.message || '删除失败')
  }
}

function toggleSelectAll() {
  if (allSelected.value) {
    selectedRows.value = new Set()
  } else {
    selectedRows.value = new Set(pagedRows.value.map((_, i) => i))
  }
}

function toggleRow(ri: number) {
  const newSet = new Set(selectedRows.value)
  if (newSet.has(ri)) {
    newSet.delete(ri)
  } else {
    newSet.add(ri)
  }
  selectedRows.value = newSet
}

function onRowInserted() {
  showAddRow.value = false
  loadData()
}

watch(() => props.tableName, () => {
  currentPage.value = 1
  loadData()
})

onMounted(() => {
  loadData()
})
</script>

<style scoped>
.data-editor {
  display: flex;
  flex-direction: column;
  gap: var(--md3-space-sm);
}

.editor-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--md3-space-sm) 0;
}

.table-label {
  font: var(--md3-type-title-medium);
  color: var(--md3-on-surface);
  font-weight: 600;
}

.toolbar-actions {
  display: flex;
  align-items: center;
  gap: var(--md3-space-sm);
}

.data-table-container {
  display: flex;
  flex-direction: column;
  gap: var(--md3-space-sm);
}

.data-error {
  padding: var(--md3-space-sm);
  background: rgba(244, 67, 54, 0.1);
  color: #f44336;
  border-radius: var(--md3-shape-xs);
  font-size: 13px;
  font-family: var(--md3-font-mono);
}

.data-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
  font-family: var(--md3-font-mono);
}

.data-table th {
  position: sticky;
  top: 0;
  background: var(--md3-surface-container-high);
  padding: var(--md3-space-xs) var(--md3-space-sm);
  text-align: left;
  font-weight: 600;
  color: var(--md3-on-surface);
  border-bottom: 1px solid var(--md3-glass-border);
}

.data-table td {
  padding: var(--md3-space-xs) var(--md3-space-sm);
  color: var(--md3-on-surface);
  border-bottom: 1px solid var(--md3-glass-border);
  white-space: nowrap;
  max-width: 300px;
  overflow: hidden;
  text-overflow: ellipsis;
  cursor: default;
}

.checkbox-col {
  width: 40px;
  text-align: center;
}

.action-col {
  width: 48px;
  text-align: center;
}

.null-cell {
  color: var(--md3-on-surface-variant);
  font-style: italic;
}

.editing {
  padding: 0;
  overflow: visible;
}

.cell-input {
  width: 100%;
  border: 1px solid var(--md3-primary);
  background: var(--md3-surface-container-low);
  color: var(--md3-on-surface);
  padding: var(--md3-space-xs) var(--md3-space-sm);
  font: var(--md3-type-body-small);
  font-family: var(--md3-font-mono);
  outline: none;
  box-sizing: border-box;
}

.row-selected {
  background: var(--md3-primary-container, rgba(25, 118, 210, 0.08));
}

.data-footer {
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

.edit-confirm-content {
  font: var(--md3-type-body-medium);
  color: var(--md3-on-surface-variant);
}

.edit-confirm-content p {
  margin: 0 0 var(--md3-space-sm);
}

.edit-sql {
  margin: 0;
  padding: var(--md3-space-sm);
  background: var(--md3-surface-container-low);
  border-radius: var(--md3-shape-xs);
  font-size: 12px;
  font-family: var(--md3-font-mono);
  white-space: pre-wrap;
  overflow-x: auto;
  color: var(--md3-on-surface);
}
</style>
