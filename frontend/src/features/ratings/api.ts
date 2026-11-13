import { api } from '@/lib/api-client'
import type { CompanyDetail, CompanyRating } from '@/types/models'

export type RatingSort = 'score' | 'issues' | 'overdue'

export const ratingsApi = {
  list: (district: string, sort: RatingSort) => api.get<CompanyRating[]>('/ratings/companies', { district, sort }),
  get: (companyId: number) => api.get<CompanyDetail>(`/ratings/companies/${companyId}`),
}
