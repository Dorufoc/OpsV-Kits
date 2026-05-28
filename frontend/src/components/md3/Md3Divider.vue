<template>
  <component
    :is="orientation === 'horizontal' ? 'hr' : 'div'"
    class="md3-divider"
    :class="[`md3-divider--${orientation}`]"
  >
    <span v-if="$slots.default || label" class="md3-divider__label">
      <slot>{{ label }}</slot>
    </span>
  </component>
</template>

<script setup lang="ts">
withDefaults(defineProps<{
  orientation?: 'horizontal' | 'vertical'
  label?: string
}>(), {
  orientation: 'horizontal',
  label: '',
})

defineSlots<{
  default(props: {}): any
}>()
</script>

<style scoped>
.md3-divider {
  display: flex;
  align-items: center;
  justify-content: center;
  border: none;
  margin: 0;
}

.md3-divider--horizontal {
  width: 100%;
  height: 1px;
  background: var(--md3-outline-variant);
  margin: var(--md3-space-md) 0;
}

.md3-divider--horizontal .md3-divider__label {
  padding: 0 var(--md3-space-md);
  font: var(--md3-type-label-medium);
  color: var(--md3-on-surface-variant);
  background: var(--md3-surface);
  white-space: nowrap;
}

.md3-divider--vertical {
  width: 1px;
  height: 100%;
  background: var(--md3-outline-variant);
  margin: 0 var(--md3-space-sm);
}

.md3-divider--vertical .md3-divider__label {
  display: none;
}
</style>
