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
                <Md3Tag size="sm" type="info">{{ app.require_memory }} MB</Md3Tag>
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
                  <Md3Button size="sm" variant="default" disabled loading>
                    安装中
                  </Md3Button>
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
            <div class="detail-memory">内存需求：{{ selectedApp.require_memory }} MB</div>
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
        <Md3Divider />
        <div class="version-select-area">
          <span class="version-label">选择版本：</span>
          <Md3Select
            v-model="selectedVersion"
            :options="versionOptions"
            style="width: 180px"
          />
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
const selectedApp = ref<StoreApp | null>(null)
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
  { label: '开发工具', value: 'devtools' },
  { label: '网络与安全', value: 'network' },
  { label: '工具与监控', value: 'tools' },
]

const categoryMap: Record<string, string> = {
  all: '',
  web: 'web_server',
  database: 'database',
  devtools: 'dev_ops',
  network: 'network',
  tools: 'monitor',
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

function getAppStatus(appId: string) {
  return store.appStatuses[appId]?.state || 'not_installed'
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

function openDetailDialog(app: StoreApp) {
  selectedApp.value = app
  selectedVersion.value = app.versions[0] || 'latest'
  showDetailDialog.value = true
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
  await store.installApp(selectedApp.value.id, env)
  showInstallDialog.value = false
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
  align-items: center;
  gap: var(--md3-space-sm);
}

.version-label {
  font: var(--md3-type-body-medium);
  color: var(--md3-on-surface);
  white-space: nowrap;
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
</style>
