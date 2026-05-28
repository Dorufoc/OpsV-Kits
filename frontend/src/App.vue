<template>
  <div class="app-shell">
    <header class="app-header">
      <div class="header-left">
        <button class="menu-toggle" @click="toggleDrawer" aria-label="切换菜单">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
            <line x1="4" y1="6" x2="20" y2="6"/>
            <line x1="4" y1="12" x2="20" y2="12"/>
            <line x1="4" y1="18" x2="20" y2="18"/>
          </svg>
        </button>
        <div class="header-brand">
          <div class="brand-icon">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="2" y="3" width="20" height="14" rx="2"/>
              <line x1="8" y1="21" x2="16" y2="21"/>
              <line x1="12" y1="17" x2="12" y2="21"/>
            </svg>
          </div>
          <span class="brand-title">OpsV-Kits</span>
        </div>
      </div>
      <nav class="header-nav">
        <router-link
          v-for="item in navItems"
          :key="item.path"
          :to="item.path"
          class="nav-link"
          :class="{ active: route.path === item.path || (item.path !== '/' && route.path.startsWith(item.path)) }"
        >
          <Md3Icon :name="item.icon" class="nav-icon" />
          <span class="nav-label">{{ item.label }}</span>
        </router-link>
      </nav>
      <div class="header-actions">
        <ThemeToggle />
      </div>
    </header>

    <div class="app-body">
      <aside class="app-sidebar" :class="{ open: drawerOpen }">
        <div class="sidebar-header">
          <span class="sidebar-title">导航菜单</span>
        </div>
        <nav class="sidebar-nav">
          <router-link
            v-for="item in sidebarItems"
            :key="item.path"
            :to="item.path"
            class="sidebar-link"
            :class="{ active: route.path === item.path || (item.path !== '/' && route.path.startsWith(item.path)) }"
            @click="drawerOpen = false"
          >
            <Md3Icon :name="item.icon" class="sidebar-icon" />
            <span class="sidebar-label">{{ item.label }}</span>
          </router-link>
        </nav>
      </aside>

      <div v-if="drawerOpen" class="drawer-overlay" @click="drawerOpen = false" />

      <main class="app-content">
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
import { ref } from 'vue'
import { useRoute } from 'vue-router'
import { Md3Icon } from '@/components/md3'
import ThemeToggle from '@/components/ThemeToggle.vue'

const route = useRoute()
const drawerOpen = ref(false)

function toggleDrawer() {
  drawerOpen.value = !drawerOpen.value
}

interface NavItem {
  path: string
  label: string
  icon: string
}

const navItems: NavItem[] = [
  { path: '/', label: '首页', icon: 'home' },
  { path: '/project', label: '项目', icon: 'chart-line' },
  { path: '/file-manager', label: '文件', icon: 'folder-open' },
  { path: '/ssh-accounts', label: 'SSH', icon: 'account-box' },
  { path: '/docker', label: 'Docker', icon: 'coin' },
  { path: '/webssh', label: '终端', icon: 'monitor' },
  { path: '/monitor', label: '监控', icon: 'chart-bar' },
]

const sidebarItems: NavItem[] = [
  { path: '/', label: '控制台', icon: 'home' },
  { path: '/project', label: '项目部署', icon: 'chart-line' },
  { path: '/file-manager', label: '远程文件管理', icon: 'folder-open' },
  { path: '/ssh-accounts', label: 'SSH 账户管理', icon: 'account-box' },
  { path: '/docker', label: 'Docker 管理', icon: 'coin' },
  { path: '/webssh', label: 'WebSSH 终端', icon: 'monitor' },
  { path: '/monitor', label: '资源监控', icon: 'chart-bar' },
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
  flex-direction: column;
  background: var(--md3-gradient-surface);
  overflow: hidden;
}

/* ===== Header ===== */
.app-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 var(--md3-space-xl);
  height: 64px;
  flex-shrink: 0;
  background: var(--md3-glass-bg);
  backdrop-filter: var(--md3-glass-blur);
  -webkit-backdrop-filter: var(--md3-glass-blur);
  border-bottom: 1px solid var(--md3-glass-border);
  position: relative;
  z-index: 100;
}

.header-left {
  display: flex;
  align-items: center;
  gap: var(--md3-space-md);
}

.menu-toggle {
  display: none;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  border: none;
  background: transparent;
  color: var(--md3-on-surface-variant);
  cursor: pointer;
  border-radius: var(--md3-shape-sm);
  transition: background var(--md3-motion-duration-short) var(--md3-motion-easing-standard);
}

.menu-toggle:hover {
  background: var(--md3-surface-container-high);
}

.header-brand {
  display: flex;
  align-items: center;
  gap: var(--md3-space-sm);
}

.brand-icon {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--md3-gradient-primary);
  border-radius: var(--md3-shape-sm);
  color: var(--md3-on-primary);
}

.brand-title {
  font: var(--md3-type-title-large);
  color: var(--md3-on-surface);
  letter-spacing: -0.02em;
}

.header-nav {
  display: flex;
  align-items: center;
  gap: var(--md3-space-xs);
}

.nav-link {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  border-radius: var(--md3-shape-full);
  color: var(--md3-on-surface-variant);
  text-decoration: none;
  font: var(--md3-type-label-large);
  transition: all var(--md3-motion-duration-short) var(--md3-motion-easing-standard);
}

.nav-link:hover {
  background: var(--md3-surface-container-high);
  color: var(--md3-on-surface);
}

.nav-link.active {
  background: var(--md3-primary-container);
  color: var(--md3-on-primary-container);
  font-weight: 600;
}

.nav-icon {
  width: 18px;
  height: 18px;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: var(--md3-space-sm);
  margin-left: auto;
}

/* ===== Body ===== */
.app-body {
  flex: 1;
  display: flex;
  overflow: hidden;
  position: relative;
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
  padding: var(--md3-space-md) 0;
  z-index: 50;
  transition: transform var(--md3-motion-duration-medium) var(--md3-motion-easing-emphasized-decelerate);
}

.sidebar-header {
  padding: var(--md3-space-sm) var(--md3-space-xl) var(--md3-space-md);
}

.sidebar-title {
  font: var(--md3-type-label-small);
  color: var(--md3-outline);
  text-transform: uppercase;
  letter-spacing: 1.2px;
}

.sidebar-nav {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 0 var(--md3-space-sm);
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

/* ===== Main Content ===== */
.app-content {
  flex: 1;
  overflow-y: auto;
  padding: var(--md3-space-xl);
}

/* ===== Drawer Overlay ===== */
.drawer-overlay {
  display: none;
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.3);
  z-index: 49;
  backdrop-filter: blur(4px);
}

/* ===== Responsive ===== */
@media (max-width: 1023px) {
  .header-nav {
    display: none;
  }

  .menu-toggle {
    display: flex;
  }

  .app-sidebar {
    position: fixed;
    top: 64px;
    left: 0;
    bottom: 0;
    transform: translateX(-100%);
    z-index: 60;
    width: 280px;
  }

  .app-sidebar.open {
    transform: translateX(0);
  }

  .drawer-overlay {
    display: block;
  }

  .app-content {
    padding: var(--md3-space-lg);
  }
}

@media (max-width: 767px) {
  .app-header {
    padding: 0 var(--md3-space-lg);
  }

  .brand-title {
    font-size: 16px;
  }

  .app-content {
    padding: var(--md3-space-md);
  }
}
</style>
