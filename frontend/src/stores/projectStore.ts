import { defineStore } from 'pinia'
import { ref } from 'vue'
import { request } from '@/api'

export interface ProjectItem {
  alias: string
  local_path: string
  remote_path: string
  ssh_alias: string
  created_at?: string
  updated_at?: string
}

export const useProjectStore = defineStore('project', () => {
  const projects = ref<ProjectItem[]>([])
  const loading = ref(false)

  async function fetchProjects() {
    loading.value = true
    try {
      const res = await request.get<ProjectItem[]>('/projects')
      projects.value = res
    } finally {
      loading.value = false
    }
  }

  async function createProject(data: { alias: string; local_path?: string; remote_path?: string; ssh_alias?: string }) {
    const res = await request.post<ProjectItem>('/projects', data)
    projects.value.push(res)
    return res
  }

  async function updateProject(alias: string, data: Partial<ProjectItem>) {
    const res = await request.put<ProjectItem>(`/projects/${alias}`, data)
    const index = projects.value.findIndex(p => p.alias === alias)
    if (index !== -1) {
      projects.value[index] = res
    }
    return res
  }

  async function deleteProject(alias: string) {
    await request.delete(`/projects/${alias}`)
    projects.value = projects.value.filter(p => p.alias !== alias)
  }

  return {
    projects,
    loading,
    fetchProjects,
    createProject,
    updateProject,
    deleteProject,
  }
})
