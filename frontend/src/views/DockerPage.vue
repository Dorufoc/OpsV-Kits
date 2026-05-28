<template>
  <div class="docker-page">
    <Md3PageHeader title="Docker 管理" :show-back="true" @back="router.push('/')" />

    <Md3Divider />

    <Md3Card class="account-card">
      <div class="account-selector">
        <span class="selector-label">SSH 服务器:</span>
        <Md3Select
          v-model="selectedAlias"
          :options="sshOptions"
          placeholder="选择 SSH 服务器管理 Docker"
          style="width: 280px"
          @update:model-value="onAccountChange"
        />
      </div>
    </Md3Card>

    <template v-if="dockerStore.currentAlias">
      <Md3Card class="env-card">
        <div class="env-info">
          <div class="env-item">
            <span class="env-label">Docker 环境:</span>
            <Md3Tag v-if="dockerInfo.version" type="success" size="sm">
              🟢 已安装 (v{{ dockerInfo.version }})
            </Md3Tag>
            <Md3Tag v-else type="danger" size="sm">未检测到</Md3Tag>
          </div>
          <div class="env-item">
            <span class="env-label">守护进程:</span>
            <Md3Tag :type="dockerInfo.daemon_status === 'running' ? 'success' : 'danger'" size="sm">
              {{ dockerInfo.daemon_status === 'running' ? '🟢 运行中' : '🔴 已停止' }}
            </Md3Tag>
          </div>
          <div class="env-item">
            <span class="env-label">Docker 权限:</span>
            <Md3Tag :type="dockerInfo.docker_group ? 'success' : 'warning'" size="sm">
              {{ dockerInfo.docker_group ? '✅ (docker 组)' : '⚠️ 无权限' }}
            </Md3Tag>
          </div>
        </div>
      </Md3Card>

      <Md3Tabs v-model="activeTab" :tabs="tabItems" class="docker-tabs" />

      <div class="tab-content">
        <template v-if="activeTab === 'containers'">
          <ContainerList
            :containers="dockerStore.containers"
            @start="handleStart"
            @stop="handleStop"
            @restart="handleRestart"
            @logs="handleLogs"
            @terminal="handleTerminal"
            @delete="handleDelete"
            @selection-change="selectedContainers = $event"
          />

          <div class="batch-actions" v-if="selectedContainers.length > 0">
            <span class="batch-label">批量操作:</span>
            <Md3Button size="sm" @click="batchStart">启动选中</Md3Button>
            <Md3Button size="sm" @click="batchStop">停止选中</Md3Button>
            <Md3Button size="sm" variant="danger" @click="batchDelete">删除选中</Md3Button>
          </div>
        </template>

        <template v-if="activeTab === 'images'">
          <div class="tab-actions">
            <Md3Button size="sm" @click="showPullDialog = true"><Md3Icon name="download" size="1em" />拉取</Md3Button>
            <Md3Button size="sm" @click="showBuildDialog = true"><Md3Icon name="refresh" size="1em" />构建</Md3Button>
            <Md3Button size="sm" @click="pruneImages"><Md3Icon name="delete" size="1em" />清理悬空</Md3Button>
          </div>

          <ImageList
            :images="dockerStore.images"
            @pull="showPullDialog = true"
            @build="showBuildDialog = true"
            @delete="handleImageDelete"
          />
        </template>

        <template v-if="activeTab === 'networks'">
          <div class="tab-actions">
            <Md3Button size="sm" @click="showNetworkDialog = true"><Md3Icon name="plus" size="1em" />创建网络</Md3Button>
          </div>

          <Md3Table
            :columns="networkColumns"
            :data="dockerStore.networks"
            stripe
            empty-text="暂无网络数据"
          >
            <template #actions="{ row }">
              <Md3Button size="sm" variant="danger" @click="confirmDeleteNetwork(row)"><Md3Icon name="delete" size="1em" />删除</Md3Button>
            </template>
          </Md3Table>
        </template>

        <template v-if="activeTab === 'volumes'">
          <div class="tab-actions">
            <Md3Button size="sm" @click="showVolumeDialog = true"><Md3Icon name="plus" size="1em" />创建卷</Md3Button>
          </div>

          <Md3Table
            :columns="volumeColumns"
            :data="dockerStore.volumes"
            stripe
            empty-text="暂无卷数据"
          >
            <template #actions="{ row }">
              <Md3Button size="sm" variant="danger" @click="confirmDeleteVolume(row)"><Md3Icon name="delete" size="1em" />删除</Md3Button>
            </template>
          </Md3Table>
        </template>

        <template v-if="activeTab === 'compose'">
          <Md3Table
            :columns="composeColumns"
            :data="dockerStore.composeProjects"
            stripe
            empty-text="暂无 Compose 项目"
          >
            <template #services="{ row }">
              <Md3Tag
                v-for="svc in row.services"
                :key="svc"
                size="sm"
                class="service-tag"
              >{{ svc }}</Md3Tag>
            </template>
            <template #actions="{ row }">
              <Md3Button size="sm" variant="default" @click="dockerStore.composeUp({ path: row.path as string, detached: true })"><Md3Icon name="play" size="1em" />启动</Md3Button>
              <Md3Button size="sm" variant="default" @click="dockerStore.composeDown({ path: row.path as string })"><Md3Icon name="pause" size="1em" />停止</Md3Button>
            </template>
          </Md3Table>
        </template>
      </div>
    </template>

    <Md3Empty v-else description="请先选择一个 SSH 服务器来管理 Docker" />

    <Md3Dialog v-model:visible="showPullDialog" title="拉取镜像" width="420px">
      <div class="dialog-form">
        <Md3Input v-model="pullForm.repository" label="镜像名称" placeholder="如：nginx" />
        <Md3Input v-model="pullForm.tag" label="标签" placeholder="latest" />
      </div>
      <template #footer>
        <Md3Button @click="showPullDialog = false">取消</Md3Button>
        <Md3Button variant="primary" @click="pullImage">拉取</Md3Button>
      </template>
    </Md3Dialog>

    <Md3Dialog v-model:visible="showBuildDialog" title="构建镜像" width="420px">
      <div class="dialog-form">
        <Md3Input v-model="buildForm.dockerfile_path" label="Dockerfile 路径" placeholder="/path/to/Dockerfile" />
        <Md3Input v-model="buildForm.tag" label="标签" placeholder="myapp:latest" />
      </div>
      <template #footer>
        <Md3Button @click="showBuildDialog = false">取消</Md3Button>
        <Md3Button variant="primary" @click="buildImage">构建</Md3Button>
      </template>
    </Md3Dialog>

    <Md3Dialog v-model:visible="showNetworkDialog" title="创建网络" width="420px">
      <div class="dialog-form">
        <Md3Input v-model="networkForm.name" label="名称" placeholder="网络名称" />
        <Md3Select v-model="networkForm.driver" :options="networkDriverOptions" label="驱动" placeholder="选择驱动" />
      </div>
      <template #footer>
        <Md3Button @click="showNetworkDialog = false">取消</Md3Button>
        <Md3Button variant="primary" @click="createNetwork">创建</Md3Button>
      </template>
    </Md3Dialog>

    <Md3Dialog v-model:visible="showVolumeDialog" title="创建卷" width="420px">
      <div class="dialog-form">
        <Md3Input v-model="volumeForm.name" label="卷名称" placeholder="卷名称" />
      </div>
      <template #footer>
        <Md3Button @click="showVolumeDialog = false">取消</Md3Button>
        <Md3Button variant="primary" @click="createVolume">创建</Md3Button>
      </template>
    </Md3Dialog>

    <Md3Dialog v-model:visible="showErrorLogDialog" title="容器启动失败日志" width="700px">
      <textarea
        v-model="errorLogContent"
        readonly
        class="error-log-textarea"
      />
      <template #footer>
        <Md3Button @click="showErrorLogDialog = false">关闭</Md3Button>
      </template>
    </Md3Dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, markRaw } from 'vue'
import { useRouter } from 'vue-router'
import { Md3Icon } from '@/components/md3'
import { useDockerStore, type DockerContainer } from '@/stores/dockerStore'
import { useSshAccountStore } from '@/stores/sshAccountStore'
import {
  Md3Dialog,
  Md3Input,
  Md3Select,
  Md3Tag,
  Md3Table,
  Md3Tabs,
  Md3PageHeader,
  Md3Divider,
  Md3Card,
  Md3Empty,
} from '@/components/md3'
import Md3Button from '@/components/Md3Button.vue'
import { Md3Confirm } from '@/components/md3/Md3Confirm'
import ContainerList from '@/components/ContainerList.vue'
import ImageList from '@/components/ImageList.vue'

const router = useRouter()
const dockerStore = useDockerStore()
const sshStore = useSshAccountStore()

const selectedAlias = ref('')
const activeTab = ref('containers')
const selectedContainers = ref<DockerContainer[]>([])

const showPullDialog = ref(false)
const showBuildDialog = ref(false)
const showNetworkDialog = ref(false)
const showVolumeDialog = ref(false)
const showErrorLogDialog = ref(false)

const pullForm = ref({ repository: '', tag: 'latest' })
const buildForm = ref({ dockerfile_path: '', tag: '' })
const networkForm = ref({ name: '', driver: 'bridge' })
const volumeForm = ref({ name: '' })
const errorLogContent = ref('')

const dockerInfo = computed(() => dockerStore.dockerInfo)
const sshAccounts = computed(() => sshStore.accounts)

const sshOptions = computed(() =>
  sshAccounts.value.map(acc => ({
    label: `${acc.alias} (${acc.host})`,
    value: acc.alias,
  }))
)

const tabItems = computed(() => [
  { label: '容器', value: 'containers', icon: markRaw({ template: '<Md3Icon name="box" size="1em" />', components: { Md3Icon } }) },
  { label: '镜像', value: 'images', icon: markRaw({ template: '<Md3Icon name="coin" size="1em" />', components: { Md3Icon } }) },
  { label: '网络', value: 'networks', icon: markRaw({ template: '<Md3Icon name="connection" size="1em" />', components: { Md3Icon } }) },
  { label: '卷', value: 'volumes', icon: markRaw({ template: '<Md3Icon name="folder" size="1em" />', components: { Md3Icon } }) },
  { label: 'Compose', value: 'compose', icon: markRaw({ template: '<Md3Icon name="folder-multiple" size="1em" />', components: { Md3Icon } }) },
])

const networkColumns = [
  { prop: 'name', label: '名称' },
  { prop: 'driver', label: '驱动' },
  { prop: 'scope', label: '范围' },
  { prop: 'containers', label: '连接容器数' },
  { prop: 'actions', label: '操作' },
]

const volumeColumns = [
  { prop: 'name', label: '名称' },
  { prop: 'driver', label: '驱动' },
  { prop: 'mountpoint', label: '挂载点' },
  { prop: 'size', label: '大小' },
  { prop: 'actions', label: '操作' },
]

const composeColumns = [
  { prop: 'name', label: '项目名' },
  { prop: 'path', label: '路径' },
  { prop: 'status', label: '状态' },
  { prop: 'services', label: '服务' },
  { prop: 'actions', label: '操作' },
]

const networkDriverOptions = [
  { label: 'bridge', value: 'bridge' },
  { label: 'host', value: 'host' },
  { label: 'overlay', value: 'overlay' },
  { label: 'macvlan', value: 'macvlan' },
]

function onAccountChange(value: string | number | (string | number)[]) {
  const alias = String(value)
  dockerStore.setAccountAlias(alias)
  refreshAll()
}

function refreshAll() {
  dockerStore.fetchInfo()
  dockerStore.fetchContainers()
  dockerStore.fetchImages()
  dockerStore.fetchNetworks()
  dockerStore.fetchVolumes()
  dockerStore.fetchComposeProjects()
}

async function handleStart(container: DockerContainer) {
  const result = await dockerStore.startContainer(container.id)
  if (!result.success && result.errorLogs) {
    errorLogContent.value = result.errorLogs
    showErrorLogDialog.value = true
  }
}

function handleStop(container: DockerContainer) {
  dockerStore.stopContainer(container.id)
}

function handleRestart(container: DockerContainer) {
  dockerStore.restartContainer(container.id)
}

function handleLogs(container: DockerContainer) {
  router.push(`/docker/container/${container.id}`)
}

function handleTerminal(container: DockerContainer) {
  router.push(`/docker/container/${container.id}?tab=terminal`)
}

function handleDelete(container: DockerContainer) {
  dockerStore.deleteContainer(container.id)
}

function handleImageDelete(image: any) {
  dockerStore.deleteImage(image.id)
}

async function pullImage() {
  await dockerStore.pullImage(pullForm.value)
  showPullDialog.value = false
  pullForm.value = { repository: '', tag: 'latest' }
}

async function buildImage() {
  await dockerStore.buildImage(buildForm.value)
  showBuildDialog.value = false
  buildForm.value = { dockerfile_path: '', tag: '' }
}

async function pruneImages() {
  await dockerStore.pruneImages()
}

function confirmDeleteNetwork(row: any) {
  Md3Confirm.show({
    title: '确认删除',
    message: '确认删除该网络?',
  }).then(confirmed => {
    if (confirmed) {
      dockerStore.deleteNetwork(row.id)
    }
  })
}

function confirmDeleteVolume(row: any) {
  Md3Confirm.show({
    title: '确认删除',
    message: '确认删除该卷?',
  }).then(confirmed => {
    if (confirmed) {
      dockerStore.deleteVolume(row.name)
    }
  })
}

async function createNetwork() {
  await dockerStore.createNetwork(networkForm.value)
  showNetworkDialog.value = false
  networkForm.value = { name: '', driver: 'bridge' }
}

async function createVolume() {
  await dockerStore.createVolume(volumeForm.value)
  showVolumeDialog.value = false
  volumeForm.value = { name: '' }
}

function batchStart() {
  selectedContainers.value.forEach(c => dockerStore.startContainer(c.id))
}

function batchStop() {
  selectedContainers.value.forEach(c => dockerStore.stopContainer(c.id))
}

function batchDelete() {
  selectedContainers.value.forEach(c => dockerStore.deleteContainer(c.id))
}

onMounted(async () => {
  await sshStore.fetchAccounts()
  const defaultAcc = sshStore.accounts.find(a => a.default)
  const firstAcc = sshStore.accounts[0]
  const alias = defaultAcc?.alias || firstAcc?.alias || ''
  if (alias) {
    selectedAlias.value = alias
    dockerStore.setAccountAlias(alias)
    refreshAll()
  }
})
</script>

<style scoped>
.docker-page {
  padding: 0;
}

.account-card {
  margin-bottom: var(--md3-space-md);
}

.account-selector {
  display: flex;
  align-items: center;
  gap: var(--md3-space-sm);
}

.selector-label {
  font: var(--md3-type-body-medium);
  color: var(--md3-on-surface-variant);
  white-space: nowrap;
}

.env-card {
  margin-bottom: var(--md3-space-lg);
}

.env-info {
  display: flex;
  gap: var(--md3-space-xl);
  flex-wrap: wrap;
}

.env-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
}

.env-label {
  color: var(--md3-outline);
  white-space: nowrap;
}

.docker-tabs {
  margin-top: var(--md3-space-sm);
  margin-bottom: var(--md3-space-lg);
}

.tab-content {
  margin-top: var(--md3-space-md);
}

.tab-actions {
  display: flex;
  gap: var(--md3-space-sm);
  margin-bottom: var(--md3-space-md);
}

.batch-actions {
  display: flex;
  align-items: center;
  gap: var(--md3-space-sm);
  margin-top: var(--md3-space-md);
  padding: var(--md3-space-sm);
  background: var(--md3-surface-container-low);
  border-radius: var(--md3-shape-sm);
  border: 1px solid var(--md3-glass-border);
  transition: box-shadow var(--md3-motion-duration-short) var(--md3-motion-easing-standard);
}

.batch-actions:hover {
  box-shadow: var(--md3-elevation-level1);
}

.batch-label {
  font-size: 12px;
  color: var(--md3-outline);
}

.service-tag {
  margin-right: 4px;
  margin-bottom: 2px;
}

.dialog-form {
  display: flex;
  flex-direction: column;
  gap: var(--md3-space-md);
}

.error-log-textarea {
  width: 100%;
  min-height: 300px;
  font-family: var(--md3-font-mono);
  font-size: 12px;
  background-color: var(--md3-inverse-surface);
  color: var(--md3-inverse-on-surface);
  border: 1px solid var(--md3-outline-variant);
  border-radius: var(--md3-shape-xs);
  padding: var(--md3-space-md);
  resize: vertical;
  outline: none;
}

.error-log-textarea:focus {
  border-color: var(--md3-primary);
}
</style>
