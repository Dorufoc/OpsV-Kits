import { describe, it, expect, vi, beforeEach } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useExampleStore } from '@/stores/example'

describe('Example Store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('应该正确初始化 count 为 0', () => {
    const store = useExampleStore()
    expect(store.count).toBe(0)
  })

  it('increment 应该增加 count', () => {
    const store = useExampleStore()
    store.increment()
    expect(store.count).toBe(1)
  })

  it('多次 increment 应该正确累加', () => {
    const store = useExampleStore()
    store.increment()
    store.increment()
    store.increment()
    expect(store.count).toBe(3)
  })
})
