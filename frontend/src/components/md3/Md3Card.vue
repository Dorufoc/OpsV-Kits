<template>
  <div
    class="md3-card"
    :class="{
      'md3-card--hoverable': hoverable,
      'md3-card--shadow': shadow,
    }"
    :style="cardStyle"
  >
    <div class="md3-card-header" v-if="$slots.header">
      <slot name="header" />
    </div>
    <div class="md3-card-body">
      <slot />
    </div>
    <div class="md3-card-actions" v-if="$slots.actions">
      <slot name="actions" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(defineProps<{
  shadow?: boolean | 'never' | 'hover' | 'always'
  hoverable?: boolean
  elevation?: 0 | 1 | 2 | 3 | 4 | 5
}>(), {
  shadow: true,
  hoverable: false,
  elevation: 1,
})

const cardStyle = computed(() => {
  return {
    boxShadow: props.shadow ? `var(--md3-elevation-level${props.elevation})` : 'none',
  }
})
</script>

<style scoped>
.md3-card {
  background: var(--md3-surface);
  border-radius: var(--md3-shape-md);
  border: 1px solid var(--md3-outline-variant);
  overflow: hidden;
  transition: box-shadow var(--md3-motion-duration-medium) var(--md3-motion-easing-standard),
              transform var(--md3-motion-duration-medium) var(--md3-motion-easing-standard);
}

.md3-card--shadow {
  border-color: transparent;
}

.md3-card--hoverable:hover {
  box-shadow: var(--md3-elevation-level2);
  transform: translateY(-2px);
}

/* ===== Header ===== */
.md3-card-header {
  padding: var(--md3-space-lg) var(--md3-space-xl) var(--md3-space-md);
  border-bottom: 1px solid var(--md3-outline-variant);
}

/* ===== Body ===== */
.md3-card-body {
  padding: var(--md3-space-lg) var(--md3-space-xl);
}

/* ===== Actions ===== */
.md3-card-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: var(--md3-space-sm);
  padding: var(--md3-space-md) var(--md3-space-xl) var(--md3-space-lg);
  border-top: 1px solid var(--md3-outline-variant);
}
</style>
