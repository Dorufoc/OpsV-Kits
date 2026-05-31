<template>
  <div
    class="md3-input-wrapper"
    :class="[
      `md3-input--${variant}`,
      {
        'md3-input--disabled': disabled,
        'md3-input--readonly': readonly,
        'md3-input--error': error,
        'md3-input--focused': isFocused,
        'md3-input--has-value': !!modelValue,
        'md3-input--no-label': !label,
      }
    ]"
  >
    <div class="md3-input-container">
      <label
        v-if="label"
        class="md3-input-label"
        :class="{ 'md3-input-label--floating': isFocused || modelValue }"
      >
        <span class="md3-input-label-text">{{ label }}</span>
      </label>
      <span v-if="$slots.prefix" class="md3-input-prefix">
        <slot name="prefix" />
      </span>
      <input
        :type="computedType"
        :value="modelValue"
        :placeholder="computedPlaceholder"
        :disabled="disabled"
        :readonly="readonly"
        :maxlength="maxlength"
        :minlength="minlength"
        :min="min"
        :max="max"
        :step="step"
        class="md3-input"
        @input="onInput"
        @focus="isFocused = true"
        @blur="isFocused = false"
      />
      <span v-if="$slots.suffix" class="md3-input-suffix">
        <slot name="suffix" />
      </span>
    </div>
    <p v-if="error || $slots.error" class="md3-input-error">
      <slot name="error">{{ error }}</slot>
    </p>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'

type InputVariant = 'outlined' | 'filled'
type InputType = 'text' | 'password' | 'number' | 'email' | 'tel' | 'url' | 'search'

const props = withDefaults(defineProps<{
  modelValue?: string | number
  label?: string
  placeholder?: string
  disabled?: boolean
  readonly?: boolean
  error?: string
  variant?: InputVariant
  type?: InputType
  maxlength?: number
  minlength?: number
  min?: number | string
  max?: number | string
  step?: number | string
}>(), {
  variant: 'outlined',
  type: 'text',
  disabled: false,
  readonly: false,
})

const emit = defineEmits<{
  'update:modelValue': [value: string | number]
}>()

const isFocused = ref(false)

const computedType = computed(() => props.type)

const computedPlaceholder = computed(() => {
  if (props.label && (isFocused.value || props.modelValue)) {
    return props.placeholder || ''
  }
  return props.placeholder || ''
})

function onInput(event: Event) {
  const target = event.target as HTMLInputElement
  let value: string | number = target.value
  if (props.type === 'number') {
    value = target.value === '' ? '' : Number(target.value)
  }
  emit('update:modelValue', value)
}
</script>

<style scoped>
.md3-input-wrapper {
  display: flex;
  flex-direction: column;
  gap: var(--md3-space-xs);
  width: 100%;
}

.md3-input-container {
  position: relative;
  display: flex;
  align-items: center;
}

.md3-input {
  width: 100%;
  border: none;
  outline: none;
  font: var(--md3-type-body-large);
  color: var(--md3-on-surface);
  background: transparent;
  padding: var(--md3-space-md);
}

.md3-input::placeholder {
  color: var(--md3-on-surface-variant);
  opacity: 0.7;
}

/* ===== Outlined Variant ===== */
.md3-input--outlined .md3-input-container {
  border: 1px solid var(--md3-outline);
  border-radius: var(--md3-shape-xs);
  background: transparent;
  transition: border-color var(--md3-motion-duration-short) var(--md3-motion-easing-standard),
              box-shadow var(--md3-motion-duration-short) var(--md3-motion-easing-standard);
}

.md3-input--outlined.md3-input--focused .md3-input-container {
  border-color: var(--md3-primary);
  box-shadow: inset 0 0 0 1px var(--md3-primary);
}

.md3-input--outlined.md3-input--error .md3-input-container {
  border-color: var(--md3-error);
}

.md3-input--outlined.md3-input--focused.md3-input--error .md3-input-container {
  border-color: var(--md3-error);
  box-shadow: inset 0 0 0 1px var(--md3-error);
}

/* ===== Filled Variant ===== */
.md3-input--filled .md3-input-container {
  border: none;
  border-bottom: 1px solid var(--md3-outline-variant);
  border-radius: var(--md3-shape-xs) var(--md3-shape-xs) 0 0;
  background: var(--md3-surface-container-highest);
  transition: background-color var(--md3-motion-duration-short) var(--md3-motion-easing-standard),
              border-color var(--md3-motion-duration-short) var(--md3-motion-easing-standard),
              box-shadow var(--md3-motion-duration-short) var(--md3-motion-easing-standard);
}

.md3-input--filled.md3-input--focused .md3-input-container {
  border-bottom-color: var(--md3-primary);
  box-shadow: inset 0 -1px 0 0 var(--md3-primary);
}

.md3-input--filled.md3-input--error .md3-input-container {
  border-bottom-color: var(--md3-error);
}

/* ===== Label ===== */
.md3-input-label {
  position: absolute;
  left: var(--md3-space-md);
  top: 50%;
  transform: translateY(-50%);
  font: var(--md3-type-body-large);
  color: var(--md3-on-surface-variant);
  pointer-events: none;
  transition: all var(--md3-motion-duration-short) var(--md3-motion-easing-standard);
  z-index: 1;
  padding: 0 var(--md3-space-xs);
  margin-left: calc(-1 * var(--md3-space-xs));
}

.md3-input-label-text {
  position: relative;
  z-index: 2;
}

.md3-input-label--floating {
  top: 0;
  transform: translateY(-50%);
  font: var(--md3-type-body-small);
  color: var(--md3-primary);
}

.md3-input--error .md3-input-label--floating {
  color: var(--md3-error);
}

/* Outlined variant label gap effect */
.md3-input--outlined .md3-input-label--floating::before {
  content: '';
  position: absolute;
  left: calc(-1.5 * var(--md3-space-xs));
  right: calc(-1.5 * var(--md3-space-xs));
  top: 50%;
  height: 2px;
  transform: translateY(-50%);
  background: inherit;
  z-index: -1;
}

.md3-input--outlined .md3-input-label--floating {
  background: inherit;
}

/* ===== Prefix/Suffix ===== */
.md3-input-prefix,
.md3-input-suffix {
  display: flex;
  align-items: center;
  color: var(--md3-on-surface-variant);
  flex-shrink: 0;
}

.md3-input-prefix {
  padding-left: var(--md3-space-sm);
}

.md3-input-suffix {
  padding-right: var(--md3-space-sm);
}

.md3-input-prefix + .md3-input {
  padding-left: var(--md3-space-sm);
}

/* ===== Error ===== */
.md3-input-error {
  margin: 0;
  font: var(--md3-type-body-small);
  color: var(--md3-error);
  padding-left: var(--md3-space-md);
}

/* ===== Disabled/Readonly ===== */
.md3-input--disabled {
  opacity: 0.38;
  pointer-events: none;
}

.md3-input--readonly .md3-input-container {
  background: var(--md3-surface-container);
  cursor: default;
}

/* ===== Dark Mode ===== */
[data-theme="dark"] .md3-input--filled .md3-input-container {
  background: var(--md3-surface-container-highest);
}

[data-theme="dark"] .md3-input--readonly .md3-input-container {
  background: var(--md3-surface-container-high);
}

[data-theme="dark"] .md3-input--outlined .md3-input-label--floating::before {
  background: var(--md3-surface);
}
</style>
