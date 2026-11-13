import { createContext, useContext } from 'react'
import type { TokenResponse } from '@/types/models'

export interface AuthContextValue {
  token: string | null
  signIn: (res: TokenResponse) => void
  signOut: () => void
}

export const AuthContext = createContext<AuthContextValue | null>(null)

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider')
  return ctx
}
