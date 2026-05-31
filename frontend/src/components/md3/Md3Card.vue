<template>
  <div
    class="md3-card"
    :class="{
      'md3-card--hoverable': hoverable,
    }"
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
const props = withDefaults(defineProps<{
  hoverable?: boolean
}>(), {
  hoverable: false,
})
</script>

<style scoped>
.md3-card {
  background: var(--md3-glass-bg);
  border-radius: var(--md3-shape-md);
  border: 1px solid var(--md3-card-border);
  backdrop-filter: var(--md3-glass-blur);
  -webkit-backdrop-filter: var(--md3-glass-blur);
  overflow: hidden;
  transition: border-color var(--md3-motion-duration-medium) var(--md3-motion-easing-standard),
              transform var(--md3-motion-duration-medium) var(--md3-motion-easing-standard);
}

.md3-card--hoverable:hover {
  border-color: var(--md3-card-border-hover);
  transform: translateY(-1px);
}

.md3-card--hoverable:active {
  border-color: var(--md3-card-border);
  transform: translateY(0);
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
