<template>
  <div class="settings">
    <el-page-header title="OpsV-Kits">
      <template #content>
        <span>系统设置</span>
      </template>
    </el-page-header>
    <el-divider />

    <el-card shadow="never">
      <template #header>
        <span><el-icon><Clock /></el-icon> 会话历史管理</span>
      </template>

      <el-form label-width="200px" label-position="left" @submit.prevent="saveSettings">
        <el-form-item label="会话历史保留时间">
          <el-input-number v-model="sessionTtlHours" :min="1" :max="720" style="width: 160px" />
          <span style="margin-left: 8px; color: #909399;">小时（1小时~30天，默认72小时）</span>
        </el-form-item>
        <el-form-item label="已保存的历史会话数">
          <el-tag type="info">{{ historyCount }} 条</el-tag>
          <el-button size="small" style="margin-left: 12px" @click="clearAllHistory" :disabled="historyCount === 0">
            清空全部历史
          </el-button>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="saveSettings" :loading="saving">保存设置</el-button>
          <el-tag v-if="saved" type="success" style="margin-left: 12px">已保存</el-tag>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card shadow="never">
      <template #header>
        <span><el-icon><FolderOpened /></el-icon> 远程硬盘（NAS）</span>
      </template>

      <el-form label-width="200px" label-position="left">
        <el-form-item label="启用远程硬盘">
          <el-switch
            v-model="remoteDriveEnabled"
            active-text="已启用"
            inactive-text="已关闭"
            @change="onRemoteDriveToggle"
          />
          <el-tag
            :type="remoteDriveRunning ? 'success' : 'info'"
            size="small"
            style="margin-left: 12px"
          >
            {{ remoteDriveRunning ? '服务运行中' : '服务已停止' }}
          </el-tag>
        </el-form-item>

        <el-form-item label="连接地址" v-if="remoteDriveEnabled">
          <div>
            <el-input
              :model-value="webdavUrl"
              readonly
              style="width: 360px"
            >
              <template #append>
                <el-button @click="copyUrl" :icon="DocumentCopy" size="small">
                  复制
                </el-button>
              </template>
            </el-input>
            <div style="margin-top: 6px; font-size: 12px; color: #909399;">
              在 Windows 资源管理器中，选择"映射网络驱动器"，输入此地址即可访问远程文件
            </div>
          </div>
        </el-form-item>

        <el-form-item label="已连接的远程主机" v-if="mounts.length > 0">
          <div style="width: 100%;">
            <el-table :data="mounts" size="small" stripe style="width: 100%;">
              <el-table-column prop="alias" label="别名" width="140" />
              <el-table-column prop="hostname" label="主机地址" width="180" />
              <el-table-column prop="port" label="端口" width="80" />
              <el-table-column label="访问地址">
                <template #default="scope">
                  <el-link type="primary" :href="scope.row.url" target="_blank">{{ scope.row.url }}</el-link>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </el-form-item>

        <el-form-item v-if="remoteDriveRunning">
          <div style="font-size: 12px; color: #67c23a;">
            <el-icon><SuccessFilled /></el-icon>
            远程硬盘服务运行中 — 共 {{ accountCount }} 台远程主机可用
          </div>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { Clock, FolderOpened, DocumentCopy, SuccessFilled } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { request } from '@/api'

const sessionTtlHours = ref(72)
const historyCount = ref(0)
const saving = ref(false)
const saved = ref(false)

const remoteDriveEnabled = ref(true)
const remoteDriveRunning = ref(false)
const remoteDrivePort = ref(8081)
const webdavUrl = ref('http://127.0.0.1:8081/')
const mounts = ref<any[]>([])
const accountCount = ref(0)

async function loadSettings() {
  try {
    const res: any = await request.get('/settings')
    sessionTtlHours.value = res.session_ttl_hours || 72
    remoteDriveEnabled.value = res.remote_drive_enabled !== false
    remoteDrivePort.value = res.remote_drive_port || 8081
  } catch {}
  try {
    const histRes: any = await request.get('/webssh/sessions/history')
    historyCount.value = histRes.count || 0
  } catch {}
  loadDriveStatus()
}

async function loadDriveStatus() {
  try {
    const status: any = await request.get('/remote-drive/status')
    remoteDriveRunning.value = status.running
    webdavUrl.value = status.webdav_url
    mounts.value = status.mounts || []
    accountCount.value = status.account_count
  } catch {}
}

async function saveSettings() {
  saving.value = true
  saved.value = false
  try {
    await request.put('/settings', {
      session_ttl_hours: sessionTtlHours.value,
      remote_drive_enabled: remoteDriveEnabled.value,
      remote_drive_port: remoteDrivePort.value,
    })
    saved.value = true
    ElMessage.success('设置已保存')
    setTimeout(() => { saved.value = false }, 2000)
  } catch {
    ElMessage.error('保存失败')
  } finally { saving.value = false }
}

async function onRemoteDriveToggle(val: boolean) {
  try {
    await request.put('/settings', { remote_drive_enabled: val })
    ElMessage.success(val ? '远程硬盘功能已开启' : '远程硬盘功能已关闭')
    loadDriveStatus()
  } catch {
    ElMessage.error('设置更新失败')
    remoteDriveEnabled.value = !val
  }
}

async function copyUrl() {
  try {
    await navigator.clipboard.writeText(webdavUrl.value)
    ElMessage.success('地址已复制到剪贴板')
  } catch {
    ElMessage.warning('复制失败，请手动复制')
  }
}

async function clearAllHistory() {
  try {
    const histRes: any = await request.get('/webssh/sessions/history')
    const sessions = histRes.sessions || []
    for (const s of sessions) {
      await request.delete(`/webssh/sessions/history/${s.session_id}`)
    }
    historyCount.value = 0
    ElMessage.success('历史已清空')
  } catch {
    ElMessage.error('清空失败')
  }
}

onMounted(loadSettings)
</script>

<style scoped>
.settings { padding: 0; }
.el-card { margin-bottom: 16px; }
</style>
