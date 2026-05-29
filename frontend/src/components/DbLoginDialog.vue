<template>
  <Md3Dialog :visible="visible" @close="handleClose" class="db-login-dialog">
    <template #header>
      <span>{{ dbType === 'mysql' ? 'MySQL' : 'Redis' }} 连接</span>
    </template>
    <div class="login-form">
      <div class="form-row">
        <label>主机</label>
        <Md3Input v-model="form.host" placeholder="localhost" />
      </div>
      <div class="form-row">
        <label>端口</label>
        <Md3Input type="number" v-model.number="form.port" :min="1" :max="65535" />
      </div>
      <template v-if="dbType === 'mysql'">
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
    </div>
    <template #footer>
      <Md3Button variant="text" @click="handleClose">取消</Md3Button>
      <Md3Button variant="primary" @click="handleSubmit">连接</Md3Button>
    </template>
  </Md3Dialog>
</template>

<script setup lang="ts">
import { reactive } from 'vue'
import type { MySqlConnectionParams, RedisConnectionParams } from '@/types/db-toolkit'
import { Md3Dialog, Md3Input } from '@/components/md3'
import Md3Button from '@/components/Md3Button.vue'

const props = defineProps<{
  dbType: 'mysql' | 'redis'
  visible: boolean
}>()

const emit = defineEmits<{
  close: []
  submit: [params: any]
}>()

const form = reactive({
  host: 'localhost',
  port: props.dbType === 'mysql' ? 3306 : 6379,
  user: 'root',
  password: '',
  database: '',
  db: 0,
})

function handleClose() {
  emit('close')
}

function handleSubmit() {
  if (props.dbType === 'mysql') {
    emit('submit', {
      host: form.host,
      port: form.port,
      user: form.user,
      password: form.password,
      database: form.database,
    } as MySqlConnectionParams)
  } else {
    emit('submit', {
      host: form.host,
      port: form.port,
      password: form.password,
      db: form.db,
    } as RedisConnectionParams)
  }
}
</script>

<style scoped>
.login-form {
  display: flex;
  flex-direction: column;
  gap: var(--md3-space-md);
  min-width: 320px;
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
</style>
