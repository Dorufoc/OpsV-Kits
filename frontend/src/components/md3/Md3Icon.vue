<script setup lang="ts">
import { computed } from 'vue'
import { getMdiIconPath, type IconName } from '@/utils/icon-map'

const props = withDefaults(defineProps<{
  name: IconName | string
  size?: number | string
  color?: string
  spin?: boolean
}>(), {
  size: 20,
  spin: false,
})

const iconPath = computed(() => getMdiIconPath(props.name))

const svgSize = computed(() => {
  if (typeof props.size === 'number') return `${props.size}px`
  return props.size
})

const svgColor = computed(() => props.color || 'currentColor')
</script>

<template>
  <svg
    class="md3-icon"
    :style="{ width: svgSize, height: svgSize, color: svgColor }"
    viewBox="0 0 24 24"
    xmlns="http://www.w3.org/2000/svg"
  >
    <path :d="iconPath" fill="currentColor" />
  </svg>
</template>

<style scoped>
.md3-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: all var(--md3-motion-duration-short) var(--md3-motion-easing-emphasized);
}

.md3-icon--spin {
  animation: md3-spin 1s linear infinite;
}

@keyframes md3-spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}
</style>
