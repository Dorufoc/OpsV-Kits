<template>
  <div class="color-presets">
    <div class="preset-label">{{ label }}</div>
    <div class="preset-grid">
      <button
        v-for="p in presets"
        :key="p.id"
        class="preset-btn"
        :class="{ active: themeStore.preset === p.id }"
        :style="{ '--swatch-color': p.color }"
        :title="p.name"
        @click="themeStore.setPreset(p.id)"
      >
        <div class="preset-swatch">
          <svg v-if="themeStore.preset === p.id" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="20 6 9 17 4 12"/>
          </svg>
        </div>
        <span class="preset-name">{{ p.name }}</span>
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useThemeStore, type ThemePreset } from '@/stores/themeStore'

defineProps<{
  label?: string
}>()

const themeStore = useThemeStore()

interface PresetItem {
  id: ThemePreset
  name: string
  color: string
}

const presets: PresetItem[] = [
  { id: 'indigo', name: '靛蓝', color: '#4F46E5' },
  { id: 'blue', name: '天蓝', color: '#2563EB' },
  { id: 'green', name: '翠绿', color: '#059669' },
  { id: 'orange', name: '橙黄', color: '#EA580C' },
  { id: 'rose', name: '玫红', color: '#E11D48' },
  { id: 'purple', name: '紫罗兰', color: '#7C3AED' },
]
</script>

<style scoped>
.color-presets {
  display: flex;
  flex-direction: column;
  gap: var(--md3-space-md);
}

.preset-label {
  font: var(--md3-type-label-large);
  color: var(--md3-on-surface-variant);
}

.preset-grid {
  display: flex;
  flex-wrap: wrap;
  gap: var(--md3-space-sm);
}

.preset-btn {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: var(--md3-space-sm);
  border: 1px solid var(--md3-outline-variant);
  background: var(--md3-surface-container-low);
  border-radius: var(--md3-shape-sm);
  cursor: pointer;
  transition: all var(--md3-motion-duration-short) var(--md3-motion-easing-standard);
  min-width: 56px;
}

.preset-btn:hover {
  background: var(--md3-surface-container-high);
  border-color: var(--md3-outline);
}

.preset-btn.active {
  background: var(--md3-primary-container);
  border-color: var(--md3-primary);
}

.preset-swatch {
  width: 32px;
  height: 32px;
  border-radius: var(--md3-shape-full);
  background: var(--swatch-color);
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  transition: transform var(--md3-motion-duration-short) var(--md3-motion-easing-standard);
}

.preset-btn:hover .preset-swatch {
  transform: scale(1.1);
}

.preset-btn.active .preset-swatch {
  box-shadow: 0 0 0 2px var(--md3-surface), 0 0 0 4px var(--swatch-color);
}

.preset-name {
  font: var(--md3-type-label-small);
  color: var(--md3-on-surface-variant);
  white-space: nowrap;
}

.preset-btn.active .preset-name {
  color: var(--md3-on-surface);
  font-weight: 600;
}
</style>
