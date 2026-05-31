<template>
  <header class="md3-page-header">
    <div class="md3-page-header__start">
      <button
        v-if="showBack"
        class="md3-page-header__back"
        aria-label="返回"
        @click="emit('back')"
      >
        <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M12.5 15L7.5 10L12.5 5" />
        </svg>
      </button>
      <div class="md3-page-header__titles">
        <h1 class="md3-page-header__title">
          <slot name="title">{{ title }}</slot>
        </h1>
        <p v-if="$slots.subtitle || subtitle" class="md3-page-header__subtitle">
          <slot name="subtitle">{{ subtitle }}</slot>
        </p>
      </div>
    </div>
    <div v-if="$slots.actions" class="md3-page-header__actions">
      <slot name="actions" />
    </div>
  </header>
</template>

<script setup lang="ts">
withDefaults(defineProps<{
  title?: string
  subtitle?: string
  showBack?: boolean
}>(), {
  title: '',
  subtitle: '',
  showBack: false,
})

const emit = defineEmits<{
  back: []
}>()

defineSlots<{
  title?(props: {}): any
  subtitle?(props: {}): any
  actions?(props: {}): any
}>()
</script>

<style scoped>
.md3-page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--md3-space-xl);
  gap: var(--md3-space-lg);
  border-bottom: 1px solid var(--md3-outline-variant);
  background: var(--md3-surface);
}

.md3-page-header__start {
  display: flex;
  align-items: center;
  gap: var(--md3-space-md);
  min-width: 0;
}

.md3-page-header__back {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border: none;
  border-radius: var(--md3-shape-full);
  background: transparent;
  color: var(--md3-on-surface-variant);
  cursor: pointer;
  transition: all var(--md3-motion-duration-short) var(--md3-motion-easing-standard);
  flex-shrink: 0;
}

.md3-page-header__back:hover {
  background: var(--md3-surface-container-highest);
  color: var(--md3-on-surface);
}

.md3-page-header__back:active {
  transform: scale(0.95);
}

.md3-page-header__back:focus-visible {
  outline: 2px solid var(--md3-primary);
  outline-offset: 2px;
}

.md3-page-header__titles {
  min-width: 0;
}

.md3-page-header__title {
  font: var(--md3-type-headline-medium);
  color: var(--md3-on-surface);
  margin: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.md3-page-header__subtitle {
  font: var(--md3-type-body-medium);
  color: var(--md3-on-surface-variant);
  margin: var(--md3-space-xs) 0 0;
}

.md3-page-header__actions {
  display: flex;
  align-items: center;
  gap: var(--md3-space-sm);
  flex-shrink: 0;
}
</style>
