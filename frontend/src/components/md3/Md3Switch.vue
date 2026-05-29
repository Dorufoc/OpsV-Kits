<template>
  <button
    type="button"
    role="switch"
    :aria-checked="modelValue"
    :disabled="disabled"
    class="md3-switch"
    :class="{
      'md3-switch--checked': modelValue,
      'md3-switch--disabled': disabled,
    }"
    @click="toggle"
  >
    <span class="md3-switch-track">
      <span v-if="onText || offText" class="md3-switch-track-text">
        {{ modelValue ? onText : offText }}
      </span>
    </span>
    <span class="md3-switch-thumb" />
  </button>
</template>

<script setup lang="ts">
const props = withDefaults(defineProps<{
  modelValue?: boolean
  disabled?: boolean
  onText?: string
  offText?: string
}>(), {
  modelValue: false,
  disabled: false,
})

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
}>()

function toggle() {
  if (!props.disabled) {
    emit('update:modelValue', !props.modelValue)
  }
}
</script>

<style scoped>
.md3-switch {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 52px;
  height: 32px;
  border: none;
  background: transparent;
  cursor: pointer;
  padding: 0;
  -webkit-tap-highlight-color: transparent;
  outline: none;
}

.md3-switch:focus-visible .md3-switch-track {
  outline: 2px solid var(--md3-primary);
  outline-offset: 2px;
}

/* ===== Track ===== */
.md3-switch-track {
  position: absolute;
  inset: 0;
  border-radius: var(--md3-shape-full);
  background: var(--md3-surface-container-highest);
  border: 2px solid var(--md3-outline);
  transition: background-color var(--md3-motion-duration-medium) var(--md3-motion-easing-standard),
              border-color var(--md3-motion-duration-medium) var(--md3-motion-easing-standard);
  display: flex;
  align-items: center;
  justify-content: center;
}

.md3-switch--checked .md3-switch-track {
  background: var(--md3-primary);
  border-color: var(--md3-primary);
}

/* ===== Track Text ===== */
.md3-switch-track-text {
  font-size: 0.625rem;
  font-weight: 500;
  color: var(--md3-on-surface-variant);
  user-select: none;
  transition: color var(--md3-motion-duration-medium) var(--md3-motion-easing-standard);
}

.md3-switch--checked .md3-switch-track-text {
  color: var(--md3-on-primary);
}

/* ===== Thumb ===== */
.md3-switch-thumb {
  position: absolute;
  left: 8px;
  top: 50%;
  transform: translateY(-50%);
  width: 18px;
  height: 18px;
  border-radius: var(--md3-shape-full);
  background: var(--md3-outline);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.2);
  transition: left var(--md3-motion-duration-medium) var(--md3-motion-easing-emphasized),
              background-color var(--md3-motion-duration-medium) var(--md3-motion-easing-standard);
}

.md3-switch--checked .md3-switch-thumb {
  left: 26px;
  background: var(--md3-on-primary);
}

/* ===== Disabled ===== */
.md3-switch--disabled {
  cursor: not-allowed;
  opacity: 0.38;
  pointer-events: none;
}

/* ===== Hover ===== */
.md3-switch:not(.md3-switch--disabled):hover .md3-switch-thumb {
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.25);
}
</style>
