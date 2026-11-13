import { api } from '@/lib/api-client'
import type { FaqItem, Meta } from '@/types/models'

export const metaApi = {
  meta: () => api.get<Meta>('/meta'),
  faq: () => api.get<FaqItem[]>('/faq'),
}
