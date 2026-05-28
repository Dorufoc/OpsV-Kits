<template>
  <button class="theme-toggle" :title="themeStore.mode === 'dark' ? '切换亮色模式' : '切换深色模式'" @click="themeStore.toggleDark()">
    <div class="toggle-track" :class="{ dark: themeStore.mode === 'dark' }">
      <div class="toggle-thumb">
        <svg v-if="themeStore.mode === 'dark'" class="icon-moon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
        </svg>
        <svg v-else class="icon-sun" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="12" cy="12" r="5"/>
          <line x1="12" y1="1" x2="12" y2="3"/>
          <line x1="12" y1="21" x2="12" y2="23"/>
          <line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/>
          <line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/>
          <line x1="1" y1="12" x2="3" y2="12"/>
          <line x1="21" y1="12" x2="23" y2="12"/>
          <line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/>
          <line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>
        </svg>
      </div>
    </div>
  </button>
</template>

<script setup lang="ts">
import { useThemeStore } from '@/stores/themeStore'

const themeStore = useThemeStore()
</script>

<style scoped>
.theme-toggle {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 4px;
  border: none;
  background: transparent;
  cursor: pointer;
  border-radius: var(--md3-shape-full);
  transition: background var(--md3-motion-duration-short) var(--md3-motion-easing-standard);
}

.theme-toggle:hover {
  background: var(--md3-surface-container-high);
}

.toggle-track {
  width: 48px;
  height: 26px;
  border-radius: var(--md3-shape-full);
  background: var(--md3-surface-container-high);
  border: 1px solid var(--md3-outline-variant);
  position: relative;
  transition: all var(--md3-motion-duration-medium) var(--md3-motion-easing-emphasized-decelerate);
}

.toggle-track.dark {
  background: var(--md3-primary-container);
  border-color: var(--md3-primary);
}

.toggle-thumb {
  position: absolute;
  top: 2px;
  left: 2px;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: var(--md3-surface);
  box-shadow: var(--md3-elevation-level1);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--md3-on-surface-variant);
  transition: transform var(--md3-motion-duration-medium) var(--md3-motion-easing-emphasized-decelerate),
              background var(--md3-motion-duration-medium) var(--md3-motion-easing-emphasized-decelerate);
}

.toggle-track.dark .toggle-thumb {
  transform: translateX(22px);
  background: var(--md3-primary);
  color: var(--md3-on-primary);
}
</style>
