<template>
  <Md3Dialog
    :visible="visible"
    @update:visible="$emit('update:visible', $event)"
    title="新建 SSH 连接"
    width="560px"
  >
    <div class="ssh-dialog-form">
      <div class="form-item">
        <label class="form-label">连接方式</label>
        <div class="radio-group">
          <Md3Radio v-model="connectMode" value="saved" label="使用已保存账户" />
          <Md3Radio v-model="connectMode" value="manual" label="手动输入" />
        </div>
      </div>

      <template v-if="connectMode === 'saved'">
        <div class="form-item">
          <label class="form-label">SSH 账户</label>
          <Md3Select v-model="formData.account_alias" placeholder="选择 SSH 账户">
            <option v-for="acc in accounts" :key="acc.alias" :value="acc.alias">
              {{ acc.alias }} ({{ acc.host }}:{{ acc.port }})
            </option>
          </Md3Select>
        </div>
      </template>

      <template v-else>
        <Md3Divider content-position="center">手动输入</Md3Divider>

        <div class="form-item">
          <label class="form-label">主机地址</label>
          <div class="host-port-row">
            <Md3Input v-model="manualForm.host" placeholder="192.168.1.100" class="host-input" />
            <Md3Input v-model.number="manualForm.port" placeholder="22" class="port-input" />
          </div>
        </div>
        <div class="form-item">
          <label class="form-label">用户名</label>
          <Md3Input v-model="manualForm.username" placeholder="root" />
        </div>
        <div class="form-item">
          <label class="form-label">认证方式</label>
          <div class="radio-group">
            <Md3Radio v-model="manualForm.auth_type" value="password" label="密码" />
            <Md3Radio v-model="manualForm.auth_type" value="key" label="SSH 密钥" />
            <Md3Radio v-model="manualForm.auth_type" value="agent" label="SSH Agent" />
          </div>
        </div>

        <div class="form-item" v-if="manualForm.auth_type === 'password'">
          <label class="form-label">密码</label>
          <Md3Input v-model="manualForm.password" type="password" show-password placeholder="登录密码" />
        </div>

        <template v-if="manualForm.auth_type === 'key'">
          <div class="form-item">
            <label class="form-label">私钥文件</label>
            <Md3Input v-model="manualForm.private_key" placeholder="~/.ssh/id_rsa" />
          </div>
          <div class="form-item">
            <label class="form-label">密钥密码</label>
            <Md3Input v-model="manualForm.key_passphrase" type="password" show-password placeholder="私钥密码（可选）" />
          </div>
        </template>

        <div class="form-item">
          <label class="form-label">双因素认证</label>
          <Md3Input v-model="manualForm.totp_code" placeholder="TOTP 验证码" class="totp-input" />
        </div>
      </template>

      <Md3Divider />

      <div class="form-item">
        <label class="form-label">选项</label>
        <div class="checkbox-group">
          <Md3Checkbox v-model="options.save_session" label="保存此会话配置" />
          <Md3Checkbox v-model="options.auto_connect" label="自动连接" />
        </div>
      </div>

      <Md3Divider content-position="center">终端设置</Md3Divider>

      <div class="form-item">
        <label class="form-label">主题</label>
        <Md3Select v-model="terminalSettings.theme" class="sm-select">
          <option value="dark">Dark</option>
          <option value="light">Light</option>
        </Md3Select>
      </div>
      <div class="form-item">
        <label class="form-label">字体</label>
        <Md3Select v-model="terminalSettings.font_family" class="md-select">
          <option value="'Fira Code', monospace">Fira Code</option>
          <option value="'Cascadia Code', monospace">Cascadia Code</option>
          <option value="Consolas, monospace">Consolas</option>
          <option value="'Courier New', monospace">Courier New</option>
        </Md3Select>
      </div>
      <div class="form-item">
        <label class="form-label">字号</label>
        <Md3Input v-model.number="terminalSettings.font_size" type="number" class="number-input" />
      </div>
      <div class="form-item">
        <label class="form-label">编码</label>
        <Md3Select v-model="terminalSettings.encoding" class="sm-select">
          <option value="utf-8">UTF-8</option>
          <option value="gbk">GBK</option>
          <option value="iso-8859-1">ISO-8859-1</option>
        </Md3Select>
      </div>
    </div>

    <template #footer>
      <Md3Button :icon="ConnectionIcon" @click="testConnection" :loading="testing">
        测试连接
      </Md3Button>
      <Md3Button @click="$emit('update:visible', false)">取消</Md3Button>
      <Md3Button variant="primary" :icon="LinkIcon" @click="doConnect">
        连接
      </Md3Button>
    </template>
  </Md3Dialog>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, defineComponent, h } from 'vue'
import { Md3Message, Md3Icon } from '@/components/md3'
import { 
  Md3Dialog, 
  Md3Input, 
  Md3Select, 
  Md3Radio, 
  Md3Checkbox, 
  Md3Divider,
} from '@/components/md3'
import Md3Button from '@/components/Md3Button.vue'
import { useSshAccountStore } from '@/stores/sshAccountStore'
import { request } from '@/api'

// Icon wrappers for Md3Button compatibility
const ConnectionIcon = defineComponent(() => () => h(Md3Icon, { name: 'connection' }))
const LinkIcon = defineComponent(() => () => h(Md3Icon, { name: 'connection' }))

defineProps<{
  visible: boolean
}>()

const emit = defineEmits<{
  'update:visible': [value: boolean]
  connect: [config: any]
}>()

const sshStore = useSshAccountStore()

const connectMode = ref<'saved' | 'manual'>('saved')

const formData = ref({
  account_alias: '',
  use_saved_account: true,
})

const manualForm = ref({
  host: '',
  port: 22,
  username: '',
  auth_type: 'password' as 'password' | 'key' | 'agent',
  password: '',
  private_key: '',
  key_passphrase: '',
  totp_code: '',
})

const options = ref({
  save_session: true,
  auto_connect: true,
})

const terminalSettings = ref({
  theme: 'dark',
  font_family: "'Fira Code', monospace",
  font_size: 14,
  encoding: 'utf-8',
})

const accounts = computed(() => sshStore.accounts)

function buildConfig() {
  const baseConfig = {
    use_saved_account: connectMode.value === 'saved',
    ...options.value,
    ...terminalSettings.value,
  }
  if (connectMode.value === 'saved') {
    return {
      ...baseConfig,
      account_alias: formData.value.account_alias,
    }
  }
  return {
    ...baseConfig,
    ...manualForm.value,
  }
}

const testing = ref(false)

async function testConnection() {
  testing.value = true
  const config: any = buildConfig()
  try {
    if (connectMode.value === 'saved' && config.account_alias) {
      const res = await sshStore.testConnection(config.account_alias)
      if (res.success) {
        Md3Message.success(res.message || '连接测试成功')
      } else {
        Md3Message.error(res.message || '连接测试失败')
      }
    } else {
      const res = await request.post<{ success: boolean; message: string }>('/webssh/test', config)
      if (res.success) {
        Md3Message.success(res.message || '连接测试成功')
      } else {
        Md3Message.error(res.message || '连接测试失败')
      }
    }
  } catch (e: any) {
    const msg = e?.response?.data?.detail || e?.message || '连接测试失败'
    Md3Message.error(msg)
  } finally {
    testing.value = false
  }
}

function doConnect() {
  const config = buildConfig()
  emit('connect', config)
}

onMounted(() => {
  sshStore.fetchAccounts()
})
</script>

<style scoped>
.account-desc {
  color: var(--md3-on-surface-variant);
  font-size: 12px;
  margin-left: var(--md3-space-sm);
}

.ssh-dialog-form {
  display: flex;
  flex-direction: column;
  gap: var(--md3-space-md);
}

.form-item {
  display: flex;
  flex-direction: column;
  gap: var(--md3-space-xs);
}

.form-label {
  font: var(--md3-type-label-small);
  color: var(--md3-on-surface-variant);
  letter-spacing: 0.5px;
}

.radio-group,
.checkbox-group {
  display: flex;
  flex-direction: column;
  gap: var(--md3-space-sm);
}

.host-port-row {
  display: flex;
  gap: var(--md3-space-sm);
}

.host-input {
  flex: 1;
}

.port-input {
  width: 70px;
}

.totp-input {
  width: 160px;
}

.sm-select {
  width: 160px;
}

.md-select {
  width: 200px;
}

.number-input {
  width: 100px;
}
</style>
