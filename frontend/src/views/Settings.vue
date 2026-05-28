<template>
  <div class="settings">
    <Md3PageHeader title="OpsV-Kits">
      <template #content>
        <span>系统设置</span>
      </template>
    </Md3PageHeader>
    <Md3Divider />

    <Md3Card class="theme-card">
      <template #header>
        <span><Md3Icon name="monitor" class="header-icon" /> 主题设置</span>
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

        <Md3Divider />

        <div class="preset-section">
          <div class="theme-info">
            <div class="theme-info-title">主题色预设</div>
            <div class="theme-info-desc">选择应用的主色调风格</div>
          </div>
          <ColorPresets />
        </div>
      </div>
    </Md3Card>

    <Md3Card>
      <template #header>
        <span><Md3Icon name="clock" class="header-icon" /> 会话历史管理</span>
      </template>

      <div class="form-group">
        <div class="form-row">
          <span class="form-label">会话历史保留时间</span>
          <Md3Input type="number" v-model="sessionTtlHours" :min="1" :max="720" class="form-input-narrow" />
          <span class="settings-hint">小时（1小时~30天，默认72小时）</span>
        </div>
        <div class="form-row">
          <span class="form-label">已保存的历史会话数</span>
          <Md3Tag type="info">{{ historyCount }} 条</Md3Tag>
          <Md3Button size="sm" class="action-btn" @click="clearAllHistory" :disabled="historyCount === 0">
            清空全部历史
          </Md3Button>
        </div>
        <div class="form-row form-actions">
          <Md3Button variant="primary" @click="saveSettings" :loading="saving">保存设置</Md3Button>
          <Md3Tag v-if="saved" type="success" class="saved-tag">已保存</Md3Tag>
        </div>
      </div>
    </Md3Card>

    <Md3Card style="margin-top: 16px">
      <template #header>
        <span><Md3Icon name="folder-open" class="header-icon" /> 远程硬盘映射账户</span>
      </template>

      <div class="form-group">
        <div class="form-row">
          <span class="form-label">登录用户名</span>
          <Md3Input v-model="driveUsername" placeholder="opsv" class="form-input-wide" />
          <span class="settings-hint">映射网络驱动器时使用的用户名</span>
        </div>
        <div class="form-row">
          <span class="form-label">登录密码</span>
          <Md3Input v-model="drivePassword" type="password" placeholder="留空则使用SSH默认账户密码" class="form-input-wide" />
          <span class="settings-hint">留空时自动使用SSH默认账户的密码</span>
        </div>
        <div class="form-row">
          <span class="form-label">当前状态</span>
          <Md3Tag v-if="drivePasswordSet" type="success">已设置自定义密码</Md3Tag>
          <Md3Tag v-else type="info">使用SSH默认账户密码</Md3Tag>
        </div>
        <div class="form-row form-actions">
          <Md3Button variant="primary" @click="saveDriveAuth" :loading="savingDrive">保存</Md3Button>
        </div>
      </div>
    </Md3Card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { Md3Icon } from '@/components/md3'
import {
  Md3PageHeader,
  Md3Divider,
  Md3Card,
  Md3Input,
  Md3Tag,
  Md3Message,
} from '@/components/md3'
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
    Md3Message.success('设置已保存')
    setTimeout(() => { saved.value = false }, 2000)
  } catch {
    Md3Message.error('保存失败')
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
    Md3Message.success('映射账户已保存')
  } catch {
    Md3Message.error('保存失败')
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
    Md3Message.success('历史已清空')
  } catch {
    Md3Message.error('清空失败')
  }
}

onMounted(loadSettings)
</script>

<style scoped>
.settings {
  padding: 0;
}

.header-icon {
  width: 16px;
  height: 16px;
  vertical-align: -3px;
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

.form-group {
  display: flex;
  flex-direction: column;
  gap: var(--md3-space-md);
  padding: var(--md3-space-sm) 0;
}

.form-row {
  display: flex;
  align-items: center;
  gap: var(--md3-space-sm);
}

.form-label {
  width: 200px;
  font-size: 14px;
  color: var(--md3-on-surface);
  flex-shrink: 0;
}

.form-input-narrow {
  width: 160px;
}

.form-input-wide {
  width: 200px;
}

.form-actions {
  margin-top: var(--md3-space-xs);
}
</style>
