<template>
  <div class="vite-deploy-panel">
    <div class="status-area">
      <div class="status-sidebar">
        <ViteStatusCard :node-status="viteStore.nodeStatus" :nginx-status="viteStore.nginxStatus" />
        <Md3Divider />
        <div class="deploy-progress-card">
          <div class="panel-header">
            <span class="panel-title">部署进度</span>
            <Md3Tag :type="deployTagType" size="sm">{{ deployTagText }}</Md3Tag>
          </div>
          <div class="step-list">
            <div
              v-for="(step, index) in deploySteps"
              :key="step.key"
              class="step-item"
              :class="{
                'step-item--active': currentStepIndex === index,
                'step-item--completed': currentStepIndex > index,
              }"
            >
              <div class="step-indicator">
                <span v-if="currentStepIndex > index" class="step-check">
                  <Md3Icon name="check" />
                </span>
                <span v-else class="step-number">{{ index + 1 }}</span>
              </div>
              <span class="step-label">{{ step.label }}</span>
            </div>
          </div>
          <div class="progress-bar-wrap" v-if="viteStore.deployStatus !== 'idle'">
            <Md3Progress
              :percentage="viteStore.progress"
              :color="progressColor"
              :animated="viteStore.deployStatus === 'running'"
            />
          </div>
        </div>
        <Md3Divider />
        <div v-if="viteStore.nginxUrl" class="nginx-url-card">
          <div class="panel-header">
            <span class="panel-title">访问地址</span>
            <Md3Tag type="success" size="sm">已部署</Md3Tag>
          </div>
          <a :href="viteStore.nginxUrl" target="_blank" class="nginx-url-link">
            <Md3Icon name="external-link" />
            <span>{{ viteStore.nginxUrl }}</span>
          </a>
        </div>
      </div>
      <div class="status-terminal">
        <div class="terminal-header">
          <span class="terminal-title">终端输出</span>
        </div>
        <Terminal ref="terminalRef" :show-toolbar="true" session-name="Vite 部署终端" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, onMounted, onUnmounted } from 'vue'
import { Md3Tag, Md3Icon, Md3Divider, Md3Progress } from '@/components/md3'
import { useViteDeployStore } from '@/stores/viteDeployStore'
import type { ProjectItem } from '@/stores/projectStore'
import ViteStatusCard from './ViteStatusCard.vue'
import Terminal from './Terminal.vue'

defineProps<{
  projectConfig: ProjectItem
}>()

defineEmits<{
  (e: 'check'): void
  (e: 'setup'): void
  (e: 'installDeps'): void
  (e: 'build'): void
  (e: 'nginx'): void
  (e: 'deploy'): void
  (e: 'stop'): void
}>()

const viteStore = useViteDeployStore()
const terminalRef = ref<InstanceType<typeof Terminal>>()

const deploySteps = [
  { key: 'setup', label: '安装 Node' },
  { key: 'install-deps', label: '安装依赖' },
  { key: 'build', label: '构建项目' },
  { key: 'nginx', label: '配置 Nginx' },
]

const stepKeyToIndex: Record<string, number> = {
  setup: 0,
  'install-deps': 1,
  build: 2,
  nginx: 3,
}

const currentStepIndex = computed(() => {
  const idx = stepKeyToIndex[viteStore.currentStep]
  return idx !== undefined ? idx : -1
})

const deployTagType = computed(() => {
  const map: Record<string, 'primary' | 'success' | 'warning' | 'danger' | 'info'> = {
    idle: 'info',
    running: 'primary',
    completed: 'success',
    failed: 'danger',
    stopped: 'warning',
  }
  return map[viteStore.deployStatus] || 'info'
})

const deployTagText = computed(() => {
  const map: Record<string, string> = {
    idle: '待部署',
    running: '部署中',
    completed: '已完成',
    failed: '失败',
    stopped: '已停止',
  }
  return map[viteStore.deployStatus] || '未知'
})

const progressColor = computed(() => {
  if (viteStore.deployStatus === 'completed') return 'var(--md3-success)'
  if (viteStore.deployStatus === 'failed') return 'var(--md3-error)'
  if (viteStore.deployStatus === 'stopped') return 'var(--md3-warning)'
  return ''
})

function setLogCallback(cb: (text: string) => void) {
  viteStore.setLogCallback(cb)
}

function writeToTerminal(text: string) {
  terminalRef.value?.write(text)
}

function writelnToTerminal(text: string) {
  terminalRef.value?.writeln(text)
}

function clearTerminal() {
  terminalRef.value?.clear()
}

onMounted(() => {
  viteStore.setLogCallback((text: string) => {
    terminalRef.value?.write(text)
  })
})

onUnmounted(() => {
  viteStore.setLogCallback(() => {})
})

defineExpose({
  setLogCallback,
  writeToTerminal,
  writelnToTerminal,
  clearTerminal,
  terminalRef,
})
</script>

<style scoped>
.vite-deploy-panel {
  display: flex;
  flex-direction: column;
  gap: var(--md3-space-lg);
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

.status-area {
  flex: 1;
  display: flex;
  gap: var(--md3-space-lg);
  min-height: 0;
  overflow: hidden;
}

.status-sidebar {
  width: 260px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: var(--md3-space-md);
  background: var(--md3-glass-bg);
  backdrop-filter: var(--md3-glass-blur);
  -webkit-backdrop-filter: var(--md3-glass-blur);
  border: 1px solid var(--md3-glass-border);
  border-radius: var(--md3-shape-md);
  padding: var(--md3-space-md);
  transition: border-color var(--md3-motion-duration-medium) var(--md3-motion-easing-standard);
  overflow-y: auto;
  max-height: 100%;
}

.status-sidebar:hover {
  border-color: var(--md3-card-border-hover);
}

.deploy-progress-card {
  padding: var(--md3-space-md);
  background: var(--md3-glass-bg);
  backdrop-filter: var(--md3-glass-blur);
  -webkit-backdrop-filter: var(--md3-glass-blur);
  border: 1px solid var(--md3-glass-border);
  border-radius: var(--md3-shape-md);
  transition: border-color var(--md3-motion-duration-medium) var(--md3-motion-easing-standard);
}

.deploy-progress-card:hover {
  border-color: var(--md3-card-border-hover);
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--md3-space-md);
}

.panel-title {
  font-weight: 600;
  font-size: 16px;
  color: var(--md3-on-surface);
}

.step-list {
  display: flex;
  flex-direction: column;
  gap: var(--md3-space-xs);
}

.step-item {
  display: flex;
  align-items: center;
  gap: var(--md3-space-sm);
  padding: var(--md3-space-sm) var(--md3-space-md);
  border-radius: var(--md3-shape-sm);
  transition: all var(--md3-motion-duration-short) var(--md3-motion-easing-standard);
  font-size: 13px;
  color: var(--md3-on-surface-variant);
}

.step-item--active {
  background: var(--md3-primary-container);
  color: var(--md3-on-primary-container);
  font-weight: 500;
}

.step-item--completed {
  color: var(--md3-success);
}

.step-indicator {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  flex-shrink: 0;
}

.step-number {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  border-radius: var(--md3-shape-full);
  background: var(--md3-surface-container-highest);
  font-size: 11px;
  font-weight: 600;
  color: var(--md3-on-surface-variant);
}

.step-item--active .step-number {
  background: var(--md3-primary);
  color: var(--md3-on-primary);
}

.step-check {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  color: var(--md3-success);
}

.step-check :deep(svg) {
  width: 16px;
  height: 16px;
}

.step-label {
  flex: 1;
}

.progress-bar-wrap {
  margin-top: var(--md3-space-md);
}

.nginx-url-card {
  padding: var(--md3-space-md);
  background: var(--md3-glass-bg);
  backdrop-filter: var(--md3-glass-blur);
  -webkit-backdrop-filter: var(--md3-glass-blur);
  border: 1px solid var(--md3-glass-border);
  border-radius: var(--md3-shape-md);
  transition: border-color var(--md3-motion-duration-medium) var(--md3-motion-easing-standard);
}

.nginx-url-card:hover {
  border-color: var(--md3-card-border-hover);
}

.nginx-url-link {
  display: flex;
  align-items: center;
  gap: var(--md3-space-sm);
  padding: var(--md3-space-sm) var(--md3-space-md);
  background: var(--md3-surface-container-low);
  border-radius: var(--md3-shape-sm);
  color: var(--md3-primary);
  font-size: 13px;
  text-decoration: none;
  word-break: break-all;
  transition: background var(--md3-motion-duration-short) var(--md3-motion-easing-standard);
}

.nginx-url-link:hover {
  background: var(--md3-primary-container);
}

.nginx-url-link :deep(svg) {
  width: 14px;
  height: 14px;
  flex-shrink: 0;
}

.status-terminal {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  overflow: hidden;
}

.terminal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--md3-space-sm) var(--md3-space-md);
  background: var(--md3-glass-bg);
  backdrop-filter: var(--md3-glass-blur);
  -webkit-backdrop-filter: var(--md3-glass-blur);
  border: 1px solid var(--md3-glass-border);
  border-bottom: none;
  border-radius: var(--md3-shape-sm) var(--md3-shape-sm) 0 0;
  flex-shrink: 0;
}

.terminal-title {
  font-weight: 500;
  font-size: 13px;
  color: var(--md3-on-surface);
}

.status-terminal :deep(.terminal-wrapper) {
  border-top-left-radius: 0;
  border-top-right-radius: 0;
  flex: 1;
  overflow: hidden;
}
</style>
