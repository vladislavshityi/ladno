import { useQuery } from '@tanstack/react-query'
import { qk } from '@/lib/query-keys'
import { metaApi } from './api'

const HOUR = 60 * 60 * 1000

/** What the server can do. Until it answers (or if it fails) the model-based features count as off. */
export function useCapabilities() {
  const { data, isPending } = useQuery({ queryKey: qk.meta, queryFn: metaApi.meta, staleTime: HOUR, retry: 1 })
  return {
    loaded: !isPending,
    llm: data?.llm ?? false,
    vision: data?.vision ?? false,
    demoData: data?.demo_data ?? false,
  }
}

export const useFaq = () => useQuery({ queryKey: qk.faq, queryFn: metaApi.faq, staleTime: Infinity })
