<template>
  <div class="git-repo-panel">
    <div class="panel-actions">
      <Md3Button size="sm" @click="showInitDialog = true">初始化仓库</Md3Button>
      <Md3Button size="sm" @click="showCloneDialog = true">克隆仓库</Md3Button>
      <Md3Button size="sm" @click="showRemoteDialog = true">配置远程</Md3Button>
    </div>

    <Md3Card class="repo-info-card">
      <template #header>
        <span class="card-title">仓库信息</span>
      </template>
      <div class="repo-info-grid">
        <div class="info-item">
          <span class="info-label">当前分支</span>
          <Md3Tag type="primary" size="sm">{{ gitStore.repoInfo.current_branch || '-' }}</Md3Tag>
        </div>
        <div class="info-item">
          <span class="info-label">分支数</span>
          <span class="info-value">{{ gitStore.repoInfo.branch_count }}</span>
        </div>
        <div class="info-item">
          <span class="info-label">远程仓库</span>
          <span class="info-value">{{ gitStore.repoInfo.remotes.map(r => r.name).join(', ') || '-' }}</span>
        </div>
        <div class="info-item">
          <span class="info-label">仓库大小</span>
          <span class="info-value">{{ gitStore.repoInfo.repo_size || '-' }}</span>
        </div>
        <div class="info-item">
          <span class="info-label">最近提交</span>
          <span class="info-value">{{ gitStore.repoInfo.last_commit || '-' }}</span>
        </div>
        <div class="info-item">
          <span class="info-label">未提交变更</span>
          <Md3Tag :type="gitStore.repoInfo.is_dirty ? 'warning' : 'success'" size="sm">
            {{ gitStore.repoInfo.is_dirty ? '有变更' : '干净' }}
          </Md3Tag>
        </div>
      </div>
    </Md3Card>

    <Md3Dialog v-model:visible="showInitDialog" title="初始化仓库" width="420px">
      <div class="dialog-form">
        <Md3Input v-model="initForm.path" label="仓库路径" placeholder="/path/to/new/repo" />
        <Md3Select v-model="initForm.gitignore_template" :options="gitignoreOptions" label="Gitignore 模板" placeholder="选择模板" />
      </div>
      <template #footer>
        <Md3Button @click="showInitDialog = false">取消</Md3Button>
        <Md3Button variant="primary" @click="handleInit">初始化</Md3Button>
      </template>
    </Md3Dialog>

    <Md3Dialog v-model:visible="showCloneDialog" title="克隆仓库" width="480px">
      <div class="dialog-form">
        <Md3Input v-model="cloneForm.url" label="仓库 URL" placeholder="https://github.com/user/repo.git" />
        <Md3Input v-model="cloneForm.target_path" label="目标路径" placeholder="/path/to/clone" />
        <Md3Input v-model="cloneForm.branch" label="分支" placeholder="main" />
        <Md3Input v-model="cloneForm.depth" label="深度" placeholder="1" type="number" />
      </div>
      <template #footer>
        <Md3Button @click="showCloneDialog = false">取消</Md3Button>
        <Md3Button variant="primary" @click="handleClone">克隆</Md3Button>
      </template>
    </Md3Dialog>

    <Md3Dialog v-model:visible="showRemoteDialog" title="配置远程仓库" width="420px">
      <div class="dialog-form">
        <Md3Input v-model="remoteForm.name" label="名称" placeholder="origin" />
        <Md3Input v-model="remoteForm.url" label="URL" placeholder="https://github.com/user/repo.git" />
      </div>
      <template #footer>
        <Md3Button @click="showRemoteDialog = false">取消</Md3Button>
        <Md3Button variant="primary" @click="handleConfigRemote">保存</Md3Button>
      </template>
    </Md3Dialog>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useGitIntegrationStore } from '@/stores/gitIntegrationStore'
import {
  Md3Card,
  Md3Dialog,
  Md3Input,
  Md3Select,
  Md3Tag,
} from '@/components/md3'
import Md3Button from '@/components/Md3Button.vue'
import { Md3Message } from '@/components/md3/Md3Message'

const gitStore = useGitIntegrationStore()

const showInitDialog = ref(false)
const showCloneDialog = ref(false)
const showRemoteDialog = ref(false)

const initForm = ref({ path: '', gitignore_template: '' })
const cloneForm = ref({ url: '', target_path: '', branch: '', depth: 1 })
const remoteForm = ref({ name: 'origin', url: '' })

const gitignoreOptions = [
  { label: '无', value: '' },
  { label: 'Python', value: 'python' },
  { label: 'Node', value: 'node' },
  { label: 'Java', value: 'java' },
  { label: 'Go', value: 'go' },
  { label: 'Rust', value: 'rust' },
  { label: 'C++', value: 'cpp' },
]

async function handleInit() {
  try {
    await gitStore.initRepo(initForm.value)
    Md3Message.success('仓库初始化成功')
    showInitDialog.value = false
    initForm.value = { path: '', gitignore_template: '' }
    gitStore.fetchRepoInfo()
  } catch {
    Md3Message.error('仓库初始化失败')
  }
}

async function handleClone() {
  try {
    await gitStore.cloneRepo(cloneForm.value)
    Md3Message.success('仓库克隆成功')
    showCloneDialog.value = false
    cloneForm.value = { url: '', target_path: '', branch: '', depth: 1 }
    gitStore.fetchRepoInfo()
  } catch {
    Md3Message.error('仓库克隆失败')
  }
}

async function handleConfigRemote() {
  try {
    await gitStore.configRemote(remoteForm.value)
    Md3Message.success('远程仓库配置成功')
    showRemoteDialog.value = false
    remoteForm.value = { name: 'origin', url: '' }
    gitStore.fetchRepoInfo()
  } catch {
    Md3Message.error('远程仓库配置失败')
  }
}
</script>

<style scoped>
.panel-actions {
  display: flex;
  gap: var(--md3-space-sm);
  margin-bottom: var(--md3-space-md);
}

.repo-info-card {
  margin-bottom: var(--md3-space-md);
}

.card-title {
  font: var(--md3-type-title-medium);
  color: var(--md3-on-surface);
}

.repo-info-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--md3-space-lg);
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.info-label {
  font: var(--md3-type-body-small);
  color: var(--md3-outline);
}

.info-value {
  font: var(--md3-type-body-medium);
  color: var(--md3-on-surface);
}

.dialog-form {
  display: flex;
  flex-direction: column;
  gap: var(--md3-space-md);
}
</style>
