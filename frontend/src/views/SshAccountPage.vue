<template>
  <div class="ssh-account-page">
    <el-page-header title="OpsV-Kits">
      <template #content>
        <span>SSH 账户管理</span>
      </template>
    </el-page-header>
    <el-divider />

    <div class="account-layout">
      <div class="account-sidebar">
        <div class="sidebar-header">
          <span class="sidebar-title">账户列表</span>
          <Md3Button size="sm" variant="primary" :icon="Plus" @click="showAddDialog = true">添加</Md3Button>
          <Md3Button size="sm" :icon="Refresh" @click="loadAccounts">刷新</Md3Button>
        </div>

        <div class="sidebar-section">
          <div class="section-label">账户分组</div>
          <el-menu :default-active="selectedGroup" class="group-menu">
            <el-menu-item index="all" @click="selectedGroup = 'all'">
              <el-icon><FolderOpened /></el-icon>
              <span>全部账户</span>
            </el-menu-item>
            <el-sub-menu
              v-for="g in groups"
              :key="g.name"
              :index="g.name"
            >
              <template #title>
                <el-icon><Folder /></el-icon>
                <span>{{ g.name }}</span>
              </template>
              <el-menu-item :index="g.name" @click="selectedGroup = g.name">
                <span>查看账户</span>
              </el-menu-item>
              <el-menu-item @click="openRenameGroup(g.name)">
                <span>重命名</span>
              </el-menu-item>
              <el-menu-item @click="confirmDeleteGroup(g.name)">
                <span style="color: var(--el-color-danger)">删除分组</span>
              </el-menu-item>
            </el-sub-menu>
          </el-menu>
          <Md3Button size="sm" class="add-group-btn" :icon="Plus" @click="showNewGroupDialog = true">新建分组</Md3Button>
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
                <el-icon v-if="acc.default" class="star-icon"><StarFilled /></el-icon>
                <span>{{ acc.alias }}</span>
              </div>
              <div class="acc-host">{{ acc.host }}:{{ acc.port }}</div>
            </div>
            <el-tag
              :type="acc.status === 'online' ? 'success' : 'info'"
              size="small"
              round
            >
              {{ acc.status === 'online' ? '在线' : '离线' }}
            </el-tag>
          </div>
        </div>
      </div>

      <div class="account-detail">
        <el-card v-if="selectedAccount" shadow="never">
          <template #header>
            <span>账户详情</span>
          </template>

          <el-descriptions :column="1" border size="small">
            <el-descriptions-item label="别名">{{ selectedAccount.alias }}</el-descriptions-item>
            <el-descriptions-item label="主机">
              {{ selectedAccount.host }}:{{ selectedAccount.port }}
            </el-descriptions-item>
            <el-descriptions-item label="用户名">{{ selectedAccount.username }}</el-descriptions-item>
            <el-descriptions-item label="认证方式">
              <el-tag size="small">
                {{ authTypeLabel(selectedAccount.auth_type) }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="私钥路径" v-if="selectedAccount.auth_type === 'key'">
              {{ selectedAccount.private_key || '-' }}
            </el-descriptions-item>
            <el-descriptions-item label="分组">{{ selectedAccount.group || '-' }}</el-descriptions-item>
            <el-descriptions-item label="远程工作目录">
              <div class="workplace-row">
                <code>{{ selectedAccount.workplace_path || '~/projects' }}</code>
                <Md3Button size="sm" variant="text" :icon="FolderOpened" @click="initWorkplace" :loading="initWorkplaceLoading">初始化</Md3Button>
              </div>
            </el-descriptions-item>
            <el-descriptions-item label="连接状态">
              <el-tag :type="selectedAccount.status === 'online' ? 'success' : 'info'" size="small" round>
                {{ selectedAccount.status === 'online' ? '已连接' : '未连接' }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="最后连接">
              {{ selectedAccount.last_connected || '从未连接' }}
            </el-descriptions-item>
          </el-descriptions>

          <div class="detail-actions">
            <Md3Button variant="primary" :icon="Connection" @click="testConnection">测试连接</Md3Button>
            <Md3Button :icon="Edit" @click="editAccount">编辑</Md3Button>
            <el-popconfirm title="确认删除该账户?" @confirm="removeAccount">
              <template #reference>
                <Md3Button variant="danger" :icon="Delete">删除</Md3Button>
              </template>
            </el-popconfirm>
            <Md3Button :icon="StarFilled" @click="setAsDefault">设为默认</Md3Button>
          </div>
        </el-card>

        <el-empty v-else description="请选择一个 SSH 账户" />

        <el-card v-if="selectedAccount" shadow="never" class="permission-card">
          <template #header>
            <span>权限测试</span>
          </template>
          <div class="permission-list">
            <div class="permission-item">
              <el-icon class="perm-success"><CircleCheck /></el-icon>
              <span>读取权限: /home/dev/projects</span>
            </div>
            <div class="permission-item">
              <el-icon class="perm-success"><CircleCheck /></el-icon>
              <span>写入权限: /home/dev/projects</span>
            </div>
            <div class="permission-item">
              <el-icon class="perm-success"><CircleCheck /></el-icon>
              <span>执行权限: /home/dev/projects</span>
            </div>
            <div class="permission-item">
              <el-icon class="perm-warning"><Warning /></el-icon>
              <span>sudo 权限: 需要密码</span>
            </div>
            <div class="permission-item">
              <el-icon class="perm-error"><CircleClose /></el-icon>
              <span>root 权限: 未获取</span>
            </div>
          </div>
          <div class="permission-actions">
            <Md3Button size="sm" :icon="Top">提升权限</Md3Button>
            <Md3Button size="sm" :icon="Tickets">查看日志</Md3Button>
          </div>
        </el-card>
      </div>
    </div>

    <el-dialog v-model="showAddDialog" :title="isEditing ? '编辑账户' : '添加账户'" width="560px">
      <el-form :model="formData" label-width="100px" label-position="left">
        <el-form-item label="别名" required>
          <el-input v-model="formData.alias" placeholder="如：生产环境" />
        </el-form-item>
        <el-form-item label="主机" required>
          <el-input v-model="formData.host" placeholder="192.168.1.100" style="width: calc(100% - 80px)" />
          <el-input v-model.number="formData.port" placeholder="22" style="width: 70px" class="port-input" />
        </el-form-item>
        <el-form-item label="用户名" required>
          <el-input v-model="formData.username" placeholder="root" />
        </el-form-item>
        <el-form-item label="认证方式">
          <el-radio-group v-model="formData.auth_type">
            <el-radio value="password">密码</el-radio>
            <el-radio value="key">SSH 密钥</el-radio>
            <el-radio value="agent">SSH Agent</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="密码" v-if="formData.auth_type === 'password'">
          <el-input v-model="formData.password" type="password" show-password placeholder="登录密码" />
        </el-form-item>
        <el-form-item label="私钥路径" v-if="formData.auth_type === 'key'">
          <el-input v-model="formData.private_key" placeholder="~/.ssh/id_rsa" />
        </el-form-item>
        <el-form-item label="密钥密码" v-if="formData.auth_type === 'key'">
          <el-input v-model="formData.key_passphrase" type="password" show-password placeholder="私钥密码（可选）" />
        </el-form-item>
        <el-form-item label="分组">
          <el-select v-model="formData.group" clearable placeholder="选择分组" style="width: calc(100% - 70px)">
            <el-option v-for="g in groups" :key="g.name" :label="g.name" :value="g.name" />
          </el-select>
          <Md3Button size="sm" variant="text" :icon="Plus" @click="showNewGroupDialog = true" style="margin-left: 4px">新建</Md3Button>
        </el-form-item>
      </el-form>
      <template #footer>
        <Md3Button @click="showAddDialog = false">取消</Md3Button>
        <Md3Button variant="primary" @click="saveAccount">保存</Md3Button>
      </template>
    </el-dialog>

    <el-dialog v-model="showNewGroupDialog" title="新建分组" width="400px">
      <el-input v-model="newGroupName" placeholder="分组名称" />
      <template #footer>
        <Md3Button @click="showNewGroupDialog = false">取消</Md3Button>
        <Md3Button variant="primary" @click="createGroup">确定</Md3Button>
      </template>
    </el-dialog>

    <el-dialog v-model="showRenameGroupDialog" title="重命名分组" width="400px">
      <el-input v-model="renameGroupNewName" placeholder="新分组名称" />
      <template #footer>
        <Md3Button @click="showRenameGroupDialog = false">取消</Md3Button>
        <Md3Button variant="primary" @click="renameGroup">确定</Md3Button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import {
  Plus, Refresh, FolderOpened, Folder,
  StarFilled, Connection, Edit, Delete,
  CircleCheck, Warning, CircleClose,
  Top, Tickets,
} from '@element-plus/icons-vue'
import Md3Button from '@/components/Md3Button.vue'
import { useSshAccountStore, type SshAccount } from '@/stores/sshAccountStore'
import { request } from '@/api'
import { ElMessage, ElMessageBox } from 'element-plus'

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
    ElMessage.success(res.message || '连接测试成功')
  } else {
    ElMessage.error(res.message || '连接测试失败')
  }
}

function editAccount() {
  if (!selectedAccount.value) return
  isEditing.value = true
  formData.value = { ...selectedAccount.value }
  showAddDialog.value = true
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
    ElMessage.error(e?.response?.data?.detail || '创建分组失败')
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
    ElMessage.success('分组已重命名')
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '重命名失败')
  }
}

function confirmDeleteGroup(name: string) {
  ElMessageBox.confirm(`确认删除分组 "${name}"？该分组下的账户将解除分组关联。`, '删除分组', {
    confirmButtonText: '删除',
    cancelButtonText: '取消',
    type: 'warning',
  }).then(async () => {
    try {
      await sshStore.deleteGroup(name)
      if (selectedGroup.value === name) {
        selectedGroup.value = 'all'
      }
      ElMessage.success('分组已删除')
    } catch (e: any) {
      ElMessage.error(e?.response?.data?.detail || '删除分组失败')
    }
  }).catch(() => {})
}

const initWorkplaceLoading = ref(false)

async function initWorkplace() {
  if (!selectedAccount.value) return
  initWorkplaceLoading.value = true
  try {
    const res = await request.post('/accounts/workplace/init', null, { params: { alias: selectedAccount.value.alias } })
    ElMessage.success(res.message)
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '初始化失败')
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

.group-menu {
  border-right: none !important;
  background: transparent;
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
  margin-left: var(--md3-space-xs);
}
</style>
