<template>
  <div
    class="md3-select-wrapper"
    :class="{
      'md3-select--disabled': disabled,
      'md3-select--open': isOpen,
    }"
    ref="wrapperRef"
  >
    <div
      class="md3-select-trigger"
      :class="[
        `md3-select--${variant}`,
        {
          'md3-select--error': error,
          'md3-select--focused': isOpen || isFocused,
        }
      ]"
      @click="toggle"
    >
      <span v-if="label" class="md3-select-label" :class="{ 'md3-select-label--floating': isOpen || hasSelected }">
        {{ label }}
      </span>

      <div class="md3-select-value">
        <template v-if="multiple">
          <span v-if="!hasSelected && !(label && !isOpen)" class="md3-select-placeholder">{{ placeholder }}</span>
          <template v-else>
            <span class="md3-select-chips">
              <span v-for="item in selectedItems" :key="item.value" class="md3-select-chip">
                {{ item.label }}
              </span>
            </span>
          </template>
        </template>
        <template v-else>
          <span v-if="!hasSelected && !(label && !isOpen)" class="md3-select-placeholder">{{ placeholder }}</span>
          <span v-else>{{ selectedItem?.label }}</span>
        </template>
      </div>

      <button
        v-if="clearable && hasSelected && !disabled"
        type="button"
        class="md3-select-clear"
        @click.stop="clear"
      >
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M18 6L6 18M6 6l12 12" />
        </svg>
      </button>

      <svg class="md3-select-arrow" :class="{ 'md3-select-arrow--open': isOpen }" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M6 9l6 6 6-6" />
      </svg>
    </div>

    <Teleport to="body">
      <Transition name="md3-select-dropdown">
        <div
          v-if="isOpen"
          class="md3-select-dropdown"
          :class="`md3-select--${variant}`"
          :style="dropdownStyle"
          @click.stop
        >
          <div v-if="searchable" class="md3-select-search">
            <input
              type="text"
              v-model="searchQuery"
              :placeholder="'Search...'"
              class="md3-select-search-input"
              @click.stop
            />
          </div>
          <div class="md3-select-options" ref="optionsRef">
            <slot v-if="!options.length">
            </slot>
            <template v-else>
              <div
                v-for="option in filteredOptions"
                :key="option.value"
                class="md3-select-option"
                :class="{
                  'md3-select-option--selected': isOptionSelected(option.value),
                  'md3-select-option--hover': hoveredIndex === option.value,
                }"
                @click="selectOption(option)"
                @mouseenter="hoveredIndex = option.value"
              >
                <span class="md3-select-option-label">{{ option.label }}</span>
                <svg v-if="isOptionSelected(option.value)" class="md3-select-option-check" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
                  <path d="M20 6L9 17l-5-5" />
                </svg>
              </div>
              <div v-if="filteredOptions.length === 0" class="md3-select-empty">
                No results found
              </div>
            </template>
          </div>
        </div>
      </Transition>
    </Teleport>

    <p v-if="error" class="md3-select-error">{{ error }}</p>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'

interface Option {
  label: string
  value: string | number
}

const props = withDefaults(defineProps<{
  modelValue?: string | number | (string | number)[]
  options?: Option[]
  label?: string
  placeholder?: string
  disabled?: boolean
  clearable?: boolean
  multiple?: boolean
  searchable?: boolean
  error?: string
  variant?: 'outlined' | 'filled'
}>(), {
  variant: 'outlined',
  disabled: false,
  clearable: false,
  multiple: false,
  searchable: false,
  placeholder: 'Select...',
  options: () => [],
})

const emit = defineEmits<{
  'update:modelValue': [value: string | number | (string | number)[]]
}>()

const isOpen = ref(false)
const isFocused = ref(false)
const searchQuery = ref('')
const wrapperRef = ref<HTMLElement>()
const optionsRef = ref<HTMLElement>()
const hoveredIndex = ref<string | number | null>(null)
const dropdownStyle = ref<Record<string, string>>({})

const hasSelected = computed(() => {
  if (props.multiple) {
    return Array.isArray(props.modelValue) && props.modelValue.length > 0
  }
  return props.modelValue !== undefined && props.modelValue !== '' && props.modelValue !== null
})

const selectedItems = computed((): Option[] => {
  if (!props.multiple || !Array.isArray(props.modelValue)) return []
  return props.options.filter(o => (props.modelValue as (string | number)[]).includes(o.value))
})

const selectedItem = computed((): Option | undefined => {
  if (props.multiple) return undefined
  const value = props.modelValue
  if (typeof value === 'string' || typeof value === 'number') {
    return props.options.find(o => o.value === value)
  }
  return undefined
})

const filteredOptions = computed((): Option[] => {
  if (!searchQuery.value) return props.options
  const q = searchQuery.value.toLowerCase()
  return props.options.filter(o => o.label.toLowerCase().includes(q))
})

function isOptionSelected(value: string | number): boolean {
  if (props.multiple) {
    return Array.isArray(props.modelValue) && props.modelValue.includes(value)
  }
  return props.modelValue === value
}

function toggle() {
  if (props.disabled) return
  isOpen.value = !isOpen.value
  if (isOpen.value) {
    searchQuery.value = ''
    updateDropdownPosition()
  }
}

function clear() {
  if (props.multiple) {
    emit('update:modelValue', [])
  } else {
    emit('update:modelValue', props.multiple ? [] : '')
  }
}

function selectOption(option: Option) {
  if (props.multiple) {
    const current = Array.isArray(props.modelValue) ? [...props.modelValue] : []
    const idx = current.indexOf(option.value)
    if (idx === -1) {
      current.push(option.value)
    } else {
      current.splice(idx, 1)
    }
    emit('update:modelValue', current)
  } else {
    emit('update:modelValue', option.value)
    isOpen.value = false
  }
}

function updateDropdownPosition() {
  if (!wrapperRef.value) return
  const rect = wrapperRef.value.getBoundingClientRect()
  dropdownStyle.value = {
    position: 'fixed',
    top: `${rect.bottom + 4}px`,
    left: `${rect.left}px`,
    width: `${rect.width}px`,
    zIndex: '2000',
  }
}

function handleClickOutside(e: MouseEvent) {
  if (wrapperRef.value && !wrapperRef.value.contains(e.target as Node)) {
    isOpen.value = false
  }
}

onMounted(() => {
  document.addEventListener('click', handleClickOutside)
  window.addEventListener('resize', updateDropdownPosition)
})

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
  window.removeEventListener('resize', updateDropdownPosition)
})
</script>

<style scoped>
.md3-select-wrapper {
  display: flex;
  flex-direction: column;
  gap: var(--md3-space-xs);
  width: 100%;
}

.md3-select-trigger {
  position: relative;
  display: flex;
  align-items: center;
  cursor: pointer;
  min-height: 48px;
  user-select: none;
  transition: border-color var(--md3-motion-duration-short) var(--md3-motion-easing-standard),
              background-color var(--md3-motion-duration-short) var(--md3-motion-easing-standard);
}

/* ===== Outlined ===== */
.md3-select--outlined.md3-select-trigger {
  border: 1px solid var(--md3-outline);
  border-radius: var(--md3-shape-xs);
  padding: 0 var(--md3-space-md);
}

.md3-select--outlined.md3-select--focused.md3-select-trigger {
  border-color: var(--md3-primary);
  box-shadow: inset 0 0 0 1px var(--md3-primary);
}

/* ===== Filled ===== */
.md3-select--filled.md3-select-trigger {
  border: none;
  border-bottom: 1px solid var(--md3-outline-variant);
  border-radius: var(--md3-shape-xs) var(--md3-shape-xs) 0 0;
  background: var(--md3-surface-container-highest);
  padding: 0 var(--md3-space-md);
}

.md3-select--filled.md3-select--focused.md3-select-trigger {
  border-bottom-color: var(--md3-primary);
  box-shadow: inset 0 -1px 0 0 var(--md3-primary);
}

/* ===== Error ===== */
.md3-select--error.md3-select-trigger {
  border-color: var(--md3-error);
}

/* ===== Label ===== */
.md3-select-label {
  position: absolute;
  left: var(--md3-space-md);
  top: 50%;
  transform: translateY(-50%);
  font: var(--md3-type-body-large);
  color: var(--md3-on-surface-variant);
  pointer-events: none;
  transition: all var(--md3-motion-duration-short) var(--md3-motion-easing-standard);
}

.md3-select-label--floating {
  top: 0;
  transform: translateY(-50%);
  font: var(--md3-type-body-small);
  color: var(--md3-primary);
}

/* ===== Value ===== */
.md3-select-value {
  flex: 1;
  font: var(--md3-type-body-large);
  color: var(--md3-on-surface);
  padding: var(--md3-space-md) 0;
}

.md3-select-placeholder {
  color: var(--md3-on-surface-variant);
  opacity: 0.7;
}

/* ===== Chips ===== */
.md3-select-chips {
  display: flex;
  flex-wrap: wrap;
  gap: var(--md3-space-xs);
}

.md3-select-chip {
  background: var(--md3-primary-container);
  color: var(--md3-on-primary-container);
  padding: 2px var(--md3-space-sm);
  border-radius: var(--md3-shape-full);
  font: var(--md3-type-body-small);
}

/* ===== Clear Button ===== */
.md3-select-clear {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border: none;
  background: transparent;
  cursor: pointer;
  color: var(--md3-on-surface-variant);
  border-radius: var(--md3-shape-full);
  transition: background-color var(--md3-motion-duration-short) var(--md3-motion-easing-standard);
}

.md3-select-clear:hover {
  background: var(--md3-surface-container-high);
}

/* ===== Arrow ===== */
.md3-select-arrow {
  flex-shrink: 0;
  margin-left: var(--md3-space-sm);
  color: var(--md3-on-surface-variant);
  transition: transform var(--md3-motion-duration-medium) var(--md3-motion-easing-standard);
}

.md3-select-arrow--open {
  transform: rotate(180deg);
}

/* ===== Dropdown ===== */
.md3-select-dropdown {
  border-radius: var(--md3-shape-xs);
  overflow: hidden;
  border: 1px solid var(--md3-outline-variant);
  backdrop-filter: var(--md3-glass-blur);
  -webkit-backdrop-filter: var(--md3-glass-blur);
  max-height: 280px;
}

.md3-select--outlined.md3-select-dropdown {
  background: var(--md3-surface-container);
  border: 1px solid var(--md3-outline-variant);
}

.md3-select--filled.md3-select-dropdown {
  background: var(--md3-surface-container-high);
}

/* ===== Search ===== */
.md3-select-search {
  padding: var(--md3-space-sm);
  border-bottom: 1px solid var(--md3-outline-variant);
}

.md3-select-search-input {
  width: 100%;
  border: none;
  outline: none;
  background: var(--md3-surface-container-highest);
  border-radius: var(--md3-shape-xs);
  padding: var(--md3-space-sm) var(--md3-space-md);
  font: var(--md3-type-body-medium);
  color: var(--md3-on-surface);
}

/* ===== Options ===== */
.md3-select-options {
  overflow-y: auto;
}

.md3-select-option {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--md3-space-md);
  cursor: pointer;
  transition: background-color var(--md3-motion-duration-short) var(--md3-motion-easing-standard);
}

.md3-select-option:hover {
  background: var(--md3-surface-container-high);
}

.md3-select-option--selected {
  background: var(--md3-primary-container);
  color: var(--md3-on-primary-container);
}

.md3-select-option-check {
  color: var(--md3-primary);
}

/* ===== Empty ===== */
.md3-select-empty {
  padding: var(--md3-space-lg);
  text-align: center;
  color: var(--md3-on-surface-variant);
  font: var(--md3-type-body-medium);
}

/* ===== Error ===== */
.md3-select-error {
  margin: 0;
  font: var(--md3-type-body-small);
  color: var(--md3-error);
  padding-left: var(--md3-space-md);
}

/* ===== Disabled ===== */
.md3-select--disabled {
  opacity: 0.38;
  pointer-events: none;
}

/* ===== Transition ===== */
.md3-select-dropdown-enter-active {
  transition: all var(--md3-motion-duration-medium) var(--md3-motion-easing-standard);
}

.md3-select-dropdown-leave-active {
  transition: all var(--md3-motion-duration-short) var(--md3-motion-easing-standard);
}

.md3-select-dropdown-enter-from,
.md3-select-dropdown-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}
</style>
