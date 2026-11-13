import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { qk } from '@/lib/query-keys'
import { getInitData } from '@/lib/telegram'
import { useAuth } from './auth-context'
import { authApi } from './api'

export const useAuthConfig = () => useQuery({ queryKey: qk.authConfig, queryFn: authApi.config, staleTime: Infinity })

export function useMe() {
  const { token } = useAuth()
  return useQuery({ queryKey: qk.me, queryFn: authApi.me, enabled: Boolean(token) })
}

export function useWidgetLogin() {
  const { signIn } = useAuth()
  return useMutation({ mutationFn: authApi.widget, onSuccess: signIn })
}

export function useWebAppLogin() {
  const { signIn } = useAuth()
  return useMutation({ mutationFn: () => authApi.webApp(getInitData()), onSuccess: signIn })
}

export function useDevLogin() {
  const { signIn } = useAuth()
  return useMutation({ mutationFn: authApi.dev, onSuccess: signIn })
}

export function useAcceptConsent() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: authApi.acceptConsent,
    onSuccess: (user) => qc.setQueryData(qk.me, user),
  })
}
