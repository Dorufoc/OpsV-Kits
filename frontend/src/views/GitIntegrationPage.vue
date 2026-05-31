<template>
  <div class="git-integration-page">
    <Md3PageHeader title="Git 集成" subtitle="代码仓库管理与自动部署" />

    <Md3Divider />

    <Md3Card class="account-card">
      <div class="git-toolbar">
        <Md3Select
          v-model="accountAlias"
          :options="accountOptions"
          label="SSH 账户"
          placeholder="选择 SSH 服务器"
          style="width: 280px"
          @update:model-value="onAccountChange"
        />
        <Md3Input
          v-model="repoPath"
          label="仓库路径"
          placeholder="/path/to/repo"
          style="flex: 1"
        />
        <Md3Button variant="primary" @click="loadRepoInfo">加载</Md3Button>
      </div>
    </Md3Card>

    <template v-if="gitStore.currentAlias && gitStore.repoPath">
      <Md3Tabs v-model="activeTab" :tabs="tabs" class="git-tabs" />

      <div class="git-content">
        <GitRepoPanel v-if="activeTab === 'repo'" />
        <GitBranchPanel v-if="activeTab === 'branch'" />
        <GitCommitPanel v-if="activeTab === 'commit'" />
        <WebhookDeployPanel v-if="activeTab === 'webhook'" />
        <GitSyncPanel v-if="activeTab === 'sync'" />
      </div>
    </template>

    <Md3Empty v-else description="请先选择 SSH 账户并输入仓库路径" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, markRaw } from 'vue'
import { Md3Icon } from '@/components/md3'
import { useGitIntegrationStore } from '@/stores/gitIntegrationStore'
import { useSshAccountStore } from '@/stores/sshAccountStore'
import {
  Md3PageHeader,
  Md3Divider,
  Md3Card,
  Md3Select,
  Md3Input,
  Md3Tabs,
  Md3Empty,
} from '@/components/md3'
import Md3Button from '@/components/Md3Button.vue'
import GitRepoPanel from '@/components/GitRepoPanel.vue'
import GitBranchPanel from '@/components/GitBranchPanel.vue'
import GitCommitPanel from '@/components/GitCommitPanel.vue'
import WebhookDeployPanel from '@/components/WebhookDeployPanel.vue'
import GitSyncPanel from '@/components/GitSyncPanel.vue'

const gitStore = useGitIntegrationStore()
const sshStore = useSshAccountStore()

const accountAlias = ref('')
const repoPath = ref('')
const activeTab = ref('repo')

const accountOptions = computed(() =>
  sshStore.accounts.map(acc => ({
    label: `${acc.alias} (${acc.host})`,
    value: acc.alias,
  }))
)

const tabs = computed(() => [
  { label: '仓库管理', value: 'repo', icon: markRaw({ template: '<Md3Icon name="folder" size="1em" />', components: { Md3Icon } }) },
  { label: '分支管理', value: 'branch', icon: markRaw({ template: '<Md3Icon name="connection" size="1em" />', components: { Md3Icon } }) },
  { label: '提交记录', value: 'commit', icon: markRaw({ template: '<Md3Icon name="coin" size="1em" />', components: { Md3Icon } }) },
  { label: 'Webhook 部署', value: 'webhook', icon: markRaw({ template: '<Md3Icon name="refresh" size="1em" />', components: { Md3Icon } }) },
  { label: '同步管理', value: 'sync', icon: markRaw({ template: '<Md3Icon name="download" size="1em" />', components: { Md3Icon } }) },
])

function onAccountChange(value: string | number | (string | number)[]) {
  const alias = String(value)
  gitStore.setAccountAlias(alias)
}

function loadRepoInfo() {
  if (!accountAlias.value || !repoPath.value) return
  gitStore.setAccountAlias(accountAlias.value)
  gitStore.setRepoPath(repoPath.value)
  gitStore.fetchRepoInfo()
}

onMounted(async () => {
  await sshStore.fetchAccounts()
  const defaultAcc = sshStore.accounts.find(a => a.default)
  const firstAcc = sshStore.accounts[0]
  const alias = defaultAcc?.alias || firstAcc?.alias || ''
  if (alias) {
    accountAlias.value = alias
    gitStore.setAccountAlias(alias)
  }
})
</script>

<style scoped>
.git-integration-page {
  padding: 0;
}

.account-card {
  margin-bottom: var(--md3-space-md);
}

.git-toolbar {
  display: flex;
  align-items: flex-end;
  gap: var(--md3-space-md);
}

.git-tabs {
  margin-top: var(--md3-space-sm);
  margin-bottom: var(--md3-space-lg);
}

.git-content {
  margin-top: var(--md3-space-md);
}
</style>
