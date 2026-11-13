import { Link } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { Score } from '@/features/ratings/components/score-badge'
import { CategoryIcon } from '@/features/issues/category-icon'
import { useCategories } from '@/features/issues/hooks'
import type { MapPoint } from '@/types/models'

/** Mini card shown in the marker popup. */
export function HousePopup({ point }: { point: MapPoint }) {
  const { data: categories } = useCategories()
  const rows = Object.entries(point.categories).sort((a, b) => b[1] - a[1])
  const top = rows[0]?.[0]
  const company = point.management_company
  return (
    <div className="grid grid-cols-[minmax(0,1fr)] gap-3 p-4">
      <div className="grid gap-1">
        <p className="font-medium">{point.address}</p>
        {company && (
          <Link to={`/ratings/${company.id}`} className="flex items-baseline justify-between gap-2 text-xs text-muted-foreground hover:text-foreground">
            <span className="line-clamp-2">{company.name}</span>
            <Score score={company.score} className="shrink-0 text-sm" />
          </Link>
        )}
      </div>
      <ul className="flex flex-col gap-1.5 text-sm">
        {rows.map(([id, count]) => {
          const category = categories?.find((c) => c.id === id)
          return (
            <li key={id} className="flex items-center justify-between gap-3">
              <span className="flex min-w-0 items-center gap-2">
                <CategoryIcon name={category?.icon ?? ''} className="size-4 shrink-0 text-muted-foreground" />
                <span className="min-w-0 truncate">{category?.title ?? id}</span>
              </span>
              <span className="tabular-nums text-muted-foreground">{count}</span>
            </li>
          )
        })}
      </ul>
      <Button asChild size="sm">
        <Link to={`/issues/new?house_id=${point.house_id}&category=${top}`}>У меня тоже</Link>
      </Button>
    </div>
  )
}
