<template>
  <div class="ssh-account-page">
    <Md3PageHeader title="OpsV-Kits" subtitle="SSH 账户管理" />
    <Md3Divider />

    <div class="account-layout">
      <div class="account-sidebar">
        <div class="sidebar-header">
          <span class="sidebar-title">账户列表</span>
          <Md3Button size="sm" variant="primary" @click="showAddDialog = true"><Md3Icon name="plus" size="1em" />添加</Md3Button>
          <Md3Button size="sm" @click="loadAccounts"><Md3Icon name="refresh" size="1em" />刷新</Md3Button>
        </div>

        <div class="sidebar-section">
          <div class="section-label">账户分组</div>
          <nav class="group-nav">
            <div
              class="nav-item"
              :class="{ active: selectedGroup === 'all' }"
              @click="selectedGroup = 'all'"
            >
              <Md3Icon name="folder-open" class="nav-icon" />
              <span>全部账户</span>
            </div>
            <template v-for="g in groups" :key="g.name">
              <div class="nav-group">
                <div
                  class="nav-item nav-group-header"
                  :class="{ active: selectedGroup === g.name }"
                  @click="selectedGroup = g.name"
                >
                  <Md3Icon name="folder" class="nav-icon" />
                  <span>{{ g.name }}</span>
                </div>
                <div class="nav-group-actions">
                  <div class="nav-item nav-sub-item" @click="selectedGroup = g.name">
                    <span>查看账户</span>
                  </div>
                  <div class="nav-item nav-sub-item" @click="openRenameGroup(g.name)">
                    <span>重命名</span>
                  </div>
                  <div class="nav-item nav-sub-item" @click="confirmDeleteGroup(g.name)">
                    <span class="text-danger">删除分组</span>
                  </div>
                </div>
              </div>
            </template>
          </nav>
          <Md3Button size="sm" class="add-group-btn" @click="showNewGroupDialog = true"><Md3Icon name="plus" size="1em" />新建分组</Md3Button>
        </div>

        <div class="account-list">
          <div
            v-for="acc in filteredAccounts"
            :key="acc.alias"
            class="account-list-item"
            :class="{ active: selectedAccount?.alias === acc.alias }"
            @click="selectAccount(acc)"
          >
            <div class="acc-info">
              <div class="acc-alias">
              <Md3Icon v-if="acc.default" name="star" class="nav-icon star-icon" />
              <span>{{ acc.alias }}</span>
            </div>
              <div class="acc-host">{{ acc.host }}:{{ acc.port }}</div>
            </div>
            <Md3Tag
              :type="acc.status === 'online' ? 'success' : 'info'"
              size="sm"
            >
              {{ acc.status === 'online' ? '在线' : '离线' }}
            </Md3Tag>
          </div>
        </div>
      </div>

      <div class="account-detail">
        <Md3Card v-if="selectedAccount" :shadow="false">
          <template #header>
            <span>账户详情</span>
          </template>

          <div class="descriptions">
            <div class="desc-item" v-for="(item, idx) in descriptionItems" :key="idx">
              <span class="desc-label">{{ item.label }}</span>
              <span class="desc-value">
                <template v-if="item.key === 'auth_type'">
                  <Md3Tag size="sm">{{ authTypeLabel(selectedAccount.auth_type) }}</Md3Tag>
                </template>
                <template v-else-if="item.key === 'workplace_path'">
                  <div class="workplace-row">
                    <code>{{ selectedAccount.workplace_path || '~/projects' }}</code>
                    <Md3Button size="sm" variant="text" @click="initWorkplace" :loading="initWorkplaceLoading"><Md3Icon name="folder-open" size="1em" />初始化</Md3Button>
                  </div>
                </template>
                <template v-else-if="item.key === 'private_key'">
                  {{ selectedAccount.private_key || '-' }}
                </template>
                <template v-else-if="item.key === 'group'">
                  {{ selectedAccount.group || '-' }}
                </template>
                <template v-else-if="item.key === 'status'">
                  <Md3Tag :type="selectedAccount.status === 'online' ? 'success' : 'info'" size="sm">
                    {{ selectedAccount.status === 'online' ? '已连接' : '未连接' }}
                  </Md3Tag>
                </template>
                <template v-else>
                  {{ item.value }}
                </template>
              </span>
            </div>
          </div>

          <div class="detail-actions">
            <Md3Button variant="primary" @click="testConnection"><Md3Icon name="connection" size="1em" />测试连接</Md3Button>
            <Md3Button @click="editAccount"><Md3Icon name="pencil" size="1em" />编辑</Md3Button>
            <Md3Button variant="danger" @click="confirmRemoveAccount"><Md3Icon name="delete" size="1em" />删除</Md3Button>
            <Md3Button @click="setAsDefault"><Md3Icon name="star" size="1em" />设为默认</Md3Button>
          </div>
        </Md3Card>

        <Md3Empty v-if="!selectedAccount" description="请选择一个 SSH 账户" />

        <Md3Card v-if="selectedAccount" :shadow="false" class="permission-card">
          <template #header>
            <span>权限测试</span>
          </template>
          <div class="permission-list">
            <div class="permission-item">
              <Md3Icon name="check-circle" class="perm-icon perm-success" />
              <span>读取权限: /home/dev/projects</span>
            </div>
            <div class="permission-item">
              <Md3Icon name="check-circle" class="perm-icon perm-success" />
              <span>写入权限: /home/dev/projects</span>
            </div>
            <div class="permission-item">
              <Md3Icon name="check-circle" class="perm-icon perm-success" />
              <span>执行权限: /home/dev/projects</span>
            </div>
            <div class="permission-item">
              <Md3Icon name="alert" class="perm-icon perm-warning" />
              <span>sudo 权限: 需要密码</span>
            </div>
            <div class="permission-item">
              <Md3Icon name="close" class="perm-icon perm-error" />
              <span>root 权限: 未获取</span>
            </div>
          </div>
          <div class="permission-actions">
            <Md3Button size="sm"><Md3Icon name="arrow-up" size="1em" />提升权限</Md3Button>
            <Md3Button size="sm"><Md3Icon name="tag" size="1em" />查看日志</Md3Button>
          </div>
        </Md3Card>
      </div>
    </div>

    <Md3Dialog v-model:visible="showAddDialog" :title="isEditing ? '编辑账户' : '添加账户'" width="560px">
      <div class="dialog-form">
        <Md3Input v-model="formData.alias" label="别名" placeholder="如：生产环境" />
        <div class="host-row">
          <Md3Input v-model="formData.host" label="主机" placeholder="192.168.1.100" style="flex:1" />
          <Md3Input v-model.number="formData.port" label="" placeholder="22" type="number" class="port-input" />
        </div>
        <Md3Input v-model="formData.username" label="用户名" placeholder="root" />
        <div class="auth-type-section">
          <span class="form-label">认证方式</span>
          <div class="radio-group">
            <Md3Radio v-model="formData.auth_type" value="password" label="密码" />
            <Md3Radio v-model="formData.auth_type" value="key" label="SSH 密钥" />
            <Md3Radio v-model="formData.auth_type" value="agent" label="SSH Agent" />
          </div>
        </div>
        <Md3Input v-if="formData.auth_type === 'password'" v-model="formData.password" label="密码" type="password" placeholder="登录密码" />
        <Md3Input v-if="formData.auth_type === 'key'" v-model="formData.private_key" label="私钥路径" placeholder="~/.ssh/id_rsa" />
        <Md3Input v-if="formData.auth_type === 'key'" v-model="formData.key_passphrase" label="密钥密码" type="password" placeholder="私钥密码（可选）" />
        <div class="group-select-row">
          <Md3Select v-model="formData.group" label="分组" placeholder="选择分组" :options="groupOptions" style="flex:1" clearable />
          <Md3Button size="sm" variant="text" @click="showNewGroupDialog = true"><Md3Icon name="plus" size="1em" />新建</Md3Button>
        </div>
      </div>
      <template #footer>
        <Md3Button @click="showAddDialog = false">取消</Md3Button>
        <Md3Button variant="primary" @click="saveAccount">保存</Md3Button>
      </template>
    </Md3Dialog>

    <Md3Dialog v-model:visible="showNewGroupDialog" title="新建分组" width="400px">
      <Md3Input v-model="newGroupName" label="" placeholder="分组名称" />
      <template #footer>
        <Md3Button @click="showNewGroupDialog = false">取消</Md3Button>
        <Md3Button variant="primary" @click="createGroup">确定</Md3Button>
      </template>
    </Md3Dialog>

    <Md3Dialog v-model:visible="showRenameGroupDialog" title="重命名分组" width="400px">
      <Md3Input v-model="renameGroupNewName" label="" placeholder="新分组名称" />
      <template #footer>
        <Md3Button @click="showRenameGroupDialog = false">取消</Md3Button>
        <Md3Button variant="primary" @click="renameGroup">确定</Md3Button>
      </template>
    </Md3Dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { Md3Icon } from '@/components/md3'
import Md3Button from '@/components/Md3Button.vue'
import { useSshAccountStore, type SshAccount } from '@/stores/sshAccountStore'
import { request } from '@/api'
import { Md3Message, Md3Confirm, Md3PageHeader, Md3Divider, Md3Card, Md3Empty, Md3Tag, Md3Input, Md3Radio, Md3Select, Md3Dialog } from '@/components/md3'

const sshStore = useSshAccountStore()

const selectedAccount = ref<SshAccount | null>(null)
const selectedGroup = ref('all')
const showAddDialog = ref(false)
const showNewGroupDialog = ref(false)
const isEditing = ref(false)
const newGroupName = ref('')
const showRenameGroupDialog = ref(false)
const renameGroupOldName = ref('')
const renameGroupNewName = ref('')

const formData = ref<SshAccount>({
  alias: '',
  host: '',
  port: 22,
  username: '',
  auth_type: 'password',
  password: '',
  private_key: '',
  key_passphrase: '',
  group: '',
})

const accounts = computed(() => sshStore.accounts)
const groups = computed(() => sshStore.groups)
const groupOptions = computed(() =>
  groups.value.map(g => ({ label: g.name, value: g.name }))
)

const filteredAccounts = computed(() => {
  if (selectedGroup.value === 'all') return accounts.value
  return accounts.value.filter(a => a.group === selectedGroup.value)
})

function authTypeLabel(type: string) {
  const map: Record<string, string> = {
    password: '密码认证',
    key: 'SSH 密钥',
    agent: 'SSH Agent',
  }
  return map[type] || type
}

const descriptionItems = computed(() => {
  const acc = selectedAccount.value
  if (!acc) return []
  const items: { label: string; key: string; value?: string }[] = [
    { label: '别名', key: 'alias', value: acc.alias },
    { label: '主机', key: 'host', value: `${acc.host}:${acc.port}` },
    { label: '用户名', key: 'username', value: acc.username },
    { label: '认证方式', key: 'auth_type' },
    { label: '远程工作目录', key: 'workplace_path' },
    { label: '分组', key: 'group' },
    { label: '连接状态', key: 'status' },
    { label: '最后连接', key: 'last_connected', value: acc.last_connected || '从未连接' },
  ]
  if (acc.auth_type === 'key') {
    items.splice(4, 0, { label: '私钥路径', key: 'private_key' })
  }
  return items
})

function selectAccount(acc: SshAccount) {
  selectedAccount.value = acc
}

async function loadAccounts() {
  await sshStore.fetchAccounts()
}

async function testConnection() {
  if (!selectedAccount.value) return
  const res = await sshStore.testConnection(selectedAccount.value.alias)
  if (res.success) {
    Md3Message.success(res.message || '连接测试成功')
  } else {
    Md3Message.error(res.message || '连接测试失败')
  }
}

function editAccount() {
  if (!selectedAccount.value) return
  isEditing.value = true
  formData.value = { ...selectedAccount.value }
  showAddDialog.value = true
}

async function confirmRemoveAccount() {
  if (!selectedAccount.value) return
  const confirmed = await Md3Confirm.show({
    title: '删除账户',
    message: `确认删除账户「${selectedAccount.value.alias}」吗？`,
    confirmText: '删除',
    cancelText: '取消',
    type: 'danger',
  })
  if (!confirmed) return
  await removeAccount()
}

async function removeAccount() {
  if (!selectedAccount.value) return
  await sshStore.deleteAccount(selectedAccount.value.alias)
  selectedAccount.value = null
}

async function setAsDefault() {
  if (!selectedAccount.value) return
  await sshStore.setDefault(selectedAccount.value.alias)
}

async function saveAccount() {
  if (isEditing.value && selectedAccount.value) {
    await sshStore.updateAccount(selectedAccount.value.alias, formData.value)
  } else {
    await sshStore.createAccount(formData.value)
  }
  showAddDialog.value = false
  isEditing.value = false
  formData.value = {
    alias: '',
    host: '',
    port: 22,
    username: '',
    auth_type: 'password',
    password: '',
    private_key: '',
    key_passphrase: '',
    group: '',
  }
}

async function createGroup() {
  if (!newGroupName.value) return
  try {
    await sshStore.createGroup(newGroupName.value)
    showNewGroupDialog.value = false
    newGroupName.value = ''
  } catch (e: any) {
    Md3Message.error(e?.response?.data?.detail || '创建分组失败')
  }
}

function openRenameGroup(name: string) {
  renameGroupOldName.value = name
  renameGroupNewName.value = name
  showRenameGroupDialog.value = true
}

async function renameGroup() {
  if (!renameGroupNewName.value || renameGroupNewName.value === renameGroupOldName.value) return
  try {
    await sshStore.updateGroup(renameGroupOldName.value, { new_name: renameGroupNewName.value })
    showRenameGroupDialog.value = false
    if (selectedGroup.value === renameGroupOldName.value) {
      selectedGroup.value = renameGroupNewName.value
    }
    Md3Message.success('分组已重命名')
  } catch (e: any) {
    Md3Message.error(e?.response?.data?.detail || '重命名失败')
  }
}

async function confirmDeleteGroup(name: string) {
  const confirmed = await Md3Confirm.show({
    title: '删除分组',
    message: `确认删除分组 "${name}"？该分组下的账户将解除分组关联。`,
    confirmText: '删除',
    cancelText: '取消',
    type: 'danger',
  })
  if (!confirmed) return
  try {
    await sshStore.deleteGroup(name)
    if (selectedGroup.value === name) {
      selectedGroup.value = 'all'
    }
    Md3Message.success('分组已删除')
  } catch (e: any) {
    Md3Message.error(e?.response?.data?.detail || '删除分组失败')
  }
}

const initWorkplaceLoading = ref(false)

async function initWorkplace() {
  if (!selectedAccount.value) return
  initWorkplaceLoading.value = true
  try {
    const res = await request.post('/accounts/workplace/init', null, { params: { alias: selectedAccount.value.alias } })
    Md3Message.success(res.message)
  } catch (e: any) {
    Md3Message.error(e?.response?.data?.detail || '初始化失败')
  } finally {
    initWorkplaceLoading.value = false
  }
}

onMounted(() => {
  loadAccounts()
  sshStore.fetchGroups()
})
</script>

<style scoped>
.ssh-account-page {
  padding: 0;
}

.account-layout {
  display: flex;
  gap: var(--md3-space-lg);
}

.account-sidebar {
  width: 280px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: var(--md3-space-md);
  padding: var(--md3-space-md);
  background: var(--md3-glass-bg);
  backdrop-filter: var(--md3-glass-blur);
  -webkit-backdrop-filter: var(--md3-glass-blur);
  border: 1px solid var(--md3-glass-border);
  border-radius: var(--md3-shape-md);
  transition: box-shadow var(--md3-motion-duration-medium) var(--md3-motion-easing-standard);
}

.account-sidebar:hover {
  box-shadow: var(--md3-elevation-level1);
}

.sidebar-header {
  display: flex;
  align-items: center;
  gap: var(--md3-space-sm);
  flex-wrap: wrap;
}

.sidebar-title {
  font: var(--md3-type-title-small);
  margin-right: auto;
}

.sidebar-section {
  display: flex;
  flex-direction: column;
  gap: var(--md3-space-xs);
}

.section-label {
  font: var(--md3-type-label-small);
  color: var(--md3-outline);
  text-transform: uppercase;
  letter-spacing: 1px;
  padding: var(--md3-space-xs) 0;
}

.group-nav {
  display: flex;
  flex-direction: column;
  gap: var(--md3-space-xs);
}

.nav-item {
  display: flex;
  align-items: center;
  gap: var(--md3-space-sm);
  padding: var(--md3-space-xs) var(--md3-space-sm);
  border-radius: var(--md3-shape-sm);
  cursor: pointer;
  font-size: 13px;
  color: var(--md3-on-surface);
  transition: background var(--md3-motion-duration-short) var(--md3-motion-easing-standard);
}

.nav-item:hover {
  background: var(--md3-surface-container-high);
}

.nav-item.active {
  background: var(--md3-primary-container);
  color: var(--md3-on-primary-container);
}

.nav-icon {
  width: 18px;
  height: 18px;
  flex-shrink: 0;
}

.nav-group {
  display: flex;
  flex-direction: column;
  gap: 0;
}

.nav-group-header {
  font-weight: 500;
}

.nav-group-actions {
  display: flex;
  flex-direction: column;
  gap: 0;
}

.nav-sub-item {
  padding-left: calc(var(--md3-space-sm) + 18px + var(--md3-space-xs));
  font-size: 12px;
}

.text-danger {
  color: var(--md3-error);
}

.perm-icon {
  width: 18px;
  height: 18px;
  flex-shrink: 0;
}

.add-group-btn {
  width: 100%;
  margin-top: var(--md3-space-xs);
}

.account-list {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.account-list-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--md3-space-sm) var(--md3-space-md);
  cursor: pointer;
  border-radius: var(--md3-shape-sm);
  transition: background var(--md3-motion-duration-short) var(--md3-motion-easing-standard),
              box-shadow var(--md3-motion-duration-short) var(--md3-motion-easing-standard);
}

.account-list-item:hover {
  background: var(--md3-surface-container-high);
}

.account-list-item.active {
  background: var(--md3-primary-container);
}

.acc-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.acc-alias {
  display: flex;
  align-items: center;
  gap: var(--md3-space-xs);
  font-weight: 500;
  font-size: 13px;
}

.star-icon {
  color: var(--md3-warning);
}

.acc-host {
  font-size: 11px;
  color: var(--md3-outline);
}

.account-detail {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: var(--md3-space-lg);
}

.descriptions {
  display: flex;
  flex-direction: column;
  gap: var(--md3-space-sm);
}

.desc-item {
  display: flex;
  align-items: flex-start;
  padding: var(--md3-space-sm) 0;
  border-bottom: 1px solid var(--md3-outline-variant);
}

.desc-label {
  font-size: 0.75rem;
  color: var(--md3-on-surface-variant);
  width: 100px;
  flex-shrink: 0;
  padding-top: 2px;
}

.desc-value {
  flex: 1;
  font-size: 0.875rem;
  color: var(--md3-on-surface);
}

.detail-actions {
  display: flex;
  gap: var(--md3-space-sm);
  margin-top: var(--md3-space-lg);
  flex-wrap: wrap;
}

.workplace-row {
  display: flex;
  align-items: center;
  gap: var(--md3-space-sm);
}

.workplace-row code {
  font-size: 12px;
  background: var(--md3-surface-container-low);
  padding: 2px 6px;
  border-radius: var(--md3-shape-xs);
  color: var(--md3-primary);
}

.permission-card {
  margin-top: var(--md3-space-sm);
}

.permission-list {
  display: flex;
  flex-direction: column;
  gap: var(--md3-space-sm);
}

.permission-item {
  display: flex;
  align-items: center;
  gap: var(--md3-space-sm);
  font-size: 13px;
}

.perm-success {
  color: var(--md3-success);
}

.perm-warning {
  color: var(--md3-warning);
}

.perm-error {
  color: var(--md3-error);
}

.permission-actions {
  display: flex;
  gap: var(--md3-space-sm);
  margin-top: var(--md3-space-md);
}

.port-input {
  width: 80px;
}

.host-row {
  display: flex;
  gap: var(--md3-space-sm);
}

.auth-type-section {
  display: flex;
  flex-direction: column;
  gap: var(--md3-space-xs);
}

.form-label {
  font-size: 0.75rem;
  color: var(--md3-on-surface-variant);
  padding-left: var(--md3-space-sm);
}

.radio-group {
  display: flex;
  gap: var(--md3-space-md);
  padding-left: var(--md3-space-sm);
}

.group-select-row {
  display: flex;
  align-items: center;
  gap: var(--md3-space-sm);
}

.dialog-form {
  display: flex;
  flex-direction: column;
  gap: var(--md3-space-md);
}
</style>
