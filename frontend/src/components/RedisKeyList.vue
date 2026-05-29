<template>
  <div class="redis-key-list">
    <div class="search-bar">
      <Md3Input
        v-model="searchPattern"
        placeholder="Key 模式 (如 user:*)"
        @keydown.enter="handleSearch"
      />
      <Md3Button size="sm" @click="handleSearch">搜索</Md3Button>
    </div>
    <div class="key-count" v-if="keys.length > 0">
      共 {{ keys.length }} 个 Key
      <span v-if="keys.length >= 200" class="count-warn">（数量较大，建议使用搜索缩小范围）</span>
    </div>
    <div class="key-items" v-if="keys.length > 0">
      <div
        v-for="key in keys"
        :key="key"
        class="key-item"
        :class="{ active: selectedKey === key }"
        @click="selectKey(key)"
      >
        <span class="key-name">{{ key }}</span>
      </div>
    </div>
    <Md3Empty v-else-if="!loading" description="无 Key" />
    <div class="load-more" v-if="hasMore">
      <Md3Button variant="text" size="sm" @click="loadMore" :disabled="loading">
        {{ loading ? '加载中...' : '加载更多' }}
      </Md3Button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useDbToolkitStore } from '@/stores/dbToolkitStore'
import Md3Button from '@/components/Md3Button.vue'
import { Md3Input, Md3Empty } from '@/components/md3'

const props = defineProps<{
  containerId: string
  accountAlias: string
}>()

const emit = defineEmits<{
  select: [key: string]
}>()

const store = useDbToolkitStore()
const searchPattern = ref('*')
const selectedKey = ref('')
const loading = ref(false)

const keys = computed(() => store.redisScanResult?.keys ?? [])
const hasMore = computed(() => store.redisScanResult?.has_more ?? false)

async function handleSearch() {
  loading.value = true
  try {
    await store.scanRedisKeys(
      props.accountAlias, props.containerId,
      searchPattern.value, 0, 100
    )
  } finally {
    loading.value = false
  }
}

async function loadMore() {
  const cursor = store.redisScanResult?.next_cursor ?? 0
  if (cursor === 0) return
  loading.value = true
  try {
    await store.scanRedisKeys(
      props.accountAlias, props.containerId,
      searchPattern.value, cursor, 100
    )
  } finally {
    loading.value = false
  }
}

function selectKey(key: string) {
  selectedKey.value = key
  emit('select', key)
}

onMounted(() => {
  handleSearch()
})
</script>

<style scoped>
.redis-key-list {
  display: flex;
  flex-direction: column;
  gap: var(--md3-space-sm);
}

.search-bar {
  display: flex;
  gap: var(--md3-space-sm);
  align-items: center;
}

.key-count {
  font-size: 12px;
  color: var(--md3-on-surface-variant);
}

.count-warn {
  color: var(--md3-error, #f44336);
}

.key-items {
  max-height: 400px;
  overflow-y: auto;
  border: 1px solid var(--md3-glass-border);
  border-radius: var(--md3-shape-xs);
}

.key-item {
  padding: var(--md3-space-xs) var(--md3-space-sm);
  font-size: 13px;
  font-family: var(--md3-font-mono);
  cursor: pointer;
  border-bottom: 1px solid var(--md3-glass-border);
}

.key-item:last-child {
  border-bottom: none;
}

.key-item:hover {
  background: var(--md3-surface-container-high);
}

.key-item.active {
  background: var(--md3-primary-container, rgba(25, 118, 210, 0.12));
}

.load-more {
  text-align: center;
}
</style>
