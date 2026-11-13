import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { useDebouncedValue } from '@/hooks/use-debounced-value'
import { qk } from '@/lib/query-keys'
import { housesApi } from './api'

export function useAddressSearch(input: string) {
  const q = useDebouncedValue(input.trim())
  const query = useQuery({
    queryKey: qk.addresses(q),
    queryFn: () => housesApi.searchAddresses(q),
    enabled: q.length >= 2,
    placeholderData: keepPreviousData,
  })
  return { ...query, searching: input.trim() !== q || query.isFetching, ready: q.length >= 2 }
}

export const useHouse = (id: number | null | undefined) =>
  useQuery({ queryKey: qk.house(id ?? 0), queryFn: () => housesApi.house(id!), enabled: id != null })

export function useCompanies(input: string) {
  const q = useDebouncedValue(input.trim())
  return useQuery({
    queryKey: qk.companies(q),
    queryFn: () => housesApi.companies(q),
    placeholderData: keepPreviousData,
  })
}
