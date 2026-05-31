<template>
  <div class="md3-tabs">
    <div class="md3-tabs__header" role="tablist">
      <button
        v-for="(tab, index) in tabs"
        :key="tab.value || index"
        class="md3-tabs__tab"
        :class="{ 'md3-tabs__tab--active': modelValue === (tab.value ?? index) }"
        role="tab"
        :aria-selected="modelValue === (tab.value ?? index)"
        @click="handleTabClick(tab.value ?? index)"
      >
        <component v-if="tab.icon" :is="tab.icon" class="md3-tabs__icon" />
        <span class="md3-tabs__label">{{ tab.label }}</span>
      </button>
      <div v-if="!hideIndicator" class="md3-tabs__indicator" :style="indicatorStyle" />
    </div>
    <div class="md3-tabs__content">
      <slot />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import type { Component } from 'vue'

export interface TabItem {
  label: string
  value?: string | number
  icon?: Component
}

const props = withDefaults(defineProps<{
  modelValue?: string | number
  tabs?: TabItem[]
  hideIndicator?: boolean
}>(), {
  modelValue: 0,
  tabs: () => [],
  hideIndicator: false,
})

const emit = defineEmits<{
  'update:modelValue': [value: string | number]
}>()

const indicatorRef = ref<HTMLElement | null>(null)

const activeTabIndex = computed(() => {
  return props.tabs.findIndex(tab => (tab.value ?? props.tabs.indexOf(tab)) === props.modelValue)
})

const indicatorStyle = computed(() => {
  if (!indicatorRef.value || activeTabIndex.value === -1) return {}
  const parent = indicatorRef.value.parentElement
  if (!parent) return {}
  const activeTab = parent.children[activeTabIndex.value] as HTMLElement
  if (!activeTab) return {}
  return {
    width: `${activeTab.offsetWidth}px`,
    transform: `translateX(${activeTab.offsetLeft}px)`,
  }
})

function handleTabClick(value: string | number) {
  emit('update:modelValue', value)
}
</script>

<style scoped>
.md3-tabs {
  display: flex;
  flex-direction: column;
  width: 100%;
}

.md3-tabs__header {
  position: relative;
  display: flex;
  gap: var(--md3-space-xs);
  padding: var(--md3-space-xs);
  background: var(--md3-surface-container-low);
  border-radius: var(--md3-shape-md);
}

.md3-tabs__tab {
  display: inline-flex;
  align-items: center;
  gap: var(--md3-space-sm);
  padding: var(--md3-space-sm) var(--md3-space-lg);
  border: none;
  background: transparent;
  border-radius: var(--md3-shape-sm);
  font: var(--md3-type-label-large);
  color: var(--md3-on-surface-variant);
  cursor: pointer;
  transition: all var(--md3-motion-duration-short) var(--md3-motion-easing-standard);
  white-space: nowrap;
  user-select: none;
  z-index: 1;
}

.md3-tabs__tab:hover {
  color: var(--md3-on-surface);
  background: var(--md3-surface-container);
}

.md3-tabs__tab:active {
  background: var(--md3-surface-container-high);
}

.md3-tabs__tab:focus-visible {
  outline: 2px solid var(--md3-primary);
  outline-offset: 2px;
}

.md3-tabs__tab--active {
  color: var(--md3-on-primary-container);
  background: var(--md3-primary-container);
}

.md3-tabs__icon {
  width: 16px;
  height: 16px;
}

.md3-tabs__indicator {
  position: absolute;
  height: 3px;
  bottom: 0;
  background: var(--md3-primary);
  border-radius: var(--md3-shape-full);
  transition: all var(--md3-motion-duration-medium) var(--md3-motion-easing-emphasized);
}

.md3-tabs__content {
  padding-top: var(--md3-space-xl);
}

/* ===== Dark Mode ===== */
[data-theme="dark"] .md3-tabs__tab--active {
  background: var(--md3-primary-container);
  color: var(--md3-primary);
}
</style>
