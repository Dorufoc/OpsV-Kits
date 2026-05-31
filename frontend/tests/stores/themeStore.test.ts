import { describe, it, expect, vi, beforeEach } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useThemeStore } from '@/stores/themeStore'
import { presetColors, darkVariantPresets } from '@/stores/themeStore'

describe('ThemeStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    localStorage.clear()
    document.documentElement.removeAttribute('data-theme')
    document.documentElement.style.cssText = ''
  })

  describe('状态初始化', () => {
    it('没有持久化状态时应该默认初始化 mode', () => {
      const store = useThemeStore()
      expect(['light', 'dark']).toContain(store.mode)
    })

    it('没有持久化状态时应该默认初始化 preset 为 indigo', () => {
      localStorage.clear()
      const store = useThemeStore()
      expect(store.preset).toBe('indigo')
    })

    it('应该从 localStorage 恢复 mode', () => {
      localStorage.setItem('opsv-theme', JSON.stringify({ mode: 'dark', preset: 'blue' }))
      const store = useThemeStore()
      expect(store.mode).toBe('dark')
    })

    it('应该从 localStorage 恢复 preset', () => {
      localStorage.setItem('opsv-theme', JSON.stringify({ mode: 'light', preset: 'green' }))
      const store = useThemeStore()
      expect(store.preset).toBe('green')
    })

    it('localStorage 中无效的 mode 应该回退到 light', () => {
      localStorage.setItem('opsv-theme', JSON.stringify({ mode: 'invalid', preset: 'indigo' }))
      const store = useThemeStore()
      expect(store.mode).toBe('light')
    })

    it('localStorage 中无效的 preset 应该回退到 indigo', () => {
      localStorage.setItem('opsv-theme', JSON.stringify({ mode: 'light', preset: 'nonexistent' }))
      const store = useThemeStore()
      expect(store.preset).toBe('indigo')
    })

    it('localStorage 中格式错误时应该使用默认值', () => {
      localStorage.setItem('opsv-theme', 'not-json')
      const store = useThemeStore()
      expect(store.preset).toBe('indigo')
    })
  })

  describe('toggleDark', () => {
    it('应该从 light 切换到 dark', () => {
      const store = useThemeStore()
      store.mode = 'light'
      store.toggleDark()
      expect(store.mode).toBe('dark')
    })

    it('应该从 dark 切换到 light', () => {
      const store = useThemeStore()
      store.mode = 'dark'
      store.toggleDark()
      expect(store.mode).toBe('light')
    })

    it('切换后应该持久化到 localStorage', () => {
      const store = useThemeStore()
      store.mode = 'light'
      store.toggleDark()
      const saved = JSON.parse(localStorage.getItem('opsv-theme')!)
      expect(saved.mode).toBe('dark')
    })

    it('切换到 dark 时应该设置 data-theme 属性', () => {
      const store = useThemeStore()
      store.mode = 'light'
      store.toggleDark()
      expect(document.documentElement.getAttribute('data-theme')).toBe('dark')
    })

    it('切换到 light 时应该移除 data-theme 属性', () => {
      const store = useThemeStore()
      store.mode = 'dark'
      store.toggleDark()
      expect(document.documentElement.getAttribute('data-theme')).toBeNull()
    })
  })

  describe('setMode', () => {
    it('应该设置 mode 为指定值', () => {
      const store = useThemeStore()
      store.setMode('dark')
      expect(store.mode).toBe('dark')
    })

    it('设置 dark 时应该设置 data-theme 属性', () => {
      const store = useThemeStore()
      store.setMode('dark')
      expect(document.documentElement.getAttribute('data-theme')).toBe('dark')
    })

    it('设置 light 时应该移除 data-theme 属性', () => {
      const store = useThemeStore()
      store.setMode('light')
      expect(document.documentElement.getAttribute('data-theme')).toBeNull()
    })

    it('设置后应该持久化到 localStorage', () => {
      const store = useThemeStore()
      store.setMode('dark')
      const saved = JSON.parse(localStorage.getItem('opsv-theme')!)
      expect(saved.mode).toBe('dark')
    })
  })

  describe('setPreset', () => {
    it('应该设置 preset 为指定值', () => {
      const store = useThemeStore()
      store.setPreset('blue')
      expect(store.preset).toBe('blue')
    })

    it('设置后应该持久化到 localStorage', () => {
      const store = useThemeStore()
      store.setPreset('green')
      const saved = JSON.parse(localStorage.getItem('opsv-theme')!)
      expect(saved.preset).toBe('green')
    })

    it('设置 preset 应该更新 CSS 变量', () => {
      const store = useThemeStore()
      store.setPreset('blue')
      const root = document.documentElement
      expect(root.style.getPropertyValue('--md3-primary')).toBe(presetColors.blue.primary)
    })

    it('设置 preset 为 orange 应该更新 primary 颜色', () => {
      const store = useThemeStore()
      store.setPreset('orange')
      const root = document.documentElement
      expect(root.style.getPropertyValue('--md3-primary')).toBe(presetColors.orange.primary)
    })
  })

  describe('CSS 变量应用', () => {
    it('dark 模式应该应用 dark 变体颜色', () => {
      const store = useThemeStore()
      store.setMode('dark')
      store.setPreset('indigo')
      const root = document.documentElement
      expect(root.style.getPropertyValue('--md3-primary-container')).toBe(darkVariantPresets.indigo.primaryContainer)
    })

    it('light 模式应该使用默认颜色', () => {
      const store = useThemeStore()
      store.setMode('light')
      store.setPreset('indigo')
      const root = document.documentElement
      expect(root.style.getPropertyValue('--md3-primary-container')).toBe(presetColors.indigo.primaryContainer)
    })

    it('应该设置 gradient-primary CSS 变量', () => {
      const store = useThemeStore()
      store.setPreset('purple')
      const root = document.documentElement
      expect(root.style.getPropertyValue('--md3-gradient-primary')).toBe(presetColors.purple.gradientPrimary)
    })
  })

  describe('presetColors 数据', () => {
    it('应该包含所有 6 个预设', () => {
      const presets: Array<keyof typeof presetColors> = ['indigo', 'blue', 'green', 'orange', 'rose', 'purple']
      for (const p of presets) {
        expect(presetColors[p]).toBeDefined()
      }
    })

    it('每个预设应该包含完整的颜色属性', () => {
      const requiredKeys = ['primary', 'primaryContainer', 'onPrimary', 'onPrimaryContainer', 'primaryContainerHover', 'primaryContainerActive', 'gradientPrimary']
      for (const key of Object.keys(presetColors) as Array<keyof typeof presetColors>) {
        for (const prop of requiredKeys) {
          expect(presetColors[key][prop as keyof typeof presetColors[typeof key]]).toBeDefined()
        }
      }
    })

    it('darkVariantPresets 应该包含所有 6 个预设', () => {
      const presets: Array<keyof typeof darkVariantPresets> = ['indigo', 'blue', 'green', 'orange', 'rose', 'purple']
      for (const p of presets) {
        expect(darkVariantPresets[p]).toBeDefined()
      }
    })
  })
})
