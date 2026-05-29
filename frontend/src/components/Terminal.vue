<template>
  <div class="terminal-wrapper" ref="terminalContainer">
    <div class="terminal-toolbar" v-if="showToolbar">
      <div class="toolbar-left">
        <slot name="toolbar-left">
          <span class="session-label">{{ sessionName || '终端' }}</span>
        </slot>
      </div>
      <div class="toolbar-right">
        <Md3Button variant="text" size="sm" @click="handleCopy">
          <Md3Icon name="content-copy" size="14" />复制选中
        </Md3Button>
        <Md3Button variant="text" size="sm" @click="handleCopyAll">
          <Md3Icon name="content-copy" size="14" />复制全部
        </Md3Button>
        <Md3Button variant="text" size="sm" @click="handlePaste">
          <Md3Icon name="upload" size="14" />粘贴
        </Md3Button>
        <Md3Button variant="text" size="sm" @click="handleClear">
          <Md3Icon name="delete" size="14" />清屏
        </Md3Button>
        <Md3Button :variant="isFrozen ? 'warning' : 'text'" size="sm" @click="handleFreeze">
          <Md3Icon :name="isFrozen ? 'play' : 'pause'" size="14" />{{ isFrozen ? '已冻结' : '冻结' }}
        </Md3Button>
        <Md3Button variant="text" size="sm" @click="handleFullscreen">
          <Md3Icon name="fullscreen" size="14" />全屏
        </Md3Button>
      </div>
    </div>
    <div class="terminal-container" ref="containerRef"></div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, watch } from 'vue'
import { Terminal } from 'xterm'
import { FitAddon } from 'xterm-addon-fit'
import 'xterm/css/xterm.css'
import { Md3Icon } from '@/components/md3'
import Md3Button from '@/components/Md3Button.vue'

const props = defineProps<{
  sessionName?: string
  showToolbar?: boolean
  fontSize?: number
  fontFamily?: string
  theme?: 'dark' | 'light'
}>()

const emit = defineEmits<{
  data: [data: string]
  resize: [cols: number, rows: number]
}>()

const containerRef = ref<HTMLElement>()
const terminalContainer = ref<HTMLElement>()
const terminalRef = ref<Terminal>()
const fitAddonRef = ref<FitAddon>()
const isFrozen = ref(false)
const frozenBuffer = ref<string[]>([])

function initTerminal() {
  if (!containerRef.value) return

  const term = new Terminal({
    cursorBlink: true,
    cursorStyle: 'block',
    fontSize: props.fontSize || 14,
    fontFamily: props.fontFamily || "'Cascadia Code', 'Fira Code', 'Consolas', 'Courier New', monospace",
    theme: props.theme === 'light' ? {
      background: '#ffffff',
      foreground: '#333333',
      cursor: '#333333',
    } : {
      background: '#1e1e1e',
      foreground: '#d4d4d4',
      cursor: '#d4d4d4',
    },
    allowTransparency: true,
    convertEol: true,
  })

  const fitAddon = new FitAddon()
  term.loadAddon(fitAddon)

  term.open(containerRef.value)
  fitAddon.fit()

  term.onData((data: string) => {
    emit('data', data)
  })

  term.onResize(({ cols, rows }) => {
    emit('resize', cols, rows)
  })

  terminalRef.value = term
  fitAddonRef.value = fitAddon
}

function write(data: string) {
  if (isFrozen.value) {
    frozenBuffer.value.push(data)
  } else {
    terminalRef.value?.write(data)
  }
}

function writeln(data: string) {
  terminalRef.value?.writeln(data)
}

function clear() {
  terminalRef.value?.clear()
}

function resize() {
  try {
    fitAddonRef.value?.fit()
  } catch {
  }
}

function focus() {
  terminalRef.value?.focus()
}

function handleCopy() {
  const selection = terminalRef.value?.getSelection()
  if (selection) {
    navigator.clipboard.writeText(selection)
  }
}

function handleCopyAll() {
  const term = terminalRef.value
  if (!term) return

  const buffer = term.buffer
  const lines: string[] = []
  const activeBuffer = buffer.active

  for (let i = 0; i < activeBuffer.length; i++) {
    const line = activeBuffer.getLine(i)
    if (line) {
      lines.push(line.translateToString(false))
    }
  }

  const allText = lines.join('\n').trimEnd()
  if (allText) {
    navigator.clipboard.writeText(allText)
  }
}

function handleFreeze() {
  isFrozen.value = !isFrozen.value

  if (!isFrozen.value && frozenBuffer.value.length > 0) {
    const term = terminalRef.value
    if (term) {
      for (const data of frozenBuffer.value) {
        term.write(data)
      }
    }
    frozenBuffer.value = []
  }
}

function handlePaste() {
  navigator.clipboard.readText().then(text => {
    emit('data', text)
  })
}

function handleClear() {
  clear()
}

function handleFullscreen() {
  if (!terminalContainer.value) return
  if (document.fullscreenElement) {
    document.exitFullscreen()
  } else {
    terminalContainer.value.requestFullscreen()
  }
}

function getTerminal(): Terminal | undefined {
  return terminalRef.value
}

function getIsFrozen(): boolean {
  return isFrozen.value
}

function syncFrozenData() {
  if (!isFrozen.value && frozenBuffer.value.length > 0) {
    const term = terminalRef.value
    if (term) {
      for (const data of frozenBuffer.value) {
        term.write(data)
      }
    }
    frozenBuffer.value = []
  }
}

defineExpose({
  write,
  writeln,
  clear,
  resize,
  focus,
  getTerminal,
  getIsFrozen,
  syncFrozenData,
})

onMounted(() => {
  initTerminal()
  const resizeObserver = new ResizeObserver(() => {
    resize()
  })
  if (containerRef.value) {
    resizeObserver.observe(containerRef.value)
  }
  onBeforeUnmount(() => {
    resizeObserver.disconnect()
    terminalRef.value?.dispose()
  })
})

watch(() => props.fontSize, (newSize) => {
  if (newSize && terminalRef.value) {
    terminalRef.value.options.fontSize = newSize
    resize()
  }
})

watch(() => props.fontFamily, (newFont) => {
  if (newFont && terminalRef.value) {
    terminalRef.value.options.fontFamily = newFont
    resize()
  }
})

watch(() => props.theme, (newTheme) => {
  if (newTheme && terminalRef.value) {
    terminalRef.value.options.theme = newTheme === 'light' ? {
      background: '#ffffff',
      foreground: '#333333',
      cursor: '#333333',
    } : {
      background: '#1e1e1e',
      foreground: '#d4d4d4',
      cursor: '#d4d4d4',
    }
  }
})
</script>

<style scoped>
.terminal-wrapper {
  display: flex;
  flex-direction: column;
  height: 100%;
  border: 1px solid var(--md3-glass-border);
  border-radius: var(--md3-shape-sm);
  overflow: hidden;
  background: var(--md3-glass-bg);
  backdrop-filter: var(--md3-glass-blur);
  -webkit-backdrop-filter: var(--md3-glass-blur);
  transition: box-shadow var(--md3-motion-duration-medium) var(--md3-motion-easing-standard);
}

.terminal-wrapper:hover {
  box-shadow: var(--md3-elevation-level1);
}

.terminal-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--md3-space-xs) var(--md3-space-sm);
  background: var(--md3-glass-bg);
  border-bottom: 1px solid var(--md3-glass-border);
  transition: background var(--md3-motion-duration-short) var(--md3-motion-easing-standard);
}

.toolbar-left,
.toolbar-right {
  display: flex;
  align-items: center;
  gap: var(--md3-space-xs);
}

.session-label {
  font-size: 13px;
  font-weight: 500;
  color: var(--md3-on-surface);
}

.terminal-container {
  flex: 1;
  overflow: hidden;
  padding: 4px;
}
</style>
