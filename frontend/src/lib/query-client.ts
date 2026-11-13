import { MutationCache, QueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { ApiError, errorMessage } from '@/lib/api-client'
import { qk } from '@/lib/query-keys'
import type { User } from '@/types/models'

export const queryClient: QueryClient = new QueryClient({
  mutationCache: new MutationCache({
    onError: (err, _vars, _ctx, mutation) => {
      if (err instanceof ApiError && err.code === 'consent_required') {
        // The consent gate in the router reacts to this flag and opens the consent screen.
        queryClient.setQueryData<User>(qk.me, (me) => me && { ...me, consent_required: true })
        return
      }
      if (!mutation.meta?.silent) toast.error(errorMessage(err))
    },
  }),
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      refetchOnWindowFocus: false,
      retry: (count, err) => !(err instanceof ApiError && err.status < 500) && count < 2,
    },
  },
})
