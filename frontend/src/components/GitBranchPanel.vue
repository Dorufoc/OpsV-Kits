<template>
  <div class="git-branch-panel">
    <div class="panel-actions">
      <Md3Button size="sm" @click="showCreateDialog = true">创建分支</Md3Button>
      <Md3Button size="sm" @click="refreshBranches">刷新</Md3Button>
    </div>

    <Md3Table
      :columns="branchColumns"
      :data="gitStore.branches"
      stripe
      hover
      empty-text="暂无分支数据"
    >
      <template #is_current="{ row }">
        <Md3Tag :type="row.is_current ? 'success' : 'info'" size="sm">
          {{ row.is_current ? '当前' : '' }}
        </Md3Tag>
      </template>
      <template #actions="{ row }">
        <div class="row-actions">
          <Md3Button size="sm" :disabled="row.is_current" @click="handleSwitch(row.name)">切换</Md3Button>
          <Md3Button size="sm" @click="openMergeDialog(row.name)">合并</Md3Button>
          <Md3Button size="sm" variant="danger" :disabled="row.is_current" @click="confirmDeleteBranch(row.name)">删除</Md3Button>
        </div>
      </template>
    </Md3Table>

    <Md3Card class="compare-card">
      <template #header>
        <span class="card-title">分支比较</span>
      </template>
      <div class="compare-form">
        <Md3Select v-model="compareSource" :options="branchOptions" label="源分支" placeholder="选择源分支" />
        <Md3Select v-model="compareTarget" :options="branchOptions" label="目标分支" placeholder="选择目标分支" />
        <Md3Button size="sm" variant="primary" @click="handleCompare">比较</Md3Button>
      </div>
      <div v-if="diffFiles.length > 0" class="diff-files">
        <div v-for="file in diffFiles" :key="file" class="diff-file-item">
          {{ file }}
        </div>
      </div>
    </Md3Card>

    <Md3Dialog v-model:visible="showCreateDialog" title="创建分支" width="420px">
      <div class="dialog-form">
        <Md3Input v-model="createForm.name" label="分支名称" placeholder="feature/new-feature" />
        <Md3Input v-model="createForm.base" label="基于分支" placeholder="main (留空则基于当前分支)" />
      </div>
      <template #footer>
        <Md3Button @click="showCreateDialog = false">取消</Md3Button>
        <Md3Button variant="primary" @click="handleCreate">创建</Md3Button>
      </template>
    </Md3Dialog>

    <Md3Dialog v-model:visible="showMergeDialog" title="合并分支" width="420px">
      <div class="dialog-form">
        <p class="merge-info">将 <strong>{{ mergeSource }}</strong> 合并到当前分支</p>
      </div>
      <template #footer>
        <Md3Button @click="showMergeDialog = false">取消</Md3Button>
        <Md3Button variant="primary" @click="handleMerge">确认合并</Md3Button>
      </template>
    </Md3Dialog>

    <Md3Dialog v-model:visible="showDeleteDialog" title="确认删除" width="380px">
      <div class="dialog-form">
        <p class="delete-info">确认删除分支 <strong>{{ deleteTarget }}</strong>？此操作不可撤销。</p>
      </div>
      <template #footer>
        <Md3Button @click="showDeleteDialog = false">取消</Md3Button>
        <Md3Button variant="danger" @click="handleDelete">删除</Md3Button>
      </template>
    </Md3Dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useGitIntegrationStore } from '@/stores/gitIntegrationStore'
import {
  Md3Card,
  Md3Dialog,
  Md3Input,
  Md3Select,
  Md3Table,
  Md3Tag,
} from '@/components/md3'
import Md3Button from '@/components/Md3Button.vue'
import { Md3Message } from '@/components/md3/Md3Message'

const gitStore = useGitIntegrationStore()

const showCreateDialog = ref(false)
const showMergeDialog = ref(false)
const showDeleteDialog = ref(false)
const mergeSource = ref('')
const deleteTarget = ref('')
const compareSource = ref('')
const compareTarget = ref('')
const diffFiles = ref<string[]>([])

const createForm = ref({ name: '', base: '' })

const branchColumns = [
  { prop: 'name', label: '名称' },
  { prop: 'is_current', label: '当前' },
  { prop: 'last_commit', label: '最近提交' },
  { prop: 'upstream', label: '上游' },
  { prop: 'actions', label: '操作' },
]

const branchOptions = computed(() =>
  gitStore.branches.map(b => ({ label: b.name, value: b.name }))
)

function refreshBranches() {
  gitStore.fetchBranches()
}

async function handleSwitch(name: string) {
  try {
    await gitStore.switchBranch(name)
    Md3Message.success(`已切换到 ${name}`)
    gitStore.fetchBranches()
    gitStore.fetchRepoInfo()
  } catch {
    Md3Message.error('切换分支失败')
  }
}

function openMergeDialog(name: string) {
  mergeSource.value = name
  showMergeDialog.value = true
}

async function handleMerge() {
  try {
    const currentBranch = gitStore.repoInfo.current_branch
    await gitStore.mergeBranch(mergeSource.value, currentBranch)
    Md3Message.success('合并成功')
    showMergeDialog.value = false
    gitStore.fetchBranches()
    gitStore.fetchRepoInfo()
  } catch {
    Md3Message.error('合并失败')
  }
}

function confirmDeleteBranch(name: string) {
  deleteTarget.value = name
  showDeleteDialog.value = true
}

async function handleDelete() {
  try {
    await gitStore.deleteBranch(deleteTarget.value)
    Md3Message.success('分支已删除')
    showDeleteDialog.value = false
    gitStore.fetchBranches()
  } catch {
    Md3Message.error('删除分支失败')
  }
}

async function handleCreate() {
  try {
    await gitStore.createBranch(createForm.value.name, createForm.value.base || undefined)
    Md3Message.success('分支创建成功')
    showCreateDialog.value = false
    createForm.value = { name: '', base: '' }
    gitStore.fetchBranches()
  } catch {
    Md3Message.error('创建分支失败')
  }
}

async function handleCompare() {
  if (!compareSource.value || !compareTarget.value) return
  try {
    const res = await gitStore.compareBranches(compareSource.value, compareTarget.value)
    diffFiles.value = res.files
  } catch {
    Md3Message.error('分支比较失败')
  }
}

onMounted(() => {
  gitStore.fetchBranches()
})
</script>

<style scoped>
.panel-actions {
  display: flex;
  gap: var(--md3-space-sm);
  margin-bottom: var(--md3-space-md);
}

.row-actions {
  display: flex;
  gap: var(--md3-space-xs);
}

.compare-card {
  margin-top: var(--md3-space-lg);
}

.card-title {
  font: var(--md3-type-title-medium);
  color: var(--md3-on-surface);
}

.compare-form {
  display: flex;
  align-items: flex-end;
  gap: var(--md3-space-md);
}

.diff-files {
  margin-top: var(--md3-space-md);
  border-top: 1px solid var(--md3-outline-variant);
  padding-top: var(--md3-space-md);
}

.diff-file-item {
  font: var(--md3-type-body-small);
  font-family: var(--md3-font-mono);
  color: var(--md3-on-surface-variant);
  padding: var(--md3-space-xs) 0;
  border-bottom: 1px solid var(--md3-outline-variant);
}

.dialog-form {
  display: flex;
  flex-direction: column;
  gap: var(--md3-space-md);
}

.merge-info,
.delete-info {
  font: var(--md3-type-body-medium);
  color: var(--md3-on-surface-variant);
}

.merge-info strong,
.delete-info strong {
  color: var(--md3-primary);
}
</style>
