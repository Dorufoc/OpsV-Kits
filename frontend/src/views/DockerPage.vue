<template>
  <div class="docker-page">
    <el-page-header title="OpsV-Kits">
      <template #content>
        <span>Docker 管理</span>
      </template>
      <template #extra>
        <Md3Button size="sm" :icon="Refresh" @click="refreshAll" :disabled="!dockerStore.currentAlias">刷新</Md3Button>
      </template>
    </el-page-header>
    <el-divider />

    <el-card shadow="never" class="account-card">
      <div class="account-selector">
        <span class="selector-label">SSH 服务器:</span>
        <el-select
          v-model="selectedAlias"
          placeholder="选择 SSH 服务器管理 Docker"
          style="width: 280px"
          @change="onAccountChange"
        >
          <el-option
            v-for="acc in sshAccounts"
            :key="acc.alias"
            :label="`${acc.alias} (${acc.host})`"
            :value="acc.alias"
          />
        </el-select>
      </div>
    </el-card>

    <template v-if="dockerStore.currentAlias">
      <el-card shadow="never" class="env-card">
        <div class="env-info">
          <div class="env-item">
            <span class="env-label">Docker 环境:</span>
            <el-tag v-if="dockerInfo.version" type="success" size="small">
              🟢 已安装 (v{{ dockerInfo.version }})
            </el-tag>
            <el-tag v-else type="danger" size="small">未检测到</el-tag>
          </div>
          <div class="env-item">
            <span class="env-label">守护进程:</span>
            <el-tag :type="dockerInfo.daemon_status === 'running' ? 'success' : 'danger'" size="small">
              {{ dockerInfo.daemon_status === 'running' ? '🟢 运行中' : '🔴 已停止' }}
            </el-tag>
          </div>
          <div class="env-item">
            <span class="env-label">Docker 权限:</span>
            <el-tag :type="dockerInfo.docker_group ? 'success' : 'warning'" size="small">
              {{ dockerInfo.docker_group ? '✅ (docker 组)' : '⚠️ 无权限' }}
            </el-tag>
          </div>
        </div>
      </el-card>

      <el-tabs v-model="activeTab" class="docker-tabs">
        <el-tab-pane label="容器" name="containers">
          <template #label>
            <span><el-icon :size="14"><Box /></el-icon> 容器</span>
          </template>

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
        </el-tab-pane>

        <el-tab-pane label="镜像" name="images">
          <template #label>
            <span><el-icon :size="14"><Coin /></el-icon> 镜像</span>
          </template>

          <div class="tab-actions">
            <Md3Button size="sm" :icon="Download" @click="showPullDialog = true">拉取</Md3Button>
            <Md3Button size="sm" :icon="Refresh" @click="showBuildDialog = true">构建</Md3Button>
            <Md3Button size="sm" :icon="Delete" @click="pruneImages">清理悬空</Md3Button>
          </div>

          <ImageList
            :images="dockerStore.images"
            @pull="showPullDialog = true"
            @build="showBuildDialog = true"
            @delete="handleImageDelete"
          />
        </el-tab-pane>

        <el-tab-pane label="网络" name="networks">
          <template #label>
            <span><el-icon :size="14"><Connection /></el-icon> 网络</span>
          </template>

          <div class="tab-actions">
            <Md3Button size="sm" :icon="Plus" @click="showNetworkDialog = true">创建网络</Md3Button>
          </div>

          <el-table :data="dockerStore.networks" size="small" stripe>
            <el-table-column prop="name" label="名称" min-width="160" />
            <el-table-column prop="driver" label="驱动" width="100" />
            <el-table-column prop="scope" label="范围" width="80" />
            <el-table-column prop="containers" label="连接容器数" width="120" align="center" />
            <el-table-column label="操作" width="100">
              <template #default="{ row }">
                <el-popconfirm title="确认删除?" @confirm="dockerStore.deleteNetwork(row.id)">
                  <template #reference>
                    <Md3Button :icon="Delete" size="sm" variant="danger">删除</Md3Button>
                  </template>
                </el-popconfirm>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <el-tab-pane label="卷" name="volumes">
          <template #label>
            <span><el-icon :size="14"><Folder /></el-icon> 卷</span>
          </template>

          <div class="tab-actions">
            <Md3Button size="sm" :icon="Plus" @click="showVolumeDialog = true">创建卷</Md3Button>
          </div>

          <el-table :data="dockerStore.volumes" size="small" stripe>
            <el-table-column prop="name" label="名称" min-width="160" />
            <el-table-column prop="driver" label="驱动" width="100" />
            <el-table-column prop="mountpoint" label="挂载点" min-width="200" />
            <el-table-column prop="size" label="大小" width="80" align="right" />
            <el-table-column label="操作" width="100">
              <template #default="{ row }">
                <el-popconfirm title="确认删除?" @confirm="dockerStore.deleteVolume(row.name)">
                  <template #reference>
                    <Md3Button :icon="Delete" size="sm" variant="danger">删除</Md3Button>
                  </template>
                </el-popconfirm>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <el-tab-pane label="Compose" name="compose">
          <template #label>
            <span><el-icon :size="14"><Files /></el-icon> Compose</span>
          </template>

          <el-table :data="dockerStore.composeProjects" size="small" stripe>
            <el-table-column prop="name" label="项目名" min-width="160" />
            <el-table-column prop="path" label="路径" min-width="240" />
            <el-table-column prop="status" label="状态" width="120" />
            <el-table-column label="服务" min-width="200">
              <template #default="{ row }">
                <el-tag
                  v-for="svc in row.services"
                  :key="svc"
                  size="small"
                  style="margin-right: 4px; margin-bottom: 2px"
                >{{ svc }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="200">
              <template #default="{ row }">
                <Md3Button :icon="VideoPlay" size="sm" variant="default" @click="dockerStore.composeUp({ path: row.path, detached: true })">启动</Md3Button>
                <Md3Button :icon="VideoPause" size="sm" variant="default" @click="dockerStore.composeDown({ path: row.path })">停止</Md3Button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>
      </el-tabs>
    </template>

    <el-empty v-else description="请先选择一个 SSH 服务器来管理 Docker" />

    <el-dialog v-model="showPullDialog" title="拉取镜像" width="420px">
      <el-form label-width="80px">
        <el-form-item label="镜像名称" required>
          <el-input v-model="pullForm.repository" placeholder="如：nginx" />
        </el-form-item>
        <el-form-item label="标签">
          <el-input v-model="pullForm.tag" placeholder="latest" />
        </el-form-item>
      </el-form>
      <template #footer>
        <Md3Button @click="showPullDialog = false">取消</Md3Button>
        <Md3Button variant="primary" @click="pullImage">拉取</Md3Button>
      </template>
    </el-dialog>

    <el-dialog v-model="showBuildDialog" title="构建镜像" width="420px">
      <el-form label-width="120px">
        <el-form-item label="Dockerfile 路径" required>
          <el-input v-model="buildForm.dockerfile_path" placeholder="/path/to/Dockerfile" />
        </el-form-item>
        <el-form-item label="标签" required>
          <el-input v-model="buildForm.tag" placeholder="myapp:latest" />
        </el-form-item>
      </el-form>
      <template #footer>
        <Md3Button @click="showBuildDialog = false">取消</Md3Button>
        <Md3Button variant="primary" @click="buildImage">构建</Md3Button>
      </template>
    </el-dialog>

    <el-dialog v-model="showNetworkDialog" title="创建网络" width="420px">
      <el-form label-width="80px">
        <el-form-item label="名称" required>
          <el-input v-model="networkForm.name" placeholder="网络名称" />
        </el-form-item>
        <el-form-item label="驱动">
          <el-select v-model="networkForm.driver" style="width: 100%">
            <el-option label="bridge" value="bridge" />
            <el-option label="host" value="host" />
            <el-option label="overlay" value="overlay" />
            <el-option label="macvlan" value="macvlan" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <Md3Button @click="showNetworkDialog = false">取消</Md3Button>
        <Md3Button variant="primary" @click="createNetwork">创建</Md3Button>
      </template>
    </el-dialog>

    <el-dialog v-model="showVolumeDialog" title="创建卷" width="420px">
      <el-input v-model="volumeForm.name" placeholder="卷名称" />
      <template #footer>
        <Md3Button @click="showVolumeDialog = false">取消</Md3Button>
        <Md3Button variant="primary" @click="createVolume">创建</Md3Button>
      </template>
    </el-dialog>

    <el-dialog v-model="showErrorLogDialog" title="容器启动失败日志" width="700px">
      <el-input
        v-model="errorLogContent"
        type="textarea"
        :rows="15"
        readonly
        class="error-log-textarea"
      />
      <template #footer>
        <Md3Button @click="showErrorLogDialog = false">关闭</Md3Button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import {
  Refresh, Box, Coin, Connection, Folder, Files,
  Download, Plus, Delete, VideoPlay, VideoPause,
} from '@element-plus/icons-vue'
import { useDockerStore, type DockerContainer } from '@/stores/dockerStore'
import { useSshAccountStore } from '@/stores/sshAccountStore'
import Md3Button from '@/components/Md3Button.vue'
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

function onAccountChange(alias: string) {
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

.error-log-textarea :deep(.el-textarea__inner) {
  font-family: var(--md3-font-mono);
  font-size: 12px;
  background-color: var(--md3-inverse-surface);
  color: var(--md3-inverse-on-surface);
  border: 1px solid var(--md3-outline-variant);
}
</style>
