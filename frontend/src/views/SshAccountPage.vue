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
          <el-button size="small" type="primary" @click="showAddDialog = true">
            <el-icon><Plus /></el-icon> 添加
          </el-button>
          <el-button size="small" @click="loadAccounts">
            <el-icon><Refresh /></el-icon> 刷新
          </el-button>
        </div>

        <div class="sidebar-section">
          <div class="section-label">账户分组</div>
          <el-menu :default-active="selectedGroup" class="group-menu">
            <el-menu-item index="all" @click="selectedGroup = 'all'">
              <el-icon><FolderOpened /></el-icon>
              <span>全部账户</span>
            </el-menu-item>
            <el-menu-item
              v-for="g in groups"
              :key="g.name"
              :index="g.name"
              @click="selectedGroup = g.name"
            >
              <el-icon><Folder /></el-icon>
              <span>{{ g.name }}</span>
            </el-menu-item>
          </el-menu>
          <el-button size="small" class="add-group-btn" @click="showNewGroupDialog = true">
            <el-icon><Plus /></el-icon> 新建分组
          </el-button>
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
                <el-button size="small" link type="primary" @click="initWorkplace" :loading="initWorkplaceLoading">
                  <el-icon><FolderOpened /></el-icon> 初始化
                </el-button>
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
            <el-button type="primary" @click="testConnection">
              <el-icon><Connection /></el-icon> 测试连接
            </el-button>
            <el-button @click="editAccount">
              <el-icon><Edit /></el-icon> 编辑
            </el-button>
            <el-popconfirm title="确认删除该账户?" @confirm="removeAccount">
              <template #reference>
                <el-button type="danger">
                  <el-icon><Delete /></el-icon> 删除
                </el-button>
              </template>
            </el-popconfirm>
            <el-button @click="setAsDefault">
              <el-icon><StarFilled /></el-icon> 设为默认
            </el-button>
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
            <el-button size="small"><el-icon><Top /></el-icon> 提升权限</el-button>
            <el-button size="small"><el-icon><Tickets /></el-icon> 查看日志</el-button>
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
          <el-input v-model="formData.group" placeholder="如：生产环境组" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAddDialog = false">取消</el-button>
        <el-button type="primary" @click="saveAccount">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="showNewGroupDialog" title="新建分组" width="400px">
      <el-input v-model="newGroupName" placeholder="分组名称" />
      <template #footer>
        <el-button @click="showNewGroupDialog = false">取消</el-button>
        <el-button type="primary" @click="createGroup">确定</el-button>
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
import { useSshAccountStore, type SshAccount } from '@/stores/sshAccountStore'
import { request } from '@/api'
import { ElMessage } from 'element-plus'

const sshStore = useSshAccountStore()

const selectedAccount = ref<SshAccount | null>(null)
const selectedGroup = ref('all')
const showAddDialog = ref(false)
const showNewGroupDialog = ref(false)
const isEditing = ref(false)
const newGroupName = ref('')

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
  await sshStore.testConnection(selectedAccount.value.alias)
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

function createGroup() {
  if (!newGroupName.value) return
  sshStore.groups.push({ name: newGroupName.value, accounts: [] })
  showNewGroupDialog.value = false
  newGroupName.value = ''
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
  gap: 16px;
}

.account-sidebar {
  width: 280px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.sidebar-header {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.sidebar-title {
  font-size: 14px;
  font-weight: 600;
  margin-right: auto;
}

.sidebar-section {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.section-label {
  font-size: 12px;
  font-weight: 600;
  color: #909399;
  text-transform: uppercase;
  letter-spacing: 1px;
  padding: 4px 0;
}

.group-menu {
  border-right: none !important;
}

.add-group-btn {
  width: 100%;
  margin-top: 4px;
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
  padding: 8px 12px;
  cursor: pointer;
  border-radius: 4px;
  transition: background 0.2s;
}

.account-list-item:hover {
  background: #f5f7fa;
}

.account-list-item.active {
  background: #ecf5ff;
}

.acc-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.acc-alias {
  display: flex;
  align-items: center;
  gap: 4px;
  font-weight: 500;
  font-size: 13px;
}

.star-icon {
  color: #e6a23c;
}

.acc-host {
  font-size: 11px;
  color: #909399;
}

.account-detail {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.detail-actions {
  display: flex;
  gap: 8px;
  margin-top: 16px;
  flex-wrap: wrap;
}

.workplace-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.workplace-row code {
  font-size: 12px;
  background: #f5f7fa;
  padding: 2px 6px;
  border-radius: 3px;
  color: #409eff;
}

.permission-card {
  margin-top: 8px;
}

.permission-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.permission-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
}

.perm-success {
  color: #67c23a;
}

.perm-warning {
  color: #e6a23c;
}

.perm-error {
  color: #f56c6c;
}

.permission-actions {
  display: flex;
  gap: 8px;
  margin-top: 12px;
}

.port-input {
  margin-left: 4px;
}
</style>
