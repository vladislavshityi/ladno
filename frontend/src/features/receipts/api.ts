import { api } from '@/lib/api-client'
import type { Check, Compare, CompareExplanation, LinePatch, Receipt, ReceiptSample, ReceiptShort, RecalculationLetter } from '@/types/models'

export const receiptsApi = {
  list: () => api.get<ReceiptShort[]>('/receipts'),
  samples: () => api.get<ReceiptSample[]>('/receipts/samples'),
  upload: (file: File) => api.upload<Receipt>('/receipts', file),
  loadSample: (id: string) => api.post<Receipt>(`/receipts/samples/${id}`),
  get: (id: string) => api.get<Receipt>(`/receipts/${id}`),
  patchLine: (id: string, lineId: number, body: LinePatch) => api.patch<Receipt>(`/receipts/${id}/lines/${lineId}`, body),
  compare: (base: string, target: string) => api.get<Compare>('/receipts/compare', { base, target }),
  compareExplanation: (base: string, target: string) => api.get<CompareExplanation>('/receipts/compare/explanation', { base, target }),
  check: (id: string) => api.get<Check>(`/receipts/${id}/check`),
  letter: (id: string) => api.post<RecalculationLetter>(`/receipts/${id}/recalculation-letter`, { finding_types: [] }),
}
