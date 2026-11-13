import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { qk } from '@/lib/query-keys'
import type { LinePatch, Receipt } from '@/types/models'
import { receiptsApi } from './api'

export const useReceipts = () => useQuery({ queryKey: qk.receipts, queryFn: receiptsApi.list })

export const useSamples = () => useQuery({ queryKey: qk.samples, queryFn: receiptsApi.samples, staleTime: Infinity })

export const useReceipt = (id: string) => useQuery({ queryKey: qk.receipt(id), queryFn: () => receiptsApi.get(id) })

function useReceiptWrite<V>(fn: (vars: V) => Promise<Receipt>) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: fn,
    onSuccess: (receipt) => {
      qc.setQueryData(qk.receipt(receipt.id), receipt)
      void qc.invalidateQueries({ queryKey: qk.receipts, exact: true })
      // Totals changed, so derived views are stale.
      void qc.invalidateQueries({ queryKey: [...qk.receipts, 'compare'] })
      void qc.invalidateQueries({ queryKey: qk.check(receipt.id) })
    },
  })
}

export const useUploadReceipt = () => useReceiptWrite(receiptsApi.upload)

export const useLoadSample = () => useReceiptWrite(receiptsApi.loadSample)

export const usePatchLine = (receiptId: string) =>
  useReceiptWrite(({ lineId, patch }: { lineId: number; patch: LinePatch }) => receiptsApi.patchLine(receiptId, lineId, patch))

export const useCompare = (base: string | undefined, target: string) =>
  useQuery({ queryKey: qk.compare(base ?? '', target), queryFn: () => receiptsApi.compare(base!, target), enabled: Boolean(base) })

/** The explanation is written by the language model and can take a while, so it loads separately from the figures. */
export const useCompareExplanation = (base: string | undefined, target: string) =>
  useQuery({
    queryKey: qk.compareExplanation(base ?? '', target),
    queryFn: () => receiptsApi.compareExplanation(base!, target),
    enabled: Boolean(base),
    staleTime: Infinity,
    retry: false,
  })

export const useCheck = (id: string, enabled: boolean) =>
  useQuery({ queryKey: qk.check(id), queryFn: () => receiptsApi.check(id), enabled })

export const useRecalculationLetter = (id: string) => useMutation({ mutationFn: () => receiptsApi.letter(id) })
