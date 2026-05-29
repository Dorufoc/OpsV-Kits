<template>
  <button
    class="theme-icon-btn"
    :aria-label="themeStore.mode === 'dark' ? '切换到亮色模式' : '切换到暗色模式'"
    @click="handleToggle"
  >
    <span class="icon-wrap" :class="{ rotating: isRotating }">
      <svg
        v-if="themeStore.mode === 'light'"
        class="theme-icon sun"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="2"
        stroke-linecap="round"
        stroke-linejoin="round"
      >
        <circle cx="12" cy="12" r="5" />
        <line x1="12" y1="1" x2="12" y2="3" />
        <line x1="12" y1="21" x2="12" y2="23" />
        <line x1="4.22" y1="4.22" x2="5.64" y2="5.64" />
        <line x1="18.36" y1="18.36" x2="19.78" y2="19.78" />
        <line x1="1" y1="12" x2="3" y2="12" />
        <line x1="21" y1="12" x2="23" y2="12" />
        <line x1="4.22" y1="19.78" x2="5.64" y2="18.36" />
        <line x1="18.36" y1="5.64" x2="19.78" y2="4.22" />
      </svg>
      <svg
        v-else
        class="theme-icon moon"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="2"
        stroke-linecap="round"
        stroke-linejoin="round"
      >
        <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
      </svg>
    </span>
  </button>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useThemeStore } from '@/stores/themeStore'

const themeStore = useThemeStore()
const isRotating = ref(false)

function handleToggle() {
  isRotating.value = true
  themeStore.toggleDark()
  setTimeout(() => {
    isRotating.value = false
  }, 500)
}
</script>

<style scoped>
.theme-icon-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  border: none;
  background: transparent;
  color: var(--md3-on-surface-variant);
  cursor: pointer;
  border-radius: var(--md3-shape-full);
  transition: background var(--md3-motion-duration-short) var(--md3-motion-easing-standard);
}

.theme-icon-btn:hover {
  background: var(--md3-surface-container-high);
  color: var(--md3-on-surface);
}

.icon-wrap {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  transition: transform 0.5s cubic-bezier(0.4, 0, 0.2, 1);
}

.icon-wrap.rotating {
  transform: rotate(180deg);
}

.theme-icon {
  width: 22px;
  height: 22px;
}
</style>
