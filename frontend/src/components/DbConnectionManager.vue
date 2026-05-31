<template>
  <div class="db-connection-manager">
    <div class="manager-header">
      <span class="manager-title">数据库连接</span>
      <Md3Button variant="primary" size="sm" icon="plus" @click="openNewDialog">新建连接</Md3Button>
    </div>

    <div class="connections-list" v-if="favoriteConnections.length > 0 || otherConnections.length > 0">
      <div class="connection-section" v-if="favoriteConnections.length > 0">
        <div class="section-label">收藏</div>
        <div
          v-for="conn in favoriteConnections"
          :key="conn.id"
          class="connection-item"
          @click="quickConnect(conn)"
        >
          <div class="conn-info">
            <Md3Icon :name="conn.deployMode === 'docker' ? 'box' : 'monitor'" size="16" class="conn-icon" />
            <Md3Tag size="sm" :type="conn.dbType === 'mysql' ? 'primary' : 'success'">{{ conn.dbType.toUpperCase() }}</Md3Tag>
            <span class="conn-name">{{ conn.name }}</span>
          </div>
          <div class="conn-actions">
            <Md3Button variant="text" size="sm" icon="star" @click.stop="toggleFav(conn.id)" :class="{ 'fav-active': conn.favorite }" />
            <Md3Button variant="text" size="sm" icon="pencil" @click.stop="editConnection(conn)" />
            <Md3Button variant="text" size="sm" icon="delete" @click.stop="confirmDelete(conn)" />
          </div>
        </div>
      </div>

      <div class="connection-section" v-if="otherConnections.length > 0">
        <div class="section-label">其他连接</div>
        <div
          v-for="conn in otherConnections"
          :key="conn.id"
          class="connection-item"
          @click="quickConnect(conn)"
        >
          <div class="conn-info">
            <Md3Icon :name="conn.deployMode === 'docker' ? 'box' : 'monitor'" size="16" class="conn-icon" />
            <Md3Tag size="sm" :type="conn.dbType === 'mysql' ? 'primary' : 'success'">{{ conn.dbType.toUpperCase() }}</Md3Tag>
            <span class="conn-name">{{ conn.name }}</span>
          </div>
          <div class="conn-actions">
            <Md3Button variant="text" size="sm" icon="star" @click.stop="toggleFav(conn.id)" />
            <Md3Button variant="text" size="sm" icon="pencil" @click.stop="editConnection(conn)" />
            <Md3Button variant="text" size="sm" icon="delete" @click.stop="confirmDelete(conn)" />
          </div>
        </div>
      </div>
    </div>

    <Md3Empty v-else description="暂无保存的连接，点击上方按钮新建" />

    <DbLoginDialog
      :deploy-mode="deployMode"
      :account-alias="accountAlias"
      :container-id="containerId"
      :visible="showNewDialog"
      :edit-target="editingTarget"
      @close="closeDialog"
      @submit="handleNewConnection"
    />

    <Md3Dialog :visible="deleteConfirmVisible" @close="deleteConfirmVisible = false">
      <template #header>确认删除</template>
      <p>确定要删除连接 "{{ deleteTarget?.name }}" 吗？</p>
      <template #footer>
        <Md3Button variant="text" @click="deleteConfirmVisible = false">取消</Md3Button>
        <Md3Button variant="danger" @click="doDelete">确认删除</Md3Button>
      </template>
    </Md3Dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import type { DeployMode, SavedConnection } from '@/types/db-toolkit'
import { useDbToolkitStore } from '@/stores/dbToolkitStore'
import { Md3Icon, Md3Tag, Md3Dialog, Md3Empty } from '@/components/md3'
import Md3Button from '@/components/Md3Button.vue'
import DbLoginDialog from '@/components/DbLoginDialog.vue'

const props = defineProps<{
  deployMode: DeployMode
  accountAlias: string
  containerId?: string
}>()

const emit = defineEmits<{
  connect: [connection: SavedConnection]
}>()

const store = useDbToolkitStore()

const favoriteConnections = computed(() =>
  store.savedConnections.filter((c) => c.favorite)
)

const otherConnections = computed(() =>
  store.savedConnections.filter((c) => !c.favorite)
)

const showNewDialog = ref(false)
const editingTarget = ref<SavedConnection | null>(null)
const deleteConfirmVisible = ref(false)
const deleteTarget = ref<SavedConnection | null>(null)

function openNewDialog() {
  editingTarget.value = null
  showNewDialog.value = true
}

function closeDialog() {
  showNewDialog.value = false
  editingTarget.value = null
}

function quickConnect(conn: SavedConnection) {
  emit('connect', conn)
}

function toggleFav(id: string) {
  store.toggleFavorite(id)
}

function editConnection(conn: SavedConnection) {
  editingTarget.value = conn
  showNewDialog.value = true
}

function confirmDelete(conn: SavedConnection) {
  deleteTarget.value = conn
  deleteConfirmVisible.value = true
}

function doDelete() {
  if (deleteTarget.value) {
    store.removeConnection(deleteTarget.value.id)
  }
  deleteConfirmVisible.value = false
  deleteTarget.value = null
}

function handleNewConnection(params: any) {
  if (params.editId) {
    store.updateConnection(params.editId, {
      name: params.name,
      deployMode: params.deployMode,
      dbType: params.dbType,
      accountAlias: props.accountAlias,
      containerId: params.containerId || '',
      connection: params.connection,
    })
    const updated = store.savedConnections.find((c) => c.id === params.editId)
    if (updated) {
      emit('connect', updated)
    }
  } else if (params.saveConnection) {
    store.addConnection({
      name: params.name || `连接 ${store.savedConnections.length + 1}`,
      deployMode: params.deployMode,
      dbType: params.dbType,
      accountAlias: props.accountAlias,
      containerId: params.containerId || '',
      connection: params.connection,
      favorite: false,
    })
    const added = store.savedConnections[store.savedConnections.length - 1]
    if (added) {
      emit('connect', added)
    }
  } else {
    const tempConn: SavedConnection = {
      id: '',
      name: params.name || '临时连接',
      deployMode: params.deployMode,
      dbType: params.dbType,
      accountAlias: props.accountAlias,
      containerId: params.containerId || '',
      connection: params.connection,
      favorite: false,
      createdAt: Date.now(),
      updatedAt: Date.now(),
    }
    emit('connect', tempConn)
  }
  closeDialog()
}
</script>

<style scoped>
.db-connection-manager {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.manager-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--md3-space-md) var(--md3-space-lg);
  border-bottom: 1px solid var(--md3-outline-variant);
}

.manager-title {
  font: var(--md3-type-title-small);
  color: var(--md3-on-surface);
}

.connections-list {
  flex: 1;
  overflow-y: auto;
  padding: var(--md3-space-sm) 0;
}

.connection-section {
  margin-bottom: var(--md3-space-sm);
}

.section-label {
  padding: var(--md3-space-xs) var(--md3-space-lg);
  font: var(--md3-type-label-small);
  color: var(--md3-on-surface-variant);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.connection-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--md3-space-sm) var(--md3-space-lg);
  cursor: pointer;
  transition: background-color var(--md3-motion-duration-short) var(--md3-motion-easing-standard);
}

.connection-item:hover {
  background: var(--md3-surface-container-high);
}

.conn-info {
  display: flex;
  align-items: center;
  gap: var(--md3-space-sm);
  min-width: 0;
  flex: 1;
}

.conn-icon {
  color: var(--md3-on-surface-variant);
  flex-shrink: 0;
}

.conn-name {
  font: var(--md3-type-body-medium);
  color: var(--md3-on-surface);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.conn-actions {
  display: flex;
  align-items: center;
  gap: 2px;
  flex-shrink: 0;
  opacity: 0;
  transition: opacity var(--md3-motion-duration-short) var(--md3-motion-easing-standard);
}

.connection-item:hover .conn-actions {
  opacity: 1;
}

.fav-active {
  color: var(--md3-warning) !important;
}

:deep(.fav-active .md3-btn__icon) {
  color: var(--md3-warning);
}
</style>
