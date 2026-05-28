<template>
  <div class="large-screen">
    <div class="ls-header">
      <div class="ls-title">全维度资源监控 · 大屏模式</div>
      <div class="ls-time">{{ currentTime }}</div>
      <div class="ls-actions">
        <Md3Select v-model="selectedAlias" :options="selectOptions" placeholder="选择服务器" style="width: 180px" size="sm" @update:model-value="onChange" />
        <Md3Button size="sm" @click="refreshNow"><Md3Icon name="refresh" size="1em" />刷新</Md3Button>
        <Md3Button size="sm" @click="$router.push('/monitor')"><Md3Icon name="close" size="1em" />退出大屏</Md3Button>
      </div>
    </div>

    <div class="ls-body" v-if="snapshot">
      <div class="ls-row">
        <div class="ls-panel panel-host">
          <div class="panel-title">服务器</div>
          <div class="host-info">
            <div class="host-name">{{ snapshot.hostname }}</div>
            <div class="host-uptime">{{ formatUptime(snapshot.uptime) }}</div>
            <div class="host-load">
              <span>1m: {{ snapshot.load.load_1m.toFixed(2) }}</span>
              <span>5m: {{ snapshot.load.load_5m.toFixed(2) }}</span>
              <span>15m: {{ snapshot.load.load_15m.toFixed(2) }}</span>
            </div>
            <div class="host-procs">{{ snapshot.load.running }} / {{ snapshot.load.total_processes }} 进程</div>
          </div>
        </div>
        <div class="ls-panel panel-gauge"><div class="panel-title">CPU</div><MonitorGaugeChart :value="snapshot.cpu.usage_percent" height="180px" /></div>
        <div class="ls-panel panel-gauge"><div class="panel-title">内存</div><MonitorGaugeChart :value="snapshot.memory.usage_percent" height="180px" /></div>
        <div class="ls-panel panel-gauge"><div class="panel-title">磁盘</div><MonitorGaugeChart :value="diskAvg" height="180px" /></div>
        <div class="ls-panel panel-gauge"><div class="panel-title">Docker CPU</div><MonitorGaugeChart :value="dockerAvg" height="180px" :max="100" /></div>
      </div>

      <div class="ls-row ls-row-main">
        <div class="ls-panel panel-chart panel-half">
          <div class="panel-title">CPU 使用率</div>
          <MonitorLineChart :data="cpuSeries" color="#1a73e8" yAxisName="%" height="180px" />
        </div>
        <div class="ls-panel panel-chart panel-half">
          <div class="panel-title">内存使用率</div>
          <MonitorLineChart :data="memSeries" color="#22c55e" yAxisName="%" height="180px" />
        </div>
      </div>

      <div class="ls-row ls-row-main">
        <div class="ls-panel panel-chart panel-third">
          <div class="panel-title">网络连接</div>
          <MonitorPieChart :data="connPie" height="200px" />
        </div>
        <div class="ls-panel panel-chart panel-third">
          <div class="panel-title">内存分布</div>
          <MonitorPieChart :data="memPie" height="200px" />
        </div>
        <div class="ls-panel panel-chart panel-third">
          <div class="panel-title">核心热力图</div>
          <MonitorHeatmap :data="coreHeat" height="200px" />
        </div>
      </div>

      <div class="ls-row ls-row-docker" v-if="snapshot.docker_containers.length">
        <div class="ls-panel panel-table">
          <div class="panel-title">Docker 容器</div>
          <div class="docker-bar">
            <div v-for="c in snapshot.docker_containers.slice(0, 8)" :key="c.container_id" class="docker-item" :style="{ borderLeftColor: c.cpu_percent > 50 ? '#ef4444' : '#22c55e' }">
              <div class="d-name">{{ c.name }}</div>
              <div class="d-cpu">CPU: {{ c.cpu_percent }}%</div>
              <div class="d-mem">MEM: {{ c.mem_percent }}%</div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div v-else class="ls-empty">
      <Md3Empty description="选择服务器以开始监控" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { Md3Icon } from '@/components/md3'
import { useMonitorStore } from '@/stores/monitorStore'
import { useSshAccountStore } from '@/stores/sshAccountStore'
import { Md3Select, Md3Empty } from '@/components/md3'
import Md3Button from '@/components/Md3Button.vue'
import MonitorLineChart from '@/components/MonitorLineChart.vue'
import MonitorGaugeChart from '@/components/MonitorGaugeChart.vue'
import MonitorPieChart from '@/components/MonitorPieChart.vue'
import MonitorHeatmap from '@/components/MonitorHeatmap.vue'

const store = useMonitorStore()
const sshStore = useSshAccountStore()

const selectedAlias = ref('')
const currentTime = ref('')
let timeTimer: ReturnType<typeof setInterval> | null = null
let pollTimer: ReturnType<typeof setInterval> | null = null

const selectOptions = computed(() => sshStore.accounts.map(a => ({ label: `${a.alias} (${a.host})`, value: a.alias })))
const snapshot = computed(() => store.snapshot)

const cpuSeries = computed(() => store.history.slice(-30).map(h => ({ time: h.timestamp, value: h.cpu?.usage_percent ?? 0 })))
const memSeries = computed(() => store.history.slice(-30).map(h => ({ time: h.timestamp, value: h.memory?.usage_percent ?? 0 })))
const diskAvg = computed(() => {
  if (!snapshot.value?.disks?.length) return 0
  const main = snapshot.value.disks.find(d => d.mount === '/')
  return main ? main.usage_percent : snapshot.value.disks[0].usage_percent
})
const dockerAvg = computed(() => {
  if (!snapshot.value?.docker_containers?.length) return 0
  const sum = snapshot.value.docker_containers.reduce((s, c) => s + c.cpu_percent, 0)
  return Math.round(sum / snapshot.value.docker_containers.length)
})
const coreHeat = computed(() => (snapshot.value?.cores || []).map(c => ({ name: `C${c.core}`, value: c.usage_percent })))
const connPie = computed(() => {
  if (!snapshot.value?.connections) return []
  return Object.entries(snapshot.value.connections).slice(0, 6).map(([k, v]) => ({ name: k, value: v }))
})
const memPie = computed(() => {
  if (!snapshot.value?.memory) return []
  const m = snapshot.value.memory
  return [{ name: '已使用', value: m.used }, { name: '可用', value: m.available }]
})

function formatUptime(s: number) {
  return `${Math.floor(s / 86400)}d ${Math.floor((s % 86400) / 3600)}h ${Math.floor((s % 3600) / 60)}m`
}

function refreshNow() {
  if (selectedAlias.value) store.fetchSnapshot()
}

function onChange(value: string | number | (string | number)[]) {
  const alias = String(value)
  store.currentAlias = alias
  store.fetchSnapshot()
}

onMounted(async () => {
  await sshStore.fetchAccounts()
  const def = sshStore.accounts.find(a => a.default) || sshStore.accounts[0]
  if (def) {
    selectedAlias.value = def.alias
    store.currentAlias = def.alias
    store.fetchSnapshot()
  }
  pollTimer = setInterval(() => { if (selectedAlias.value) store.fetchSnapshot() }, 5000)
  timeTimer = setInterval(() => {
    const d = new Date()
    currentTime.value = d.toLocaleString('zh-CN', { hour12: false })
  }, 1000)
})

onBeforeUnmount(() => {
  if (pollTimer) clearInterval(pollTimer)
  if (timeTimer) clearInterval(timeTimer)
})
</script>

<style scoped>
.large-screen {
  position: fixed; inset: 0; z-index: 9999;
  background: #0a0e1a;
  color: #e2e8f0;
  display: flex; flex-direction: column;
  font-family: 'JetBrains Mono', 'Plus Jakarta Sans', sans-serif;
}
.ls-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 12px 24px;
  background: linear-gradient(135deg, #0f172a, #1e293b);
  border-bottom: 1px solid rgba(255,255,255,0.05);
}
.ls-title { font-size: 20px; font-weight: 700; background: linear-gradient(90deg, #1a73e8, #22c55e); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
.ls-time { font-size: 18px; font-weight: 600; color: #94a3b8; font-family: 'JetBrains Mono', monospace; }
.ls-actions { display: flex; gap: 8px; align-items: center; }
.ls-body { flex: 1; overflow-y: auto; padding: 16px; }
.ls-empty { flex: 1; display: flex; align-items: center; justify-content: center; }
.ls-row { display: grid; gap: 12px; margin-bottom: 12px; }
.ls-row { grid-template-columns: repeat(5, 1fr); }
.ls-row-main { grid-template-columns: 1fr 1fr; }
.ls-row-docker { grid-template-columns: 1fr; }
.ls-panel {
  background: linear-gradient(135deg, rgba(15,23,42,0.8), rgba(30,41,59,0.6));
  border: 1px solid rgba(255,255,255,0.06);
  border-radius: 12px;
  padding: 12px;
}
.panel-title { font-size: 12px; text-transform: uppercase; letter-spacing: 1px; color: #64748b; margin-bottom: 8px; }
.panel-host .host-info { text-align: center; }
.host-name { font-size: 18px; font-weight: 700; }
.host-uptime { font-size: 13px; color: #94a3b8; margin-top: 4px; }
.host-load { display: flex; justify-content: center; gap: 12px; font-size: 13px; color: #64748b; margin-top: 8px; }
.host-procs { font-size: 13px; color: #64748b; margin-top: 4px; }
.panel-half { grid-column: span 1; }
.panel-third { }
.docker-bar { display: flex; flex-wrap: wrap; gap: 8px; }
.docker-item {
  flex: 1; min-width: 160px; padding: 8px 12px;
  background: rgba(15,23,42,0.5); border-radius: 8px;
  border-left: 3px solid #22c55e;
}
.d-name { font-weight: 600; font-size: 13px; }
.d-cpu, .d-mem { font-size: 12px; color: #94a3b8; margin-top: 2px; }

@media (max-width: 1200px) { .ls-row { grid-template-columns: repeat(3, 1fr); } .ls-row-main { grid-template-columns: 1fr; } }
@media (max-width: 768px) { .ls-row { grid-template-columns: 1fr 1fr; } }
</style>