<template>
  <div class="redis-key-detail" v-if="keyInfo">
    <div class="detail-header">
      <span class="key-name">{{ keyInfo.key }}</span>
      <Md3Tag size="sm" :type="typeTagColor">{{ keyInfo.type }}</Md3Tag>
      <span class="ttl">TTL: {{ keyInfo.ttl_display }}</span>
    </div>
    <div class="value-section">
      <div class="section-title">Value</div>
      <template v-if="keyInfo.type === 'string'">
        <pre class="value-text">{{ keyInfo.value }}</pre>
      </template>
      <template v-else-if="keyInfo.type === 'hash'">
        <table class="kv-table">
          <thead><tr><th>Field</th><th>Value</th></tr></thead>
          <tbody>
            <tr v-for="(v, k) in (keyInfo.value as Record<string, string>)" :key="k">
              <td>{{ k }}</td><td>{{ v }}</td>
            </tr>
          </tbody>
        </table>
      </template>
      <template v-else-if="keyInfo.type === 'list'">
        <ol class="value-list">
          <li v-for="(item, i) in (keyInfo.value as string[])" :key="i">{{ item }}</li>
        </ol>
      </template>
      <template v-else-if="keyInfo.type === 'set'">
        <div class="value-set">
          <Md3Tag v-for="(item, i) in (keyInfo.value as string[])" :key="i" size="sm">{{ item }}</Md3Tag>
        </div>
      </template>
      <template v-else-if="keyInfo.type === 'zset'">
        <table class="kv-table">
          <thead><tr><th>Score</th><th>Member</th></tr></thead>
          <tbody>
            <tr v-for="(item, i) in (keyInfo.value as Array<{member: string; score: string}>)" :key="i">
              <td>{{ item.score }}</td><td>{{ item.member }}</td>
            </tr>
          </tbody>
        </table>
      </template>
      <template v-else>
        <pre class="value-text">{{ keyInfo.value }}</pre>
      </template>
      <div class="truncation-hint" v-if="keyInfo.truncated">
        内容过长，已截断展示
      </div>
    </div>
    <div class="detail-actions">
      <Md3Button variant="danger" size="sm" @click="handleDelete">删除 Key</Md3Button>
    </div>
    <Md3Dialog :visible="deleteConfirmVisible" @close="deleteConfirmVisible = false">
      <template #header>确认删除</template>
      <p>确定要删除 Key "{{ keyInfo.key }}" 吗？此操作不可恢复。</p>
      <template #footer>
        <Md3Button variant="text" @click="deleteConfirmVisible = false">取消</Md3Button>
        <Md3Button variant="danger" @click="confirmDelete">确认删除</Md3Button>
      </template>
    </Md3Dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import type { RedisKeyInfo } from '@/types/db-toolkit'
import { useDbToolkitStore } from '@/stores/dbToolkitStore'
import Md3Button from '@/components/Md3Button.vue'
import { Md3Tag, Md3Dialog } from '@/components/md3'

const props = defineProps<{
  keyInfo: RedisKeyInfo | null
  containerId: string
  accountAlias: string
}>()

const emit = defineEmits<{
  deleted: []
}>()

const store = useDbToolkitStore()
const deleteConfirmVisible = ref(false)

const typeTagColor = computed<'primary' | 'success' | 'warning' | 'danger' | 'info'>(() => {
  if (!props.keyInfo) return 'info'
  const map: Record<string, 'primary' | 'success' | 'warning' | 'danger' | 'info'> = {
    string: 'success',
    hash: 'warning',
    list: 'info',
    set: 'info',
    zset: 'info',
    stream: 'info',
  }
  return map[props.keyInfo.type] || 'info'
})

function handleDelete() {
  deleteConfirmVisible.value = true
}

async function confirmDelete() {
  if (!props.keyInfo) return
  deleteConfirmVisible.value = false
  try {
    await store.deleteRedisKey(props.accountAlias, props.containerId, props.keyInfo.key)
    emit('deleted')
  } catch {
  }
}
</script>

<style scoped>
.redis-key-detail {
  display: flex;
  flex-direction: column;
  gap: var(--md3-space-md);
}

.detail-header {
  display: flex;
  align-items: center;
  gap: var(--md3-space-sm);
}

.key-name {
  font-family: var(--md3-font-mono);
  font-size: 14px;
  font-weight: 500;
}

.ttl {
  font-size: 12px;
  color: var(--md3-on-surface-variant);
}

.section-title {
  font-size: 13px;
  font-weight: 600;
  margin-bottom: var(--md3-space-xs);
}

.value-text {
  padding: var(--md3-space-sm);
  background: var(--md3-surface-container-low);
  border-radius: var(--md3-shape-xs);
  font-size: 12px;
  font-family: var(--md3-font-mono);
  white-space: pre-wrap;
  max-height: 300px;
  overflow-y: auto;
}

.kv-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
  font-family: var(--md3-font-mono);
}

.kv-table th, .kv-table td {
  padding: var(--md3-space-xs) var(--md3-space-sm);
  border-bottom: 1px solid var(--md3-glass-border);
  text-align: left;
}

.kv-table th {
  background: var(--md3-surface-container-low);
  font-weight: 600;
}

.value-list {
  padding-left: var(--md3-space-lg);
  font-size: 12px;
  font-family: var(--md3-font-mono);
}

.value-set {
  display: flex;
  flex-wrap: wrap;
  gap: var(--md3-space-xs);
}

.truncation-hint {
  font-size: 12px;
  color: var(--md3-on-surface-variant);
  font-style: italic;
}

.detail-actions {
  margin-top: var(--md3-space-sm);
}
</style>
