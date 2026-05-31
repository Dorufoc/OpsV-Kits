<template>
  <div class="db-sidebar">
    <div class="sidebar-header">
      <div class="connection-info">
        <Md3Icon :name="deployModeIcon" size="16" />
        <span class="connection-name">{{ store.activeConnection?.name }}</span>
      </div>
      <Md3Button variant="text" size="sm" @click="emit('disconnect')">
        <Md3Icon name="logout" size="14" />
      </Md3Button>
    </div>

    <template v-if="dbType === 'mysql'">
      <div class="sidebar-section">
        <div class="section-header" @click="databasesExpanded = !databasesExpanded">
          <Md3Icon :name="databasesExpanded ? 'chevron-down' : 'chevron-right'" size="14" />
          <span>数据库</span>
          <Md3Button variant="text" size="sm" @click.stop="refreshDatabases">
            <Md3Icon name="refresh" size="12" />
          </Md3Button>
        </div>
        <div v-show="databasesExpanded" class="section-content">
          <div
            v-for="db in databases"
            :key="db"
            class="tree-item database-item"
            :class="{ active: currentDatabase === db }"
            @click="selectDatabase(db)"
          >
            <Md3Icon name="database" size="14" />
            <span>{{ db }}</span>
          </div>
        </div>
      </div>

      <div class="sidebar-section" v-if="currentDatabase">
        <div class="section-header" @click="tablesExpanded = !tablesExpanded">
          <Md3Icon :name="tablesExpanded ? 'chevron-down' : 'chevron-right'" size="14" />
          <span>数据表 ({{ tables.length }})</span>
          <Md3Button variant="text" size="sm" @click.stop="refreshTables">
            <Md3Icon name="refresh" size="12" />
          </Md3Button>
        </div>
        <div v-show="tablesExpanded" class="section-content">
          <Md3Input v-model="tableFilter" placeholder="搜索表名..." class="table-filter" />
          <div
            v-for="t in filteredTables"
            :key="t"
            class="tree-item table-item"
            :class="{ active: selectedTable === t }"
            @click="selectTable(t)"
          >
            <Md3Icon name="table" size="14" />
            <span>{{ t }}</span>
          </div>
        </div>
      </div>
    </template>

    <template v-else>
      <div class="sidebar-section">
        <div class="section-header">
          <Md3Icon name="chevron-down" size="14" />
          <span>Redis 数据库</span>
        </div>
        <div class="section-content">
          <div
            v-for="i in 16"
            :key="i - 1"
            class="tree-item redis-db-item"
            :class="{ active: currentRedisDb === i - 1 }"
            @click="selectRedisDb(i - 1)"
          >
            <Md3Icon name="storage" size="14" />
            <span>DB{{ i - 1 }}</span>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useDbToolkitStore } from '@/stores/dbToolkitStore'
import type { DbType } from '@/types/db-toolkit'
import Md3Button from '@/components/Md3Button.vue'
import { Md3Icon, Md3Input, Md3Message } from '@/components/md3'

const props = defineProps<{
  dbType: DbType
  accountAlias: string
  containerId?: string
}>()

const emit = defineEmits<{
  selectTable: [tableName: string]
  selectDatabase: [dbName: string]
  selectRedisDb: [dbIndex: number]
  disconnect: []
}>()

const store = useDbToolkitStore()

const databases = ref<string[]>([])
const currentDatabase = ref('')
const selectedTable = ref('')
const currentRedisDb = ref(0)
const databasesExpanded = ref(true)
const tablesExpanded = ref(true)
const tableFilter = ref('')

const tables = computed(() => store.mysqlTables)

const filteredTables = computed(() => {
  if (!tableFilter.value) return tables.value
  const q = tableFilter.value.toLowerCase()
  return tables.value.filter((t) => t.toLowerCase().includes(q))
})

const deployModeIcon = computed(() => {
  return store.activeDeployMode === 'docker' ? 'docker' : 'server'
})

async function refreshDatabases() {
  try {
    databases.value = await store.loadMysqlDatabases(props.accountAlias, props.containerId)
  } catch (e: any) {
    databases.value = []
    Md3Message.error(e?.response?.data?.detail || e?.message || '加载数据库列表失败')
  }
}

async function refreshTables() {
  if (!currentDatabase.value) return
  try {
    await store.loadMysqlTables(props.accountAlias, props.containerId)
  } catch (e: any) {
    Md3Message.error(e?.response?.data?.detail || e?.message || '加载表列表失败')
  }
}

function selectDatabase(db: string) {
  currentDatabase.value = db
  selectedTable.value = ''
  store.switchMysqlDatabase(db)
  emit('selectDatabase', db)
  refreshTables()
}

function selectTable(t: string) {
  selectedTable.value = t
  emit('selectTable', t)
}

function selectRedisDb(index: number) {
  currentRedisDb.value = index
  if (store.redisConnection) {
    store.redisConnection = { ...store.redisConnection, db: index }
  }
  emit('selectRedisDb', index)
}

onMounted(() => {
  if (props.dbType === 'mysql') {
    refreshDatabases()
  }
})
</script>

<style scoped>
.db-sidebar {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow-y: auto;
  background: var(--md3-surface-container-low);
  border-right: 1px solid var(--md3-outline-variant);
}

.sidebar-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--md3-space-sm) var(--md3-space-md);
  border-bottom: 1px solid var(--md3-outline-variant);
  flex-shrink: 0;
}

.connection-info {
  display: flex;
  align-items: center;
  gap: var(--md3-space-sm);
  min-width: 0;
}

.connection-name {
  font: var(--md3-type-label-medium);
  color: var(--md3-on-surface);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.sidebar-section {
  display: flex;
  flex-direction: column;
}

.section-header {
  display: flex;
  align-items: center;
  gap: var(--md3-space-xs);
  padding: var(--md3-space-xs) var(--md3-space-sm);
  font: var(--md3-type-label-small);
  color: var(--md3-on-surface-variant);
  cursor: pointer;
  user-select: none;
  transition: background var(--md3-motion-duration-short) var(--md3-motion-easing-standard);
}

.section-header:hover {
  background: var(--md3-surface-container);
}

.section-header span {
  flex: 1;
}

.section-content {
  display: flex;
  flex-direction: column;
}

.table-filter {
  padding: var(--md3-space-xs) var(--md3-space-sm);
}

.tree-item {
  display: flex;
  align-items: center;
  gap: var(--md3-space-xs);
  padding: var(--md3-space-xs) var(--md3-space-sm) var(--md3-space-xs) var(--md3-space-lg);
  font: var(--md3-type-body-small);
  color: var(--md3-on-surface);
  cursor: pointer;
  transition: background var(--md3-motion-duration-short) var(--md3-motion-easing-standard);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.tree-item:hover {
  background: var(--md3-surface-container-high);
}

.tree-item.active {
  background: var(--md3-primary-container);
  color: var(--md3-on-primary-container);
  font-weight: 500;
}

.redis-db-item {
  padding-left: var(--md3-space-lg);
}

[data-theme="dark"] .tree-item.active {
  background: var(--md3-primary-container);
  color: var(--md3-primary);
}
</style>
