<template>
  <div class="webhook-deploy-panel">
    <Md3Card class="section-card">
      <template #header>
        <span class="card-title">Webhook 配置</span>
      </template>
      <div class="section-actions">
        <Md3Button size="sm" @click="showWebhookDialog = true">创建 Webhook</Md3Button>
        <Md3Button size="sm" @click="gitStore.fetchWebhooks()">刷新</Md3Button>
      </div>
      <Md3Table
        :columns="webhookColumns"
        :data="gitStore.webhooks"
        stripe
        hover
        empty-text="暂无 Webhook 配置"
      >
        <template #status="{ row }">
          <Md3Tag :type="row.status === 'active' ? 'success' : 'danger'" size="sm">
            {{ row.status === 'active' ? '启用' : '停用' }}
          </Md3Tag>
        </template>
        <template #actions="{ row }">
          <div class="row-actions">
            <Md3Button size="sm" @click="handleToggleWebhook(row)">
              {{ row.status === 'active' ? '停用' : '启用' }}
            </Md3Button>
            <Md3Button size="sm" variant="danger" @click="handleDeleteWebhook(row.id)">删除</Md3Button>
          </div>
        </template>
      </Md3Table>
    </Md3Card>

    <Md3Card class="section-card">
      <template #header>
        <span class="card-title">部署流程</span>
      </template>
      <div class="section-actions">
        <Md3Button size="sm" @click="openPipelineDialog()">创建流程</Md3Button>
        <Md3Button size="sm" @click="gitStore.fetchPipelines()">刷新</Md3Button>
      </div>
      <Md3Table
        :columns="pipelineColumns"
        :data="gitStore.pipelines"
        stripe
        hover
        empty-text="暂无部署流程"
      >
        <template #stages="{ row }">
          <Md3Tag v-for="s in row.stages" :key="s" size="sm" class="stage-tag">{{ s }}</Md3Tag>
        </template>
        <template #actions="{ row }">
          <div class="row-actions">
            <Md3Button size="sm" @click="openPipelineDialog(row)">编辑</Md3Button>
            <Md3Button size="sm" variant="danger" @click="handleDeletePipeline(row.id)">删除</Md3Button>
          </div>
        </template>
      </Md3Table>
    </Md3Card>

    <Md3Card class="section-card">
      <template #header>
        <span class="card-title">部署历史</span>
      </template>
      <div class="section-actions">
        <Md3Button size="sm" @click="gitStore.fetchDeployHistory()">刷新</Md3Button>
      </div>
      <Md3Table
        :columns="historyColumns"
        :data="gitStore.deployHistory"
        stripe
        hover
        empty-text="暂无部署历史"
      >
        <template #status="{ row }">
          <Md3Tag :type="deployStatusType(row.status)" size="sm">
            {{ deployStatusLabel(row.status) }}
          </Md3Tag>
        </template>
        <template #actions="{ row }">
          <Md3Button size="sm" variant="warning" @click="handleRollback(row.id)">回滚</Md3Button>
        </template>
      </Md3Table>
    </Md3Card>

    <Md3Dialog v-model:visible="showWebhookDialog" title="创建 Webhook" width="480px">
      <div class="dialog-form">
        <Md3Select v-model="webhookForm.platform" :options="platformOptions" label="平台" placeholder="选择平台" />
        <Md3Select v-model="webhookForm.event" :options="eventOptions" label="事件" placeholder="选择事件" />
        <Md3Input v-model="webhookForm.branch_filter" label="分支过滤" placeholder="main,develop" />
      </div>
      <template #footer>
        <Md3Button @click="showWebhookDialog = false">取消</Md3Button>
        <Md3Button variant="primary" @click="handleCreateWebhook">创建</Md3Button>
      </template>
    </Md3Dialog>

    <Md3Dialog v-model:visible="showPipelineDialog" :title="pipelineEditId ? '编辑部署流程' : '创建部署流程'" width="560px">
      <div class="dialog-form">
        <Md3Input v-model="pipelineForm.name" label="流程名称" placeholder="deploy-production" />
        <Md3Input v-model="pipelineForm.trigger_branch" label="触发分支" placeholder="main" />
        <div class="yaml-editor-label">YAML 配置</div>
        <textarea
          v-model="pipelineForm.yaml_content"
          class="yaml-editor"
          placeholder="stages:&#10;  - build&#10;  - test&#10;  - deploy"
        />
      </div>
      <template #footer>
        <Md3Button @click="showPipelineDialog = false">取消</Md3Button>
        <Md3Button variant="primary" @click="handleSavePipeline">保存</Md3Button>
      </template>
    </Md3Dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useGitIntegrationStore, type DeployPipeline } from '@/stores/gitIntegrationStore'
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
import { Md3Confirm } from '@/components/md3/Md3Confirm'

const gitStore = useGitIntegrationStore()

const showWebhookDialog = ref(false)
const showPipelineDialog = ref(false)
const pipelineEditId = ref('')

const webhookForm = ref({ platform: '', event: '', branch_filter: '' })
const pipelineForm = ref({ name: '', trigger_branch: '', yaml_content: '' })

const webhookColumns = [
  { prop: 'platform', label: '平台' },
  { prop: 'event', label: '事件' },
  { prop: 'branch_filter', label: '分支过滤' },
  { prop: 'status', label: '状态' },
  { prop: 'actions', label: '操作' },
]

const pipelineColumns = [
  { prop: 'name', label: '名称' },
  { prop: 'trigger_branch', label: '触发分支' },
  { prop: 'stages', label: '阶段' },
  { prop: 'actions', label: '操作' },
]

const historyColumns = [
  { prop: 'time', label: '时间' },
  { prop: 'trigger_type', label: '触发方式' },
  { prop: 'branch', label: '分支' },
  { prop: 'status', label: '状态' },
  { prop: 'duration', label: '耗时' },
  { prop: 'actions', label: '操作' },
]

const platformOptions = [
  { label: 'GitHub', value: 'github' },
  { label: 'GitLab', value: 'gitlab' },
  { label: 'Gitea', value: 'gitea' },
  { label: 'Gogs', value: 'gogs' },
]

const eventOptions = [
  { label: 'Push', value: 'push' },
  { label: 'Tag', value: 'tag' },
  { label: 'Pull Request', value: 'pull_request' },
]

function deployStatusType(status: string) {
  if (status === 'success') return 'success'
  if (status === 'failed') return 'danger'
  return 'warning'
}

function deployStatusLabel(status: string) {
  if (status === 'success') return '成功'
  if (status === 'failed') return '失败'
  return '运行中'
}

async function handleCreateWebhook() {
  try {
    await gitStore.createWebhook(webhookForm.value)
    Md3Message.success('Webhook 创建成功')
    showWebhookDialog.value = false
    webhookForm.value = { platform: '', event: '', branch_filter: '' }
    gitStore.fetchWebhooks()
  } catch {
    Md3Message.error('Webhook 创建失败')
  }
}

async function handleToggleWebhook(row: any) {
  const newStatus = row.status === 'active' ? 'inactive' : 'active'
  try {
    await gitStore.toggleWebhook(row.id, newStatus)
    Md3Message.success('状态已更新')
    gitStore.fetchWebhooks()
  } catch {
    Md3Message.error('状态更新失败')
  }
}

async function handleDeleteWebhook(id: string) {
  const confirmed = await Md3Confirm.show({ title: '确认删除', message: '确认删除该 Webhook？' })
  if (!confirmed) return
  try {
    await gitStore.deleteWebhook(id)
    Md3Message.success('已删除')
    gitStore.fetchWebhooks()
  } catch {
    Md3Message.error('删除失败')
  }
}

function openPipelineDialog(pipeline?: DeployPipeline) {
  if (pipeline) {
    pipelineEditId.value = pipeline.id
    pipelineForm.value = {
      name: pipeline.name,
      trigger_branch: pipeline.trigger_branch,
      yaml_content: pipeline.yaml_content,
    }
  } else {
    pipelineEditId.value = ''
    pipelineForm.value = { name: '', trigger_branch: '', yaml_content: '' }
  }
  showPipelineDialog.value = true
}

async function handleSavePipeline() {
  try {
    if (pipelineEditId.value) {
      await gitStore.updatePipeline(pipelineEditId.value, pipelineForm.value)
      Md3Message.success('流程已更新')
    } else {
      await gitStore.createPipeline(pipelineForm.value)
      Md3Message.success('流程创建成功')
    }
    showPipelineDialog.value = false
    gitStore.fetchPipelines()
  } catch {
    Md3Message.error('保存失败')
  }
}

async function handleDeletePipeline(id: string) {
  const confirmed = await Md3Confirm.show({ title: '确认删除', message: '确认删除该部署流程？' })
  if (!confirmed) return
  try {
    await gitStore.deletePipeline(id)
    Md3Message.success('已删除')
    gitStore.fetchPipelines()
  } catch {
    Md3Message.error('删除失败')
  }
}

async function handleRollback(historyId: string) {
  const confirmed = await Md3Confirm.show({ title: '确认回滚', message: '确认回滚到该部署版本？' })
  if (!confirmed) return
  try {
    await gitStore.rollback(historyId)
    Md3Message.success('回滚成功')
    gitStore.fetchDeployHistory()
  } catch {
    Md3Message.error('回滚失败')
  }
}

onMounted(() => {
  gitStore.fetchWebhooks()
  gitStore.fetchPipelines()
  gitStore.fetchDeployHistory()
})
</script>

<style scoped>
.section-card {
  margin-bottom: var(--md3-space-lg);
}

.card-title {
  font: var(--md3-type-title-medium);
  color: var(--md3-on-surface);
}

.section-actions {
  display: flex;
  gap: var(--md3-space-sm);
  margin-bottom: var(--md3-space-md);
}

.row-actions {
  display: flex;
  gap: var(--md3-space-xs);
}

.stage-tag {
  margin-right: 4px;
  margin-bottom: 2px;
}

.dialog-form {
  display: flex;
  flex-direction: column;
  gap: var(--md3-space-md);
}

.yaml-editor-label {
  font: var(--md3-type-body-small);
  color: var(--md3-outline);
}

.yaml-editor {
  width: 100%;
  min-height: 200px;
  font-family: var(--md3-font-mono);
  font-size: 13px;
  background: var(--md3-inverse-surface);
  color: var(--md3-inverse-on-surface);
  border: 1px solid var(--md3-outline-variant);
  border-radius: var(--md3-shape-xs);
  padding: var(--md3-space-md);
  resize: vertical;
  outline: none;
}

.yaml-editor:focus {
  border-color: var(--md3-primary);
}
</style>
