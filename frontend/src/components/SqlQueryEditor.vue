<template>
  <div class="sql-query-editor">
    <div class="editor-header">
      <span class="editor-label">SQL 查询</span>
      <div class="history-dropdown" v-if="store.mysqlQueryHistory.length > 0">
        <Md3Button variant="text" size="sm" @click="showHistory = !showHistory">
          <Md3Icon name="history" size="14" />历史
        </Md3Button>
        <div class="history-list" v-if="showHistory">
          <div
            v-for="(h, i) in store.mysqlQueryHistory"
            :key="i"
            class="history-item"
            @click="selectHistory(h)"
          >{{ h }}</div>
        </div>
      </div>
    </div>
    <textarea
      ref="textareaRef"
      v-model="sql"
      class="sql-input"
      placeholder="输入 SQL 语句... (Ctrl+Enter 执行)"
      rows="4"
      :disabled="loading"
      @keydown.ctrl.enter="handleExecute"
    />
    <div class="editor-actions">
      <Md3Button
        variant="primary"
        size="sm"
        :disabled="!sql.trim() || loading"
        @click="handleExecute"
      >
        {{ loading ? '执行中...' : '执行' }}
      </Md3Button>
      <span v-if="sql.length > 3800" class="length-hint">
        {{ sql.length }}/4096
      </span>
    </div>
    <Md3Dialog :visible="confirmVisible" @close="confirmVisible = false">
      <template #header>高危操作确认</template>
      <div class="confirm-content">
        <p class="confirm-reason">{{ dangerousReason }}</p>
        <p>是否继续执行？</p>
      </div>
      <template #footer>
        <Md3Button variant="text" @click="confirmVisible = false">取消</Md3Button>
        <Md3Button variant="danger" @click="confirmExecute">确认执行</Md3Button>
      </template>
    </Md3Dialog>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useDbToolkitStore } from '@/stores/dbToolkitStore'
import { Md3Dialog, Md3Icon } from '@/components/md3'
import Md3Button from '@/components/Md3Button.vue'

const props = defineProps<{
  accountAlias: string
  containerId: string
  loading: boolean
}>()

const emit = defineEmits<{
  execute: [sql: string]
}>()

const store = useDbToolkitStore()
const sql = ref('')
const showHistory = ref(false)
const confirmVisible = ref(false)
const dangerousReason = ref('')
const textareaRef = ref<HTMLTextAreaElement>()

async function handleExecute() {
  const trimmed = sql.value.trim()
  if (!trimmed) return
  const check = await store.checkDangerousSql(trimmed)
  if (check.is_dangerous) {
    dangerousReason.value = check.reason
    confirmVisible.value = true
    return
  }
  emit('execute', trimmed)
}

function confirmExecute() {
  confirmVisible.value = false
  emit('execute', sql.value.trim())
}

function selectHistory(h: string) {
  sql.value = h
  showHistory.value = false
}
</script>

<style scoped>
.sql-query-editor {
  display: flex;
  flex-direction: column;
  gap: var(--md3-space-sm);
}

.editor-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.editor-label {
  font-size: 13px;
  font-weight: 500;
  color: var(--md3-on-surface);
}

.history-dropdown {
  position: relative;
}

.history-list {
  position: absolute;
  top: 100%;
  right: 0;
  background: var(--md3-surface-container-high);
  border: 1px solid var(--md3-glass-border);
  border-radius: var(--md3-shape-xs);
  max-height: 200px;
  overflow-y: auto;
  z-index: 10;
  min-width: 300px;
}

.history-item {
  padding: var(--md3-space-xs) var(--md3-space-sm);
  font-size: 12px;
  font-family: var(--md3-font-mono);
  cursor: pointer;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.history-item:hover {
  background: var(--md3-surface-container-highest);
}

.sql-input {
  width: 100%;
  font-family: var(--md3-font-mono);
  font-size: 13px;
  padding: var(--md3-space-sm);
  border: 1px solid var(--md3-glass-border);
  border-radius: var(--md3-shape-xs);
  background: var(--md3-surface-container-low);
  color: var(--md3-on-surface);
  resize: vertical;
  outline: none;
}

.sql-input:focus {
  border-color: var(--md3-primary);
}

.editor-actions {
  display: flex;
  align-items: center;
  gap: var(--md3-space-sm);
}

.length-hint {
  font-size: 12px;
  color: var(--md3-on-surface-variant);
}

.confirm-content p {
  margin: var(--md3-space-sm) 0;
}

.confirm-reason {
  color: var(--md3-error, #f44336);
  font-weight: 500;
}
</style>
