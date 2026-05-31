import { createApp, ref } from 'vue'

interface ConfirmOptions {
  title?: string
  message: string
  confirmText?: string
  cancelText?: string
  type?: 'default' | 'danger' | 'warning'
}

let confirmApp: ReturnType<typeof createApp> | null = null
let confirmContainer: HTMLDivElement | null = null

function showConfirm(options: ConfirmOptions): Promise<boolean> {
  return new Promise((resolve) => {
    if (!confirmContainer) {
      confirmContainer = document.createElement('div')
      confirmContainer.className = 'md3-confirm-container'
      document.body.appendChild(confirmContainer)
    }
    const visible = ref(true)
    confirmApp = createApp({
      setup() {
        return {
          visible,
          title: options.title || 'Confirm',
          message: options.message,
          confirmText: options.confirmText || 'Confirm',
          cancelText: options.cancelText || 'Cancel',
          type: options.type || 'default',
          onConfirm() {
            visible.value = false
            setTimeout(() => {
              resolve(true)
              cleanup()
            }, 250)
          },
          onCancel() {
            visible.value = false
            setTimeout(() => {
              resolve(false)
              cleanup()
            }, 250)
          },
        }
      },
      template: `
        <Transition name="md3-confirm-mask" @after-leave="onCancel">
          <div v-if="visible" class="md3-confirm-mask" @click.self="onCancel">
            <Transition name="md3-confirm">
              <div v-if="visible" class="md3-confirm-dialog">
                <div class="md3-confirm-header">
                  <h3 class="md3-confirm-title">{{ title }}</h3>
                </div>
                <div class="md3-confirm-body">
                  <p>{{ message }}</p>
                </div>
                <div class="md3-confirm-footer">
                  <button
                    class="md3-confirm-btn md3-confirm-btn--cancel"
                    @click="onCancel"
                  >
                    {{ cancelText }}
                  </button>
                  <button
                    class="md3-confirm-btn md3-confirm-btn--confirm"
                    :class="{ 'md3-confirm-btn--danger': type === 'danger', 'md3-confirm-btn--warning': type === 'warning' }"
                    @click="onConfirm"
                  >
                    {{ confirmText }}
                  </button>
                </div>
              </div>
            </Transition>
          </div>
        </Transition>
      `,
    })
    confirmApp.mount(confirmContainer)
  })
}

function cleanup() {
  if (confirmApp) {
    confirmApp.unmount()
    confirmApp = null
  }
  if (confirmContainer && confirmContainer.parentNode) {
    confirmContainer.parentNode.removeChild(confirmContainer)
    confirmContainer = null
  }
}

export const Md3Confirm = {
  show(options: ConfirmOptions | string): Promise<boolean> {
    if (typeof options === 'string') {
      return showConfirm({ message: options })
    }
    return showConfirm(options)
  },
}

// Inject global styles
const styleEl = document.createElement('style')
styleEl.textContent = `
.md3-confirm-container {
  position: fixed;
  inset: 0;
  z-index: 3000;
}

.md3-confirm-mask {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 3000;
  padding: var(--md3-space-xl);
}

.md3-confirm-dialog {
  background: var(--md3-surface-container-high);
  border-radius: var(--md3-shape-xl);
  box-shadow: var(--md3-elevation-level3);
  overflow: hidden;
  width: 400px;
  max-width: calc(100vw - var(--md3-space-3xl));
}

.md3-confirm-header {
  padding: var(--md3-space-xl) var(--md3-space-xl) var(--md3-space-sm);
}

.md3-confirm-title {
  margin: 0;
  font: var(--md3-type-headline-small);
  color: var(--md3-on-surface);
}

.md3-confirm-body {
  padding: var(--md3-space-sm) var(--md3-space-xl) var(--md3-space-xl);
  color: var(--md3-on-surface-variant);
  font: var(--md3-type-body-medium);
}

.md3-confirm-footer {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: var(--md3-space-sm);
  padding: var(--md3-space-md) var(--md3-space-xl);
  border-top: 1px solid var(--md3-outline-variant);
}

.md3-confirm-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: var(--md3-space-sm) var(--md3-space-lg);
  border: none;
  border-radius: var(--md3-shape-full);
  font: var(--md3-type-label-large);
  cursor: pointer;
  transition: background-color var(--md3-motion-duration-short) var(--md3-motion-easing-standard);
  min-height: 40px;
}

.md3-confirm-btn--cancel {
  background: transparent;
  color: var(--md3-on-surface-variant);
}

.md3-confirm-btn--cancel:hover {
  background: var(--md3-surface-container-high);
}

.md3-confirm-btn--confirm {
  background: var(--md3-primary);
  color: var(--md3-on-primary);
}

.md3-confirm-btn--confirm:hover {
  box-shadow: var(--md3-elevation-level1);
}

.md3-confirm-btn--danger {
  background: var(--md3-error);
  color: var(--md3-on-error);
}

.md3-confirm-btn--danger:hover {
  box-shadow: 0 2px 8px rgba(179, 38, 30, 0.3);
}

.md3-confirm-btn--warning {
  background: var(--md3-tertiary);
  color: var(--md3-on-tertiary);
}

.md3-confirm-btn--warning:hover {
  box-shadow: 0 2px 8px rgba(100, 80, 0, 0.3);
}

/* ===== Transitions ===== */
.md3-confirm-mask-enter-active,
.md3-confirm-mask-leave-active {
  transition: opacity 250ms cubic-bezier(0.2, 0, 0, 1);
}

.md3-confirm-mask-enter-from,
.md3-confirm-mask-leave-to {
  opacity: 0;
}

.md3-confirm-enter-active {
  transition: all 350ms cubic-bezier(0.05, 0.7, 0.1, 1);
}

.md3-confirm-leave-active {
  transition: all 250ms cubic-bezier(0.3, 0, 0.8, 0.15);
}

.md3-confirm-enter-from,
.md3-confirm-leave-to {
  opacity: 0;
  transform: scale(0.9);
}
`
document.head.appendChild(styleEl)
