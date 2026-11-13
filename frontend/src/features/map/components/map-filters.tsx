import { ChevronDown } from 'lucide-react'
import { FilterChip } from '@/components/filter-chip'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { useCategories } from '@/features/issues/hooks'
import type { MapFilters } from '../api'

const PERIODS = [7, 30, 90] as const

interface Props {
  filters: MapFilters
  onChange: (filters: MapFilters) => void
}

/** One row of chips above the map: category, period and "active only". */
export function MapFiltersBar({ filters, onChange }: Props) {
  const { data: categories } = useCategories()
  const current = categories?.find((c) => c.id === filters.category)
  return (
    <div className="no-scrollbar -mx-4 flex gap-2 overflow-x-auto px-4 md:mx-0 md:flex-wrap md:overflow-visible md:px-0">
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <FilterChip active={Boolean(current)}>
            {current?.title ?? 'Все категории'} <ChevronDown className="size-3.5" />
          </FilterChip>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="start" className="max-h-80 rounded-xl">
          <DropdownMenuRadioGroup value={filters.category} onValueChange={(category) => onChange({ ...filters, category })}>
            <DropdownMenuRadioItem value="">Все категории</DropdownMenuRadioItem>
            {categories?.map((c) => (
              <DropdownMenuRadioItem key={c.id} value={c.id}>
                {c.title}
              </DropdownMenuRadioItem>
            ))}
          </DropdownMenuRadioGroup>
        </DropdownMenuContent>
      </DropdownMenu>
      {PERIODS.map((days) => (
        <FilterChip key={days} active={filters.days === days} onClick={() => onChange({ ...filters, days })}>
          {days} дн.
        </FilterChip>
      ))}
      <FilterChip active={filters.active} onClick={() => onChange({ ...filters, active: !filters.active })}>
        Только активные
      </FilterChip>
    </div>
  )
}
