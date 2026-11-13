import { useState } from 'react'
import { SearchX } from 'lucide-react'
import { DemoBadge } from '@/components/demo-badge'
import { EmptyState } from '@/components/empty-state'
import { FilterChip } from '@/components/filter-chip'
import { PageHeader } from '@/components/page-header'
import { Skeleton } from '@/components/ui/skeleton'
import type { RatingSort } from '../api'
import { CompanyCard } from '../components/company-card'
import { useRatings } from '../hooks'

const SORTS: { id: RatingSort; label: string }[] = [
  { id: 'score', label: 'По баллу' },
  { id: 'issues', label: 'По обращениям' },
  { id: 'overdue', label: 'По просрочкам' },
]

export default function RatingsPage() {
  const [district, setDistrict] = useState('')
  const [sort, setSort] = useState<RatingSort>('score')
  const { data: companies, isLoading } = useRatings(district, sort)
  // The district list comes from the unfiltered ranking, so chips stay put while one is selected.
  const { data: all } = useRatings('', 'score')
  const districts = [...new Set(all?.flatMap((c) => c.districts))].sort()

  return (
    <div className="mx-auto grid max-w-2xl gap-5">
      <PageHeader
        title="Рейтинг управляющих компаний"
        description="Как УК отвечают на обращения жителей, по данным сервиса"
        actions={<DemoBadge />}
      />
      <div className="-mx-4 flex gap-2 overflow-x-auto px-4 pb-1 md:mx-0 md:px-0">
        {SORTS.map((s) => (
          <FilterChip key={s.id} active={sort === s.id} onClick={() => setSort(s.id)}>
            {s.label}
          </FilterChip>
        ))}
      </div>
      {districts.length > 1 && (
        <div className="-mx-4 flex gap-2 overflow-x-auto px-4 pb-1 md:mx-0 md:px-0">
          <FilterChip active={district === ''} onClick={() => setDistrict('')}>
            Все районы
          </FilterChip>
          {districts.map((d) => (
            <FilterChip key={d} active={district === d} onClick={() => setDistrict(d)}>
              {d}
            </FilterChip>
          ))}
        </div>
      )}
      {isLoading && (
        <div className="grid gap-3">
          {[0, 1, 2].map((i) => (
            <Skeleton key={i} className="h-20 rounded-2xl" />
          ))}
        </div>
      )}
      {companies?.length === 0 && (
        <EmptyState icon={SearchX} title="Пока нет данных" description="Рейтинг появится, когда жители подадут обращения." />
      )}
      <div className="grid gap-3">
        {companies?.map((c) => (
          <CompanyCard key={c.id} company={c} />
        ))}
      </div>
      <p className="text-xs text-muted-foreground">
        Как считаем: 50% — доля решённых обращений, 30% — ответы в срок, 20% — обращения без эскалации. Меньше трёх обращений — мало данных.
      </p>
    </div>
  )
}
