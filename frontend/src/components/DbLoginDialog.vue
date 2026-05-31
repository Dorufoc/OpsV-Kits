<template>
  <Md3Dialog :visible="visible" @close="handleClose" class="db-login-dialog" width="520px">
    <template #header>
      <span>{{ isEditing ? '编辑连接' : '新建连接' }}</span>
    </template>
    <div class="login-form">
      <div class="form-row">
        <label>连接名称</label>
        <Md3Input v-model="form.name" placeholder="输入连接名称" />
      </div>
      <div class="form-row">
        <label>数据库类型</label>
        <Md3Select
          v-model="form.dbType"
          :options="dbTypeOptions"
          placeholder="选择数据库类型"
        />
      </div>
      <div class="form-row">
        <label>部署类型</label>
        <Md3Select
          v-model="form.deployMode"
          :options="deployModeOptions"
          placeholder="选择部署类型"
        />
      </div>
      <div class="form-row" v-if="form.deployMode === 'docker'">
        <label>容器 ID</label>
        <Md3Input v-model="form.containerId" placeholder="输入容器 ID" />
      </div>
      <div class="form-row">
        <label>主机</label>
        <Md3Input v-model="form.host" placeholder="localhost" />
      </div>
      <div class="form-row">
        <label>端口</label>
        <Md3Input type="number" v-model.number="form.port" :min="1" :max="65535" />
      </div>
      <template v-if="form.dbType === 'mysql'">
        <div class="form-row">
          <label>用户名</label>
          <Md3Input v-model="form.user" placeholder="root" />
        </div>
        <div class="form-row">
          <label>密码</label>
          <Md3Input type="password" v-model="form.password" autocomplete="off" />
        </div>
        <div class="form-row">
          <label>数据库</label>
          <Md3Input v-model="form.database" placeholder="可选" />
        </div>
      </template>
      <template v-else>
        <div class="form-row">
          <label>密码</label>
          <Md3Input type="password" v-model="form.password" autocomplete="off" />
        </div>
        <div class="form-row">
          <label>数据库编号</label>
          <Md3Input type="number" v-model.number="form.db" :min="0" :max="15" />
        </div>
      </template>
      <div class="form-row form-row--test">
        <Md3Button
          variant="default"
          size="sm"
          :loading="testing"
          @click="testConnection"
        >
          测试连接
        </Md3Button>
        <Md3Checkbox v-model="form.saveConnection" label="保存连接" />
      </div>
      <Md3Alert
        v-if="testResult"
        :type="testResult.success ? 'success' : 'danger'"
        :message="testResult.message"
        closable
        @close="testResult = null"
      />
    </div>
    <template #footer>
      <Md3Button variant="text" @click="handleClose">取消</Md3Button>
      <Md3Button variant="primary" @click="handleSubmit">
        {{ isEditing ? '保存' : '连接' }}
      </Md3Button>
    </template>
  </Md3Dialog>
</template>

<script setup lang="ts">
import { reactive, ref, computed, watch } from 'vue'
import type { MySqlConnectionParams, RedisConnectionParams, DeployMode, DbType, SavedConnection } from '@/types/db-toolkit'
import { Md3Dialog, Md3Input, Md3Select, Md3Checkbox, Md3Alert } from '@/components/md3'
import Md3Button from '@/components/Md3Button.vue'
import { useDbToolkitStore } from '@/stores/dbToolkitStore'

const props = defineProps<{
  deployMode: DeployMode
  accountAlias: string
  containerId?: string
  visible: boolean
  editTarget?: SavedConnection | null
}>()

const emit = defineEmits<{
  close: []
  submit: [params: {
    connection: MySqlConnectionParams | RedisConnectionParams
    deployMode: DeployMode
    dbType: DbType
    name: string
    containerId?: string
    saveConnection: boolean
    editId?: string
  }]
}>()

const store = useDbToolkitStore()

const dbTypeOptions = [
  { label: 'MySQL', value: 'mysql' },
  { label: 'Redis', value: 'redis' },
]

const deployModeOptions = [
  { label: 'Docker 容器', value: 'docker' },
  { label: 'Linux 主机', value: 'host' },
]

const isEditing = computed(() => !!props.editTarget)

const form = reactive({
  name: '',
  deployMode: props.deployMode as DeployMode,
  dbType: 'mysql' as DbType,
  host: 'localhost',
  port: 3306,
  user: 'root',
  password: '',
  database: '',
  db: 0,
  containerId: props.containerId || '',
  saveConnection: true,
})

const testing = ref(false)
const testResult = ref<{ success: boolean; message: string } | null>(null)

watch(() => form.dbType, (newType) => {
  form.port = newType === 'mysql' ? 3306 : 6379
})

watch(() => props.visible, (val) => {
  if (val) {
    testResult.value = null
    if (props.editTarget) {
      const conn = props.editTarget
      form.name = conn.name
      form.deployMode = conn.deployMode
      form.dbType = conn.dbType
      form.containerId = conn.containerId
      form.saveConnection = true
      if (conn.dbType === 'mysql') {
        const c = conn.connection as MySqlConnectionParams
        form.host = c.host
        form.port = c.port
        form.user = c.user
        form.password = c.password
        form.database = c.database
      } else {
        const c = conn.connection as RedisConnectionParams
        form.host = c.host
        form.port = c.port
        form.password = c.password
        form.db = c.db
      }
    } else {
      form.name = ''
      form.deployMode = props.deployMode
      form.dbType = 'mysql'
      form.host = 'localhost'
      form.port = 3306
      form.user = 'root'
      form.password = ''
      form.database = ''
      form.db = 0
      form.containerId = props.containerId || ''
      form.saveConnection = true
    }
  }
})

async function testConnection() {
  testing.value = true
  testResult.value = null
  try {
    const result = await store.detectClient(
      form.dbType,
      props.accountAlias,
      form.deployMode === 'docker' ? form.containerId : undefined
    )
    if (result.installed) {
      testResult.value = { success: true, message: `客户端已安装: ${result.client_version}` }
    } else {
      testResult.value = { success: false, message: result.error || '客户端未安装' }
    }
  } catch (e: any) {
    testResult.value = { success: false, message: e.message || '探测失败' }
  } finally {
    testing.value = false
  }
}

function handleClose() {
  emit('close')
}

function handleSubmit() {
  let connection: MySqlConnectionParams | RedisConnectionParams
  if (form.dbType === 'mysql') {
    connection = {
      host: form.host,
      port: form.port,
      user: form.user,
      password: form.password,
      database: form.database,
    } as MySqlConnectionParams
  } else {
    connection = {
      host: form.host,
      port: form.port,
      password: form.password,
      db: form.db,
    } as RedisConnectionParams
  }
  emit('submit', {
    connection,
    deployMode: form.deployMode,
    dbType: form.dbType,
    name: form.name,
    containerId: form.deployMode === 'docker' ? form.containerId : undefined,
    saveConnection: form.saveConnection,
    editId: props.editTarget?.id,
  })
}
</script>

<style scoped>
.login-form {
  display: flex;
  flex-direction: column;
  gap: var(--md3-space-md);
  min-width: 360px;
}

.form-row {
  display: flex;
  align-items: center;
  gap: var(--md3-space-sm);
}

.form-row label {
  width: 80px;
  font-size: 13px;
  color: var(--md3-on-surface-variant);
  flex-shrink: 0;
}

.form-row--test {
  justify-content: space-between;
  padding-top: var(--md3-space-xs);
}
</style>
