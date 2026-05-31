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
    <div class="editor-container">
      <pre class="sql-highlight-overlay" v-html="highlightedSql"></pre>
      <textarea
        ref="textareaRef"
        v-model="sql"
        class="sql-input"
        placeholder="输入 SQL 语句... (Ctrl+Enter 执行)"
        rows="4"
        :disabled="loading"
        @keydown.ctrl.enter="handleExecute"
      />
    </div>
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
import { ref, computed } from 'vue'
import { useDbToolkitStore } from '@/stores/dbToolkitStore'
import { Md3Dialog, Md3Icon, Md3Message } from '@/components/md3'
import Md3Button from '@/components/Md3Button.vue'

const SQL_KEYWORDS = [
  'SELECT', 'FROM', 'WHERE', 'INSERT', 'INTO', 'VALUES', 'UPDATE', 'SET',
  'DELETE', 'CREATE', 'TABLE', 'ALTER', 'DROP', 'INDEX', 'SHOW', 'DESCRIBE',
  'USE', 'AND', 'OR', 'NOT', 'IN', 'LIKE', 'BETWEEN', 'JOIN', 'LEFT',
  'RIGHT', 'INNER', 'OUTER', 'ON', 'AS', 'ORDER', 'BY', 'GROUP', 'HAVING',
  'LIMIT', 'OFFSET', 'DISTINCT', 'COUNT', 'SUM', 'AVG', 'MAX', 'MIN',
  'UNION', 'ALL', 'EXISTS', 'CASE', 'WHEN', 'THEN', 'ELSE', 'END', 'NULL',
  'IS', 'PRIMARY', 'KEY', 'FOREIGN', 'REFERENCES', 'TRUNCATE', 'DATABASE',
  'SCHEMAS', 'GRANT', 'REVOKE'
]

function escapeHtml(text: string): string {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
}

const highlightedSql = computed(() => {
  const input = sql.value
  if (!input) return '\n'
  const escaped = escapeHtml(input)
  const keywordPattern = new RegExp(
    `\\b(${SQL_KEYWORDS.join('|')})\\b`,
    'gi'
  )
  let result = escaped.replace(keywordPattern, (match) => {
    return `<span class="sql-keyword">${match}</span>`
  })
  result = result.replace(
    /'([^']*?)'/g,
    '<span class="sql-string">\'$1\'</span>'
  )
  result = result.replace(
    /\b(\d+(?:\.\d+)?)\b/g,
    '<span class="sql-number">$1</span>'
  )
  result = result.replace(
    /(--[^\n]*)/g,
    '<span class="sql-comment">$1</span>'
  )
  return result
})

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
  try {
    const check = await store.checkDangerousSql(trimmed)
    if (check.is_dangerous) {
      dangerousReason.value = check.reason
      confirmVisible.value = true
      return
    }
  } catch (e: any) {
    Md3Message.error(e?.response?.data?.detail || e?.message || 'SQL 检查失败')
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

.editor-container {
  position: relative;
}

.sql-highlight-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  padding: var(--md3-space-sm);
  font-family: var(--md3-font-mono);
  font-size: 13px;
  line-height: 1.5;
  white-space: pre-wrap;
  word-wrap: break-word;
  overflow: auto;
  pointer-events: none;
  color: transparent;
  margin: 0;
  border: 1px solid transparent;
}

.sql-keyword { color: #c678dd; font-weight: 600; }
.sql-string { color: #98c379; }
.sql-number { color: #d19a66; }
.sql-comment { color: #5c6370; font-style: italic; }

.sql-input {
  width: 100%;
  font-family: var(--md3-font-mono);
  font-size: 13px;
  line-height: 1.5;
  padding: var(--md3-space-sm);
  border: 1px solid var(--md3-glass-border);
  border-radius: var(--md3-shape-xs);
  background: var(--md3-surface-container-low);
  color: transparent;
  caret-color: var(--md3-on-surface);
  resize: vertical;
  outline: none;
  position: relative;
  z-index: 1;
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
