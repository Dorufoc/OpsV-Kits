<template>
  <Md3Dialog :visible="true" @close="emit('close')" class="data-row-form">
    <template #header>新增行 - {{ tableName }}</template>
    <div class="form-body">
      <div v-for="col in tableStructure?.columns" :key="col.field" class="form-field">
        <label class="field-label">
          {{ col.field }}
          <Md3Tag v-if="col.key === 'PRI'" size="sm" type="primary">PK</Md3Tag>
          <span class="field-type">{{ col.type }}</span>
        </label>
        <Md3Input
          v-model="formData[col.field]"
          :placeholder="col.null === 'YES' ? 'NULL' : '必填'"
          :disabled="col.extra.includes('auto_increment')"
        />
      </div>
    </div>
    <template #footer>
      <Md3Button variant="text" @click="emit('close')">取消</Md3Button>
      <Md3Button variant="primary" @click="handleInsert" :disabled="inserting">
        {{ inserting ? '插入中...' : '插入' }}
      </Md3Button>
    </template>
  </Md3Dialog>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useDbToolkitStore } from '@/stores/dbToolkitStore'
import type { MysqlTableStructure } from '@/types/db-toolkit'
import Md3Button from '@/components/Md3Button.vue'
import { Md3Dialog, Md3Input, Md3Tag, Md3Message } from '@/components/md3'

const props = defineProps<{
  accountAlias: string
  containerId?: string
  tableName: string
}>()

const emit = defineEmits<{
  close: []
  inserted: []
}>()

const store = useDbToolkitStore()
const tableStructure = ref<MysqlTableStructure | null>(null)
const formData = reactive<Record<string, string>>({})
const inserting = ref(false)

async function loadStructure() {
  try {
    tableStructure.value = await store.loadMysqlTableStructure(
      props.accountAlias, props.containerId, props.tableName
    )
  } catch (e: any) {
    tableStructure.value = null
    Md3Message.error(e?.response?.data?.detail || e?.message || '加载表结构失败')
  }
}

function buildInsertSql(): string {
  const cols = tableStructure.value?.columns.filter(c => !c.extra.includes('auto_increment')) ?? []
  const colNames = cols.map(c => `\`${c.field}\``).join(', ')
  const values = cols.map(c => {
    const val = formData[c.field]
    if (!val) return 'NULL'
    return `'${val.replace(/'/g, "\\'")}'`
  }).join(', ')
  return `INSERT INTO \`${props.tableName}\` (${colNames}) VALUES (${values})`
}

async function handleInsert() {
  const sql = buildInsertSql()
  inserting.value = true
  try {
    const result = await store.executeMysqlQuery(props.accountAlias, props.containerId, sql)
    if (result.error) {
      Md3Message.error(result.error)
    } else {
      Md3Message.success('插入成功')
      emit('inserted')
    }
  } catch (e: any) {
    Md3Message.error(e?.response?.data?.detail || e?.message || '插入失败')
  } finally {
    inserting.value = false
  }
}

onMounted(() => {
  loadStructure()
})
</script>

<style scoped>
.data-row-form :deep(.md3-dialog) {
  width: 560px;
}

.form-body {
  display: flex;
  flex-direction: column;
  gap: var(--md3-space-md);
  max-height: 60vh;
  overflow-y: auto;
}

.form-field {
  display: flex;
  flex-direction: column;
  gap: var(--md3-space-xs);
}

.field-label {
  display: flex;
  align-items: center;
  gap: var(--md3-space-xs);
  font: var(--md3-type-label-medium);
  color: var(--md3-on-surface);
}

.field-type {
  font: var(--md3-type-body-small);
  color: var(--md3-on-surface-variant);
}
</style>
