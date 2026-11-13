import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { qk } from '@/lib/query-keys'
import { ratingsApi, type RatingSort } from './api'

export const useRatings = (district: string, sort: RatingSort) =>
  useQuery({
    queryKey: qk.ratings(district, sort),
    queryFn: () => ratingsApi.list(district, sort),
    placeholderData: keepPreviousData,
  })

/** A 404 just means the company has no issues yet, so there is nothing to retry. */
export const useCompanyRating = (companyId: number | null | undefined) =>
  useQuery({
    queryKey: qk.rating(companyId ?? 0),
    queryFn: () => ratingsApi.get(companyId!),
    enabled: companyId != null,
    retry: false,
  })
