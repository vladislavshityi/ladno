import { MapPin } from 'lucide-react'
import type { MapPoint } from '@/types/models'

const TOP = 5

/** Houses with the most active issues; picking one moves the map there. */
export function TopHouses({ points, onSelect }: { points: MapPoint[]; onSelect: (point: MapPoint) => void }) {
  const top = points
    .filter((p) => p.active > 0)
    .sort((a, b) => b.active - a.active)
    .slice(0, TOP)
  return (
    <div className="grid gap-2">
      <h2 className="text-sm font-medium">Больше всего активных обращений</h2>
      {top.length === 0 && <p className="text-sm text-muted-foreground">Активных обращений нет</p>}
      <ul className="grid gap-1">
        {top.map((p) => (
          <li key={p.house_id}>
            <button
              type="button"
              onClick={() => onSelect(p)}
              className="flex w-full items-start gap-2 rounded-xl p-2 text-left text-sm transition-colors hover:bg-muted"
            >
              <MapPin className="mt-0.5 size-3.5 shrink-0 text-muted-foreground" />
              <span className="min-w-0 flex-1">{p.address}</span>
              <span className="tabular-nums text-muted-foreground">{p.active}</span>
            </button>
          </li>
        ))}
      </ul>
    </div>
  )
}
