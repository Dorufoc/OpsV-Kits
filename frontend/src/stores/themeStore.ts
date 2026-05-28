import { defineStore } from 'pinia'
import { ref } from 'vue'

export type ThemeMode = 'light' | 'dark'

export type ThemePreset = 'indigo' | 'blue' | 'green' | 'orange' | 'rose' | 'purple'

export interface ThemePresetColors {
  primary: string
  primaryContainer: string
  onPrimary: string
  onPrimaryContainer: string
  primaryContainerHover: string
  primaryContainerActive: string
  gradientPrimary: string
}

const presetColors: Record<ThemePreset, ThemePresetColors> = {
  indigo: {
    primary: '#4F46E5',
    primaryContainer: '#E0DFFF',
    onPrimary: '#FFFFFF',
    onPrimaryContainer: '#1A1265',
    primaryContainerHover: '#D5D4FF',
    primaryContainerActive: '#C5C2FF',
    gradientPrimary: 'linear-gradient(135deg, #4F46E5 0%, #7C3AED 100%)',
  },
  blue: {
    primary: '#2563EB',
    primaryContainer: '#DBE4FF',
    onPrimary: '#FFFFFF',
    onPrimaryContainer: '#001A41',
    primaryContainerHover: '#CED8FF',
    primaryContainerActive: '#BDC9FF',
    gradientPrimary: 'linear-gradient(135deg, #2563EB 0%, #1D4ED8 100%)',
  },
  green: {
    primary: '#059669',
    primaryContainer: '#D1FAE5',
    onPrimary: '#FFFFFF',
    onPrimaryContainer: '#022C22',
    primaryContainerHover: '#C2F5D8',
    primaryContainerActive: '#AFEFC8',
    gradientPrimary: 'linear-gradient(135deg, #059669 0%, #047857 100%)',
  },
  orange: {
    primary: '#EA580C',
    primaryContainer: '#FFEDD5',
    onPrimary: '#FFFFFF',
    onPrimaryContainer: '#431407',
    primaryContainerHover: '#FFE5C2',
    primaryContainerActive: '#FFDAAF',
    gradientPrimary: 'linear-gradient(135deg, #EA580C 0%, #C2410C 100%)',
  },
  rose: {
    primary: '#E11D48',
    primaryContainer: '#FFE4E6',
    onPrimary: '#FFFFFF',
    onPrimaryContainer: '#4C0519',
    primaryContainerHover: '#FFD9DB',
    primaryContainerActive: '#FFC9CD',
    gradientPrimary: 'linear-gradient(135deg, #E11D48 0%, #BE123C 100%)',
  },
  purple: {
    primary: '#7C3AED',
    primaryContainer: '#EDE9FE',
    onPrimary: '#FFFFFF',
    onPrimaryContainer: '#2E1065',
    primaryContainerHover: '#E2DCFD',
    primaryContainerActive: '#D4CDFC',
    gradientPrimary: 'linear-gradient(135deg, #7C3AED 0%, #6D28D9 100%)',
  },
}

const darkVariantPresets: Record<ThemePreset, Partial<ThemePresetColors>> = {
  indigo: {
    primaryContainer: '#2E2A6E',
    onPrimaryContainer: '#CCC2FF',
    primaryContainerHover: '#4A44A0',
    primaryContainerActive: '#252260',
    gradientPrimary: 'linear-gradient(135deg, #7C73E8 0%, #9A8EFF 100%)',
  },
  blue: {
    primaryContainer: '#002D6E',
    onPrimaryContainer: '#B3CCFF',
    primaryContainerHover: '#0047A0',
    primaryContainerActive: '#002050',
    gradientPrimary: 'linear-gradient(135deg, #5B8DEF 0%, #7BA7FF 100%)',
  },
  green: {
    primaryContainer: '#064E3B',
    onPrimaryContainer: '#A7F3D0',
    primaryContainerHover: '#0A7045',
    primaryContainerActive: '#043B28',
    gradientPrimary: 'linear-gradient(135deg, #34D399 0%, #10B981 100%)',
  },
  orange: {
    primaryContainer: '#5C1A04',
    onPrimaryContainer: '#FFC8A2',
    primaryContainerHover: '#7A2A08',
    primaryContainerActive: '#401404',
    gradientPrimary: 'linear-gradient(135deg, #FB923C 0%, #F97316 100%)',
  },
  rose: {
    primaryContainer: '#66001A',
    onPrimaryContainer: '#FFB3C1',
    primaryContainerHover: '#8A0027',
    primaryContainerActive: '#4D0014',
    gradientPrimary: 'linear-gradient(135deg, #FB7185 0%, #F43F5E 100%)',
  },
  purple: {
    primaryContainer: '#3B0764',
    onPrimaryContainer: '#D8B4FE',
    primaryContainerHover: '#55188A',
    primaryContainerActive: '#2E054F',
    gradientPrimary: 'linear-gradient(135deg, #A78BFA 0%, #8B5CF6 100%)',
  },
}

function applyTheme(mode: ThemeMode, preset: ThemePreset) {
  const root = document.documentElement
  const colors = presetColors[preset]

  root.style.setProperty('--md3-primary', colors.primary)
  root.style.setProperty('--md3-primary-container', colors.primaryContainer)
  root.style.setProperty('--md3-on-primary', colors.onPrimary)
  root.style.setProperty('--md3-on-primary-container', colors.onPrimaryContainer)
  root.style.setProperty('--md3-primary-container-hover', colors.primaryContainerHover)
  root.style.setProperty('--md3-primary-container-active', colors.primaryContainerActive)
  root.style.setProperty('--md3-gradient-primary', colors.gradientPrimary)

  if (mode === 'dark') {
    root.setAttribute('data-theme', 'dark')
    const darkColors = darkVariantPresets[preset]
    if (darkColors.primaryContainer) {
      root.style.setProperty('--md3-primary-container', darkColors.primaryContainer)
    }
    if (darkColors.onPrimaryContainer) {
      root.style.setProperty('--md3-on-primary-container', darkColors.onPrimaryContainer)
    }
    if (darkColors.primaryContainerHover) {
      root.style.setProperty('--md3-primary-container-hover', darkColors.primaryContainerHover)
    }
    if (darkColors.primaryContainerActive) {
      root.style.setProperty('--md3-primary-container-active', darkColors.primaryContainerActive)
    }
    if (darkColors.gradientPrimary) {
      root.style.setProperty('--md3-gradient-primary', darkColors.gradientPrimary)
    }
  } else {
    root.removeAttribute('data-theme')
  }
}

function loadPersistedState(): { mode: ThemeMode; preset: ThemePreset } {
  try {
    const saved = localStorage.getItem('opsv-theme')
    if (saved) {
      const parsed = JSON.parse(saved)
      return {
        mode: parsed.mode === 'dark' ? 'dark' : 'light',
        preset: parsed.preset in presetColors ? parsed.preset : 'indigo',
      }
    }
  } catch {
  }

  const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches
  return { mode: prefersDark ? 'dark' : 'light', preset: 'indigo' }
}

export const useThemeStore = defineStore('theme', () => {
  const initialState = loadPersistedState()

  const mode = ref<ThemeMode>(initialState.mode)
  const preset = ref<ThemePreset>(initialState.preset)

  function persist() {
    localStorage.setItem('opsv-theme', JSON.stringify({ mode: mode.value, preset: preset.value }))
  }

  function toggleDark() {
    mode.value = mode.value === 'light' ? 'dark' : 'light'
    applyTheme(mode.value, preset.value)
    persist()
  }

  function setMode(newMode: ThemeMode) {
    mode.value = newMode
    applyTheme(mode.value, preset.value)
    persist()
  }

  function setPreset(newPreset: ThemePreset) {
    preset.value = newPreset
    applyTheme(mode.value, preset.value)
    persist()
  }

  applyTheme(mode.value, preset.value)

  return {
    mode,
    preset,
    toggleDark,
    setMode,
    setPreset,
  }
})

export { presetColors, darkVariantPresets }
