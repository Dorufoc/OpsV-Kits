<template>
  <div class="md3-collapse">
    <button
      class="md3-collapse__header"
      :aria-expanded="modelValue"
      @click="toggle"
    >
      <slot name="title">
        <span class="md3-collapse__title">{{ title }}</span>
      </slot>
      <svg
        class="md3-collapse__icon"
        :class="{ 'md3-collapse__icon--open': modelValue }"
        width="20"
        height="20"
        viewBox="0 0 20 20"
        fill="none"
        stroke="currentColor"
        stroke-width="2"
        stroke-linecap="round"
      >
        <path d="M5 7.5L10 12.5L15 7.5" />
      </svg>
    </button>
    <div
      ref="contentRef"
      class="md3-collapse__body"
      :class="{ 'md3-collapse__body--open': modelValue }"
    >
      <div class="md3-collapse__inner">
        <slot />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, nextTick, onMounted } from 'vue'

const props = withDefaults(defineProps<{
  modelValue?: boolean
  title?: string
}>(), {
  modelValue: false,
  title: '',
})

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
}>()

const contentRef = ref<HTMLElement | null>(null)

function toggle() {
  emit('update:modelValue', !props.modelValue)
}

watch(() => props.modelValue, async (open) => {
  if (!contentRef.value) return
  if (open) {
    await nextTick()
    contentRef.value.style.height = `${contentRef.value.scrollHeight}px`
  } else {
    contentRef.value.style.height = `${contentRef.value.scrollHeight}px`
    await nextTick()
    contentRef.value.style.height = '0'
  }
}, { immediate: false })

onMounted(async () => {
  if (props.modelValue && contentRef.value) {
    await nextTick()
    contentRef.value.style.height = `${contentRef.value.scrollHeight}px`
  }
})
</script>

<style scoped>
.md3-collapse {
  border-radius: var(--md3-shape-md);
  overflow: hidden;
  background: var(--md3-surface-container-low);
  border: 1px solid var(--md3-outline-variant);
}

.md3-collapse__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  padding: var(--md3-space-lg);
  border: none;
  background: transparent;
  cursor: pointer;
  transition: background var(--md3-motion-duration-short) var(--md3-motion-easing-standard);
}

.md3-collapse__header:hover {
  background: var(--md3-surface-container);
}

.md3-collapse__header:active {
  background: var(--md3-surface-container-high);
}

.md3-collapse__header:focus-visible {
  outline: 2px solid var(--md3-primary);
  outline-offset: -2px;
}

.md3-collapse__title {
  font: var(--md3-type-title-large);
  color: var(--md3-on-surface);
}

.md3-collapse__icon {
  color: var(--md3-on-surface-variant);
  transition: transform var(--md3-motion-duration-medium) var(--md3-motion-easing-standard);
}

.md3-collapse__icon--open {
  transform: rotate(180deg);
}

.md3-collapse__body {
  height: 0;
  overflow: hidden;
  transition: height var(--md3-motion-duration-long) var(--md3-motion-easing-emphasized);
}

.md3-collapse__inner {
  padding: 0 var(--md3-space-lg) var(--md3-space-lg);
}

/* ===== Dark Mode ===== */
[data-theme="dark"] .md3-collapse {
  border-color: var(--md3-outline-variant);
}
</style>
