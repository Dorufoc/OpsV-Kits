<template>
  <label
    class="md3-checkbox"
    :class="{
      'md3-checkbox--checked': isChecked,
      'md3-checkbox--disabled': disabled,
      'md3-checkbox--indeterminate': indeterminate,
    }"
  >
    <input
      type="checkbox"
      :checked="isChecked"
      :disabled="disabled"
      class="md3-checkbox-input"
      @change="onChange"
    />
    <span class="md3-checkbox-box">
      <svg v-if="indeterminate" class="md3-checkbox-icon" width="18" height="18" viewBox="0 0 24 24">
        <path d="M19 13H5v-2h14v2z" fill="currentColor" />
      </svg>
      <svg v-else-if="isChecked" class="md3-checkbox-icon" width="18" height="18" viewBox="0 0 24 24">
        <path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41L9 16.17z" fill="currentColor" />
      </svg>
    </span>
    <span v-if="label" class="md3-checkbox-label">{{ label }}</span>
  </label>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(defineProps<{
  modelValue?: boolean | (string | number)[]
  disabled?: boolean
  indeterminate?: boolean
  label?: string
  value?: string | number
}>(), {
  modelValue: false,
  disabled: false,
  indeterminate: false,
})

const emit = defineEmits<{
  'update:modelValue': [value: boolean | (string | number)[]]
  'change': [value: boolean | (string | number)[]]
}>()

const isChecked = computed(() => {
  if (Array.isArray(props.modelValue)) {
    return props.value !== undefined && props.modelValue.includes(props.value)
  }
  return !!props.modelValue
})

function onChange(event: Event) {
  const target = event.target as HTMLInputElement
  const checked = target.checked
  if (Array.isArray(props.modelValue) && props.value !== undefined) {
    const newValue = [...props.modelValue]
    if (checked) {
      newValue.push(props.value)
    } else {
      const idx = newValue.indexOf(props.value)
      if (idx !== -1) newValue.splice(idx, 1)
    }
    emit('update:modelValue', newValue)
    emit('change', newValue)
  } else {
    emit('update:modelValue', checked)
    emit('change', checked)
  }
}
</script>

<style scoped>
.md3-checkbox {
  display: inline-flex;
  align-items: center;
  gap: var(--md3-space-sm);
  cursor: pointer;
  user-select: none;
  -webkit-tap-highlight-color: transparent;
}

.md3-checkbox-input {
  position: absolute;
  opacity: 0;
  pointer-events: none;
}

/* ===== Checkbox Box ===== */
.md3-checkbox-box {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 18px;
  height: 18px;
  border: 2px solid var(--md3-on-surface-variant);
  border-radius: var(--md3-shape-xs);
  transition: background-color var(--md3-motion-duration-short) var(--md3-motion-easing-standard),
              border-color var(--md3-motion-duration-short) var(--md3-motion-easing-standard);
  flex-shrink: 0;
}

.md3-checkbox--checked .md3-checkbox-box {
  background: var(--md3-primary);
  border-color: var(--md3-primary);
}

/* ===== Icon ===== */
.md3-checkbox-icon {
  color: var(--md3-on-primary);
  transition: transform var(--md3-motion-duration-short) var(--md3-motion-easing-emphasized);
}

/* ===== Label ===== */
.md3-checkbox-label {
  font-size: 0.875rem;
  line-height: 1.25rem;
  color: var(--md3-on-surface);
}

/* ===== Disabled ===== */
.md3-checkbox--disabled {
  cursor: not-allowed;
  opacity: 0.38;
  pointer-events: none;
}

/* ===== Hover ===== */
.md3-checkbox:not(.md3-checkbox--disabled):hover .md3-checkbox-box {
  background: var(--md3-primary-container);
  border-color: var(--md3-primary);
}

.md3-checkbox:not(.md3-checkbox--disabled):hover.md3-checkbox--checked .md3-checkbox-box {
  background: var(--md3-primary-container-hover);
}

/* ===== Focus ===== */
.md3-checkbox-input:focus-visible + .md3-checkbox-box {
  outline: 2px solid var(--md3-primary);
  outline-offset: 2px;
}

/* ===== Indeterminate ===== */
.md3-checkbox--indeterminate .md3-checkbox-box {
  background: var(--md3-primary);
  border-color: var(--md3-primary);
}
</style>
