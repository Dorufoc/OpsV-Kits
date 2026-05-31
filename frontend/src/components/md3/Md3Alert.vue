<template>
  <div
    class="md3-alert"
    :class="[`md3-alert--${type}`]"
    role="alert"
  >
    <svg class="md3-alert__icon" width="20" height="20" viewBox="0 0 20 20" fill="currentColor">
      <path v-if="type === 'success'" d="M10 2C5.58 2 2 5.58 2 10s3.58 8 8 8 8-3.58 8-8-3.58-8-8-8zm-1 12.41L5.59 11 7 9.59l2 2 4-4L14.41 9 9 14.41z" />
      <path v-else-if="type === 'warning'" d="M10 2L1 18h18L10 2zm0 4.5L13.5 15.5h-7L10 6.5zM9 11v2h2v-2H9zm0 3v2h2v-2H9z" />
      <path v-else-if="type === 'danger'" d="M10 2C5.58 2 2 5.58 2 10s3.58 8 8 8 8-3.58 8-8-3.58-8-8-8zM9 6h2v5H9V6zm0 6h2v2H9v-2z" />
      <path v-else d="M10 2C5.58 2 2 5.58 2 10s3.58 8 8 8 8-3.58 8-8-3.58-8-8-8zm0 13c-.55 0-1-.45-1-1s.45-1 1-1 1 .45 1 1-.45 1-1 1zm1-3H9V7h2v5z" />
    </svg>
    <div class="md3-alert__content">
      <div v-if="$slots.title || title" class="md3-alert__title">
        <slot name="title">{{ title }}</slot>
      </div>
      <div class="md3-alert__message">
        <slot name="message">{{ message }}</slot>
      </div>
    </div>
    <button
      v-if="closable"
      class="md3-alert__close"
      aria-label="关闭"
      @click="emit('close')"
    >
      <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
        <path d="M12 4L4 12M4 4L12 12" />
      </svg>
    </button>
  </div>
</template>

<script setup lang="ts">
type AlertType = 'success' | 'warning' | 'danger' | 'info'

withDefaults(defineProps<{
  type?: AlertType
  title?: string
  message?: string
  closable?: boolean
}>(), {
  type: 'info',
  title: '',
  message: '',
  closable: false,
})

const emit = defineEmits<{
  close: []
}>()

defineSlots<{
  title?(props: {}): any
  message?(props: {}): any
}>()
</script>

<style scoped>
.md3-alert {
  display: flex;
  align-items: flex-start;
  gap: var(--md3-space-md);
  padding: var(--md3-space-lg);
  border-radius: var(--md3-shape-md);
  border: 1px solid transparent;
}

.md3-alert__icon {
  flex-shrink: 0;
  margin-top: 1px;
}

.md3-alert__content {
  flex: 1;
  min-width: 0;
}

.md3-alert__title {
  font: var(--md3-type-title-small);
  margin-bottom: var(--md3-space-xs);
}

.md3-alert__message {
  font: var(--md3-type-body-medium);
}

.md3-alert__close {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border: none;
  border-radius: var(--md3-shape-full);
  background: transparent;
  color: currentColor;
  cursor: pointer;
  transition: background var(--md3-motion-duration-short) var(--md3-motion-easing-standard);
  flex-shrink: 0;
  opacity: 0.6;
}

.md3-alert__close:hover {
  background: rgba(0, 0, 0, 0.08);
  opacity: 1;
}

.md3-alert__close:focus-visible {
  outline: 2px solid currentColor;
  outline-offset: 2px;
}

/* ===== Type Variants ===== */
.md3-alert--success {
  color: var(--md3-on-success-container);
  background: var(--md3-success-container);
  border-color: var(--md3-success-container);
}

.md3-alert--warning {
  color: var(--md3-on-warning-container);
  background: var(--md3-warning-container);
  border-color: var(--md3-warning-container);
}

.md3-alert--danger {
  color: var(--md3-on-error-container);
  background: var(--md3-error-container);
  border-color: var(--md3-error-container);
}

.md3-alert--info {
  color: var(--md3-on-primary-container);
  background: var(--md3-primary-container);
  border-color: var(--md3-primary-container);
}

/* ===== Dark Mode ===== */
[data-theme="dark"] .md3-alert__close:hover {
  background: rgba(255, 255, 255, 0.08);
}
</style>
