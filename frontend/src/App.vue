<template>
  <div class="app-shell">
    <aside class="app-sidebar" :class="{ collapsed: sidebarCollapsed }">
      <div class="sidebar-brand">
        <div class="brand-logo">
          <img src="./styles/opsV.png" alt="OpsV-Kits" />
        </div>
        <span class="brand-title" v-show="!sidebarCollapsed">OpsV-Kits</span>
      </div>

      <Md3Divider />

      <nav class="sidebar-nav">
        <router-link
          v-for="item in sidebarItems"
          :key="item.path"
          :to="item.path"
          class="sidebar-link"
          :class="{ active: isActiveRoute(route.path, item.path), disabled: !sshReady && item.path !== '/ssh-accounts' }"
          :style="{ pointerEvents: !sshReady && item.path !== '/ssh-accounts' ? 'none' : 'auto', opacity: !sshReady && item.path !== '/ssh-accounts' ? 0.5 : 1 }"
        >
          <Md3Icon :name="item.icon" class="sidebar-icon" />
          <span class="sidebar-label" v-show="!sidebarCollapsed">{{ item.label }}</span>
        </router-link>
      </nav>
    </aside>

    <div class="app-main">
      <header class="app-header">
        <button class="sidebar-toggle" @click="toggleSidebar" aria-label="切换侧边栏">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
            <path d="M3 12h18M3 6h18M3 18h18"/>
          </svg>
        </button>
        <div class="header-actions">
          <ThemeToggle />
        </div>
      </header>

      <main class="app-content">
        <div v-if="!sshReady && currentRoute !== '/ssh-accounts'" class="app-mask">
          <div class="mask-content">
            <Md3Icon name="connection" class="mask-icon" />
            <h2>功能不可用</h2>
            <p>未配置 SSH 服务器，请先前往 SSH 账户管理页面添加账户</p>
            <Md3Button variant="primary" size="lg" :icon="AccountIcon" @click="goToSshAccounts">
              前往 SSH 账户管理
            </Md3Button>
          </div>
        </div>
        <router-view v-slot="{ Component: RouteComponent }">
          <transition name="route" mode="out-in">
            <component :is="RouteComponent" />
          </transition>
        </router-view>
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Md3Icon, Md3Divider } from '@/components/md3'
import ThemeToggle from '@/components/ThemeToggle.vue'
import Md3Button from '@/components/Md3Button.vue'
import { useSshAccountStore } from '@/stores/sshAccountStore'

const route = useRoute()
const router = useRouter()
const sidebarCollapsed = ref(false)
const sshAccountStore = useSshAccountStore()
const sshReady = ref(true)

const STORAGE_KEY = 'opskits_ssh_dismissed'

const currentRoute = computed(() => route.path)

function toggleSidebar() {
  sidebarCollapsed.value = !sidebarCollapsed.value
}

const isActiveRoute = (currentPath: string | undefined, targetPath: string): boolean => {
  if (!currentPath) return false
  if (targetPath === '/') return currentPath === '/'
  if (targetPath === '/docker') return currentPath === '/docker' || currentPath.startsWith('/docker/')
  return currentPath === targetPath || currentPath.startsWith(targetPath + '/')
}

const AccountIcon = 'account-box'

function goToSshAccounts() {
  router.push('/ssh-accounts')
}

async function checkSshStatus() {
  const dismissed = localStorage.getItem(STORAGE_KEY) === 'true'
  if (!dismissed) {
    sshReady.value = true
    return
  }
  
  try {
    await sshAccountStore.fetchAccounts()
    sshReady.value = sshAccountStore.accounts.length > 0
  } catch {
    sshReady.value = false
  }
}

onMounted(() => {
  checkSshStatus()
})

interface NavItem {
  path: string
  label: string
  icon: string
}

const sidebarItems: NavItem[] = [
  { path: '/', label: '控制台', icon: 'home' },
  { path: '/project', label: '项目部署', icon: 'chart-line' },
  { path: '/file-manager', label: '远程文件管理', icon: 'folder-open' },
  { path: '/ssh-accounts', label: 'SSH 账户管理', icon: 'account-box' },
  { path: '/docker', label: 'Docker 管理', icon: 'coin' },
  { path: '/docker-store', label: '应用商店', icon: 'store' },
  { path: '/webssh', label: 'WebSSH 终端', icon: 'monitor' },
  { path: '/monitor', label: '资源监控', icon: 'chart-bar' },
  { path: '/process', label: '进程管理', icon: 'monitor' },
  { path: '/security-network', label: '安全与网络', icon: 'shield' },
  { path: '/cron-backup', label: '计划任务与备份', icon: 'schedule' },
  { path: '/automation', label: '任务调度与自动化', icon: 'account-cog' },
  { path: '/tools', label: '工具箱', icon: 'wrench' },
  { path: '/settings', label: '系统设置', icon: 'cog' },
]
</script>

<style>
/* ===== Route Transition ===== */
.route-enter-active {
  animation: md3-slide-up var(--md3-motion-duration-long) var(--md3-motion-easing-emphasized-decelerate) forwards;
}

.route-leave-active {
  animation: md3-fade-in var(--md3-motion-duration-medium) var(--md3-motion-easing-standard) reverse forwards;
}
</style>

<style scoped>
/* ===== App Shell ===== */
.app-shell {
  height: 100vh;
  display: flex;
  background: var(--md3-gradient-surface);
  overflow: hidden;
}

/* ===== Sidebar ===== */
.app-sidebar {
  width: 240px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  background: var(--md3-glass-bg);
  backdrop-filter: var(--md3-glass-blur);
  -webkit-backdrop-filter: var(--md3-glass-blur);
  border-right: 1px solid var(--md3-glass-border);
  overflow-y: auto;
  overflow-x: hidden;
  z-index: 50;
  transition: width var(--md3-motion-duration-medium) var(--md3-motion-easing-emphasized-decelerate);
}

.app-sidebar.collapsed {
  width: 64px;
}

.app-sidebar :deep(.md3-divider--horizontal) {
  flex-shrink: 0;
  margin: 0;
}

.sidebar-brand {
  display: flex;
  align-items: center;
  justify-content: flex-start;
  gap: var(--md3-space-sm);
  box-sizing: border-box;
  width: 100%;
  height: 48px;
  padding: 0 var(--md3-space-lg);
  flex-shrink: 0;
}

.app-sidebar.collapsed .sidebar-brand {
  gap: 0;
  justify-content: center;
  padding: 0;
}

.brand-logo {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  overflow: hidden;
}

.brand-logo img {
  display: block;
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
}

.brand-title {
  font: var(--md3-type-title-large);
  color: var(--md3-on-surface);
  letter-spacing: -0.02em;
  white-space: nowrap;
  overflow: hidden;
  line-height: 1;
}

.sidebar-toggle {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border: none;
  background: transparent;
  color: var(--md3-on-surface-variant);
  cursor: pointer;
  border-radius: var(--md3-shape-sm);
  transition: all var(--md3-motion-duration-short) var(--md3-motion-easing-standard);
  flex-shrink: 0;
}

.sidebar-toggle:hover {
  background: var(--md3-surface-container-high);
  color: var(--md3-on-surface);
}

.sidebar-nav {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: var(--md3-space-xs) var(--md3-space-sm);
  flex: 1;
}

.sidebar-link {
  display: flex;
  align-items: center;
  gap: var(--md3-space-md);
  padding: 10px var(--md3-space-lg);
  border-radius: var(--md3-shape-sm);
  color: var(--md3-on-surface-variant);
  text-decoration: none;
  font: var(--md3-type-body-medium);
  transition: all var(--md3-motion-duration-short) var(--md3-motion-easing-standard);
  white-space: nowrap;
  overflow: hidden;
}

.app-sidebar.collapsed .sidebar-link {
  justify-content: center;
  padding: 10px;
}

.sidebar-link:hover {
  background: var(--md3-surface-container-high);
  color: var(--md3-on-surface);
}

.sidebar-link.active {
  background: var(--md3-primary-container);
  color: var(--md3-on-primary-container);
  font-weight: 600;
}

.sidebar-icon {
  width: 20px;
  height: 20px;
  flex-shrink: 0;
}

/* ===== Main ===== */
.app-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.app-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 var(--md3-space-lg);
  height: 48px;
  flex-shrink: 0;
  background: var(--md3-glass-bg);
  backdrop-filter: var(--md3-glass-blur);
  -webkit-backdrop-filter: var(--md3-glass-blur);
  border-bottom: 1px solid var(--md3-glass-border);
}

.header-actions {
  display: flex;
  align-items: center;
  gap: var(--md3-space-sm);
}

.app-content {
  flex: 1;
  overflow-y: auto;
  padding: var(--md3-space-xl);
  position: relative;
}

/* ===== Mask ===== */
.app-mask {
  position: absolute;
  inset: 0;
  background: rgba(0, 0, 0, 0.6);
  backdrop-filter: blur(4px);
  -webkit-backdrop-filter: blur(4px);
  z-index: 100;
  display: flex;
  align-items: center;
  justify-content: center;
}

.mask-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--md3-space-lg);
  padding: var(--md3-space-3xl);
  background: var(--md3-surface-container);
  border-radius: var(--md3-shape-xl);
  box-shadow: var(--md3-elevation-level3);
  max-width: 400px;
  text-align: center;
}

.mask-icon {
  width: 48px;
  height: 48px;
  color: var(--md3-error);
}

.mask-content h2 {
  margin: 0;
  font: var(--md3-type-headline-medium);
  color: var(--md3-on-surface);
}

.mask-content p {
  margin: 0;
  font: var(--md3-type-body-large);
  color: var(--md3-on-surface-variant);
  line-height: 1.5;
}
</style>
