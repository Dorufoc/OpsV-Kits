<template>
  <div class="db-toolkit-panel">
    <MySqlPanel
      v-if="dbType === 'mysql'"
      :container-id="containerId"
      :account-alias="accountAlias"
      :container-state="containerState"
    />
    <RedisPanel
      v-else
      :container-id="containerId"
      :account-alias="accountAlias"
      :container-state="containerState"
    />
  </div>
</template>

<script setup lang="ts">
import MySqlPanel from '@/components/MySqlPanel.vue'
import RedisPanel from '@/components/RedisPanel.vue'

defineProps<{
  dbType: 'mysql' | 'redis'
  containerId: string
  accountAlias: string
  containerState: string
}>()
</script>

<style scoped>
.db-toolkit-panel {
  padding: var(--md3-space-sm) 0;
}
</style>
