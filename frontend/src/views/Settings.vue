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
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { Clock } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { request } from '@/api'

const sessionTtlHours = ref(72)
const historyCount = ref(0)
const saving = ref(false)
const saved = ref(false)

async function loadSettings() {
  try {
    const res: any = await request.get('/settings')
    sessionTtlHours.value = res.session_ttl_hours || 72
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
