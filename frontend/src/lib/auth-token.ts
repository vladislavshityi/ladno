const KEY = 'ladno.token'
const listeners = new Set<() => void>()

export function getToken(): string | null {
  try {
    return localStorage.getItem(KEY)
  } catch {
    return null
  }
}

export function setToken(token: string | null) {
  try {
    if (token) localStorage.setItem(KEY, token)
    else localStorage.removeItem(KEY)
  } catch {
    /* storage unavailable */
  }
  listeners.forEach((l) => l())
}

export function subscribeToken(listener: () => void) {
  listeners.add(listener)
  return () => {
    listeners.delete(listener)
  }
}
