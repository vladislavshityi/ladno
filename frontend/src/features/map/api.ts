import { api } from '@/lib/api-client'
import type { MapPoint } from '@/types/models'

export interface MapFilters {
  category: string
  days: 7 | 30 | 90
  active: boolean
}

export const mapApi = {
  points: (f: MapFilters) => api.get<MapPoint[]>('/map/points', { category: f.category, days: f.days, active: f.active }),
}
