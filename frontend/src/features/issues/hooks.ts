import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { qk } from '@/lib/query-keys'
import type { Issue, IssuePatch, RouteRequest } from '@/types/models'
import { issuesApi } from './api'

export const useCategories = () => useQuery({ queryKey: qk.categories, queryFn: issuesApi.categories, staleTime: Infinity })

export const useQuestions = (category: string) =>
  useQuery({ queryKey: qk.questions(category), queryFn: () => issuesApi.questions(category), staleTime: Infinity })

export const useUploadPhoto = () => useMutation({ mutationFn: issuesApi.uploadPhoto })

export const useClassify = () => useMutation({ mutationFn: issuesApi.classify })

export const useRoutePreview = (req: RouteRequest) =>
  useQuery({ queryKey: qk.route(req), queryFn: () => issuesApi.route(req) })

export const useIssues = () => useQuery({ queryKey: qk.issues, queryFn: issuesApi.list })

export const useIssue = (id: string) => useQuery({ queryKey: qk.issue(id), queryFn: () => issuesApi.get(id) })

export const useSubmission = (id: string, enabled: boolean) =>
  useQuery({ queryKey: qk.submission(id), queryFn: () => issuesApi.submission(id), enabled })

/** Keeps the list and the single-issue caches in sync after any issue write. */
function useIssueWrite<V>(fn: (vars: V) => Promise<Issue>) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: fn,
    onSuccess: (issue) => {
      qc.setQueryData(qk.issue(issue.id), issue)
      void qc.invalidateQueries({ queryKey: qk.issues, exact: true })
    },
  })
}

export const useCreateIssue = () => useIssueWrite(issuesApi.create)

export const usePatchIssue = (id: string) => useIssueWrite((body: IssuePatch) => issuesApi.patch(id, body))

export const useRefreshLetter = (id: string) => useIssueWrite(() => issuesApi.refreshLetter(id))

export const useEscalate = (id: string) => useIssueWrite(() => issuesApi.escalate(id))

/** Photos are private, so the file is fetched with the token; the object URL lives as long as the cached blob. */
export function useAuthedImage(url: string) {
  const { data } = useQuery({
    queryKey: ['photo', url],
    queryFn: async () => URL.createObjectURL(await issuesApi.photoBlob(url)),
    staleTime: Infinity,
  })
  return data
}
