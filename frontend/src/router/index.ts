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
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
