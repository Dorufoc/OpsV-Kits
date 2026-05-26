<template>
  <div class="session-manager">
    <div class="section-label" v-if="sessions.length > 0">活跃会话</div>
    <div class="session-list">
      <div
        v-for="session in sessions"
        :key="session.id"
        class="session-item"
        :class="{ active: session.id === activeSessionId }"
        @click="$emit('select', session.id)"
      >
        <div class="session-info">
          <span class="session-alias">{{ session.alias || session.host }}</span>
          <span class="session-user">@{{ session.username }}</span>
        </div>
        <div class="session-meta">
          <el-tag
            :type="session.status === 'online' ? 'success' : session.status === 'connecting' ? 'warning' : 'info'"
            size="small"
            round
          >
            {{ session.status === 'online' ? '在线' : session.status === 'connecting' ? '连接中' : '离线' }}
          </el-tag>
          <el-button
            size="small"
            text
            type="danger"
            @click.stop="$emit('disconnect', session.id)"
          >
            <el-icon><Close /></el-icon>
          </el-button>
        </div>
      </div>
    </div>

    <div class="section-label" v-if="historyRecords.length > 0">历史记录</div>
    <div class="session-list">
      <div
        v-for="record in historyRecords"
        :key="record.session_id"
        class="session-item history-item"
        @click="$emit('reconnect', record)"
      >
        <div class="session-info">
          <span class="session-alias">{{ record.account_alias || record.host }}</span>
          <span class="session-user">@{{ record.username }}</span>
        </div>
        <div class="session-meta">
          <span class="time-label">{{ formatTime(record.disconnected_at) }}</span>
          <el-tag type="info" size="small" round>历史</el-tag>
          <el-button
            size="small"
            text
            type="danger"
            @click.stop="$emit('deleteHistory', record.session_id)"
          >
            <el-icon><Delete /></el-icon>
          </el-button>
        </div>
      </div>
    </div>

    <div v-if="sessions.length === 0 && historyRecords.length === 0" class="session-empty">
      <el-empty description="暂无会话" :image-size="60" />
    </div>

    <div class="session-actions">
      <el-button size="small" type="primary" @click="$emit('newSession')">
        <el-icon><Plus /></el-icon> 新建会话
      </el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { Close, Plus, Delete } from '@element-plus/icons-vue'
import type { WebSshSession, HistoryRecord } from '@/stores/websshStore'

defineProps<{
  sessions: WebSshSession[]
  historyRecords: HistoryRecord[]
  activeSessionId: string
}>()

defineEmits<{
  select: [id: string]
  disconnect: [id: string]
  newSession: []
  reconnect: [record: HistoryRecord]
  deleteHistory: [sessionId: string]
}>()

function formatTime(isoStr: string): string {
  if (!isoStr) return ''
  try {
    const d = new Date(isoStr)
    const month = (d.getMonth() + 1).toString().padStart(2, '0')
    const day = d.getDate().toString().padStart(2, '0')
    const hour = d.getHours().toString().padStart(2, '0')
    const min = d.getMinutes().toString().padStart(2, '0')
    return `${month}-${day} ${hour}:${min}`
  } catch { return '' }
}
</script>

<style scoped>
.session-manager {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.section-label {
  font-size: 11px;
  font-weight: 600;
  color: #909399;
  text-transform: uppercase;
  letter-spacing: 1px;
  padding: 8px 12px 4px;
  border-bottom: 1px solid #f0f0f0;
}

.session-list {
  flex: 1;
  overflow-y: auto;
}

.session-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  cursor: pointer;
  border-bottom: 1px solid #f0f0f0;
  transition: background 0.2s;
}

.session-item:hover {
  background: #f5f7fa;
}

.session-item.active {
  background: #ecf5ff;
  border-left: 3px solid #409eff;
}

.history-item {
  opacity: 0.75;
}

.history-item:hover {
  opacity: 1;
}

.session-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.session-alias {
  font-weight: 500;
  font-size: 13px;
  color: #303133;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.session-user {
  font-size: 11px;
  color: #909399;
}

.session-meta {
  display: flex;
  align-items: center;
  gap: 4px;
  flex-shrink: 0;
}

.time-label {
  font-size: 10px;
  color: #c0c4cc;
  white-space: nowrap;
}

.session-empty {
  padding: 20px 0;
}

.session-actions {
  padding: 12px;
  border-top: 1px solid #e4e7ed;
}
</style>
