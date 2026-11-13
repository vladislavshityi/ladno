import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { qk } from '@/lib/query-keys'
import type { Collective } from '@/types/models'
import { collectivesApi } from './api'

/** Neighbours with the same problem; skipped for an address outside the directory (no house id). */
export const useSimilar = (houseId: number | null | undefined, category: string) =>
  useQuery({
    queryKey: qk.similar(houseId ?? null, category),
    queryFn: () => collectivesApi.similar(houseId!, category),
    enabled: Boolean(houseId),
  })

export const useCollective = (id: string | null | undefined) =>
  useQuery({ queryKey: qk.collective(id ?? ''), queryFn: () => collectivesApi.get(id!), enabled: Boolean(id) })

/** Joining changes the issue (it gets a collective id), so its caches are refreshed too. */
export function useJoinCollective() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: collectivesApi.join,
    onSuccess: (collective, vars) => {
      qc.setQueryData(qk.collective(collective.id), collective)
      void qc.invalidateQueries({ queryKey: qk.issue(vars.issue_id) })
      void qc.invalidateQueries({ queryKey: qk.issues, exact: true })
    },
  })
}

function useCollectiveWrite<V>(id: string, fn: (vars: V) => Promise<Collective>) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: fn,
    onSuccess: (collective) => {
      qc.setQueryData(qk.collective(id), collective)
      // Submitting starts the deadline of the member issues.
      void qc.invalidateQueries({ queryKey: qk.issues })
    },
  })
}

export const useSetConsent = (id: string) => useCollectiveWrite(id, (consent: boolean) => collectivesApi.setConsent(id, consent))

export const useSubmitCollective = (id: string) => useCollectiveWrite(id, () => collectivesApi.submit(id))

export const useCollectiveLetter = (id: string) => useMutation({ mutationFn: () => collectivesApi.letter(id) })
