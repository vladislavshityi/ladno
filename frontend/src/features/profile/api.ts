import { api } from '@/lib/api-client'
import type { ProfileUpdate, User, UserExport } from '@/types/models'

export const profileApi = {
  update: (data: ProfileUpdate) => api.put<User>('/users/me/profile', data),
  export: () => api.get<UserExport>('/users/me/export'),
  delete: () => api.delete('/users/me'),
}
