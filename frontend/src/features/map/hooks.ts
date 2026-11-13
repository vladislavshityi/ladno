import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { qk } from '@/lib/query-keys'
import { mapApi, type MapFilters } from './api'

export const useMapPoints = (filters: MapFilters) =>
  useQuery({ queryKey: qk.mapPoints(filters), queryFn: () => mapApi.points(filters), placeholderData: keepPreviousData })
