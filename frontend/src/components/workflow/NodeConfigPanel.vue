<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { Md3Input, Md3Select, Md3Switch, Md3Divider } from '@/components/md3'
import Md3Button from '@/components/Md3Button.vue'

interface NodeData {
  id: string
  node_type: string
  name: string
  config: Record<string, any>
  position_x: number
  position_y: number
}

interface SshAccount {
  id: string
  name: string
}

const props = defineProps<{
  node: NodeData | null
  sshAccounts?: SshAccount[]
}>()

const emit = defineEmits<{
  update: [nodeId: string, config: Record<string, any>]
  close: []
}>()

const localConfig = ref<Record<string, any>>({})

watch(() => props.node, (newNode) => {
  if (newNode) {
    localConfig.value = { ...newNode.config }
  }
}, { immediate: true })

const nodeTypeLabel = computed(() => {
  const labels: Record<string, string> = {
    trigger_cron: '定时触发器',
    trigger_webhook: 'Webhook 触发器',
    trigger_event: '事件触发器',
    action_shell: 'Shell 命令',
    action_http: 'HTTP 请求',
    action_script: '脚本执行',
    condition: '条件判断',
    loop: '循环',
    wait: '等待',
    notify: '通知',
    end: '结束',
  }
  return props.node ? labels[props.node.node_type] || props.node.node_type : ''
})

const httpMethodOptions = [
  { label: 'GET', value: 'GET' },
  { label: 'POST', value: 'POST' },
  { label: 'PUT', value: 'PUT' },
  { label: 'DELETE', value: 'DELETE' },
]

const loopTypeOptions = [
  { label: '计数循环', value: 'count' },
  { label: '迭代循环', value: 'iterate' },
  { label: '条件循环', value: 'while' },
]

const notifyChannelOptions = [
  { label: 'Webhook', value: 'webhook' },
  { label: '邮件', value: 'email' },
  { label: '钉钉', value: 'dingtalk' },
  { label: '企业微信', value: 'wecom' },
]

const eventTypeOptions = [
  { label: '部署完成', value: 'deploy_complete' },
  { label: '构建失败', value: 'build_failed' },
  { label: '服务异常', value: 'service_error' },
  { label: '自定义', value: 'custom' },
]

const eventSourceOptions = [
  { label: '系统', value: 'system' },
  { label: '外部', value: 'external' },
]

const sshAccountOptions = computed(() => {
  return (props.sshAccounts || []).map(a => ({ label: a.name, value: a.id }))
})

function addEnvVar() {
  if (!localConfig.value.env_vars) localConfig.value.env_vars = []
  localConfig.value.env_vars.push({ key: '', value: '' })
}

function removeEnvVar(index: number) {
  localConfig.value.env_vars.splice(index, 1)
}

function addHeader() {
  if (!localConfig.value.headers) localConfig.value.headers = []
  localConfig.value.headers.push({ key: '', value: '' })
}

function removeHeader(index: number) {
  localConfig.value.headers.splice(index, 1)
}

function save() {
  if (!props.node) return
  emit('update', props.node.id, { ...localConfig.value })
}
</script>

<template>
  <Transition name="panel-slide">
    <div v-if="node" class="node-config-panel">
      <div class="panel-header">
        <div class="panel-header-info">
          <span class="panel-header-title">{{ node.name }}</span>
          <span class="panel-header-type">{{ nodeTypeLabel }}</span>
        </div>
        <button class="panel-close-btn" @click="emit('close')">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M18 6L6 18M6 6l12 12" />
          </svg>
        </button>
      </div>

      <div class="panel-body">
        <template v-if="node.node_type === 'trigger_cron'">
          <Md3Input v-model="localConfig.cron_expression" label="Cron 表达式" placeholder="0 * * * *" />
          <Md3Input v-model="localConfig.timezone" label="时区" placeholder="Asia/Shanghai" />
        </template>

        <template v-else-if="node.node_type === 'trigger_webhook'">
          <Md3Input
            :model-value="localConfig.webhook_url || `https://your-domain.com/api/webhook/${node.id}`"
            label="Webhook URL"
            readonly
          />
          <Md3Switch v-model="localConfig.verify_signature" />
          <span class="switch-label">验证签名</span>
        </template>

        <template v-else-if="node.node_type === 'trigger_event'">
          <Md3Select
            v-model="localConfig.event_type"
            :options="eventTypeOptions"
            label="事件类型"
          />
          <Md3Select
            v-model="localConfig.event_source"
            :options="eventSourceOptions"
            label="事件来源"
          />
        </template>

        <template v-else-if="node.node_type === 'action_shell'">
          <Md3Input v-model="localConfig.command" label="命令" placeholder="echo hello" />
          <Md3Select
            v-model="localConfig.ssh_account_id"
            :options="sshAccountOptions"
            label="SSH 账户"
            placeholder="本机执行"
          />
          <Md3Input v-model="localConfig.working_dir" label="工作目录" placeholder="/home/user" />
          <Md3Divider label="环境变量" />
          <div v-for="(env, i) in localConfig.env_vars || []" :key="i" class="kv-row">
            <Md3Input v-model="env.key" placeholder="KEY" />
            <Md3Input v-model="env.value" placeholder="VALUE" />
            <button class="kv-remove-btn" @click="removeEnvVar(i)">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M18 6L6 18M6 6l12 12" />
              </svg>
            </button>
          </div>
          <Md3Button variant="text" size="sm" @click="addEnvVar">+ 添加环境变量</Md3Button>
        </template>

        <template v-else-if="node.node_type === 'action_http'">
          <Md3Select
            v-model="localConfig.method"
            :options="httpMethodOptions"
            label="请求方法"
          />
          <Md3Input v-model="localConfig.url" label="URL" placeholder="https://api.example.com" />
          <Md3Divider label="请求头" />
          <div v-for="(h, i) in localConfig.headers || []" :key="i" class="kv-row">
            <Md3Input v-model="h.key" placeholder="Header" />
            <Md3Input v-model="h.value" placeholder="Value" />
            <button class="kv-remove-btn" @click="removeHeader(i)">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M18 6L6 18M6 6l12 12" />
              </svg>
            </button>
          </div>
          <Md3Button variant="text" size="sm" @click="addHeader">+ 添加请求头</Md3Button>
          <Md3Input
            v-model="localConfig.body"
            label="请求体"
            placeholder="{}"
          />
          <Md3Input
            v-model="localConfig.timeout"
            label="超时 (秒)"
            type="number"
            placeholder="30"
          />
        </template>

        <template v-else-if="node.node_type === 'action_script'">
          <Md3Input v-model="localConfig.language" label="脚本语言" placeholder="python" />
          <Md3Input v-model="localConfig.script" label="脚本内容" placeholder="#!/usr/bin/env python3" />
          <Md3Input v-model="localConfig.working_dir" label="工作目录" placeholder="/home/user" />
        </template>

        <template v-else-if="node.node_type === 'condition'">
          <Md3Input
            v-model="localConfig.expression"
            label="条件表达式"
            placeholder="${result.status} === 'success'"
          />
          <div class="hint-text">使用 ${variable} 引用上游节点输出变量</div>
        </template>

        <template v-else-if="node.node_type === 'loop'">
          <Md3Select
            v-model="localConfig.loop_type"
            :options="loopTypeOptions"
            label="循环类型"
          />
          <Md3Input
            v-if="localConfig.loop_type === 'count'"
            v-model="localConfig.count"
            label="循环次数"
            type="number"
            placeholder="10"
          />
          <Md3Input
            v-if="localConfig.loop_type === 'iterate'"
            v-model="localConfig.items"
            label="迭代列表"
            placeholder='${[1, 2, 3]}'
          />
          <Md3Input
            v-if="localConfig.loop_type === 'while'"
            v-model="localConfig.condition"
            label="循环条件"
            placeholder="${counter} < 10"
          />
        </template>

        <template v-else-if="node.node_type === 'wait'">
          <Md3Input
            v-model="localConfig.seconds"
            label="等待时间 (秒)"
            type="number"
            placeholder="5"
          />
        </template>

        <template v-else-if="node.node_type === 'notify'">
          <Md3Select
            v-model="localConfig.channel"
            :options="notifyChannelOptions"
            label="通知渠道"
          />
          <Md3Input v-model="localConfig.recipients" label="接收人" placeholder="user@example.com" />
          <Md3Input v-model="localConfig.message" label="消息内容" placeholder="工作流执行完成" />
          <Md3Input
            v-if="localConfig.channel === 'webhook'"
            v-model="localConfig.webhook_url"
            label="Webhook URL"
            placeholder="https://hooks.example.com/xxx"
          />
        </template>

        <template v-else-if="node.node_type === 'end'">
          <div class="empty-hint">结束节点无需配置</div>
        </template>
      </div>

      <div class="panel-footer">
        <Md3Button variant="primary" block @click="save">保存配置</Md3Button>
      </div>
    </div>
  </Transition>
</template>

<style scoped>
.node-config-panel {
  position: absolute;
  top: 0;
  right: 0;
  width: 360px;
  height: 100%;
  background: var(--md3-surface-container);
  border-left: 1px solid var(--md3-outline-variant);
  display: flex;
  flex-direction: column;
  z-index: 20;
  box-shadow: -4px 0 12px rgba(0, 0, 0, 0.08);
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--md3-space-lg) var(--md3-space-xl);
  border-bottom: 1px solid var(--md3-outline-variant);
  flex-shrink: 0;
}

.panel-header-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.panel-header-title {
  font: var(--md3-type-title-medium);
  color: var(--md3-on-surface);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.panel-header-type {
  font: var(--md3-type-body-small);
  color: var(--md3-on-surface-variant);
}

.panel-close-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border: none;
  background: transparent;
  color: var(--md3-on-surface-variant);
  cursor: pointer;
  border-radius: var(--md3-shape-full);
  flex-shrink: 0;
  transition: background-color var(--md3-motion-duration-short) var(--md3-motion-easing-standard);
}

.panel-close-btn:hover {
  background: var(--md3-surface-container-highest);
}

.panel-body {
  flex: 1;
  overflow-y: auto;
  padding: var(--md3-space-lg) var(--md3-space-xl);
  display: flex;
  flex-direction: column;
  gap: var(--md3-space-md);
}

.panel-footer {
  padding: var(--md3-space-md) var(--md3-space-xl) var(--md3-space-lg);
  border-top: 1px solid var(--md3-outline-variant);
  flex-shrink: 0;
}

.kv-row {
  display: flex;
  gap: var(--md3-space-xs);
  align-items: center;
}

.kv-row .md3-input-wrapper {
  flex: 1;
  min-width: 0;
}

.kv-remove-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border: none;
  background: transparent;
  color: var(--md3-on-surface-variant);
  cursor: pointer;
  border-radius: var(--md3-shape-full);
  flex-shrink: 0;
  transition: background-color var(--md3-motion-duration-short) var(--md3-motion-easing-standard);
}

.kv-remove-btn:hover {
  background: var(--md3-error-container);
  color: var(--md3-error);
}

.switch-label {
  font: var(--md3-type-body-small);
  color: var(--md3-on-surface-variant);
  margin-top: calc(-1 * var(--md3-space-xs));
}

.hint-text {
  font: var(--md3-type-body-small);
  color: var(--md3-on-surface-variant);
  opacity: 0.7;
  padding: var(--md3-space-xs) 0;
}

.empty-hint {
  font: var(--md3-type-body-medium);
  color: var(--md3-on-surface-variant);
  text-align: center;
  padding: var(--md3-space-xl) 0;
  opacity: 0.6;
}

.panel-slide-enter-active {
  transition: transform var(--md3-motion-duration-medium) var(--md3-motion-easing-emphasized-decelerate);
}

.panel-slide-leave-active {
  transition: transform var(--md3-motion-duration-short) var(--md3-motion-easing-emphasized-accelerate);
}

.panel-slide-enter-from,
.panel-slide-leave-to {
  transform: translateX(100%);
}
</style>
