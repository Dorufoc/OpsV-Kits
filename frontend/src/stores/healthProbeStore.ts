import { defineStore } from 'pinia'
import { ref } from 'vue'
import {
  healthProbeApi,
  type ProbeTarget,
  type ProbeTargetCreate,
  type ProbeTargetUpdate,
  type ProbeResult,
  type ProbeStatistics,
  type ProbeOverview,
  type ProbeLogQueryResult,
} from '@/api'

export const useHealthProbeStore = defineStore('health-probe', () => {
  const targets = ref<ProbeTarget[]>([])
  const overview = ref<ProbeOverview | null>(null)
  const currentTarget = ref<ProbeTarget | null>(null)
  const currentStats = ref<ProbeStatistics | null>(null)
  const currentLogs = ref<ProbeLogQueryResult | null>(null)
  const loading = ref(false)
  const probing = ref(false)

  async function fetchOverview() {
    loading.value = true
    try {
      overview.value = await healthProbeApi.getOverview()
      targets.value = overview.value.targets
    } finally {
      loading.value = false
    }
  }

  async function fetchTargets(tag?: string, probeType?: string) {
    loading.value = true
    try {
      targets.value = await healthProbeApi.listTargets(tag, probeType)
    } finally {
      loading.value = false
    }
  }

  async function createTarget(data: ProbeTargetCreate) {
    const target = await healthProbeApi.createTarget(data)
    targets.value.push(target)
    return target
  }

  async function updateTarget(id: string, data: ProbeTargetUpdate) {
    const updated = await healthProbeApi.updateTarget(id, data)
    const idx = targets.value.findIndex((t) => t.id === id)
    if (idx >= 0) targets.value[idx] = updated
    if (currentTarget.value?.id === id) currentTarget.value = updated
    return updated
  }

  async function deleteTarget(id: string) {
    await healthProbeApi.deleteTarget(id)
    targets.value = targets.value.filter((t) => t.id !== id)
    if (currentTarget.value?.id === id) currentTarget.value = null
  }

  async function probeNow(id: string) {
    probing.value = true
    try {
      const result = await healthProbeApi.probeNow(id)
      const idx = targets.value.findIndex((t) => t.id === id)
      if (idx >= 0) {
        const updated = await healthProbeApi.getTarget(id)
        targets.value[idx] = updated
        if (currentTarget.value?.id === id) currentTarget.value = updated
      }
      return result
    } finally {
      probing.value = false
    }
  }

  async function fetchStatistics(id: string, hours = 24) {
    currentStats.value = await healthProbeApi.getStatistics(id, hours)
    return currentStats.value
  }

  async function fetchLogs(id: string, params?: { limit?: number; offset?: number; time_start?: string; time_end?: string; success?: boolean }) {
    currentLogs.value = await healthProbeApi.getLogs(id, params)
    return currentLogs.value
  }

  function selectTarget(target: ProbeTarget | null) {
    currentTarget.value = target
    currentStats.value = null
    currentLogs.value = null
  }

  return {
    targets,
    overview,
    currentTarget,
    currentStats,
    currentLogs,
    loading,
    probing,
    fetchOverview,
    fetchTargets,
    createTarget,
    updateTarget,
    deleteTarget,
    probeNow,
    fetchStatistics,
    fetchLogs,
    selectTarget,
  }
})
