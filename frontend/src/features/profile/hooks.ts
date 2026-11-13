import { useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { useAuth } from '@/features/auth/auth-context'
import { qk } from '@/lib/query-keys'
import { profileApi } from './api'

export function useUpdateProfile() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: profileApi.update,
    onSuccess: (user) => qc.setQueryData(qk.me, user),
  })
}

export function useExportData() {
  return useMutation({
    mutationFn: profileApi.export,
    onSuccess: (data) => {
      const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' }))
      const a = document.createElement('a')
      a.href = url
      a.download = 'ladno-moi-dannye.json'
      a.click()
      URL.revokeObjectURL(url)
    },
  })
}

export function useDeleteAccount() {
  const { signOut } = useAuth()
  return useMutation({
    mutationFn: profileApi.delete,
    onSuccess: () => {
      signOut()
      toast.success('Аккаунт и все данные удалены')
    },
  })
}
