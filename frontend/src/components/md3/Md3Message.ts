import { createApp, h, type VNode } from 'vue'

interface MessageInstance {
  id: string
  message: string
  type: MessageType
  duration: number
}

type MessageType = 'success' | 'error' | 'warning' | 'info'

let messageContainer: HTMLDivElement | null = null
let messageInstances: MessageInstance[] = []
let instanceId = 0

function ensureContainer() {
  if (!messageContainer) {
    messageContainer = document.createElement('div')
    messageContainer.className = 'md3-message-container'
    document.body.appendChild(messageContainer)
  }
}

function createMessage(type: MessageType, message: string, duration = 3000) {
  ensureContainer()
  const id = `md3-msg-${++instanceId}`
  const instance: MessageInstance = { id, message, type, duration }
  messageInstances.push(instance)
  renderMessages()
  if (duration > 0) {
    setTimeout(() => removeMessage(id), duration)
  }
  return id
}

function removeMessage(id: string) {
  const idx = messageInstances.findIndex(m => m.id === id)
  if (idx !== -1) {
    messageInstances.splice(idx, 1)
    renderMessages()
  }
}

function renderMessages() {
  if (!messageContainer) return
  const app = createApp({
    render() {
      return messageInstances.map(m =>
        h('div', {
          class: `md3-message md3-message--${m.type}`,
          key: m.id,
          role: 'alert',
        }, [
          h('span', { class: 'md3-message-icon' }, getIcon(m.type)),
          h('span', { class: 'md3-message-text' }, m.message),
          h('button', {
            class: 'md3-message-close',
            onClick: () => removeMessage(m.id),
          }, '×'),
        ])
      )
    },
  })
  while (messageContainer.firstChild) {
    messageContainer.removeChild(messageContainer.firstChild)
  }
  app.mount(messageContainer)
}

function getIcon(type: MessageType): VNode {
  const icons: Record<MessageType, VNode> = {
    success: h('svg', { width: 18, height: 18, viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '2.5' }, [
      h('path', { d: 'M20 6L9 17l-5-5' }),
    ]),
    error: h('svg', { width: 18, height: 18, viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '2.5' }, [
      h('path', { d: 'M18 6L6 18M6 6l12 12' }),
    ]),
    warning: h('svg', { width: 18, height: 18, viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '2.5' }, [
      h('path', { d: 'M12 9v4M12 17h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z' }),
    ]),
    info: h('svg', { width: 18, height: 18, viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '2.5' }, [
      h('circle', { cx: '12', cy: '12', r: '10' }),
      h('path', { d: 'M12 16v-4M12 8h.01' }),
    ]),
  }
  return icons[type]
}

export const Md3Message = {
  success(message: string, duration?: number) { return createMessage('success', message, duration) },
  error(message: string, duration?: number) { return createMessage('error', message, duration) },
  warning(message: string, duration?: number) { return createMessage('warning', message, duration) },
  info(message: string, duration?: number) { return createMessage('info', message, duration) },
  remove(id: string) { removeMessage(id) },
  closeAll() {
    messageInstances = []
    renderMessages()
  },
}

// Inject global styles
const styleEl = document.createElement('style')
styleEl.textContent = `
.md3-message-container {
  position: fixed;
  top: var(--md3-space-xl);
  left: 50%;
  transform: translateX(-50%);
  z-index: 3000;
  display: flex;
  flex-direction: column;
  gap: var(--md3-space-sm);
  pointer-events: none;
}

.md3-message {
  display: flex;
  align-items: center;
  gap: var(--md3-space-sm);
  padding: var(--md3-space-md) var(--md3-space-lg);
  border-radius: var(--md3-shape-md);
  font: var(--md3-type-label-large);
  box-shadow: var(--md3-elevation-level3);
  pointer-events: auto;
  animation: md3-message-in var(--md3-motion-duration-medium) var(--md3-motion-easing-standard) forwards;
  min-width: 280px;
  max-width: 480px;
}

.md3-message--success {
  background: var(--md3-success-container);
  color: var(--md3-on-success-container, var(--md3-success));
}

.md3-message--error {
  background: var(--md3-error-container);
  color: var(--md3-on-error-container, var(--md3-error));
}

.md3-message--warning {
  background: var(--md3-warning-container);
  color: var(--md3-on-warning-container, var(--md3-warning));
}

.md3-message--info {
  background: var(--md3-primary-container);
  color: var(--md3-on-primary-container);
}

.md3-message-icon {
  flex-shrink: 0;
  display: flex;
}

.md3-message-text {
  flex: 1;
}

.md3-message-close {
  flex-shrink: 0;
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: none;
  background: transparent;
  cursor: pointer;
  color: inherit;
  opacity: 0.7;
  font: var(--md3-type-label-large);
  border-radius: var(--md3-shape-full);
  transition: opacity var(--md3-motion-duration-short) var(--md3-motion-easing-standard);
}

.md3-message-close:hover {
  opacity: 1;
}

@keyframes md3-message-in {
  from {
    opacity: 0;
    transform: translateY(calc(-1 * var(--md3-space-sm)));
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
`
document.head.appendChild(styleEl)
