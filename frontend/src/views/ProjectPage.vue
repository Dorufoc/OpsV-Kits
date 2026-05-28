<template>
  <div class="project-page">
    <el-page-header title="OpsV-Kits">
      <template #content>
        <span>项目配置与一键部署</span>
      </template>
    </el-page-header>
    <el-divider />

    <div class="project-layout">
      <div class="project-sidebar">
        <div class="sidebar-title">项目列表</div>
        <el-menu :default-active="currentProject" class="project-menu">
          <el-menu-item
            v-for="proj in projectStore.projects"
            :key="proj.alias"
            :index="proj.alias"
            @click="selectProject(proj)"
          >
            <el-icon><Folder /></el-icon>
            <span>{{ proj.alias }}</span>
          </el-menu-item>
        </el-menu>
        <Md3Button class="new-project-btn" size="sm" :icon="Plus" @click="showNewProject = true">新建项目</Md3Button>
      </div>

      <div class="project-main">
        <el-card class="config-card" shadow="never">
          <template #header>
            <div class="config-header">
              <span>项目配置</span>
              <div class="config-header-actions">
                <Md3Button
                  v-if="currentProject && selectedProject"
                  size="sm"
                  variant="danger"
                  :icon="Delete"
                  @click="confirmDelete"
                >删除项目</Md3Button>
                <Md3Button
                  v-if="currentProject"
                  variant="primary"
                  :icon="Check"
                  @click="saveConfig"
                  :loading="savingConfig"
                >保存配置</Md3Button>
              </div>
            </div>
          </template>
          <el-form :model="projectConfig" label-width="100px" label-position="left">
            <el-form-item label="本地路径">
              <el-input v-model="projectConfig.local_path" placeholder="E:\Projects\MyJavaApp" />
            </el-form-item>
            <el-form-item label="远程路径">
              <el-input v-model="projectConfig.remote_path" placeholder="/home/dev/projects/MyJavaApp" />
            </el-form-item>
            <el-form-item label="SSH 账户">
              <el-select v-model="projectConfig.ssh_alias" placeholder="选择 SSH 账户" style="width: 100%">
                <el-option
                  v-for="acc in sshAccounts"
                  :key="acc.alias"
                  :label="acc.alias"
                  :value="acc.alias"
                >
                  <span>{{ acc.alias }}</span>
                  <span class="account-host">({{ acc.host }})</span>
                </el-option>
              </el-select>
            </el-form-item>
            <el-form-item label="当前用户">
              <el-tag v-if="currentUser" type="info" size="small">{{ currentUser }}</el-tag>
              <span v-else class="text-muted">请选择 SSH 账户</span>
            </el-form-item>
            <el-form-item label="JDK 版本">
              <el-select v-model="projectConfig.jdk_version" placeholder="JDK 21" style="width: 160px">
                <el-option label="JDK 8 (1.8)" value="8" />
                <el-option label="JDK 11" value="11" />
                <el-option label="JDK 17" value="17" />
                <el-option label="JDK 21" value="21" />
              </el-select>
              <span style="margin-left: 8px; font-size: 12px;" class="text-muted">默认 JDK 21</span>
            </el-form-item>
          </el-form>
        </el-card>

        <div class="action-bar">
          <Md3Button variant="primary" size="lg" @click="handleDeploy" :loading="isRunning">一键部署</Md3Button>
          <Md3Button @click="handleSync" :disabled="!canSync">仅同步</Md3Button>
          <Md3Button @click="handleBuild" :disabled="!canBuild">仅编译</Md3Button>
          <Md3Button @click="handleTest" :disabled="!canBuild">仅测试</Md3Button>
          <Md3Button @click="handleRun" :disabled="!canRun">仅运行</Md3Button>
          <Md3Button variant="danger" @click="handleStop" :disabled="!isRunning">停止</Md3Button>
        </div>

        <div class="status-area">
          <div class="status-sidebar">
            <SyncPanel :sync-status="syncStore.syncStatus" :progress="syncStore.progress" />
            <el-divider />
            <BuildPanel
              :build-status="buildStore.buildStatus"
              :run-status="buildStore.runStatus"
            />
          </div>
          <div class="status-terminal">
            <div class="terminal-header">
              <span class="terminal-title">终端输出</span>
            </div>
            <Terminal ref="terminalRef" :show-toolbar="true" session-name="构建终端" />
          </div>
        </div>
      </div>
    </div>

    <!-- 新建项目对话框 -->
    <el-dialog v-model="showNewProject" title="新建项目" width="480px">
      <el-form :model="newProjectForm" label-width="100px" label-position="left">
        <el-form-item label="项目别名" required>
          <el-input v-model="newProjectForm.alias" placeholder="如：MyApp" />
        </el-form-item>
        <el-form-item label="本地路径">
          <el-input v-model="newProjectForm.local_path" placeholder="E:\Projects\MyJavaApp" />
        </el-form-item>
        <el-form-item label="远程路径">
          <el-input v-model="newProjectForm.remote_path" placeholder="/home/dev/projects/MyJavaApp" />
        </el-form-item>
        <el-form-item label="SSH 账户">
          <el-select v-model="newProjectForm.ssh_alias" placeholder="选择 SSH 账户" style="width: 100%">
            <el-option
              v-for="acc in sshAccounts"
              :key="acc.alias"
              :label="acc.alias"
              :value="acc.alias"
            >
              <span>{{ acc.alias }}</span>
              <span class="account-host">({{ acc.host }})</span>
            </el-option>
          </el-select>
        </el-form-item>
        <el-form-item label="JDK 版本">
          <el-select v-model="newProjectForm.jdk_version" placeholder="JDK 21" style="width: 160px">
            <el-option label="JDK 8 (1.8)" value="8" />
            <el-option label="JDK 11" value="11" />
            <el-option label="JDK 17" value="17" />
            <el-option label="JDK 21" value="21" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <Md3Button @click="showNewProject = false">取消</Md3Button>
        <Md3Button variant="primary" @click="handleCreateProject" :loading="creatingProject">确定创建</Md3Button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { Folder, Plus, Delete, Check } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useSyncStore } from '@/stores/syncStore'
import { useBuildStore } from '@/stores/buildStore'
import { useSshAccountStore } from '@/stores/sshAccountStore'
import { useProjectStore, type ProjectItem } from '@/stores/projectStore'
import Md3Button from '@/components/Md3Button.vue'
import SyncPanel from '@/components/SyncPanel.vue'
import BuildPanel from '@/components/BuildPanel.vue'
import Terminal from '@/components/Terminal.vue'

const syncStore = useSyncStore()
const buildStore = useBuildStore()
const sshStore = useSshAccountStore()
const projectStore = useProjectStore()

const terminalRef = ref<InstanceType<typeof Terminal>>()
const currentProject = ref('')
const selectedProject = ref<ProjectItem | null>(null)
const showNewProject = ref(false)
const creatingProject = ref(false)
const savingConfig = ref(false)

const projectConfig = ref<ProjectItem>({
  alias: '',
  local_path: '',
  remote_path: '',
  ssh_alias: '',
  jdk_version: '21',
})

const newProjectForm = ref({
  alias: '',
  local_path: '',
  remote_path: '',
  ssh_alias: '',
  jdk_version: '21',
})

const isDeploying = ref(false)

const isRunning = computed(() =>
  isDeploying.value ||
  syncStore.syncStatus === 'syncing' ||
  syncStore.syncStatus === 'scanning' ||
  buildStore.buildStatus === 'building' ||
  buildStore.runStatus === 'running'
)

const canSync = computed(() =>
  !!projectConfig.value.local_path &&
  !!projectConfig.value.remote_path &&
  !!projectConfig.value.ssh_alias &&
  !isRunning.value
)

const canBuild = computed(() =>
  !!projectConfig.value.remote_path &&
  !!projectConfig.value.ssh_alias &&
  !isRunning.value
)

const canRun = computed(() =>
  !!projectConfig.value.remote_path &&
  !!projectConfig.value.ssh_alias &&
  !isRunning.value
)

const sshAccounts = computed(() => sshStore.accounts)
const currentUser = computed(() => {
  const acc = sshAccounts.value.find(a => a.alias === projectConfig.value.ssh_alias)
  return acc ? `${acc.username} (${acc.host})` : ''
})

watch(() => projectConfig.value.ssh_alias, (newAlias) => {
  if (!newAlias) return
  const acc = sshAccounts.value.find(a => a.alias === newAlias)
  if (acc && acc.workplace_path && !projectConfig.value.remote_path) {
    projectConfig.value.remote_path = acc.workplace_path
  }
})

function selectProject(proj: ProjectItem) {
  selectedProject.value = proj
  projectConfig.value = { ...proj }
  currentProject.value = proj.alias
}

async function saveConfig() {
  if (!currentProject.value || !selectedProject.value) return
  savingConfig.value = true
  try {
    const updated = await projectStore.updateProject(selectedProject.value.alias, {
      local_path: projectConfig.value.local_path,
      remote_path: projectConfig.value.remote_path,
      ssh_alias: projectConfig.value.ssh_alias,
    })
    selectedProject.value = updated
    ElMessage.success('配置已保存')
  } catch {
    ElMessage.error('保存配置失败')
  } finally {
    savingConfig.value = false
  }
}

async function confirmDelete() {
  if (!selectedProject.value) return
  try {
    await ElMessageBox.confirm(
      `确定要删除项目「${selectedProject.value.alias}」吗？`,
      '删除项目',
      { confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning' }
    )
    await projectStore.deleteProject(selectedProject.value.alias)
    selectedProject.value = null
    currentProject.value = ''
    projectConfig.value = { alias: '', local_path: '', remote_path: '', ssh_alias: '', jdk_version: '' }
    ElMessage.success('项目已删除')
  } catch {
    // cancelled
  }
}

async function handleCreateProject() {
  if (!newProjectForm.value.alias) {
    ElMessage.warning('请输入项目别名')
    return
  }
  if (projectStore.projects.some(p => p.alias === newProjectForm.value.alias)) {
    ElMessage.warning('项目别名已存在')
    return
  }
  creatingProject.value = true
  try {
    const project = await projectStore.createProject(newProjectForm.value)
    showNewProject.value = false
    newProjectForm.value = { alias: '', local_path: '', remote_path: '', ssh_alias: '', jdk_version: '' }
    selectProject(project)
    ElMessage.success('项目已创建')
  } catch {
    ElMessage.error('创建项目失败')
  } finally {
    creatingProject.value = false
  }
}

async function handleDeploy() {
  if (isDeploying.value || isRunning.value) return
  isDeploying.value = true
  const steps = [
    { name: '同步', fn: handleSync },
    { name: '编译', fn: handleBuild },
    { name: '测试', fn: handleTest },
    { name: '运行', fn: handleRun },
  ]
  try {
    for (const step of steps) {
      await step.fn()
    }
    terminalRef.value?.writeln('\x1b[32m一键部署完成\x1b[0m')
  } catch (e: any) {
    terminalRef.value?.writeln(`\x1b[31m一键部署中止: ${e?.message || e}\x1b[0m`)
  } finally {
    isDeploying.value = false
  }
}

async function handleTest() {
  if (!isDeploying.value && !canBuild.value) return
  terminalRef.value?.clear()
  terminalRef.value?.writeln('开始测试项目...')
  try {
    await buildStore.startTest({
      remote_path: projectConfig.value.remote_path,
      account_alias: projectConfig.value.ssh_alias,
      local_path: projectConfig.value.local_path || undefined,
      jdk_version: projectConfig.value.jdk_version || undefined,
    })
    const result = await buildStore.waitForCompletion()
    if (result === 'failed') throw new Error('测试失败')
  } catch (e: any) {
    terminalRef.value?.writeln(`\x1b[31m${e?.message || '测试失败'}\x1b[0m`)
    throw e
  }
}

async function handleSync() {
  if (!isDeploying.value && !canSync.value) return
  terminalRef.value?.writeln('开始同步文件...')
  try {
    await syncStore.startSync({
      local_path: projectConfig.value.local_path,
      remote_path: projectConfig.value.remote_path,
      account_alias: projectConfig.value.ssh_alias,
    })
    const result = await syncStore.waitForCompletion()
    if (result === 'failed') throw new Error('文件同步失败')
  } catch (e: any) {
    terminalRef.value?.writeln(`\x1b[31m${e?.message || '文件同步失败'}\x1b[0m`)
    throw e
  }
}

async function handleBuild() {
  if (!isDeploying.value && !canBuild.value) return
  terminalRef.value?.clear()
  terminalRef.value?.writeln('开始编译项目...')
  try {
    await buildStore.startBuild({
      remote_path: projectConfig.value.remote_path,
      account_alias: projectConfig.value.ssh_alias,
      local_path: projectConfig.value.local_path || undefined,
      jdk_version: projectConfig.value.jdk_version || undefined,
    })
    const result = await buildStore.waitForCompletion()
    if (result === 'failed') throw new Error('编译失败')
  } catch (e: any) {
    terminalRef.value?.writeln(`\x1b[31m${e?.message || '编译失败'}\x1b[0m`)
    throw e
  }
}

async function handleRun() {
  if (!isDeploying.value && !canRun.value) return
  terminalRef.value?.writeln('启动应用程序...')
  try {
    await buildStore.startRun({
      remote_path: projectConfig.value.remote_path,
      account_alias: projectConfig.value.ssh_alias,
      local_path: projectConfig.value.local_path || undefined,
      jdk_version: projectConfig.value.jdk_version || undefined,
    })
    const result = await buildStore.waitForCompletion()
    if (result === 'failed') throw new Error('启动失败')
  } catch (e: any) {
    terminalRef.value?.writeln(`\x1b[31m${e?.message || '启动失败'}\x1b[0m`)
    throw e
  }
}

async function handleStop() {
  try {
    if (syncStore.syncStatus !== 'idle') {
      await syncStore.stopSync()
    }
    if (buildStore.buildStatus === 'building' || buildStore.runStatus === 'running') {
      await buildStore.stopTask()
    }
  } catch {
    // 子函数已有内部异常保护，此处仅作兜底
  }
  terminalRef.value?.writeln('\x1b[33m任务已停止\x1b[0m')
}

onMounted(async () => {
  buildStore.setLogCallback((text: string) => {
    terminalRef.value?.write(text)
  })
  syncStore.setLogCallback((text: string) => {
    terminalRef.value?.write(text)
  })
  await sshStore.fetchAccounts()
  await projectStore.fetchProjects()
  if (projectStore.projects.length > 0) {
    selectProject(projectStore.projects[0])
  }
})
</script>

<style scoped>
.project-page {
  padding: 0;
}

.project-layout {
  display: flex;
  gap: var(--md3-space-lg);
  height: calc(100vh - 160px);
}

.project-sidebar {
  width: 200px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: var(--md3-space-sm);
  padding: var(--md3-space-md);
  background: var(--md3-glass-bg);
  backdrop-filter: var(--md3-glass-blur);
  -webkit-backdrop-filter: var(--md3-glass-blur);
  border: 1px solid var(--md3-glass-border);
  border-radius: var(--md3-shape-md);
  transition: box-shadow var(--md3-motion-duration-medium) var(--md3-motion-easing-standard);
}

.project-sidebar:hover {
  box-shadow: var(--md3-elevation-level1);
}

.sidebar-title {
  font: var(--md3-type-title-small);
  color: var(--md3-on-surface);
  padding: var(--md3-space-sm) 0;
}

.project-menu {
  border-right: none !important;
  flex: 1;
  background: transparent;
}

.new-project-btn {
  width: 100%;
}

.project-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: var(--md3-space-lg);
  overflow-y: auto;
}

.config-card {
  flex-shrink: 0;
}

.config-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.config-header-actions {
  display: flex;
  gap: var(--md3-space-sm);
}

.account-host {
  color: var(--md3-outline);
  font-size: 12px;
  margin-left: var(--md3-space-sm);
}

.text-muted {
  color: var(--md3-outline);
  font-size: 13px;
}

.action-bar {
  display: flex;
  gap: var(--md3-space-md);
  flex-wrap: wrap;
  padding: var(--md3-space-md);
  background: var(--md3-glass-bg);
  backdrop-filter: var(--md3-glass-blur);
  -webkit-backdrop-filter: var(--md3-glass-blur);
  border: 1px solid var(--md3-glass-border);
  border-radius: var(--md3-shape-md);
  transition: box-shadow var(--md3-motion-duration-medium) var(--md3-motion-easing-standard);
}

.action-bar:hover {
  box-shadow: var(--md3-elevation-level1);
}

.status-area {
  flex: 1;
  display: flex;
  gap: var(--md3-space-lg);
  min-height: 300px;
}

.status-sidebar {
  width: 260px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  background: var(--md3-glass-bg);
  backdrop-filter: var(--md3-glass-blur);
  -webkit-backdrop-filter: var(--md3-glass-blur);
  border: 1px solid var(--md3-glass-border);
  border-radius: var(--md3-shape-md);
  padding: var(--md3-space-md);
  transition: box-shadow var(--md3-motion-duration-medium) var(--md3-motion-easing-standard);
}

.status-sidebar:hover {
  box-shadow: var(--md3-elevation-level1);
}

.status-terminal {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.terminal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--md3-space-sm) var(--md3-space-md);
  background: var(--md3-glass-bg);
  backdrop-filter: var(--md3-glass-blur);
  -webkit-backdrop-filter: var(--md3-glass-blur);
  border: 1px solid var(--md3-glass-border);
  border-bottom: none;
  border-radius: var(--md3-shape-sm) var(--md3-shape-sm) 0 0;
}

.terminal-title {
  font-weight: 500;
  font-size: 13px;
  color: var(--md3-on-surface);
}

.status-terminal :deep(.terminal-wrapper) {
  border-top-left-radius: 0;
  border-top-right-radius: 0;
  flex: 1;
}
</style>
