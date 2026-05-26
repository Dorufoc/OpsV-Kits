<template>
  <el-dialog
    :model-value="visible"
    @update:model-value="$emit('update:visible', $event)"
    title="新建 SSH 连接"
    width="560px"
    top="5vh"
  >
    <el-form label-width="110px" label-position="left">
      <el-form-item label="连接方式">
        <el-radio-group v-model="connectMode">
          <el-radio value="saved">使用已保存账户</el-radio>
          <el-radio value="manual">手动输入</el-radio>
        </el-radio-group>
      </el-form-item>

      <template v-if="connectMode === 'saved'">
        <el-form-item label="SSH 账户">
          <el-select v-model="formData.account_alias" placeholder="选择 SSH 账户" style="width: 100%">
            <el-option
              v-for="acc in accounts"
              :key="acc.alias"
              :label="acc.alias"
              :value="acc.alias"
            >
              <span>{{ acc.alias }}</span>
              <span class="account-desc">({{ acc.host }}:{{ acc.port }})</span>
            </el-option>
          </el-select>
        </el-form-item>
      </template>

      <template v-else>
        <el-divider content-position="center">手动输入</el-divider>

        <el-form-item label="主机地址">
          <el-input v-model="manualForm.host" placeholder="192.168.1.100" style="width: calc(100% - 80px)" />
          <el-input v-model.number="manualForm.port" placeholder="22" style="width: 70px; margin-left: 4px" />
        </el-form-item>
        <el-form-item label="用户名">
          <el-input v-model="manualForm.username" placeholder="root" />
        </el-form-item>
        <el-form-item label="认证方式">
          <el-radio-group v-model="manualForm.auth_type">
            <el-radio value="password">密码</el-radio>
            <el-radio value="key">SSH 密钥</el-radio>
            <el-radio value="agent">SSH Agent</el-radio>
          </el-radio-group>
        </el-form-item>

        <el-form-item label="密码" v-if="manualForm.auth_type === 'password'">
          <el-input v-model="manualForm.password" type="password" show-password placeholder="登录密码" />
        </el-form-item>

        <template v-if="manualForm.auth_type === 'key'">
          <el-form-item label="私钥文件">
            <el-input v-model="manualForm.private_key" placeholder="~/.ssh/id_rsa" />
          </el-form-item>
          <el-form-item label="密钥密码">
            <el-input v-model="manualForm.key_passphrase" type="password" show-password placeholder="私钥密码（可选）" />
          </el-form-item>
        </template>

        <el-form-item label="双因素认证">
          <el-input v-model="manualForm.totp_code" placeholder="TOTP 验证码" style="width: 160px" />
        </el-form-item>
      </template>

      <el-divider />

      <el-form-item label="选项">
        <el-checkbox v-model="options.save_session">保存此会话配置</el-checkbox>
        <el-checkbox v-model="options.auto_connect" style="margin-left: 16px">自动连接</el-checkbox>
      </el-form-item>

      <el-divider content-position="center">终端设置</el-divider>

      <el-form-item label="主题">
        <el-select v-model="terminalSettings.theme" style="width: 160px">
          <el-option label="Dark" value="dark" />
          <el-option label="Light" value="light" />
        </el-select>
      </el-form-item>
      <el-form-item label="字体">
        <el-select v-model="terminalSettings.font_family" style="width: 200px">
          <el-option label="Fira Code" value="'Fira Code', monospace" />
          <el-option label="Cascadia Code" value="'Cascadia Code', monospace" />
          <el-option label="Consolas" value="Consolas, monospace" />
          <el-option label="Courier New" value="'Courier New', monospace" />
        </el-select>
      </el-form-item>
      <el-form-item label="字号">
        <el-input-number v-model="terminalSettings.font_size" :min="10" :max="24" />
      </el-form-item>
      <el-form-item label="编码">
        <el-select v-model="terminalSettings.encoding" style="width: 160px">
          <el-option label="UTF-8" value="utf-8" />
          <el-option label="GBK" value="gbk" />
          <el-option label="ISO-8859-1" value="iso-8859-1" />
        </el-select>
      </el-form-item>
    </el-form>

    <template #footer>
      <el-button @click="testConnection" :loading="testing">
        <el-icon><Connection /></el-icon> 测试连接
      </el-button>
      <el-button @click="$emit('update:visible', false)">取消</el-button>
      <el-button type="primary" @click="doConnect">
        <el-icon><Link /></el-icon> 连接
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { Connection, Link } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { useSshAccountStore } from '@/stores/sshAccountStore'
import { request } from '@/api'

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
        ElMessage.success(res.message || '连接测试成功')
      } else {
        ElMessage.error(res.message || '连接测试失败')
      }
    } else {
      const res = await request.post<any>('/webssh/test', config)
      ElMessage.success(res.message || '连接测试成功')
    }
  } catch (e: any) {
    const msg = e?.response?.data?.detail || e?.message || '连接测试失败'
    ElMessage.error(msg)
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
  color: #909399;
  font-size: 12px;
  margin-left: 8px;
}
</style>
