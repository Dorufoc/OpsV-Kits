<template>
  <div class="md3-empty">
    <div class="md3-empty__image">
      <slot name="image">
        <svg width="120" height="120" viewBox="0 0 120 120" fill="none">
          <circle cx="60" cy="60" r="48" stroke="currentColor" stroke-width="2" stroke-dasharray="4 4" />
          <path d="M40 60L55 75L80 45" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" />
        </svg>
      </slot>
    </div>
    <div v-if="$slots.title || title" class="md3-empty__title">
      <slot name="title">{{ title }}</slot>
    </div>
    <div v-if="$slots.description || description" class="md3-empty__description">
      <slot name="description">{{ description }}</slot>
    </div>
    <div v-if="$slots.action" class="md3-empty__action">
      <slot name="action" />
    </div>
  </div>
</template>

<script setup lang="ts">
withDefaults(defineProps<{
  title?: string
  description?: string
}>(), {
  title: '暂无数据',
  description: '',
})

defineSlots<{
  image?(props: {}): any
  title?(props: {}): any
  description?(props: {}): any
  action?(props: {}): any
}>()
</script>

<style scoped>
.md3-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--md3-space-3xl) var(--md3-space-xl);
  text-align: center;
}

.md3-empty__image {
  color: var(--md3-outline-variant);
  margin-bottom: var(--md3-space-lg);
}

.md3-empty__title {
  font: var(--md3-type-title-medium);
  color: var(--md3-on-surface);
  margin-bottom: var(--md3-space-sm);
}

.md3-empty__description {
  font: var(--md3-type-body-medium);
  color: var(--md3-on-surface-variant);
  max-width: 320px;
  margin-bottom: var(--md3-space-lg);
}

.md3-empty__action {
  display: flex;
  gap: var(--md3-space-sm);
}

[data-theme="dark"] .md3-empty__image {
  color: var(--md3-outline);
}
</style>
