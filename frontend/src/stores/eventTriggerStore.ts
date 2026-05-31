import { defineStore } from 'pinia'
import { ref } from 'vue'
import { eventTriggerApi } from '@/api'

export interface EventFilterCondition {
  field: string
  operator: string
  value: string
}

export interface EventFilterGroup {
  logic: string
  conditions: EventFilterCondition[]
}

export interface EventTransform {
  source_field: string
  target_field: string
  template?: string
}

export interface EventRoute {
  id: string
  source_id: string
  workflow_id: string
  filter_group?: EventFilterGroup
  transforms: EventTransform[]
  enabled: boolean
  created_at: string
}

export interface EventSource {
  id: string
  name: string
  source_type: string
  config: Record<string, any>
  webhook_url?: string
  webhook_secret?: string
  account_alias?: string
  status: string
  description?: string
  last_event_at?: string
  event_count: number
  created_at: string
  updated_at: string
}

export interface EventLog {
  id: string
  source_id: string
  source_name: string
  event_type: string
  raw_data: Record<string, any>
  filtered: boolean
  matched_routes: string[]
  triggered_workflows: string[]
  status: string
  error_message?: string
  received_at: string
}

export const useEventTriggerStore = defineStore('eventTrigger', () => {
  const sources = ref<EventSource[]>([])
  const routes = ref<EventRoute[]>([])
  const eventLogs = ref<EventLog[]>([])
  const loading = ref(false)

  async function fetchSources() {
    loading.value = true
    try {
      const res: any = await eventTriggerApi.listSources()
      sources.value = res.items || []
    } finally {
      loading.value = false
    }
  }

  async function createSource(data: any) {
    const res: any = await eventTriggerApi.createSource(data)
    sources.value.push(res)
    return res
  }

  async function updateSource(id: string, data: any) {
    const res: any = await eventTriggerApi.updateSource(id, data)
    const idx = sources.value.findIndex(s => s.id === id)
    if (idx >= 0) sources.value[idx] = res
    return res
  }

  async function deleteSource(id: string) {
    await eventTriggerApi.deleteSource(id)
    sources.value = sources.value.filter(s => s.id !== id)
  }

  async function fetchRoutes(sourceId?: string) {
    const res: any = await eventTriggerApi.listRoutes(sourceId)
    routes.value = res.items || []
  }

  async function createRoute(data: any) {
    const res: any = await eventTriggerApi.createRoute(data)
    routes.value.push(res)
    return res
  }

  async function updateRoute(id: string, data: any) {
    const res: any = await eventTriggerApi.updateRoute(id, data)
    const idx = routes.value.findIndex(r => r.id === id)
    if (idx >= 0) routes.value[idx] = res
    return res
  }

  async function deleteRoute(id: string) {
    await eventTriggerApi.deleteRoute(id)
    routes.value = routes.value.filter(r => r.id !== id)
  }

  async function fetchEventLogs(sourceId?: string, eventType?: string, status?: string) {
    loading.value = true
    try {
      const res: any = await eventTriggerApi.listLogs(sourceId, eventType, status)
      eventLogs.value = res.items || []
    } finally {
      loading.value = false
    }
  }

  async function replayEvent(logId: string) {
    const res: any = await eventTriggerApi.replayEvent(logId)
    return res
  }

  return {
    sources, routes, eventLogs, loading,
    fetchSources, createSource, updateSource, deleteSource,
    fetchRoutes, createRoute, updateRoute, deleteRoute,
    fetchEventLogs, replayEvent,
  }
})
