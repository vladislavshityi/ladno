import { api } from '@/lib/api-client'
import type { AuthConfig, TokenResponse, User } from '@/types/models'

export const authApi = {
  config: () => api.get<AuthConfig>('/auth/config'),
  widget: (data: Record<string, unknown>) => api.post<TokenResponse>('/auth/telegram/widget', data),
  webApp: (initData: string) => api.post<TokenResponse>('/auth/telegram/webapp', { init_data: initData }),
  dev: () => api.post<TokenResponse>('/auth/dev', { telegram_id: 1, first_name: 'Анна' }),
  me: () => api.get<User>('/users/me'),
  acceptConsent: (version: string) => api.post<User>('/users/me/consent', { version }),
}
