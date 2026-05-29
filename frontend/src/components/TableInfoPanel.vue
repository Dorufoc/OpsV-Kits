<template>
  <div class="table-info-panel">
    <div class="panel-left">
      <div class="table-list-header">数据表</div>
      <div class="table-list" v-if="tables.length > 0">
        <div
          v-for="t in tables"
          :key="t"
          class="table-item"
          :class="{ active: selectedTable === t }"
          @click="selectTable(t)"
        >{{ t }}</div>
      </div>
      <Md3Empty v-else description="无数据表" />
    </div>
    <div class="panel-right">
      <template v-if="currentStructure">
        <div class="structure-section">
          <div class="section-title">列定义</div>
          <table class="info-table">
            <thead>
              <tr>
                <th>Field</th><th>Type</th><th>Null</th><th>Key</th><th>Default</th><th>Extra</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="col in currentStructure.columns" :key="col.field">
                <td>{{ col.field }}</td><td>{{ col.type }}</td>
                <td>{{ col.null }}</td><td>{{ col.key }}</td>
                <td>{{ col.default ?? 'NULL' }}</td><td>{{ col.extra }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <div class="structure-section" v-if="currentStructure.indexes.length > 0">
          <div class="section-title">索引</div>
          <table class="info-table">
            <thead>
              <tr><th>Name</th><th>Column</th><th>Unique</th></tr>
            </thead>
            <tbody>
              <tr v-for="idx in currentStructure.indexes" :key="idx.name">
                <td>{{ idx.name }}</td><td>{{ idx.column }}</td>
                <td>{{ idx.unique ? 'Yes' : 'No' }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <div class="structure-meta">
          <span>行数: {{ currentStructure.row_count }}</span>
          <Md3Button variant="text" size="sm" @click="showDdl = !showDdl">
            {{ showDdl ? '隐藏' : '查看' }}建表语句
          </Md3Button>
        </div>
        <pre class="ddl-block" v-if="showDdl">{{ currentStructure.create_ddl }}</pre>
      </template>
      <Md3Empty v-else description="选择左侧表名查看结构" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useDbToolkitStore } from '@/stores/dbToolkitStore'
import type { MysqlTableStructure } from '@/types/db-toolkit'
import Md3Button from '@/components/Md3Button.vue'
import { Md3Empty } from '@/components/md3'

const props = defineProps<{
  containerId: string
  accountAlias: string
}>()

const store = useDbToolkitStore()
const tables = ref<string[]>([])
const selectedTable = ref('')
const currentStructure = ref<MysqlTableStructure | null>(null)
const showDdl = ref(false)
const loading = ref(false)

async function loadTables() {
  try {
    tables.value = await store.loadMysqlTables(props.accountAlias, props.containerId)
  } catch {
    tables.value = []
  }
}

async function selectTable(name: string) {
  selectedTable.value = name
  showDdl.value = false
  loading.value = true
  try {
    currentStructure.value = await store.loadMysqlTableStructure(
      props.accountAlias, props.containerId, name
    )
  } catch {
    currentStructure.value = null
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadTables()
})
</script>

<style scoped>
.table-info-panel {
  display: flex;
  gap: var(--md3-space-md);
  min-height: 300px;
}

.panel-left {
  width: 200px;
  flex-shrink: 0;
  border: 1px solid var(--md3-glass-border);
  border-radius: var(--md3-shape-xs);
  overflow-y: auto;
}

.table-list-header {
  padding: var(--md3-space-sm);
  font-weight: 600;
  font-size: 13px;
  border-bottom: 1px solid var(--md3-glass-border);
}

.table-item {
  padding: var(--md3-space-xs) var(--md3-space-sm);
  font-size: 13px;
  cursor: pointer;
}

.table-item:hover {
  background: var(--md3-surface-container-high);
}

.table-item.active {
  background: var(--md3-primary-container, rgba(25, 118, 210, 0.12));
  color: var(--md3-primary);
  font-weight: 500;
}

.panel-right {
  flex: 1;
  overflow-y: auto;
}

.structure-section {
  margin-bottom: var(--md3-space-md);
}

.section-title {
  font-size: 13px;
  font-weight: 600;
  margin-bottom: var(--md3-space-xs);
}

.info-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
  font-family: var(--md3-font-mono);
}

.info-table th, .info-table td {
  padding: var(--md3-space-xs) var(--md3-space-sm);
  border-bottom: 1px solid var(--md3-glass-border);
  text-align: left;
}

.info-table th {
  background: var(--md3-surface-container-low);
  font-weight: 600;
}

.structure-meta {
  display: flex;
  align-items: center;
  gap: var(--md3-space-md);
  font-size: 13px;
  color: var(--md3-on-surface-variant);
}

.ddl-block {
  margin-top: var(--md3-space-sm);
  padding: var(--md3-space-sm);
  background: var(--md3-surface-container-low);
  border-radius: var(--md3-shape-xs);
  font-size: 12px;
  font-family: var(--md3-font-mono);
  white-space: pre-wrap;
  overflow-x: auto;
}
</style>
