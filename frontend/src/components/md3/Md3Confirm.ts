import { createApp, ref } from 'vue'

interface ConfirmOptions {
  title?: string
  message: string
  confirmText?: string
  cancelText?: string
  type?: 'default' | 'danger'
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
                    :class="{ 'md3-confirm-btn--danger': type === 'danger' }"
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
  padding: 16px;
}

.md3-confirm-dialog {
  background: var(--md3-surface-container-high);
  border-radius: var(--md3-shape-xl);
  box-shadow: var(--md3-elevation-level3);
  overflow: hidden;
  width: 400px;
  max-width: calc(100vw - 48px);
}

.md3-confirm-header {
  padding: 24px 24px 8px;
}

.md3-confirm-title {
  margin: 0;
  font-size: 1.25rem;
  font-weight: 600;
  color: var(--md3-on-surface);
}

.md3-confirm-body {
  padding: 8px 24px 24px;
  color: var(--md3-on-surface-variant);
  font-size: 0.875rem;
  line-height: 1.5rem;
}

.md3-confirm-footer {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
  padding: 16px 24px;
  border-top: 1px solid var(--md3-outline-variant);
}

.md3-confirm-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 8px 16px;
  border: none;
  border-radius: var(--md3-shape-full);
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  transition: background-color 150ms cubic-bezier(0.2, 0, 0, 1);
  min-height: 36px;
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
