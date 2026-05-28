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
          <Md3Button :icon="Close" size="sm" variant="danger" @click.stop="$emit('disconnect', session.id)">断开</Md3Button>
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
          <Md3Button :icon="Delete" size="sm" variant="danger" @click.stop="$emit('deleteHistory', record.session_id)">删除</Md3Button>
        </div>
      </div>
    </div>

    <div v-if="sessions.length === 0 && historyRecords.length === 0" class="session-empty">
      <el-empty description="暂无会话" :image-size="60" />
    </div>

    <div class="session-actions">
      <Md3Button size="sm" variant="primary" :icon="Plus" @click="$emit('newSession')">新建会话</Md3Button>
    </div>
  </div>
</template>

<script setup lang="ts">
import Md3Button from '@/components/Md3Button.vue'
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
  background: var(--md3-glass-bg);
  backdrop-filter: var(--md3-glass-blur);
  -webkit-backdrop-filter: var(--md3-glass-blur);
  border: 1px solid var(--md3-glass-border);
  border-radius: var(--md3-shape-sm);
  overflow: hidden;
  transition: box-shadow var(--md3-motion-duration-medium) var(--md3-motion-easing-standard);
}

.session-manager:hover {
  box-shadow: var(--md3-elevation-level1);
}

.section-label {
  font-size: 11px;
  font-weight: 600;
  color: var(--md3-on-surface-variant);
  text-transform: uppercase;
  letter-spacing: 1px;
  padding: var(--md3-space-sm) var(--md3-space-md) var(--md3-space-xs);
  border-bottom: 1px solid var(--md3-surface-container-low);
}

.session-list {
  flex: 1;
  overflow-y: auto;
}

.session-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--md3-space-sm) var(--md3-space-md);
  cursor: pointer;
  border-bottom: 1px solid var(--md3-surface-container-low);
  transition: background var(--md3-motion-duration-short) var(--md3-motion-easing-standard),
              border-color var(--md3-motion-duration-short) var(--md3-motion-easing-standard);
}

.session-item:hover {
  background: var(--md3-surface-container-low);
}

.session-item.active {
  background: var(--md3-primary-container);
  border-left: 3px solid var(--md3-primary);
}

.history-item {
  opacity: 0.75;
  transition: opacity var(--md3-motion-duration-short) var(--md3-motion-easing-standard);
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
  color: var(--md3-on-surface);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.session-user {
  font-size: 11px;
  color: var(--md3-on-surface-variant);
}

.session-meta {
  display: flex;
  align-items: center;
  gap: var(--md3-space-xs);
  flex-shrink: 0;
}

.time-label {
  font-size: 10px;
  color: var(--md3-outline-variant);
  white-space: nowrap;
}

.session-empty {
  padding: var(--md3-space-xl) 0;
}

.session-actions {
  padding: var(--md3-space-md);
  border-top: 1px solid var(--md3-outline-variant);
}
</style>
