import { useState } from 'react'
import type { Map as LeafletMap } from 'leaflet'
import { ListOrdered } from 'lucide-react'
import { DemoBadge } from '@/components/demo-badge'
import { PageHeader } from '@/components/page-header'
import { Button } from '@/components/ui/button'
import { Sheet, SheetContent, SheetHeader, SheetTitle } from '@/components/ui/sheet'
import { isTelegramWebApp } from '@/lib/telegram'
import { cn } from '@/lib/utils'
import type { MapPoint } from '@/types/models'
import type { MapFilters } from '../api'
import { MapFiltersBar } from '../components/map-filters'
import { ProblemMap } from '../components/problem-map'
import { TopHouses } from '../components/top-houses'
import { useMapPoints } from '../hooks'

const FOCUS_ZOOM = 17

export default function MapPage() {
  const [filters, setFilters] = useState<MapFilters>({ category: '', days: 30, active: false })
  const [map, setMap] = useState<LeafletMap | null>(null)
  const [listOpen, setListOpen] = useState(false)
  const { data: points = [] } = useMapPoints(filters)

  const focus = (point: MapPoint) => {
    setListOpen(false)
    map?.flyTo([point.lat, point.lon], FOCUS_ZOOM)
  }
  const top = <TopHouses points={points} onSelect={focus} />

  return (
    <div className="grid gap-4">
      <PageHeader title="Карта проблем" description="Где жители уже обращались: по домам, без личных данных" actions={<DemoBadge />} />
      <MapFiltersBar filters={filters} onChange={setFilters} />
      <div className="grid gap-4 md:grid-cols-[1fr_16rem]">
        <div
          className={cn(
            // isolate keeps Leaflet's high z-indexes inside the map, under sheets and dialogs.
            'relative isolate min-h-80 overflow-hidden rounded-2xl border border-border',
            // The Mini App has no browser chrome, so the map can take more of the viewport.
            isTelegramWebApp() ? 'h-[calc(100svh-19rem)] md:h-[calc(100svh-14rem)]' : 'h-[calc(100svh-21rem)] md:h-[calc(100svh-14rem)]',
          )}
        >
          <ProblemMap points={points} onReady={setMap} />
          <Button
            variant="outline"
            size="sm"
            className="absolute bottom-6 left-3 z-[1000] rounded-xl shadow-sm md:hidden"
            onClick={() => setListOpen(true)}
          >
            <ListOrdered /> Топ домов
          </Button>
        </div>
        <aside className="hidden self-start rounded-2xl border border-border bg-card p-3 md:block">{top}</aside>
      </div>
      <Sheet open={listOpen} onOpenChange={setListOpen}>
        <SheetContent side="bottom" className="rounded-t-2xl p-4">
          <SheetHeader className="p-0">
            <SheetTitle className="sr-only">Топ домов</SheetTitle>
          </SheetHeader>
          {top}
        </SheetContent>
      </Sheet>
    </div>
  )
}
