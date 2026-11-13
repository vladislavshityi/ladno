import { useCallback, useMemo, useSyncExternalStore, type ReactNode } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { getToken, setToken, subscribeToken } from '@/lib/auth-token'
import { qk } from '@/lib/query-keys'
import type { TokenResponse } from '@/types/models'
import { AuthContext } from './auth-context'

export function AuthProvider({ children }: { children: ReactNode }) {
  const qc = useQueryClient()
  const token = useSyncExternalStore(subscribeToken, getToken)

  const signIn = useCallback(
    (res: TokenResponse) => {
      qc.clear()
      setToken(res.access_token)
      qc.setQueryData(qk.me, res.user)
    },
    [qc],
  )
  const signOut = useCallback(() => {
    setToken(null)
    qc.clear()
  }, [qc])

  const value = useMemo(() => ({ token, signIn, signOut }), [token, signIn, signOut])
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
