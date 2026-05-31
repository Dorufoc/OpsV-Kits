<template>
  <label
    class="md3-radio"
    :class="{
      'md3-radio--checked': isChecked,
      'md3-radio--disabled': disabled,
    }"
  >
    <input
      type="radio"
      :value="value"
      :checked="isChecked"
      :disabled="disabled"
      class="md3-radio-input"
      @change="onChange"
    />
    <span class="md3-radio-circle">
      <span class="md3-radio-dot" />
    </span>
    <span v-if="label" class="md3-radio-label">{{ label }}</span>
  </label>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(defineProps<{
  modelValue?: string | number
  disabled?: boolean
  label?: string
  value?: string | number
}>(), {
  modelValue: '',
  disabled: false,
})

const emit = defineEmits<{
  'update:modelValue': [value: string | number]
  'change': [value: string | number]
}>()

const isChecked = computed(() => props.modelValue === props.value)

function onChange() {
  if (props.value !== undefined) {
    emit('update:modelValue', props.value)
    emit('change', props.value)
  }
}
</script>

<style scoped>
.md3-radio {
  display: inline-flex;
  align-items: center;
  gap: var(--md3-space-sm);
  cursor: pointer;
  user-select: none;
  -webkit-tap-highlight-color: transparent;
}

.md3-radio-input {
  position: absolute;
  opacity: 0;
  pointer-events: none;
}

/* ===== Circle ===== */
.md3-radio-circle {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  border: 2px solid var(--md3-on-surface-variant);
  border-radius: var(--md3-shape-full);
  transition: border-color var(--md3-motion-duration-short) var(--md3-motion-easing-standard);
  flex-shrink: 0;
}

.md3-radio--checked .md3-radio-circle {
  border-color: var(--md3-primary);
}

/* ===== Dot ===== */
.md3-radio-dot {
  width: 10px;
  height: 10px;
  border-radius: var(--md3-shape-full);
  background: transparent;
  transform: scale(0);
  transition: transform var(--md3-motion-duration-short) var(--md3-motion-easing-emphasized),
              background-color var(--md3-motion-duration-short) var(--md3-motion-easing-standard);
}

.md3-radio--checked .md3-radio-dot {
  background: var(--md3-primary);
  transform: scale(1);
}

/* ===== Label ===== */
.md3-radio-label {
  font: var(--md3-type-body-medium);
  color: var(--md3-on-surface);
}

/* ===== Disabled ===== */
.md3-radio--disabled {
  cursor: not-allowed;
  opacity: 0.38;
  pointer-events: none;
}

/* ===== Hover ===== */
.md3-radio:not(.md3-radio--disabled):hover .md3-radio-circle {
  border-color: var(--md3-primary);
}

.md3-radio:not(.md3-radio--disabled):hover.md3-radio--checked .md3-radio-dot {
  background: var(--md3-primary);
}

/* ===== Focus ===== */
.md3-radio-input:focus-visible + .md3-radio-circle {
  outline: 2px solid var(--md3-primary);
  outline-offset: 2px;
}
</style>
