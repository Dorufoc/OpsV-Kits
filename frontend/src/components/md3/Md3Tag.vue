<template>
  <span
    class="md3-tag"
    :class="[
      `md3-tag--${type}`,
      `md3-tag--${size}`,
      {
        'md3-tag--closable': closable,
      }
    ]"
  >
    <slot />
    <button
      v-if="closable"
      type="button"
      class="md3-tag-close"
      @click.stop="emit('close')"
    >
      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3">
        <path d="M18 6L6 18M6 6l12 12" />
      </svg>
    </button>
  </span>
</template>

<script setup lang="ts">
type TagType = 'primary' | 'success' | 'warning' | 'danger' | 'info'
type TagSize = 'sm' | 'md' | 'lg'

withDefaults(defineProps<{
  type?: TagType
  size?: TagSize
  closable?: boolean
}>(), {
  type: 'info',
  size: 'md',
  closable: false,
})

const emit = defineEmits<{
  close: []
}>()
</script>

<style scoped>
.md3-tag {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  border-radius: var(--md3-shape-sm);
  font-weight: 500;
  line-height: 1;
  white-space: nowrap;
  user-select: none;
}

/* ===== Sizes ===== */
.md3-tag--sm {
  padding: 2px 6px;
  font-size: 0.625rem;
}

.md3-tag--md {
  padding: 4px 8px;
  font-size: 0.75rem;
}

.md3-tag--lg {
  padding: 6px 10px;
  font-size: 0.875rem;
}

/* ===== Primary ===== */
.md3-tag--primary {
  background: var(--md3-primary-container);
  color: var(--md3-on-primary-container);
}

/* ===== Success ===== */
.md3-tag--success {
  background: var(--md3-success-container);
  color: var(--md3-on-success-container, var(--md3-success));
}

/* ===== Warning ===== */
.md3-tag--warning {
  background: var(--md3-warning-container);
  color: var(--md3-on-warning-container, var(--md3-warning));
}

/* ===== Danger ===== */
.md3-tag--danger {
  background: var(--md3-error-container);
  color: var(--md3-on-error-container, var(--md3-error));
}

/* ===== Info ===== */
.md3-tag--info {
  background: var(--md3-surface-container-high);
  color: var(--md3-on-surface-variant);
}

/* ===== Close ===== */
.md3-tag-close {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 14px;
  height: 14px;
  border: none;
  background: transparent;
  cursor: pointer;
  padding: 0;
  color: inherit;
  opacity: 0.7;
  transition: opacity var(--md3-motion-duration-short) var(--md3-motion-easing-standard);
}

.md3-tag-close:hover {
  opacity: 1;
}

[data-theme="dark"] .md3-tag--success {
  color: var(--md3-success);
}

[data-theme="dark"] .md3-tag--warning {
  color: var(--md3-warning);
}

[data-theme="dark"] .md3-tag--danger {
  color: var(--md3-error);
}
</style>
