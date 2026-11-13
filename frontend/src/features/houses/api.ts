import { api } from '@/lib/api-client'
import type { AddressSuggestion, House, ManagementCompany } from '@/types/models'

export const housesApi = {
  searchAddresses: (q: string) => api.get<AddressSuggestion[]>('/addresses/search', { q }),
  house: (id: number) => api.get<House>(`/houses/${id}`),
  companies: (q: string) => api.get<ManagementCompany[]>('/management-companies', { q }),
  companiesByInn: (inn: string) => api.get<ManagementCompany[]>('/management-companies', { inn }),
}
