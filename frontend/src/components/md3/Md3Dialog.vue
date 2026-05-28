<template>
  <Teleport to="body">
    <Transition name="md3-dialog-mask">
      <div
        v-if="visible"
        class="md3-dialog-mask"
        @click="handleMaskClick"
      >
        <Transition name="md3-dialog">
          <div
            v-if="visible"
            class="md3-dialog"
            :class="{
              'md3-dialog--fullscreen': fullscreen,
            }"
            :style="dialogStyle"
            @click.stop
            @keydown="onKeydown"
          >
            <div class="md3-dialog-header" v-if="title || $slots.header">
              <slot name="header">
                <h3 class="md3-dialog-title">{{ title }}</h3>
              </slot>
              <button
                v-if="closable"
                type="button"
                class="md3-dialog-close"
                @click="close"
              >
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M18 6L6 18M6 6l12 12" />
                </svg>
              </button>
            </div>
            <div class="md3-dialog-body">
              <slot />
            </div>
            <div class="md3-dialog-footer" v-if="$slots.footer">
              <slot name="footer" />
            </div>
          </div>
        </Transition>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { computed, watch } from 'vue'

const props = withDefaults(defineProps<{
  visible?: boolean
  title?: string
  width?: string
  fullscreen?: boolean
  closable?: boolean
  closeOnMaskClick?: boolean
  closeOnEsc?: boolean
}>(), {
  visible: false,
  closable: true,
  closeOnMaskClick: true,
  closeOnEsc: true,
})

const emit = defineEmits<{
  'update:visible': [value: boolean]
  'close': []
}>()

const dialogStyle = computed(() => {
  if (props.fullscreen) return {}
  return {
    width: props.width || '480px',
    maxWidth: 'calc(100vw - 48px)',
  }
})

function close() {
  emit('update:visible', false)
  emit('close')
}

function handleEsc() {
  if (props.closeOnEsc) {
    close()
  }
}

function onKeydown(event: KeyboardEvent) {
  if (event.key === 'Escape' && props.closeOnEsc) {
    handleEsc()
  }
}

function handleMaskClick() {
  if (props.closeOnMaskClick) {
    close()
  }
}

function handleBodyKeydown(e: KeyboardEvent) {
  if (e.key === 'Escape' && props.visible && props.closeOnEsc) {
    close()
  }
}

watch(() => props.visible, (val) => {
  if (val) {
    document.body.style.overflow = 'hidden'
    document.addEventListener('keydown', handleBodyKeydown)
  } else {
    document.body.style.overflow = ''
    document.removeEventListener('keydown', handleBodyKeydown)
  }
}, { immediate: true })
</script>

<style scoped>
.md3-dialog-mask {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2000;
  padding: var(--md3-space-lg);
}

.md3-dialog {
  background: var(--md3-surface-container-high);
  border-radius: var(--md3-shape-xl);
  box-shadow: var(--md3-elevation-level3);
  overflow: hidden;
  display: flex;
  flex-direction: column;
  max-height: calc(100vh - 96px);
}

.md3-dialog--fullscreen {
  width: calc(100vw - 48px);
  height: calc(100vh - 96px);
  max-width: 1200px;
  max-height: calc(100vh - 96px);
  border-radius: var(--md3-shape-xl);
}

/* ===== Header ===== */
.md3-dialog-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--md3-space-lg) var(--md3-space-xl) var(--md3-space-sm);
  border-bottom: 1px solid var(--md3-outline-variant);
}

.md3-dialog-title {
  margin: 0;
  font-size: 1.25rem;
  font-weight: 600;
  color: var(--md3-on-surface);
  line-height: 1.75rem;
}

/* ===== Close Button ===== */
.md3-dialog-close {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border: none;
  background: transparent;
  color: var(--md3-on-surface-variant);
  cursor: pointer;
  border-radius: var(--md3-shape-full);
  transition: background-color var(--md3-motion-duration-short) var(--md3-motion-easing-standard);
}

.md3-dialog-close:hover {
  background: var(--md3-surface-container-highest);
}

/* ===== Body ===== */
.md3-dialog-body {
  padding: var(--md3-space-md) var(--md3-space-xl) var(--md3-space-xl);
  overflow-y: auto;
  flex: 1;
  color: var(--md3-on-surface-variant);
  font-size: 0.875rem;
  line-height: 1.5rem;
}

/* ===== Footer ===== */
.md3-dialog-footer {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: var(--md3-space-sm);
  padding: var(--md3-space-md) var(--md3-space-xl) var(--md3-space-lg);
  border-top: 1px solid var(--md3-outline-variant);
}

/* ===== Transitions ===== */
.md3-dialog-mask-enter-active,
.md3-dialog-mask-leave-active {
  transition: opacity var(--md3-motion-duration-medium) var(--md3-motion-easing-standard);
}

.md3-dialog-mask-enter-from,
.md3-dialog-mask-leave-to {
  opacity: 0;
}

.md3-dialog-enter-active {
  transition: all var(--md3-motion-duration-long) var(--md3-motion-easing-emphasized-decelerate);
}

.md3-dialog-leave-active {
  transition: all var(--md3-motion-duration-medium) var(--md3-motion-easing-emphasized-accelerate);
}

.md3-dialog-enter-from,
.md3-dialog-leave-to {
  opacity: 0;
  transform: scale(0.9);
}
</style>
