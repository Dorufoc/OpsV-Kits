<template>
  <div
    class="md3-tooltip"
    :class="[`md3-tooltip--${placement}`]"
    @mouseenter="handleMouseEnter"
    @mouseleave="handleMouseLeave"
    @click="handleClick"
  >
    <div ref="triggerRef" class="md3-tooltip__trigger">
      <slot name="trigger" />
    </div>
    <Transition name="md3-tooltip">
      <div
        v-if="visible"
        ref="tooltipRef"
        class="md3-tooltip__content"
        role="tooltip"
      >
        <slot />
      </div>
    </Transition>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount } from 'vue'

type TooltipPlacement = 'top' | 'bottom' | 'left' | 'right'
type TooltipTrigger = 'hover' | 'click'

const props = withDefaults(defineProps<{
  trigger?: TooltipTrigger
  placement?: TooltipPlacement
}>(), {
  trigger: 'hover',
  placement: 'top',
})

const visible = ref(false)
const triggerRef = ref<HTMLElement | null>(null)
const tooltipRef = ref<HTMLElement | null>(null)

function handleMouseEnter() {
  if (props.trigger === 'hover') {
    visible.value = true
  }
}

function handleMouseLeave() {
  if (props.trigger === 'hover') {
    visible.value = false
  }
}

function handleClick(_e: MouseEvent) {
  if (props.trigger === 'click') {
    visible.value = !visible.value
  }
}

function handleClickOutside(e: MouseEvent) {
  if (props.trigger === 'click' && visible.value && tooltipRef.value && !tooltipRef.value.contains(e.target as Node)) {
    visible.value = false
  }
}

onMounted(() => {
  if (props.trigger === 'click') {
    document.addEventListener('click', handleClickOutside)
  }
})

onBeforeUnmount(() => {
  document.removeEventListener('click', handleClickOutside)
})

defineSlots<{
  default(props: {}): any
  trigger?(props: {}): any
}>()
</script>

<style scoped>
.md3-tooltip {
  position: relative;
  display: inline-flex;
}

.md3-tooltip__trigger {
  display: inline-flex;
}

.md3-tooltip__content {
  position: absolute;
  z-index: 1000;
  padding: var(--md3-space-sm) var(--md3-space-md);
  background: var(--md3-inverse-surface);
  color: var(--md3-inverse-on-surface);
  font: var(--md3-type-label-small);
  border-radius: var(--md3-shape-xs);
  white-space: nowrap;
  border: 1px solid var(--md3-outline-variant);
}

/* ===== Placement ===== */
.md3-tooltip--top .md3-tooltip__content {
  bottom: calc(100% + var(--md3-space-sm));
  left: 50%;
  transform: translateX(-50%);
}

.md3-tooltip--bottom .md3-tooltip__content {
  top: calc(100% + var(--md3-space-sm));
  left: 50%;
  transform: translateX(-50%);
}

.md3-tooltip--left .md3-tooltip__content {
  right: calc(100% + var(--md3-space-sm));
  top: 50%;
  transform: translateY(-50%);
}

.md3-tooltip--right .md3-tooltip__content {
  left: calc(100% + var(--md3-space-sm));
  top: 50%;
  transform: translateY(-50%);
}

/* ===== Transition ===== */
.md3-tooltip-enter-active {
  transition: all var(--md3-motion-duration-short) var(--md3-motion-easing-emphasized-decelerate);
}

.md3-tooltip-leave-active {
  transition: all var(--md3-motion-duration-short) var(--md3-motion-easing-emphasized-accelerate);
}

.md3-tooltip-enter-from,
.md3-tooltip-leave-to {
  opacity: 0;
  transform: translateY(4px) scale(0.95);
}

.md3-tooltip--left .md3-tooltip-enter-from,
.md3-tooltip--left .md3-tooltip-leave-to {
  transform: translateX(4px) scale(0.95);
}

.md3-tooltip--right .md3-tooltip-enter-from,
.md3-tooltip--right .md3-tooltip-leave-to {
  transform: translateX(-4px) scale(0.95);
}
</style>
