import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { getToken, setToken, subscribeToken } from './auth-token'

function stubStorage() {
  const store = new Map<string, string>()
  vi.stubGlobal('localStorage', {
    getItem: (k: string) => store.get(k) ?? null,
    setItem: (k: string, v: string) => void store.set(k, v),
    removeItem: (k: string) => void store.delete(k),
  })
}

describe('auth-token', () => {
  beforeEach(stubStorage)
  afterEach(() => vi.unstubAllGlobals())

  it('stores and clears the token', () => {
    setToken('abc')
    expect(getToken()).toBe('abc')
    setToken(null)
    expect(getToken()).toBeNull()
  })

  it('notifies subscribers on change', () => {
    const listener = vi.fn()
    const unsubscribe = subscribeToken(listener)
    setToken('abc')
    unsubscribe()
    setToken(null)
    expect(listener).toHaveBeenCalledTimes(1)
  })

  it('survives unavailable storage', () => {
    vi.stubGlobal('localStorage', {
      getItem: () => {
        throw new Error('blocked')
      },
    })
    expect(getToken()).toBeNull()
  })
})
