<template>
  <div class="project-page">
    <Md3PageHeader title="OpsV-Kits" subtitle="项目配置与一键部署" />
    <Md3Divider />

    <div class="project-layout">
      <div class="project-sidebar">
        <div class="sidebar-title">项目列表</div>
        <nav class="project-menu">
          <div
            v-for="proj in projectStore.projects"
            :key="proj.alias"
            class="project-menu-item"
            :class="{ 'project-menu-item--active': currentProject === proj.alias }"
            @click="selectProject(proj)"
          >
            <Md3Icon :name="proj.project_type === 'vite' ? 'bolt' : 'folder'" class="project-menu-icon" />
            <span class="project-menu-text">{{ proj.alias }}</span>
            <span v-if="proj.project_type" class="project-menu-type">{{ proj.project_type }}</span>
            <button
              class="project-menu-edit"
              @click.stop="openEditDialog(proj)"
              title="编辑项目"
            >
              <Md3Icon name="pencil" class="project-menu-edit-icon" />
            </button>
          </div>
        </nav>
        <Md3Button class="new-project-btn" size="sm" icon="plus" @click="showNewProject = true">新建项目</Md3Button>
      </div>

      <div class="project-main">
        <div class="action-bar">
          <template v-if="isViteProject">
            <Md3Button variant="primary" size="lg" @click="handleViteDeploy" :loading="isRunning">一键部署</Md3Button>
            <Md3Button @click="handleViteCheck" :disabled="isRunning || !canViteAction">检查环境</Md3Button>
            <Md3Button @click="handleViteSetup" :disabled="isRunning || !canViteAction">安装 Node</Md3Button>
            <Md3Button @click="handleViteInstallDeps" :disabled="isRunning || !canViteAction">安装依赖</Md3Button>
            <Md3Button @click="handleViteBuild" :disabled="isRunning || !canViteAction">构建</Md3Button>
            <Md3Button @click="handleViteNginx" :disabled="isRunning || !canViteAction">配置 Nginx</Md3Button>
            <Md3Button variant="danger" @click="handleStop" :disabled="!isRunning">停止</Md3Button>
          </template>
          <template v-else>
            <Md3Button variant="primary" size="lg" @click="handleDeploy" :loading="isRunning">一键部署</Md3Button>
            <Md3Button @click="handleSync" :disabled="!canSync">仅同步</Md3Button>
            <Md3Button @click="handleBuild" :disabled="!canBuild">仅编译</Md3Button>
            <Md3Button @click="handleTest" :disabled="!canBuild">仅测试</Md3Button>
            <Md3Button @click="handleRun" :disabled="!canRun">仅运行</Md3Button>
            <Md3Button variant="danger" @click="handleStop" :disabled="!isRunning">停止</Md3Button>
          </template>
        </div>

        <div class="status-area" v-if="isViteProject">
          <ViteDeployPanel ref="vitePanelRef" :project-config="projectConfig" />
        </div>
        <div class="status-area" v-else>
          <div class="status-sidebar">
            <SyncPanel :sync-status="syncStore.syncStatus" :progress="syncStore.progress" />
            <Md3Divider />
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
    <Md3Dialog v-model:visible="showNewProject" title="新建项目" width="480px">
      <div class="dialog-form">
        <Md3Input v-model="newProjectForm.alias" label="项目别名" placeholder="如：MyApp" />
        <Md3Input v-model="newProjectForm.local_path" label="本地路径" placeholder="E:\Projects\MyJavaApp" />
        <Md3Input v-model="newProjectForm.remote_path" label="远程路径" placeholder="/home/dev/projects/MyJavaApp" />
        <Md3Select v-model="newProjectForm.ssh_alias" label="SSH 账户" placeholder="选择 SSH 账户" :options="sshAccountOptions" />
        <Md3Select v-model="newProjectForm.project_type" label="项目类型" placeholder="选择项目类型" :options="projectTypeOptions" />
        <template v-if="newProjectForm.project_type === 'java'">
          <Md3Select v-model="newProjectForm.jdk_version" label="JDK 版本" placeholder="JDK 21" :options="jdkOptions" />
          <Md3Select v-model="newProjectForm.run_mode" label="运行模式" placeholder="Spring Boot" :options="runModeOptions" />
        </template>
        <template v-if="newProjectForm.project_type === 'vite'">
          <Md3Input v-model="newProjectForm.node_version" label="Node 版本" placeholder="20" />
          <Md3Input v-model.number="newProjectForm.nginx_port" label="Nginx 端口" placeholder="8080" />
          <Md3Input v-model="newProjectForm.build_command" label="构建命令" placeholder="npm run build" />
        </template>
      </div>
      <template #footer>
        <Md3Button @click="showNewProject = false">取消</Md3Button>
        <Md3Button variant="primary" @click="handleCreateProject" :loading="creatingProject">确定创建</Md3Button>
      </template>
    </Md3Dialog>

    <!-- 编辑项目对话框 -->
    <Md3Dialog v-model:visible="showEditProject" title="编辑项目" width="480px">
      <div class="dialog-form">
        <Md3Input v-model="editProjectForm.local_path" label="本地路径" placeholder="E:\Projects\MyJavaApp" />
        <Md3Input v-model="editProjectForm.remote_path" label="远程路径" placeholder="/home/dev/projects/MyJavaApp" />
        <Md3Select v-model="editProjectForm.ssh_alias" label="SSH 账户" placeholder="选择 SSH 账户" :options="sshAccountOptions" />
        <Md3Select v-model="editProjectForm.project_type" label="项目类型" placeholder="选择项目类型" :options="projectTypeOptions" />
        <template v-if="editProjectForm.project_type === 'java'">
          <Md3Select v-model="editProjectForm.jdk_version" label="JDK 版本" placeholder="JDK 21" :options="jdkOptions" />
          <Md3Select v-model="editProjectForm.run_mode" label="运行模式" placeholder="Spring Boot" :options="runModeOptions" />
        </template>
        <template v-if="editProjectForm.project_type === 'vite'">
          <Md3Input v-model="editProjectForm.node_version" label="Node 版本" placeholder="20" />
          <Md3Input v-model.number="editProjectForm.nginx_port" label="Nginx 端口" placeholder="8080" />
          <Md3Input v-model="editProjectForm.build_command" label="构建命令" placeholder="npm run build" />
        </template>
      </div>
      <template #footer>
        <Md3Button @click="showEditProject = false">取消</Md3Button>
        <Md3Button variant="primary" @click="handleEditProject" :loading="editingProject">确定保存</Md3Button>
      </template>
    </Md3Dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { Md3Icon } from '@/components/md3'
import { Md3Message, Md3PageHeader, Md3Divider, Md3Input, Md3Select, Md3Dialog } from '@/components/md3'
import { useSyncStore } from '@/stores/syncStore'
import { useBuildStore } from '@/stores/buildStore'
import { useSshAccountStore } from '@/stores/sshAccountStore'
import { useProjectStore, type ProjectItem } from '@/stores/projectStore'
import { useViteDeployStore } from '@/stores/viteDeployStore'
import Md3Button from '@/components/Md3Button.vue'
import SyncPanel from '@/components/SyncPanel.vue'
import BuildPanel from '@/components/BuildPanel.vue'
import ViteDeployPanel from '@/components/ViteDeployPanel.vue'
import Terminal from '@/components/Terminal.vue'

const syncStore = useSyncStore()
const buildStore = useBuildStore()
const sshStore = useSshAccountStore()
const projectStore = useProjectStore()
const viteStore = useViteDeployStore()

const terminalRef = ref<InstanceType<typeof Terminal>>()
const vitePanelRef = ref<InstanceType<typeof ViteDeployPanel>>()
const currentProject = ref('')
const selectedProject = ref<ProjectItem | null>(null)
const showNewProject = ref(false)
const showEditProject = ref(false)
const creatingProject = ref(false)
const editingProject = ref(false)

const projectConfig = ref<ProjectItem>({
  alias: '',
  local_path: '',
  remote_path: '',
  ssh_alias: '',
  project_type: 'java',
  jdk_version: '21',
  node_version: '20',
  nginx_port: 8080,
  build_command: 'npm run build',
  run_mode: 'spring-boot',
})

const newProjectForm = ref({
  alias: '',
  local_path: '',
  remote_path: '',
  ssh_alias: '',
  project_type: 'java',
  jdk_version: '21',
  node_version: '20',
  nginx_port: 8080,
  build_command: 'npm run build',
  run_mode: 'spring-boot',
})

const editProjectForm = ref({
  alias: '',
  local_path: '',
  remote_path: '',
  ssh_alias: '',
  project_type: 'java',
  jdk_version: '21',
  node_version: '20',
  nginx_port: 8080,
  build_command: 'npm run build',
  run_mode: 'spring-boot',
})

const isDeploying = ref(false)
const isViteDeploying = ref(false)

const isViteProject = computed(() => projectConfig.value.project_type === 'vite')

const isRunning = computed(() =>
  isDeploying.value ||
  isViteDeploying.value ||
  syncStore.syncStatus === 'syncing' ||
  syncStore.syncStatus === 'scanning' ||
  buildStore.buildStatus === 'building' ||
  buildStore.runStatus === 'running' ||
  viteStore.deployStatus === 'running'
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

const canViteAction = computed(() =>
  !!projectConfig.value.remote_path &&
  !!projectConfig.value.ssh_alias &&
  !isRunning.value
)

const sshAccounts = computed(() => sshStore.accounts)
const sshAccountOptions = computed(() =>
  sshAccounts.value.map(a => ({ label: a.alias, value: a.alias }))
)
const projectTypeOptions = [
  { label: 'Java', value: 'java' },
  { label: 'Vite', value: 'vite' },
]
const jdkOptions = [
  { label: 'JDK 8 (1.8)', value: '8' },
  { label: 'JDK 11', value: '11' },
  { label: 'JDK 17', value: '17' },
  { label: 'JDK 21', value: '21' },
]
const runModeOptions = [
  { label: 'Spring Boot (mvn spring-boot:run)', value: 'spring-boot' },
  { label: '普通运行 (java -jar / mvn exec:java)', value: 'default' },
]

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

function openEditDialog(proj: ProjectItem) {
  editProjectForm.value = {
    alias: proj.alias,
    local_path: proj.local_path,
    remote_path: proj.remote_path,
    ssh_alias: proj.ssh_alias,
    project_type: proj.project_type || 'java',
    jdk_version: proj.jdk_version || '21',
    node_version: proj.node_version || '20',
    nginx_port: proj.nginx_port ?? 8080,
    build_command: proj.build_command || 'npm run build',
    run_mode: proj.run_mode || 'spring-boot',
  }
  showEditProject.value = true
}

async function handleEditProject() {
  if (!editProjectForm.value.local_path || !editProjectForm.value.remote_path) {
    Md3Message.warning('请填写完整信息')
    return
  }
  editingProject.value = true
  try {
    const updated = await projectStore.updateProject(editProjectForm.value.alias, {
      local_path: editProjectForm.value.local_path,
      remote_path: editProjectForm.value.remote_path,
      ssh_alias: editProjectForm.value.ssh_alias,
      project_type: editProjectForm.value.project_type,
      jdk_version: editProjectForm.value.jdk_version || '21',
      node_version: editProjectForm.value.node_version || '20',
      nginx_port: editProjectForm.value.nginx_port ?? 8080,
      build_command: editProjectForm.value.build_command || 'npm run build',
      run_mode: editProjectForm.value.run_mode || 'spring-boot',
    })
    if (selectedProject.value?.alias === editProjectForm.value.alias) {
      selectedProject.value = updated
      projectConfig.value = { ...updated }
    }
    showEditProject.value = false
    Md3Message.success('项目配置已更新')
  } catch {
    Md3Message.error('更新项目配置失败')
  } finally {
    editingProject.value = false
  }
}

async function handleCreateProject() {
  if (!newProjectForm.value.alias) {
    Md3Message.warning('请输入项目别名')
    return
  }
  if (projectStore.projects.some(p => p.alias === newProjectForm.value.alias)) {
    Md3Message.warning('项目别名已存在')
    return
  }
  creatingProject.value = true
  try {
    const project = await projectStore.createProject(newProjectForm.value)
    showNewProject.value = false
    newProjectForm.value = { alias: '', local_path: '', remote_path: '', ssh_alias: '', project_type: 'java', jdk_version: '21', node_version: '20', nginx_port: 8080, build_command: 'npm run build', run_mode: 'spring-boot' }
    selectProject(project)
    Md3Message.success('项目已创建')
  } catch {
    Md3Message.error('创建项目失败')
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

async function handleViteDeploy() {
  if (isViteDeploying.value || isRunning.value) return
  isViteDeploying.value = true
  try {
    await viteStore.startDeploy({
      account_alias: projectConfig.value.ssh_alias,
      project_alias: projectConfig.value.alias,
      project_path: projectConfig.value.remote_path,
      node_version: projectConfig.value.node_version || '20',
      nginx_port: projectConfig.value.nginx_port || 8080,
      build_command: projectConfig.value.build_command || 'npm run build',
    })
    const result = await viteStore.waitForCompletion()
    if (result === 'failed') throw new Error('部署失败')
  } catch (e: any) {
    viteStore.pipeToTerminal(`\r\n\x1b[31m一键部署中止: ${e?.message || e}\x1b[0m\r\n`)
  } finally {
    isViteDeploying.value = false
  }
}

async function handleViteCheck() {
  if (!canViteAction.value) return
  try {
    const result = await viteStore.checkEnvironment(
      projectConfig.value.ssh_alias,
      projectConfig.value.remote_path
    )
    Md3Message.info(`环境检查完成: Node=${result.node?.installed ? result.node.version : '未安装'}, Nginx=${result.nginx?.installed ? (result.nginx?.running ? '运行中' : '已安装') : '未安装'}`)
  } catch (e: any) {
    Md3Message.error(`环境检查失败: ${e?.message || e}`)
  }
}

async function handleViteSetup() {
  if (!canViteAction.value) return
  try {
    await viteStore.startStep('setup', {
      account_alias: projectConfig.value.ssh_alias,
      project_path: projectConfig.value.remote_path,
      node_version: projectConfig.value.node_version || '20',
    })
    const result = await viteStore.waitForCompletion()
    if (result === 'failed') throw new Error('安装 Node 失败')
  } catch (e: any) {
    Md3Message.error(`安装 Node 失败: ${e?.message || e}`)
    throw e
  }
}

async function handleViteInstallDeps() {
  if (!canViteAction.value) return
  try {
    await viteStore.startStep('install-deps', {
      account_alias: projectConfig.value.ssh_alias,
      project_path: projectConfig.value.remote_path,
    })
    const result = await viteStore.waitForCompletion()
    if (result === 'failed') throw new Error('安装依赖失败')
  } catch (e: any) {
    Md3Message.error(`安装依赖失败: ${e?.message || e}`)
    throw e
  }
}

async function handleViteBuild() {
  if (!canViteAction.value) return
  try {
    await viteStore.startStep('build', {
      account_alias: projectConfig.value.ssh_alias,
      project_path: projectConfig.value.remote_path,
      build_command: projectConfig.value.build_command || 'npm run build',
    })
    const result = await viteStore.waitForCompletion()
    if (result === 'failed') throw new Error('构建失败')
  } catch (e: any) {
    Md3Message.error(`构建失败: ${e?.message || e}`)
    throw e
  }
}

async function handleViteNginx() {
  if (!canViteAction.value) return
  try {
    await viteStore.startStep('nginx', {
      account_alias: projectConfig.value.ssh_alias,
      project_path: projectConfig.value.remote_path,
      project_alias: projectConfig.value.alias,
      port: projectConfig.value.nginx_port || 8080,
    })
    const result = await viteStore.waitForCompletion()
    if (result === 'failed') throw new Error('配置 Nginx 失败')
  } catch (e: any) {
    Md3Message.error(`配置 Nginx 失败: ${e?.message || e}`)
    throw e
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
      run_mode: projectConfig.value.run_mode || 'spring-boot',
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
    if (isViteProject.value) {
      await viteStore.stopDeploy()
    } else {
      if (syncStore.syncStatus !== 'idle') {
        await syncStore.stopSync()
      }
      if (buildStore.buildStatus === 'building' || buildStore.runStatus === 'running') {
        await buildStore.stopTask()
      }
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
  overflow: hidden;
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
  display: flex;
  flex-direction: column;
  flex: 1;
  gap: 2px;
  overflow-y: auto;
}

.project-menu-item {
  display: flex;
  align-items: center;
  gap: var(--md3-space-sm);
  padding: var(--md3-space-sm) var(--md3-space-md);
  border-radius: var(--md3-shape-sm);
  cursor: pointer;
  transition: all var(--md3-motion-duration-short) var(--md3-motion-easing-standard);
  font: var(--md3-type-body-medium);
  color: var(--md3-on-surface-variant);
  user-select: none;
  position: relative;
}

.project-menu-item:hover {
  background: var(--md3-surface-container-highest);
  color: var(--md3-on-surface);
}

.project-menu-item--active {
  background: var(--md3-primary-container);
  color: var(--md3-on-primary-container);
  font-weight: 500;
}

.project-menu-item--active:hover {
  background: var(--md3-primary-container);
  color: var(--md3-on-primary-container);
}

.project-menu-icon {
  width: 18px;
  height: 18px;
  flex-shrink: 0;
}

.project-menu-text {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.project-menu-edit {
  display: none;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  padding: 0;
  border: none;
  background: transparent;
  border-radius: var(--md3-shape-sm);
  cursor: pointer;
  transition: background var(--md3-motion-duration-short) var(--md3-motion-easing-standard);
}

.project-menu-item:hover .project-menu-edit {
  display: flex;
}

.project-menu-edit:hover {
  background: rgba(0, 0, 0, 0.1);
}

.project-menu-item--active .project-menu-edit:hover {
  background: rgba(255, 255, 255, 0.2);
}

.project-menu-edit-icon {
  width: 14px;
  height: 14px;
  color: var(--md3-on-surface-variant);
}

.project-menu-type {
  font-size: 11px;
  color: var(--md3-on-surface-variant);
  background: var(--md3-surface-container-highest);
  padding: 2px 6px;
  border-radius: var(--md3-shape-xs);
  text-transform: uppercase;
  flex-shrink: 0;
}

.project-menu-item--active .project-menu-type {
  background: rgba(255, 255, 255, 0.2);
  color: var(--md3-on-primary-container);
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
  overflow-x: hidden;
  min-width: 0;
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

.config-form {
  display: flex;
  flex-direction: column;
  gap: var(--md3-space-md);
}

.form-item {
  display: flex;
  flex-direction: column;
  gap: var(--md3-space-xs);
}

.form-label {
  font-size: 0.75rem;
  color: var(--md3-on-surface-variant);
  padding-left: var(--md3-space-sm);
}

.jdk-item {
  flex-direction: row;
  align-items: center;
}

.jdk-row {
  display: flex;
  align-items: center;
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
  flex-shrink: 0;
}

.action-bar:hover {
  box-shadow: var(--md3-elevation-level1);
}

.status-area {
  flex: 1;
  display: flex;
  gap: var(--md3-space-lg);
  min-height: 0;
  overflow: hidden;
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
  overflow-y: auto;
  max-height: 100%;
}

.status-sidebar:hover {
  box-shadow: var(--md3-elevation-level1);
}

.status-terminal {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  overflow: hidden;
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
  flex-shrink: 0;
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
  overflow: hidden;
}

.dialog-form {
  display: flex;
  flex-direction: column;
  gap: var(--md3-space-md);
}
</style>
