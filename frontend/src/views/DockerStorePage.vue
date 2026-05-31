<template>
  <div class="docker-store-page">
    <Md3PageHeader title="应用商店" :show-back="true" @back="router.push('/')" />

    <Md3Divider />

    <Md3Card class="account-card">
      <div class="account-selector">
        <span class="selector-label">SSH 服务器:</span>
        <Md3Select
          v-model="selectedAlias"
          :options="sshOptions"
          placeholder="选择 SSH 服务器"
          style="width: 280px"
          @update:model-value="onAccountChange"
        />
      </div>
    </Md3Card>

    <template v-if="dockerStore.currentAlias">
      <Md3Alert
        v-if="!store.registryMirror.enabled"
        type="warning"
        class="mirror-alert"
      >
        <template #title>未配置国内镜像源</template>
        <template #message>
          <div class="mirror-alert-content">
            <span>拉取镜像可能较慢或失败，建议配置国内镜像源加速。</span>
            <Md3Button size="sm" variant="primary" @click="handleConfigureMirror">
              <Md3Icon name="cog" size="1em" />
              一键配置
            </Md3Button>
          </div>
        </template>
      </Md3Alert>

      <div class="category-bar">
        <Md3Button
          v-for="cat in categories"
          :key="cat.value"
          size="sm"
          :variant="activeCategory === cat.value ? 'primary' : 'default'"
          @click="activeCategory = cat.value"
        >
          {{ cat.label }}
        </Md3Button>
      </div>

      <div v-if="filteredApps.length > 0" class="app-grid">
        <Md3Card
          v-for="app in filteredApps"
          :key="app.id"
          class="app-card"
          hoverable
          @click="openDetailDialog(app)"
        >
          <div class="app-card-body">
            <div class="app-header">
              <img class="app-icon" :src="app.icon" :alt="app.name" />
              <div class="app-meta">
                <div class="app-name-row">
                  <span class="app-name">{{ app.name }}</span>
                </div>
                <span class="app-desc">{{ app.description }}</span>
              </div>
            </div>
            <div class="app-footer">
              <div class="app-info">
                <Md3Tag v-if="getAppSize(app.id)" size="sm" type="info">{{ getAppSize(app.id) }}</Md3Tag>
                <Md3Tag v-else size="sm" type="info">{{ app.require_memory }} MB</Md3Tag>
                <StatusTag :status="getAppStatus(app.id)" />
              </div>
              <div class="app-actions" @click.stop>
                <template v-if="getAppStatus(app.id) === 'not_installed'">
                  <Md3Button size="sm" variant="primary" @click="openInstallFromDetail(app)">
                    <Md3Icon name="download" size="1em" />
                    安装
                  </Md3Button>
                </template>
                <template v-else-if="getAppStatus(app.id) === 'installing'">
                  <div class="install-progress-inline">
                    <Md3Button size="sm" variant="default" disabled loading>
                      安装中
                    </Md3Button>
                    <div class="progress-bar-mini">
                      <div
                        class="progress-bar-fill"
                        :style="{ width: (store.installProgressPercent[app.id] || 0) + '%' }"
                      />
                    </div>
                    <span class="progress-text-mini">{{ store.installProgressMessage[app.id] || '准备中...' }}</span>
                  </div>
                </template>
                <template v-else>
                  <Md3Button size="sm" variant="default" @click="openUninstallDialog(app)">
                    <Md3Icon name="delete" size="1em" />
                    卸载
                  </Md3Button>
                  <Md3Button size="sm" variant="primary" @click="goToContainer(app)">
                    <Md3Icon name="box" size="1em" />
                    管理
                  </Md3Button>
                </template>
              </div>
            </div>
          </div>
        </Md3Card>
      </div>

      <Md3Empty v-else description="暂无应用" />
    </template>

    <Md3Empty v-else description="请先选择一个 SSH 服务器" />

    <Md3Dialog v-model:visible="showDetailDialog" title="应用详情" width="600px">
      <div v-if="selectedApp" class="detail-content">
        <div class="detail-header">
          <img class="detail-icon" :src="selectedApp.icon" :alt="selectedApp.name" />
          <div class="detail-title-area">
            <div class="detail-name">{{ selectedApp.name }}</div>
            <div class="detail-memory">
              <template v-if="selectedAppSize">
                <span class="size-total">{{ selectedAppSize.total_size_human }}</span>
                <span class="size-detail">
                  镜像 {{ selectedAppSize.image_size_human }} +
                  容器 {{ selectedAppSize.container_size_human }} +
                  卷 {{ selectedAppSize.volume_size_human }} +
                  数据 {{ selectedAppSize.data_dir_size_human }}
                </span>
              </template>
              <template v-else>内存需求：{{ selectedApp.require_memory }} MB</template>
            </div>
          </div>
        </div>
        <Md3Divider />
        <div class="detail-section">
          <div class="detail-section-title">简介</div>
          <p class="detail-desc">{{ selectedApp.description }}</p>
        </div>
        <div class="detail-section">
          <div class="detail-section-title">核心功能</div>
          <ul class="detail-list">
            <li v-for="f in selectedApp.features" :key="f">{{ f }}</li>
          </ul>
        </div>
        <div class="detail-section">
          <div class="detail-section-title">推荐用途</div>
          <ul class="detail-list">
            <li v-for="r in selectedApp.recommended_for" :key="r">{{ r }}</li>
          </ul>
        </div>
        <div v-if="selectedAppSize && selectedAppSize.total_size > 0" class="detail-section">
          <div class="detail-section-title">磁盘占用</div>
          <div class="size-breakdown">
            <div v-if="selectedAppSize.image_size > 0" class="size-item">
              <Md3Icon name="box" size="1em" />
              <span class="size-label">镜像</span>
              <span class="size-value">{{ selectedAppSize.image_size_human }}</span>
            </div>
            <div v-if="selectedAppSize.container_size > 0" class="size-item">
              <Md3Icon name="container" size="1em" />
              <span class="size-label">容器层</span>
              <span class="size-value">{{ selectedAppSize.container_size_human }}</span>
            </div>
            <div v-if="selectedAppSize.volume_size > 0" class="size-item">
              <Md3Icon name="database" size="1em" />
              <span class="size-label">数据卷</span>
              <span class="size-value">{{ selectedAppSize.volume_size_human }}</span>
            </div>
            <div v-if="selectedAppSize.data_dir_size > 0" class="size-item">
              <Md3Icon name="folder" size="1em" />
              <span class="size-label">数据目录</span>
              <span class="size-value">{{ selectedAppSize.data_dir_size_human }}</span>
            </div>
            <div class="size-item size-total-row">
              <Md3Icon name="hard-drive" size="1em" />
              <span class="size-label">总计</span>
              <span class="size-value size-total-value">{{ selectedAppSize.total_size_human }}</span>
            </div>
          </div>
        </div>
        <Md3Divider />
        <div class="version-select-area">
          <span class="version-label">选择版本：</span>
          <div class="version-select-wrapper">
            <Md3Select
              v-model="selectedVersion"
              :options="versionOptionsWithSize"
              style="width: 220px"
            />
            <span v-if="selectedVersionSize" class="version-size-badge" :class="selectedVersionSize.status">
              {{ selectedVersionSize.size_human }}
            </span>
            <Md3Spinner v-else-if="store.versionSizeLoading[selectedApp?.id || '']" size="sm" />
          </div>
          <div v-if="selectedVersionSize?.last_updated" class="version-meta">
            更新于 {{ formatDate(selectedVersionSize.last_updated) }}
          </div>
        </div>
      </div>
      <template #footer>
        <Md3Button @click="showDetailDialog = false">关闭</Md3Button>
        <Md3Button
          v-if="getAppStatus(selectedApp?.id || '') === 'not_installed'"
          variant="primary"
          @click="submitInstallFromDetail"
        >
          <Md3Icon name="download" size="1em" />
          安装
        </Md3Button>
        <Md3Button
          v-else-if="getAppStatus(selectedApp?.id || '') !== 'not_installed'"
          variant="primary"
          @click="showDetailDialog = false; goToContainer(selectedApp!)"
        >
          <Md3Icon name="box" size="1em" />
          管理
        </Md3Button>
      </template>
    </Md3Dialog>

    <Md3Dialog v-model:visible="showInstallDialog" title="安装应用" width="520px">
      <div v-if="selectedApp" class="dialog-form">
        <div class="install-app-header">
          <img class="install-app-icon" :src="selectedApp.icon" :alt="selectedApp.name" />
          <div>
            <div class="install-app-name">{{ selectedApp.name }}</div>
            <div class="install-app-version">版本：{{ selectedVersion || selectedApp.versions?.[0] || 'latest' }}</div>
          </div>
        </div>
        <Md3Divider />
        <div v-if="selectedApp.env_config.length > 0" class="env-form">
          <div
            v-for="field in selectedApp.env_config"
            :key="field.key"
            class="env-field"
          >
            <Md3Input
              v-if="field.type === 'password'"
              v-model="installForm[field.key]"
              :label="field.label"
              :placeholder="field.description || ''"
              type="password"
            />
            <Md3Input
              v-else-if="field.type === 'int' || field.type === 'port'"
              v-model.number="installForm[field.key]"
              :label="field.label"
              :placeholder="field.description || ''"
              type="number"
            />
            <Md3Input
              v-else
              v-model="installForm[field.key]"
              :label="field.label"
              :placeholder="field.description || ''"
              type="text"
            />
          </div>
        </div>
        <div v-else class="no-env-hint">该应用无需额外配置</div>
      </div>
      <template #footer>
        <Md3Button @click="showInstallDialog = false">取消</Md3Button>
        <Md3Button variant="primary" :loading="store.installing" @click="submitInstall">
          安装
        </Md3Button>
      </template>
    </Md3Dialog>

    <!-- 安装进度弹窗 -->
    <Md3Dialog v-model:visible="showProgressDialog" title="安装进度" width="480px" :closable="!store.installing">
      <div v-if="progressApp" class="progress-dialog-content">
        <div class="progress-app-info">
          <img class="progress-app-icon" :src="progressApp.icon" :alt="progressApp.name" />
          <div>
            <div class="progress-app-name">{{ progressApp.name }}</div>
            <div class="progress-app-version">版本：{{ selectedVersion || progressApp.versions?.[0] || 'latest' }}</div>
          </div>
        </div>
        <Md3Divider />
        <div class="progress-area">
          <div class="progress-bar-large">
            <div
              class="progress-bar-fill-large"
              :style="{ width: (store.installProgressPercent[progressApp.id] || 0) + '%' }"
            />
          </div>
          <div class="progress-percent">{{ Math.round(store.installProgressPercent[progressApp.id] || 0) }}%</div>
          <div class="progress-message">{{ store.installProgressMessage[progressApp.id] || '准备中...' }}</div>
        </div>
        <div v-if="store.installProgress[progressApp.id]?.type === 'error'" class="progress-error">
          <Md3Icon name="alert-circle" size="1.2em" />
          <span>{{ store.installProgressMessage[progressApp.id] }}</span>
        </div>
      </div>
      <template #footer>
        <Md3Button v-if="!store.installing" @click="showProgressDialog = false">
          {{ store.installProgress[progressApp?.id || '']?.type === 'error' ? '关闭' : '完成' }}
        </Md3Button>
      </template>
    </Md3Dialog>

    <Md3Dialog v-model:visible="showUninstallDialog" title="卸载应用" width="420px">
      <div v-if="selectedApp" class="dialog-form">
        <p class="uninstall-message">
          确认卸载 <strong>{{ selectedApp.name }}</strong> 吗？
        </p>
        <div class="uninstall-options">
          <label class="radio-option">
            <input v-model="uninstallRemoveData" type="radio" :value="false" />
            <span class="radio-label">保留数据（仅卸载容器，保留卷数据）</span>
          </label>
          <label class="radio-option">
            <input
              v-model="uninstallRemoveData"
              type="radio"
              :value="true"
            />
            <span class="radio-label">完全删除（卸载容器并清理所有数据）</span>
          </label>
        </div>
      </div>
      <template #footer>
        <Md3Button @click="showUninstallDialog = false">取消</Md3Button>
        <Md3Button variant="danger" :loading="store.uninstalling" @click="submitUninstall">
          卸载
        </Md3Button>
      </template>
    </Md3Dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { Md3Icon } from '@/components/md3'
import { useDockerStore } from '@/stores/dockerStore'
import { useDockerStoreStore, type StoreApp } from '@/stores/dockerStoreStore'
import { useSshAccountStore } from '@/stores/sshAccountStore'
import {
  Md3Dialog,
  Md3Input,
  Md3Select,
  Md3Tag,
  Md3PageHeader,
  Md3Divider,
  Md3Card,
  Md3Empty,
  Md3Alert,
} from '@/components/md3'
import Md3Button from '@/components/Md3Button.vue'

const router = useRouter()
const dockerStore = useDockerStore()
const store = useDockerStoreStore()
const sshStore = useSshAccountStore()

const selectedAlias = ref('')
const activeCategory = ref('all')
const showDetailDialog = ref(false)
const showInstallDialog = ref(false)
const showUninstallDialog = ref(false)
const showProgressDialog = ref(false)
const selectedApp = ref<StoreApp | null>(null)
const progressApp = ref<StoreApp | null>(null)
const selectedVersion = ref('')
const installForm = ref<Record<string, string | number>>({})
const uninstallRemoveData = ref(false)

let pollTimer: ReturnType<typeof setInterval> | null = null

const sshAccounts = computed(() => sshStore.accounts)
const sshOptions = computed(() =>
  sshAccounts.value.map(acc => ({
    label: `${acc.alias} (${acc.host})`,
    value: acc.alias,
  }))
)

const categories = [
  { label: '全部', value: 'all' },
  { label: 'Web服务', value: 'web' },
  { label: '数据库', value: 'database' },
  { label: 'AI/ML', value: 'ai_ml' },
  { label: '开发运维', value: 'dev_ops' },
  { label: '开发工具', value: 'dev_tools' },
  { label: '网络与安全', value: 'network' },
  { label: '监控', value: 'monitor' },
  { label: '媒体娱乐', value: 'media' },
  { label: '自动化', value: 'automation' },
  { label: '团队协作', value: 'collaboration' },
  { label: '业务管理', value: 'business' },
  { label: '邮件服务', value: 'email' },
  { label: '实用工具', value: 'tools' },
]

const categoryMap: Record<string, string> = {
  all: '',
  web: 'web_server',
  database: 'database',
  ai_ml: 'ai_ml',
  dev_ops: 'dev_ops',
  dev_tools: 'dev_tools',
  network: 'network',
  monitor: 'monitor',
  media: 'media',
  automation: 'automation',
  collaboration: 'collaboration',
  business: 'business',
  email: 'email',
  tools: 'tools',
}

const filteredApps = computed(() => {
  const mappedCategory = categoryMap[activeCategory.value]
  if (!mappedCategory) return store.apps
  return store.apps.filter(a => a.category === mappedCategory)
})

const versionOptions = computed(() => {
  if (!selectedApp.value?.versions) return []
  return selectedApp.value.versions.map(v => ({ label: v, value: v }))
})

const versionOptionsWithSize = computed(() => {
  if (!selectedApp.value?.versions) return []
  const sizes = store.imageVersionSizes[selectedApp.value.id]
  return selectedApp.value.versions.map(v => {
    const sizeInfo = sizes?.versions?.find(sv => sv.version === v)
    const sizeLabel = sizeInfo && sizeInfo.size > 0 ? ` (${sizeInfo.size_human})` : ''
    return { label: `${v}${sizeLabel}`, value: v }
  })
})

const selectedVersionSize = computed(() => {
  if (!selectedApp.value || !selectedVersion.value) return null
  const sizes = store.imageVersionSizes[selectedApp.value.id]
  if (!sizes?.versions) return null
  return sizes.versions.find(v => v.version === selectedVersion.value) || null
})

const selectedAppSize = computed(() => {
  if (!selectedApp.value) return null
  return store.appSizes[selectedApp.value.id] || null
})

function getAppStatus(appId: string) {
  return store.appStatuses[appId]?.state || 'not_installed'
}

function getAppSize(appId: string): string {
  const sizeInfo = store.appSizes[appId]
  if (!sizeInfo || sizeInfo.total_size === 0) return ''
  return sizeInfo.total_size_human
}

function onAccountChange(value: string | number | (string | number)[]) {
  const alias = String(value)
  dockerStore.setAccountAlias(alias)
  refreshAll()
}

async function refreshAll() {
  await store.fetchApps()
  await store.fetchAppStatuses()
  await store.fetchRegistryMirrors()
}

function startPolling() {
  stopPolling()
  pollTimer = setInterval(() => {
    if (dockerStore.currentAlias) {
      store.fetchAppStatuses()
    }
  }, 5000)
}

function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

async function openDetailDialog(app: StoreApp) {
  selectedApp.value = app
  selectedVersion.value = app.versions[0] || 'latest'
  showDetailDialog.value = true
  // 已安装的应用才获取实际大小
  if (getAppStatus(app.id) !== 'not_installed') {
    await store.fetchAppSize(app.id)
  }
  // 获取各版本镜像大小（无需 SSH 账户）
  await store.fetchImageVersionSizes(app.id)
}

function formatDate(dateStr: string): string {
  if (!dateStr) return ''
  try {
    const d = new Date(dateStr)
    return d.toLocaleDateString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit' })
  } catch {
    return dateStr
  }
}

function openInstallFromDetail(app: StoreApp) {
  showDetailDialog.value = false
  openInstallDialog(app)
}

async function submitInstallFromDetail() {
  if (!selectedApp.value) return
  showDetailDialog.value = false
  openInstallDialog(selectedApp.value)
}

function openInstallDialog(app: StoreApp) {
  selectedApp.value = app
  installForm.value = {}
  app.env_config.forEach(field => {
    installForm.value[field.key] = field.default ?? (field.type === 'int' || field.type === 'port' ? 0 : '')
  })
  showInstallDialog.value = true
}

async function submitInstall() {
  if (!selectedApp.value) return
  const env: Record<string, string | number> = {}
  selectedApp.value.env_config.forEach(field => {
    const v = installForm.value[field.key]
    env[field.key] = v === '' || v === undefined ? (field.default ?? '') : v
  })

  // 添加 VERSION 到环境变量
  if (selectedVersion.value) {
    env.VERSION = selectedVersion.value
  }

  showInstallDialog.value = false
  progressApp.value = selectedApp.value
  showProgressDialog.value = true

  try {
    const result = await store.installAppWithProgress(selectedApp.value.id, env)
    if (result.success) {
      await store.fetchAppStatuses()
    }
  } catch (error: any) {
    console.error('[DockerStore] 安装失败:', error)
    // 错误状态已通过 WebSocket 更新到 store
  }
}

function openUninstallDialog(app: StoreApp) {
  selectedApp.value = app
  uninstallRemoveData.value = false
  showUninstallDialog.value = true
}

async function submitUninstall() {
  if (!selectedApp.value) return
  await store.uninstallApp(selectedApp.value.id, uninstallRemoveData.value)
  showUninstallDialog.value = false
}

function goToContainer(app: StoreApp) {
  const status = store.appStatuses[app.id]
  if (status?.container_id) {
    router.push(`/docker/container/${status.container_id}`)
  } else {
    router.push('/docker')
  }
}

async function handleConfigureMirror() {
  await store.configureRegistryMirror('')
}

onMounted(async () => {
  await sshStore.fetchAccounts()
  const defaultAcc = sshStore.accounts.find(a => a.default)
  const firstAcc = sshStore.accounts[0]
  const alias = defaultAcc?.alias || firstAcc?.alias || ''
  if (alias) {
    selectedAlias.value = alias
    dockerStore.setAccountAlias(alias)
    await refreshAll()
    startPolling()
  }
})

onUnmounted(() => {
  stopPolling()
})
</script>

<script lang="ts">
import { defineComponent, h } from 'vue'
import { Md3Tag as Md3TagComp } from '@/components/md3'

const StatusTag = defineComponent({
  props: {
    status: { type: String, required: true },
  },
  setup(props) {
    const map: Record<string, { type: 'info' | 'success' | 'warning' | 'danger'; text: string }> = {
      not_installed: { type: 'info', text: '未安装' },
      installing: { type: 'warning', text: '安装中' },
      running: { type: 'success', text: '运行中' },
      stopped: { type: 'warning', text: '已停止' },
      error: { type: 'danger', text: '错误' },
    }
    const conf = map[props.status] || map.not_installed
    return () => h(Md3TagComp, { type: conf.type, size: 'sm' }, () => conf.text)
  },
})

export { StatusTag }
</script>

<style scoped>
.docker-store-page {
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

.mirror-alert {
  margin-bottom: var(--md3-space-md);
}

.mirror-alert-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--md3-space-md);
  flex-wrap: wrap;
}

.category-bar {
  display: flex;
  gap: var(--md3-space-sm);
  margin-bottom: var(--md3-space-lg);
  flex-wrap: wrap;
}

.app-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--md3-space-lg);
}

@media (max-width: 1200px) {
  .app-grid {
    grid-template-columns: repeat(3, 1fr);
  }
}

@media (max-width: 900px) {
  .app-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 600px) {
  .app-grid {
    grid-template-columns: 1fr;
  }
}

.app-card {
  display: flex;
  flex-direction: column;
}

.app-card-body {
  display: flex;
  flex-direction: column;
  gap: var(--md3-space-md);
  padding: var(--md3-space-lg);
}

.app-header {
  display: flex;
  gap: var(--md3-space-md);
  align-items: flex-start;
}

.app-icon {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  object-fit: contain;
  flex-shrink: 0;
  background: var(--md3-surface-variant);
  padding: 4px;
}

.app-meta {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.app-name-row {
  display: flex;
  align-items: center;
  gap: var(--md3-space-sm);
}

.app-name {
  font: var(--md3-type-title-medium);
  color: var(--md3-on-surface);
}

.app-desc {
  font: var(--md3-type-body-small);
  color: var(--md3-on-surface-variant);
  line-height: 1.4;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.app-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--md3-space-sm);
  flex-wrap: wrap;
}

.app-info {
  display: flex;
  gap: var(--md3-space-xs);
  align-items: center;
}

.app-actions {
  display: flex;
  gap: var(--md3-space-sm);
}

.detail-content {
  display: flex;
  flex-direction: column;
  gap: var(--md3-space-md);
}

.detail-header {
  display: flex;
  align-items: center;
  gap: var(--md3-space-md);
}

.detail-icon {
  width: 64px;
  height: 64px;
  border-radius: 16px;
  object-fit: contain;
  flex-shrink: 0;
  background: var(--md3-surface-variant);
  padding: 6px;
}

.detail-title-area {
  flex: 1;
}

.detail-name {
  font: var(--md3-type-title-large);
  color: var(--md3-on-surface);
}

.detail-memory {
  font: var(--md3-type-body-small);
  color: var(--md3-on-surface-variant);
  margin-top: 4px;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.size-total {
  font: var(--md3-type-label-large);
  color: var(--md3-primary);
  font-weight: 600;
}

.size-detail {
  font: var(--md3-type-body-small);
  color: var(--md3-on-surface-variant);
  opacity: 0.8;
}

.detail-section {
  display: flex;
  flex-direction: column;
  gap: var(--md3-space-sm);
}

.detail-section-title {
  font: var(--md3-type-label-large);
  color: var(--md3-on-surface);
  font-weight: 600;
}

.detail-desc {
  font: var(--md3-type-body-medium);
  color: var(--md3-on-surface-variant);
  line-height: 1.6;
  margin: 0;
}

.detail-list {
  margin: 0;
  padding-left: 1.2em;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.detail-list li {
  font: var(--md3-type-body-medium);
  color: var(--md3-on-surface-variant);
  line-height: 1.5;
}

.version-select-area {
  display: flex;
  flex-direction: column;
  gap: var(--md3-space-sm);
}

.version-select-wrapper {
  display: flex;
  align-items: center;
  gap: var(--md3-space-md);
}

.version-label {
  font: var(--md3-type-label-large);
  color: var(--md3-on-surface);
  white-space: nowrap;
}

.version-size-badge {
  font: var(--md3-type-label-medium);
  padding: 2px 8px;
  border-radius: 12px;
  background: var(--md3-surface-variant);
  color: var(--md3-on-surface-variant);
  white-space: nowrap;
}

.version-size-badge.found {
  background: var(--md3-primary-container);
  color: var(--md3-on-primary-container);
}

.version-size-badge.not_found {
  background: var(--md3-error-container);
  color: var(--md3-on-error-container);
}

.version-meta {
  font: var(--md3-type-body-small);
  color: var(--md3-on-surface-variant);
  opacity: 0.7;
}

.dialog-form {
  display: flex;
  flex-direction: column;
  gap: var(--md3-space-md);
}

.install-app-header {
  display: flex;
  align-items: center;
  gap: var(--md3-space-md);
}

.install-app-icon {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  object-fit: contain;
  flex-shrink: 0;
  background: var(--md3-surface-variant);
  padding: 4px;
}

.install-app-name {
  font: var(--md3-type-title-medium);
  color: var(--md3-on-surface);
}

.install-app-version {
  font: var(--md3-type-body-small);
  color: var(--md3-on-surface-variant);
}

.env-form {
  display: flex;
  flex-direction: column;
  gap: var(--md3-space-md);
}

.no-env-hint {
  text-align: center;
  color: var(--md3-on-surface-variant);
  font: var(--md3-type-body-medium);
  padding: var(--md3-space-lg) 0;
}

.uninstall-message {
  font: var(--md3-type-body-medium);
  color: var(--md3-on-surface);
  margin: 0;
}

.uninstall-options {
  display: flex;
  flex-direction: column;
  gap: var(--md3-space-md);
  margin-top: var(--md3-space-sm);
}

.radio-option {
  display: flex;
  align-items: flex-start;
  gap: var(--md3-space-sm);
  cursor: pointer;
  font: var(--md3-type-body-medium);
  color: var(--md3-on-surface-variant);
}

.radio-option input {
  margin-top: 3px;
}

.radio-label {
  line-height: 1.4;
}

.size-breakdown {
  display: flex;
  flex-direction: column;
  gap: var(--md3-space-sm);
}

.size-item {
  display: flex;
  align-items: center;
  gap: var(--md3-space-sm);
  padding: var(--md3-space-sm) var(--md3-space-md);
  background: var(--md3-surface-variant);
  border-radius: 8px;
}

.size-item .md3-icon {
  color: var(--md3-on-surface-variant);
  flex-shrink: 0;
}

.size-label {
  flex: 1;
  font: var(--md3-type-body-medium);
  color: var(--md3-on-surface);
}

.size-value {
  font: var(--md3-type-body-medium);
  color: var(--md3-on-surface-variant);
  font-weight: 500;
  font-variant-numeric: tabular-nums;
}

.size-total-row {
  background: var(--md3-primary-container);
  margin-top: var(--md3-space-xs);
}

.size-total-row .md3-icon,
.size-total-row .size-label {
  color: var(--md3-on-primary-container);
}

.size-total-value {
  color: var(--md3-primary);
  font: var(--md3-type-label-large);
  font-weight: 600;
}

/* 安装进度条 - 卡片内联 */
.install-progress-inline {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 4px;
  min-width: 120px;
}

.progress-bar-mini {
  width: 100px;
  height: 4px;
  background: var(--md3-surface-variant);
  border-radius: 2px;
  overflow: hidden;
}

.progress-bar-fill {
  height: 100%;
  background: var(--md3-primary);
  border-radius: 2px;
  transition: width 0.3s ease;
}

.progress-text-mini {
  font: var(--md3-type-body-small);
  color: var(--md3-on-surface-variant);
  max-width: 120px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* 安装进度弹窗 */
.progress-dialog-content {
  display: flex;
  flex-direction: column;
  gap: var(--md3-space-md);
}

.progress-app-info {
  display: flex;
  align-items: center;
  gap: var(--md3-space-md);
}

.progress-app-icon {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  object-fit: contain;
  flex-shrink: 0;
  background: var(--md3-surface-variant);
  padding: 4px;
}

.progress-app-name {
  font: var(--md3-type-title-medium);
  color: var(--md3-on-surface);
}

.progress-app-version {
  font: var(--md3-type-body-small);
  color: var(--md3-on-surface-variant);
}

.progress-area {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--md3-space-sm);
  padding: var(--md3-space-md) 0;
}

.progress-bar-large {
  width: 100%;
  height: 8px;
  background: var(--md3-surface-variant);
  border-radius: 4px;
  overflow: hidden;
}

.progress-bar-fill-large {
  height: 100%;
  background: linear-gradient(90deg, var(--md3-primary), var(--md3-primary) 70%, var(--md3-tertiary));
  border-radius: 4px;
  transition: width 0.4s ease;
}

.progress-percent {
  font: var(--md3-type-headline-small);
  color: var(--md3-primary);
  font-weight: 600;
}

.progress-message {
  font: var(--md3-type-body-medium);
  color: var(--md3-on-surface-variant);
  text-align: center;
}

.progress-error {
  display: flex;
  align-items: center;
  gap: var(--md3-space-sm);
  padding: var(--md3-space-sm) var(--md3-space-md);
  background: var(--md3-error-container);
  color: var(--md3-on-error-container);
  border-radius: 8px;
  font: var(--md3-type-body-medium);
}
</style>
