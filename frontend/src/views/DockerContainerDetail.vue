<template>
  <div class="docker-detail-page">
    <Md3PageHeader title="Docker 管理" @back="goBack">
      <template #content>
        <span>容器: {{ containerName }}</span>
      </template>
      <template #extra>
        <Md3Button size="sm" variant="default" @click="goBack"><Md3Icon name="close" size="sm" />关闭</Md3Button>
      </template>
    </Md3PageHeader>
    <Md3Divider />

    <Md3Card :shadow="false" class="info-card">
      <div class="description-grid" v-if="containerDetail">
        <div class="desc-item">
          <span class="desc-label">ID</span>
          <span class="desc-value mono-text">{{ containerDetail.id }}</span>
        </div>
        <div class="desc-item">
          <span class="desc-label">名称</span>
          <span class="desc-value">{{ containerDetail.name }}</span>
        </div>
        <div class="desc-item">
          <span class="desc-label">状态</span>
          <span class="desc-value">
            <Md3Tag :type="containerDetail.state === 'running' ? 'success' : 'info'" size="sm">
              {{ containerDetail.state === 'running' ? '🟢 运行中' : '⚪ 已停止' }}
            </Md3Tag>
          </span>
        </div>
        <div class="desc-item">
          <span class="desc-label">镜像</span>
          <span class="desc-value">{{ containerDetail.image }}</span>
        </div>
        <div class="desc-item">
          <span class="desc-label">端口</span>
          <span class="desc-value">{{ containerDetail.ports || '-' }}</span>
        </div>
        <div class="desc-item">
          <span class="desc-label">创建时间</span>
          <span class="desc-value">{{ containerDetail.created }}</span>
        </div>
        <div class="desc-item desc-full">
          <span class="desc-label">命令</span>
          <span class="desc-value mono-text">{{ containerDetail.command || '-' }}</span>
        </div>
      </div>
      <div v-else>
        <div class="skeleton-loader">
          <div class="skeleton-line" v-for="i in 4" :key="i"></div>
        </div>
      </div>
    </Md3Card>

    <Md3Tabs v-model="activeTab" :tabs="tabItems" class="detail-tabs" />
    <div class="tab-content">
      <div v-show="activeTab === 'overview'">
        <div class="overview-grid">
          <Md3Card :shadow="false" class="stat-card">
            <template #header><span>资源监控</span></template>
            <div class="stat-list">
              <div class="stat-item">
                <span class="stat-label">CPU</span>
                <Md3Progress :percentage="45" type="line" :stroke-width="16" />
              </div>
              <div class="stat-item">
                <span class="stat-label">内存</span>
                <Md3Progress :percentage="32" type="line" :stroke-width="16" color="var(--md3-warning)" />
              </div>
              <div class="stat-item">
                <span class="stat-label">磁盘</span>
                <Md3Progress :percentage="56" type="line" :stroke-width="16" color="var(--md3-error)" />
              </div>
              <div class="stat-item">
                <span class="stat-label">网络</span>
                <span class="stat-value">12 MB/s</span>
              </div>
            </div>
          </Md3Card>
          <Md3Card :shadow="false" class="info-card">
            <template #header><span>健康检查</span></template>
            <div class="health-info">
              <div class="health-status">
                <Md3Icon name="check-circle" :size="32" class="health-icon" />
                <span class="health-text">健康状态正常</span>
              </div>
              <div class="health-detail">
                <div>检查间隔: 30s</div>
                <div>超时时间: 10s</div>
                <div>重试次数: 3</div>
              </div>
            </div>
          </Md3Card>
        </div>
      </div>

      <div v-show="activeTab === 'logs'">
        <div class="log-controls">
          <Md3Button size="sm" :variant="isLogStreaming ? 'danger' : 'primary'" @click="toggleLogStream">{{ isLogStreaming ? '暂停' : '实时日志' }}</Md3Button>
          <Md3Button size="sm" @click="downloadLogs"><Md3Icon name="download" size="sm" />下载</Md3Button>
          <Md3Input
            type="number"
            v-model.number="logTailLines"
            :min="50"
            :max="1000"
            class="log-tail-input"
          />
        </div>
        <div class="log-viewer" ref="logViewerRef">
          <div
            v-for="(line, index) in containerLogs"
            :key="index"
            class="log-line"
            :class="logLevelClass(line)"
          >
            {{ line }}
          </div>
        </div>
      </div>

      <div v-show="activeTab === 'terminal'">
        <Terminal ref="containerTerminalRef" session-name="容器终端" :show-toolbar="true" />
      </div>

      <div v-show="activeTab === 'config'">
        <div class="config-section">
          <div class="config-item">
            <span class="config-label">环境变量</span>
            <pre class="config-pre">JAVA_HOME=/usr/lib/jvm/java-17
SPRING_PROFILES_ACTIVE=dev</pre>
          </div>
          <div class="config-item">
            <span class="config-label">挂载卷</span>
            <pre class="config-pre">/host/data:/app/data
/host/config:/app/config</pre>
          </div>
          <div class="config-item">
            <span class="config-label">网络</span>
            <pre class="config-pre">bridge (172.17.0.2)
ports: 0.0.0.0:8080->8080/tcp</pre>
          </div>
          <div class="config-item">
            <span class="config-label">标签</span>
            <div class="config-tags">
              <Md3Tag size="sm">version=1.0</Md3Tag>
              <Md3Tag size="sm">env=production</Md3Tag>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div class="detail-actions">
      <Md3Button @click="restartContainer"><Md3Icon name="refresh" size="sm" />重启</Md3Button>
      <Md3Button @click="stopContainer"><Md3Icon name="pause" size="sm" />停止</Md3Button>
      <Md3Button variant="danger" @click="killContainer"><Md3Icon name="remove" size="sm" />强制停止</Md3Button>
      <Md3Button variant="danger" @click="deleteContainer"><Md3Icon name="delete" size="sm" />删除</Md3Button>
      <Md3Button @click="openStats"><Md3Icon name="chart-bar" size="sm" />资源监控</Md3Button>
      <Md3Button @click="activeTab = 'terminal'"><Md3Icon name="monitor" size="sm" />进入终端</Md3Button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useDockerStore, type DockerContainer } from '@/stores/dockerStore'
import Md3Button from '@/components/Md3Button.vue'
import Terminal from '@/components/Terminal.vue'
import {
  Md3PageHeader,
  Md3Divider,
  Md3Card,
  Md3Tag,
  Md3Progress,
  Md3Tabs,
  Md3Input,
  Md3Icon,
} from '@/components/md3'

const route = useRoute()
const router = useRouter()
const dockerStore = useDockerStore()

const tabItems = [
  { label: '概览', value: 'overview' },
  { label: '日志', value: 'logs' },
  { label: '终端', value: 'terminal' },
  { label: '配置', value: 'config' },
]

const containerId = ref(route.params.id as string)
const containerName = ref('')
const activeTab = ref((route.query.tab as string) || 'overview')
const containerLogs = ref<string[]>([])
const isLogStreaming = ref(false)
const logTailLines = ref(200)
const logViewerRef = ref<HTMLElement>()
const containerTerminalRef = ref<InstanceType<typeof Terminal>>()

const containerDetail = ref<DockerContainer | null>(null)

function goBack() {
  router.push('/docker')
}

async function loadContainerDetail() {
  try {
    const container = dockerStore.containers.find(c => c.id.startsWith(containerId.value) || c.name === containerId.value)
    if (container) {
      containerDetail.value = container
      containerName.value = container.name
    }
  } catch {
  }
}

async function loadLogs() {
  try {
    const logs = await dockerStore.getContainerLogs(containerId.value, logTailLines.value)
    containerLogs.value = logs || []
    setTimeout(() => {
      if (logViewerRef.value) {
        logViewerRef.value.scrollTop = logViewerRef.value.scrollHeight
      }
    }, 50)
  } catch {
  }
}

function toggleLogStream() {
  isLogStreaming.value = !isLogStreaming.value
  if (isLogStreaming.value) {
    loadLogs()
  }
}

function downloadLogs() {
  const blob = new Blob([containerLogs.value.join('\n')], { type: 'text/plain' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `${containerName.value}-logs.txt`
  a.click()
  URL.revokeObjectURL(url)
}

function logLevelClass(line: string) {
  if (line.includes('ERROR') || line.includes('FATAL')) return 'log-error'
  if (line.includes('WARN')) return 'log-warn'
  return 'log-info'
}

function restartContainer() {
  dockerStore.restartContainer(containerId.value)
}

function stopContainer() {
  dockerStore.stopContainer(containerId.value)
}

function killContainer() {
  dockerStore.killContainer(containerId.value)
}

function deleteContainer() {
  dockerStore.deleteContainer(containerId.value)
  goBack()
}

function openStats() {
  activeTab.value = 'overview'
}

watch(() => logTailLines.value, () => {
  if (isLogStreaming.value) loadLogs()
})

onMounted(() => {
  loadContainerDetail()
})
</script>

<style scoped>
.docker-detail-page {
  padding: 0;
}

.info-card {
  margin-bottom: var(--md3-space-lg);
}

.mono-text {
  font-family: var(--md3-font-mono);
  font-size: 12px;
  background: var(--md3-surface-container-low);
  padding: 1px 4px;
  border-radius: var(--md3-shape-xs);
}

.description-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--md3-space-md) var(--md3-space-lg);
}

.desc-item {
  display: flex;
  flex-direction: column;
  gap: var(--md3-space-xs);
  padding: var(--md3-space-sm) 0;
}

.desc-full {
  grid-column: 1 / -1;
}

.desc-label {
  font-size: 12px;
  color: var(--md3-on-surface-variant);
  font-weight: 500;
}

.desc-value {
  font-size: 14px;
  color: var(--md3-on-surface);
  word-break: break-all;
}

.skeleton-loader {
  display: flex;
  flex-direction: column;
  gap: var(--md3-space-md);
}

.skeleton-line {
  height: 16px;
  background: var(--md3-surface-container-low);
  border-radius: var(--md3-shape-xs);
  animation: skeleton-pulse 1.5s ease-in-out infinite;
}

@keyframes skeleton-pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.detail-tabs {
  margin-top: var(--md3-space-sm);
}

.tab-content {
  min-height: 200px;
}

.overview-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--md3-space-lg);
}

.stat-card {
  margin-bottom: var(--md3-space-lg);
}

.stat-list {
  display: flex;
  flex-direction: column;
  gap: var(--md3-space-lg);
}

.stat-item {
  display: flex;
  align-items: center;
  gap: var(--md3-space-md);
}

.stat-label {
  width: 40px;
  font-size: 13px;
  color: var(--md3-on-surface-variant);
  flex-shrink: 0;
}

.stat-value {
  font-weight: 500;
  color: var(--md3-on-surface);
}

.health-info {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--md3-space-md);
  padding: var(--md3-space-lg);
}

.health-status {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--md3-space-sm);
}

.health-icon {
  width: 32px;
  height: 32px;
  color: var(--md3-success);
}

.health-text {
  font-weight: 600;
  color: var(--md3-success);
}

.health-detail {
  font-size: 13px;
  color: var(--md3-on-surface-variant);
  display: flex;
  flex-direction: column;
  gap: var(--md3-space-xs);
}

.log-controls {
  display: flex;
  align-items: center;
  gap: var(--md3-space-sm);
  margin-bottom: var(--md3-space-md);
}

.log-tail-input {
  width: 100px;
}

.log-viewer {
  max-height: 400px;
  overflow-y: auto;
  background: var(--md3-inverse-surface);
  color: var(--md3-inverse-on-surface);
  padding: var(--md3-space-sm);
  border-radius: var(--md3-shape-xs);
  font-family: var(--md3-font-mono);
  font-size: 12px;
  line-height: 1.6;
}

.log-line {
  white-space: nowrap;
}

.log-line.log-info {
  color: var(--md3-inverse-on-surface);
}

.log-line.log-warn {
  color: #ce9178;
}

.log-line.log-error {
  color: #f44747;
}

.config-section {
  display: flex;
  flex-direction: column;
  gap: var(--md3-space-md);
}

.config-item {
  display: flex;
  flex-direction: column;
  gap: var(--md3-space-xs);
}

.config-label {
  font-size: 13px;
  font-weight: 600;
  color: var(--md3-on-surface);
}

.config-pre {
  margin: 0;
  font-family: var(--md3-font-mono);
  font-size: 12px;
  line-height: 1.5;
  white-space: pre-wrap;
  background: var(--md3-surface-container-low);
  padding: var(--md3-space-sm);
  border-radius: var(--md3-shape-xs);
}

.config-tags {
  display: flex;
  gap: var(--md3-space-sm);
}

.detail-actions {
  display: flex;
  gap: var(--md3-space-sm);
  margin-top: var(--md3-space-lg);
  flex-wrap: wrap;
}
</style>
