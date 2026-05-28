<template>
  <button
    class="md3-btn"
    :class="[
      `md3-btn--${variant}`,
      `md3-btn--${computedSize}`,
      {
        'md3-btn--icon-only': isIconOnly,
        'md3-btn--disabled': disabled,
        'md3-btn--loading': loading,
        'md3-btn--block': block,
      }
    ]"
    :disabled="disabled || loading"
    :title="tooltip"
    @click="emit('click', $event)"
  >
    <span v-if="loading" class="md3-btn__spinner">
      <svg width="1em" height="1em" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round">
        <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83"/>
      </svg>
    </span>
    <Md3Icon v-else-if="typeof icon === 'string'" :name="icon" class="md3-btn__icon" />
    <component v-else-if="icon" :is="icon" class="md3-btn__icon" />
    <span v-if="$slots.default" class="md3-btn__label">
      <slot />
    </span>
  </button>
</template>

<script setup lang="ts">
import { computed, useSlots } from 'vue'
import type { Component } from 'vue'
import { Md3Icon } from '@/components/md3'

type ButtonVariant = 'default' | 'primary' | 'danger' | 'success' | 'warning' | 'text'
type ButtonSize = 'sm' | 'md' | 'lg'
type ButtonIcon = Component | string

const props = withDefaults(defineProps<{
  icon?: ButtonIcon
  variant?: ButtonVariant
  size?: ButtonSize
  disabled?: boolean
  loading?: boolean
  block?: boolean
  tooltip?: string
}>(), {
  variant: 'default',
  disabled: false,
  loading: false,
  block: false,
})

defineSlots<{
  default(props: {}): any
}>()

const emit = defineEmits<{
  click: [event: MouseEvent]
}>()

const slots = useSlots()

const isIconOnly = computed(() => !!props.icon && !slots.default)

const computedSize = computed(() => props.size || (isIconOnly.value ? 'sm' : 'md'))
</script>

<style scoped>
/* ===== Base ===== */
.md3-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  border: 1px solid transparent;
  cursor: pointer;
  border-radius: var(--md3-shape-full);
  font-family: var(--md3-font-body);
  font-weight: 500;
  transition: all var(--md3-motion-duration-short) var(--md3-motion-easing-standard);
  position: relative;
  overflow: hidden;
  flex-shrink: 0;
  user-select: none;
  -webkit-tap-highlight-color: transparent;
  text-decoration: none;
  white-space: nowrap;
  line-height: 1;
}

.md3-btn::before {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: inherit;
  background: currentColor;
  opacity: 0;
  transition: opacity var(--md3-motion-duration-short) var(--md3-motion-easing-standard);
}

.md3-btn:hover::before {
  opacity: 0.08;
}

.md3-btn:active::before {
  opacity: 0.12;
}

.md3-btn:focus-visible {
  outline: 2px solid var(--md3-primary);
  outline-offset: 2px;
}

/* ===== Sizes ===== */
/* Icon-only sizes */
.md3-btn--icon-only.md3-btn--sm {
  width: 28px;
  height: 28px;
  padding: 0;
}
.md3-btn--icon-only.md3-btn--md {
  width: 32px;
  height: 32px;
  padding: 0;
}
.md3-btn--icon-only.md3-btn--lg {
  width: 36px;
  height: 36px;
  padding: 0;
}
.md3-btn--icon-only .md3-btn__icon {
  flex-shrink: 0;
}
.md3-btn--icon-only.md3-btn--sm .md3-btn__icon { width: 14px; height: 14px; }
.md3-btn--icon-only.md3-btn--md .md3-btn__icon { width: 16px; height: 16px; }
.md3-btn--icon-only.md3-btn--lg .md3-btn__icon { width: 18px; height: 18px; }
.md3-btn--icon-only .md3-btn__label { display: none; }

/* Full button sizes (icon + text or text only) */
.md3-btn:not(.md3-btn--icon-only).md3-btn--sm {
  padding: 4px 12px;
  font-size: 12px;
  gap: 4px;
  min-height: 28px;
}
.md3-btn:not(.md3-btn--icon-only).md3-btn--md {
  padding: 6px 16px;
  font-size: 13px;
  gap: 6px;
  min-height: 34px;
}
.md3-btn:not(.md3-btn--icon-only).md3-btn--lg {
  padding: 8px 24px;
  font-size: 15px;
  gap: 8px;
  min-height: 42px;
  font-weight: 600;
}
.md3-btn:not(.md3-btn--icon-only) .md3-btn__icon {
  width: 1em;
  height: 1em;
  flex-shrink: 0;
}

/* ===== Variants ===== */
.md3-btn--default {
  color: var(--md3-on-surface-variant);
  background: transparent;
  border-color: var(--md3-outline-variant);
}
.md3-btn--default:hover {
  color: var(--md3-on-surface);
  background: var(--md3-surface-container-high);
  border-color: var(--md3-outline);
  transform: translateY(-1px);
}
.md3-btn--default:active {
  transform: translateY(0);
}

.md3-btn--primary {
  color: var(--md3-on-primary);
  background: var(--md3-primary);
  border-color: var(--md3-primary);
}
.md3-btn--primary:hover {
  box-shadow: var(--md3-elevation-level1);
  transform: translateY(-1px);
}
.md3-btn--primary:active {
  transform: translateY(0);
  box-shadow: none;
}
.md3-btn--primary::before {
  background: white;
}

.md3-btn--danger {
  color: var(--md3-on-error);
  background: var(--md3-error);
  border-color: var(--md3-error);
}
.md3-btn--danger:hover {
  box-shadow: 0 2px 8px rgba(179, 38, 30, 0.3);
  transform: translateY(-1px);
}
.md3-btn--danger:active {
  transform: translateY(0);
  box-shadow: none;
}
.md3-btn--danger::before {
  background: white;
}

.md3-btn--success {
  color: var(--md3-on-success);
  background: var(--md3-success);
  border-color: var(--md3-success);
}
.md3-btn--success:hover {
  box-shadow: var(--md3-elevation-level1);
  transform: translateY(-1px);
}
.md3-btn--success:active {
  transform: translateY(0);
  box-shadow: none;
}
.md3-btn--success::before {
  background: white;
}

.md3-btn--warning {
  color: var(--md3-on-warning);
  background: var(--md3-warning);
  border-color: var(--md3-warning);
}
.md3-btn--warning:hover {
  box-shadow: var(--md3-elevation-level1);
  transform: translateY(-1px);
}
.md3-btn--warning:active {
  transform: translateY(0);
  box-shadow: none;
}
.md3-btn--warning::before {
  background: white;
}

/* Text variant (minimal, no border/bg) */
.md3-btn--text {
  color: var(--md3-on-surface-variant);
  background: transparent;
  border-color: transparent;
  padding-left: 8px;
  padding-right: 8px;
}
.md3-btn--text:hover {
  color: var(--md3-primary);
  background: var(--md3-primary-container);
  transform: translateY(-1px);
}
.md3-btn--text:active {
  transform: translateY(0);
}

/* ===== Dark Mode Adjustments ===== */
[data-theme="dark"] .md3-btn--default {
  color: var(--md3-outline);
  border-color: var(--md3-outline-variant);
}

[data-theme="dark"] .md3-btn--default:hover {
  color: var(--md3-primary);
  background: var(--md3-primary-container);
  border-color: transparent;
}

[data-theme="dark"] .md3-btn--default:active {
  background: var(--md3-primary-container-active);
}

[data-theme="dark"] .md3-btn--primary {
  color: var(--md3-primary);
  background: var(--md3-primary-container);
  border-color: transparent;
}

[data-theme="dark"] .md3-btn--primary:hover {
  background: var(--md3-primary-container-hover);
  box-shadow: var(--md3-elevation-level1);
}

[data-theme="dark"] .md3-btn--danger {
  color: var(--md3-error);
  background: var(--md3-error-container);
  border-color: transparent;
}

[data-theme="dark"] .md3-btn--danger:hover {
  background: var(--md3-error-container-hover);
}

[data-theme="dark"] .md3-btn--success {
  color: var(--md3-success);
  background: var(--md3-success-container);
  border-color: transparent;
}

[data-theme="dark"] .md3-btn--success:hover {
  background: var(--md3-success-container-hover);
}

[data-theme="dark"] .md3-btn--warning {
  color: var(--md3-warning);
  background: var(--md3-warning-container);
  border-color: transparent;
}

[data-theme="dark"] .md3-btn--warning:hover {
  background: var(--md3-warning-container-hover);
}

/* Suppress white ::before overlay in dark mode for filled variants */
[data-theme="dark"] .md3-btn--primary::before,
[data-theme="dark"] .md3-btn--danger::before,
[data-theme="dark"] .md3-btn--success::before,
[data-theme="dark"] .md3-btn--warning::before {
  background: transparent;
}

/* ===== Disabled ===== */
.md3-btn--disabled {
  opacity: 0.38;
  cursor: not-allowed;
  pointer-events: none;
}

/* ===== Loading ===== */
.md3-btn--loading {
  cursor: wait;
  pointer-events: none;
}
.md3-btn__spinner {
  display: flex;
  animation: md3-btn-spin 1s linear infinite;
}
@keyframes md3-btn-spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

/* ===== Block ===== */
.md3-btn--block {
  width: 100%;
  justify-content: center;
}
</style>
