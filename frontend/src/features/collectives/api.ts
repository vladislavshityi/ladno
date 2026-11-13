import { api } from '@/lib/api-client'
import type { Collective, CollectiveJoin, CollectiveLetter, SimilarIssues } from '@/types/models'

export const collectivesApi = {
  similar: (houseId: number, category: string) => api.get<SimilarIssues>('/issues/similar', { house_id: houseId, category }),
  get: (id: string) => api.get<Collective>(`/collectives/${id}`),
  join: (body: CollectiveJoin) => api.post<Collective>('/collectives/join', body),
  setConsent: (id: string, consentLetter: boolean) => api.patch<Collective>(`/collectives/${id}/membership`, { consent_letter: consentLetter }),
  letter: (id: string) => api.post<CollectiveLetter>(`/collectives/${id}/letter`),
  /** The PDF holds residents' data, so it is fetched with the token like the issue letter. */
  letterPdf: async (id: string) => (await api.raw('GET', `/collectives/${id}/letter.pdf`)).blob(),
  submit: (id: string) => api.post<Collective>(`/collectives/${id}/submit`),
}
