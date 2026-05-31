import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    name: 'Home',
    component: () => import('@/views/Home.vue'),
    meta: { title: '首页' },
  },
  {
    path: '/project',
    name: 'Project',
    component: () => import('@/views/ProjectPage.vue'),
    meta: { title: '项目部署' },
  },
  {
    path: '/file-manager',
    name: 'FileManager',
    component: () => import('@/views/FileManagerPage.vue'),
    meta: { title: '远程文件管理' },
  },
  {
    path: '/ssh-accounts',
    name: 'SshAccounts',
    component: () => import('@/views/SshAccountPage.vue'),
    meta: { title: 'SSH 账户管理' },
  },
  {
    path: '/docker',
    name: 'Docker',
    component: () => import('@/views/DockerPage.vue'),
    meta: { title: 'Docker 管理' },
  },
  {
    path: '/docker-store',
    name: 'DockerStore',
    component: () => import('@/views/DockerStorePage.vue'),
    meta: { title: '应用商店' },
  },
  {
    path: '/docker/container/:id',
    name: 'DockerContainerDetail',
    component: () => import('@/views/DockerContainerDetail.vue'),
    meta: { title: '容器详情' },
  },
  {
    path: '/webssh',
    name: 'WebSSH',
    component: () => import('@/views/WebSSHPage.vue'),
    meta: { title: 'WebSSH 终端' },
  },
  {
    path: '/tools',
    name: 'Tools',
    component: () => import('@/views/Tools.vue'),
    meta: { title: '工具箱' },
  },
  {
    path: '/settings',
    name: 'Settings',
    component: () => import('@/views/Settings.vue'),
    meta: { title: '设置' },
  },
  {
    path: '/monitor',
    name: 'MonitorDashboard',
    component: () => import('@/views/MonitorDashboard.vue'),
    meta: { title: '资源监控' },
  },
  {
    path: '/monitor/large-screen',
    name: 'MonitorLargeScreen',
    component: () => import('@/views/MonitorLargeScreen.vue'),
    meta: { title: '监控大屏' },
  },
  {
    path: '/process',
    name: 'ProcessManager',
    component: () => import('@/views/ProcessManagerPage.vue'),
    meta: { title: '进程管理' },
  },
  {
    path: '/security-network',
    name: 'SecurityNetwork',
    component: () => import('@/views/SecurityNetworkPage.vue'),
    meta: { title: '安全与网络' },
  },
  {
    path: '/cron-backup',
    name: 'CronBackup',
    component: () => import('@/views/CronBackupPage.vue'),
    meta: { title: '计划任务与备份' },
  },
  {
    path: '/log-analysis',
    name: 'LogAnalysis',
    component: () => import('@/views/LogAnalysisPage.vue'),
    meta: { title: '日志分析' },
  },
  {
    path: '/automation',
    name: 'Automation',
    component: () => import('@/views/AutomationPage.vue'),
    meta: { title: '自动化' },
  },
  {
    path: '/automation/workflow/:id',
    name: 'WorkflowEditor',
    component: () => import('@/views/WorkflowEditorPage.vue'),
    meta: { title: '工作流编辑器' },
  },
  {
    path: '/git-integration',
    name: 'GitIntegration',
    component: () => import('@/views/GitIntegrationPage.vue'),
    meta: { title: 'Git 集成' },
  },
  {
    path: '/audit-log',
    name: 'AuditLog',
    component: () => import('@/views/AuditLogPage.vue'),
    meta: { title: '审计日志' },
  },
  {
    path: '/health-probe',
    name: 'HealthProbe',
    component: () => import('@/views/HealthProbePage.vue'),
    meta: { title: '健康检查' },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
