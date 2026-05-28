<template>
  <div class="settings">
    <el-page-header title="OpsV-Kits">
      <template #content>
        <span>系统设置</span>
      </template>
    </el-page-header>
    <el-divider />

    <el-card shadow="never" class="theme-card">
      <template #header>
        <span><el-icon><Monitor /></el-icon> 主题设置</span>
      </template>

      <div class="theme-section">
        <div class="theme-row">
          <div class="theme-info">
            <div class="theme-info-title">外观模式</div>
            <div class="theme-info-desc">选择亮色或深色界面主题</div>
          </div>
          <div class="theme-control">
            <ThemeToggle />
            <span class="mode-label">{{ themeStore.mode === 'dark' ? '深色模式' : '亮色模式' }}</span>
          </div>
        </div>

        <el-divider />

        <div class="preset-section">
          <div class="theme-info">
            <div class="theme-info-title">主题色预设</div>
            <div class="theme-info-desc">选择应用的主色调风格</div>
          </div>
          <ColorPresets />
        </div>
      </div>
    </el-card>

    <el-card shadow="never">
      <template #header>
        <span><el-icon><Clock /></el-icon> 会话历史管理</span>
      </template>

      <el-form label-width="200px" label-position="left" @submit.prevent="saveSettings">
        <el-form-item label="会话历史保留时间">
          <el-input-number v-model="sessionTtlHours" :min="1" :max="720" style="width: 160px" />
          <span class="settings-hint">小时（1小时~30天，默认72小时）</span>
        </el-form-item>
        <el-form-item label="已保存的历史会话数">
          <el-tag type="info">{{ historyCount }} 条</el-tag>
          <Md3Button size="sm" class="action-btn" @click="clearAllHistory" :disabled="historyCount === 0">
            清空全部历史
          </Md3Button>
        </el-form-item>
        <el-form-item>
          <Md3Button variant="primary" @click="saveSettings" :loading="saving">保存设置</Md3Button>
          <el-tag v-if="saved" type="success" class="saved-tag">已保存</el-tag>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card shadow="never" style="margin-top: 16px">
      <template #header>
        <span><el-icon><FolderOpened /></el-icon> 远程硬盘映射账户</span>
      </template>

      <el-form label-width="200px" label-position="left" @submit.prevent="saveDriveAuth">
        <el-form-item label="登录用户名">
          <el-input v-model="driveUsername" placeholder="opsv" style="width: 200px" />
          <span class="settings-hint">映射网络驱动器时使用的用户名</span>
        </el-form-item>
        <el-form-item label="登录密码">
          <el-input v-model="drivePassword" type="password" show-password placeholder="留空则使用SSH默认账户密码" style="width: 200px" />
          <span class="settings-hint">留空时自动使用SSH默认账户的密码</span>
        </el-form-item>
        <el-form-item label="当前状态">
          <el-tag v-if="drivePasswordSet" type="success">已设置自定义密码</el-tag>
          <el-tag v-else type="info">使用SSH默认账户密码</el-tag>
        </el-form-item>
        <el-form-item>
          <Md3Button variant="primary" @click="saveDriveAuth" :loading="savingDrive">保存</Md3Button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { Clock, Monitor, FolderOpened } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import Md3Button from '@/components/Md3Button.vue'
import { request } from '@/api'
import { useThemeStore } from '@/stores/themeStore'
import ThemeToggle from '@/components/ThemeToggle.vue'
import ColorPresets from '@/components/ColorPresets.vue'

const themeStore = useThemeStore()

const sessionTtlHours = ref(72)
const historyCount = ref(0)
const saving = ref(false)
const saved = ref(false)

const driveUsername = ref('opsv')
const drivePassword = ref('')
const drivePasswordSet = ref(false)
const savingDrive = ref(false)

async function loadSettings() {
  try {
    const res: any = await request.get('/settings')
    sessionTtlHours.value = res.session_ttl_hours || 72
    driveUsername.value = res.remote_drive_username || 'opsv'
    drivePasswordSet.value = res.remote_drive_password_set || false
  } catch {}
  try {
    const histRes: any = await request.get('/webssh/sessions/history')
    historyCount.value = histRes.count || 0
  } catch {}
}

async function saveSettings() {
  saving.value = true
  saved.value = false
  try {
    await request.put('/settings', { session_ttl_hours: sessionTtlHours.value })
    saved.value = true
    ElMessage.success('设置已保存')
    setTimeout(() => { saved.value = false }, 2000)
  } catch {
    ElMessage.error('保存失败')
  } finally { saving.value = false }
}

async function saveDriveAuth() {
  savingDrive.value = true
  try {
    const data: any = { remote_drive_username: driveUsername.value }
    if (drivePassword.value) {
      data.remote_drive_password = drivePassword.value
    }
    await request.put('/settings', data)
    drivePassword.value = ''
    drivePasswordSet.value = !!data.remote_drive_password
    ElMessage.success('映射账户已保存')
  } catch {
    ElMessage.error('保存失败')
  } finally { savingDrive.value = false }
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
.settings {
  padding: 0;
}

.theme-card {
  margin-bottom: var(--md3-space-lg);
}

.theme-section {
  display: flex;
  flex-direction: column;
  gap: var(--md3-space-md);
}

.theme-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: var(--md3-space-md);
}

.preset-section {
  display: flex;
  flex-direction: column;
  gap: var(--md3-space-lg);
}

.theme-info-title {
  font: var(--md3-type-title-small);
  color: var(--md3-on-surface);
}

.theme-info-desc {
  font: var(--md3-type-body-small);
  color: var(--md3-on-surface-variant);
  margin-top: 2px;
}

.theme-control {
  display: flex;
  align-items: center;
  gap: var(--md3-space-md);
}

.mode-label {
  font: var(--md3-type-body-medium);
  color: var(--md3-on-surface-variant);
  min-width: 64px;
}

.settings-hint {
  margin-left: var(--md3-space-sm);
  color: var(--md3-on-surface-variant);
  font-size: 13px;
}

.action-btn {
  margin-left: var(--md3-space-md);
}

.saved-tag {
  margin-left: var(--md3-space-md);
}
</style>
