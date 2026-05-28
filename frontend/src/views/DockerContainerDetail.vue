<template>
  <div class="docker-detail-page">
    <el-page-header title="Docker 管理" @back="goBack">
      <template #content>
        <span>容器: {{ containerName }}</span>
      </template>
      <template #extra>
        <Md3Button :icon="Close" size="sm" variant="default" @click="goBack">关闭</Md3Button>
      </template>
    </el-page-header>
    <el-divider />

    <el-card shadow="never" class="info-card">
      <el-descriptions :column="3" border size="small" v-if="containerDetail">
        <el-descriptions-item label="ID" :span="1">
          <code class="mono-text">{{ containerDetail.id }}</code>
        </el-descriptions-item>
        <el-descriptions-item label="名称" :span="1">{{ containerDetail.name }}</el-descriptions-item>
        <el-descriptions-item label="状态" :span="1">
          <el-tag :type="containerDetail.state === 'running' ? 'success' : 'info'" size="small">
            {{ containerDetail.state === 'running' ? '🟢 运行中' : '⚪ 已停止' }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="镜像" :span="1">{{ containerDetail.image }}</el-descriptions-item>
        <el-descriptions-item label="端口" :span="1">{{ containerDetail.ports || '-' }}</el-descriptions-item>
        <el-descriptions-item label="创建时间" :span="1">{{ containerDetail.created }}</el-descriptions-item>
        <el-descriptions-item label="命令" :span="3">
          <code class="mono-text">{{ containerDetail.command || '-' }}</code>
        </el-descriptions-item>
      </el-descriptions>
      <div v-else>
        <el-skeleton :rows="4" animated />
      </div>
    </el-card>

    <el-tabs v-model="activeTab" class="detail-tabs">
      <el-tab-pane label="概览" name="overview">
        <el-row :gutter="16">
          <el-col :span="12">
            <el-card shadow="never" class="stat-card">
              <template #header><span>资源监控</span></template>
              <div class="stat-list">
                <div class="stat-item">
                  <span class="stat-label">CPU</span>
                  <el-progress :percentage="45" :stroke-width="16" />
                </div>
                <div class="stat-item">
                  <span class="stat-label">内存</span>
                  <el-progress :percentage="32" :stroke-width="16" status="warning" />
                </div>
                <div class="stat-item">
                  <span class="stat-label">磁盘</span>
                  <el-progress :percentage="56" :stroke-width="16" status="exception" />
                </div>
                <div class="stat-item">
                  <span class="stat-label">网络</span>
                  <span class="stat-value">12 MB/s</span>
                </div>
              </div>
            </el-card>
          </el-col>
          <el-col :span="12">
            <el-card shadow="never" class="info-card">
              <template #header><span>健康检查</span></template>
              <div class="health-info">
                <div class="health-status">
                  <el-icon :size="32" color="#67c23a"><CircleCheck /></el-icon>
                  <span class="health-text">健康状态正常</span>
                </div>
                <div class="health-detail">
                  <div>检查间隔: 30s</div>
                  <div>超时时间: 10s</div>
                  <div>重试次数: 3</div>
                </div>
              </div>
            </el-card>
          </el-col>
        </el-row>
      </el-tab-pane>

      <el-tab-pane label="日志" name="logs">
        <div class="log-controls">
          <Md3Button size="sm" :variant="isLogStreaming ? 'danger' : 'primary'" @click="toggleLogStream">{{ isLogStreaming ? '暂停' : '实时日志' }}</Md3Button>
          <Md3Button size="sm" :icon="Download" @click="downloadLogs">下载</Md3Button>
          <el-input-number v-model="logTailLines" :min="50" :max="1000" :step="50" size="small" />
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
      </el-tab-pane>

      <el-tab-pane label="终端" name="terminal">
        <Terminal ref="containerTerminalRef" session-name="容器终端" :show-toolbar="true" />
      </el-tab-pane>

      <el-tab-pane label="配置" name="config">
        <el-descriptions :column="1" border size="small">
          <el-descriptions-item label="环境变量">
            <pre class="config-pre">JAVA_HOME=/usr/lib/jvm/java-17
SPRING_PROFILES_ACTIVE=dev</pre>
          </el-descriptions-item>
          <el-descriptions-item label="挂载卷">
            <pre class="config-pre">/host/data:/app/data
/host/config:/app/config</pre>
          </el-descriptions-item>
          <el-descriptions-item label="网络">
            <pre class="config-pre">bridge (172.17.0.2)
ports: 0.0.0.0:8080->8080/tcp</pre>
          </el-descriptions-item>
          <el-descriptions-item label="标签">
            <el-tag size="small">version=1.0</el-tag>
            <el-tag size="small" style="margin-left: 4px">env=production</el-tag>
          </el-descriptions-item>
        </el-descriptions>
      </el-tab-pane>
    </el-tabs>

    <div class="detail-actions">
      <Md3Button :icon="Refresh" @click="restartContainer">重启</Md3Button>
      <Md3Button :icon="VideoPause" @click="stopContainer">停止</Md3Button>
      <Md3Button variant="danger" :icon="Remove" @click="killContainer">强制停止</Md3Button>
      <el-popconfirm title="确认删除容器?" @confirm="deleteContainer">
        <template #reference>
          <Md3Button variant="danger" :icon="Delete">删除</Md3Button>
        </template>
      </el-popconfirm>
      <Md3Button :icon="DataAnalysis" @click="openStats">资源监控</Md3Button>
      <Md3Button :icon="Monitor" @click="activeTab = 'terminal'">进入终端</Md3Button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  Close, Download, Refresh, VideoPause, Remove,
  Delete, DataAnalysis, Monitor, CircleCheck,
} from '@element-plus/icons-vue'
import { useDockerStore, type DockerContainer } from '@/stores/dockerStore'
import Md3Button from '@/components/Md3Button.vue'
import Terminal from '@/components/Terminal.vue'

const route = useRoute()
const router = useRouter()
const dockerStore = useDockerStore()

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

.detail-tabs {
  margin-top: var(--md3-space-sm);
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

.config-pre {
  margin: 0;
  font-family: var(--md3-font-mono);
  font-size: 12px;
  line-height: 1.5;
  white-space: pre-wrap;
}

.detail-actions {
  display: flex;
  gap: var(--md3-space-sm);
  margin-top: var(--md3-space-lg);
  flex-wrap: wrap;
}
</style>
