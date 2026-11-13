import { useMemo, useState } from 'react'
import { divIcon, DomEvent, type LatLngBoundsLiteral, type Map as LeafletMap } from 'leaflet'
import { CircleMarker, MapContainer, Marker, Popup, TileLayer, useMap, useMapEvents } from 'react-leaflet'
import { Minus, Plus } from 'lucide-react'
import Supercluster from 'supercluster'
import { Button } from '@/components/ui/button'
import { openExternal } from '@/lib/telegram'
import type { MapPoint } from '@/types/models'
import { HousePopup } from './house-popup'
import '../map.css'

const VLADIVOSTOK: [number, number] = [43.1155, 131.8855]
const DEFAULT_ZOOM = 12
const MAX_ZOOM = 18

// CARTO basemaps now need an API key, so the map uses OpenStreetMap tiles muted by a CSS filter.
const TILES_URL = 'https://tile.openstreetmap.org/{z}/{x}/{y}.png'

const dotRadius = (total: number) => Math.min(14, 6 + total * 1.5)
const dotOpacity = (total: number) => Math.min(0.95, 0.5 + total * 0.08)

function clusterIcon(count: number) {
  const size = count < 10 ? 32 : count < 50 ? 38 : 44
  return divIcon({
    html: `<div class="map-cluster" style="width:${size}px;height:${size}px">${count}</div>`,
    className: '',
    iconSize: [size, size],
  })
}

function ZoomControls() {
  const map = useMap()
  return (
    // Clicks on the buttons must not reach the map underneath.
    <div ref={(el) => { if (el) DomEvent.disableClickPropagation(el) }} className="absolute top-3 right-3 z-[1000] grid gap-2">
      <Button variant="outline" size="icon" className="rounded-xl shadow-sm" aria-label="Приблизить" onClick={() => map.zoomIn()}>
        <Plus />
      </Button>
      <Button variant="outline" size="icon" className="rounded-xl shadow-sm" aria-label="Отдалить" onClick={() => map.zoomOut()}>
        <Minus />
      </Button>
    </div>
  )
}

function Attribution() {
  return (
    <p className="absolute right-2 bottom-1.5 z-[1000] rounded-md bg-background/70 px-1.5 py-0.5 text-[10px] text-muted-foreground backdrop-blur">
      ©{' '}
      <button type="button" className="hover:underline" onClick={() => openExternal('https://www.openstreetmap.org/copyright')}>
        OpenStreetMap
      </button>
    </p>
  )
}

/** Groups nearby houses into numbered clusters and draws the rest as dots. */
function PointsLayer({ points }: { points: MapPoint[] }) {
  const map = useMap()
  const index = useMemo(() => {
    const cluster = new Supercluster<{ point: MapPoint }>({ radius: 56, maxZoom: MAX_ZOOM - 1 })
    cluster.load(
      points.map((point) => ({
        type: 'Feature',
        properties: { point },
        geometry: { type: 'Point', coordinates: [point.lon, point.lat] },
      })),
    )
    return cluster
  }, [points])

  const view = () => {
    const b = map.getBounds()
    return { bbox: [b.getWest(), b.getSouth(), b.getEast(), b.getNorth()] as [number, number, number, number], zoom: map.getZoom() }
  }
  const [{ bbox, zoom }, setView] = useState(view)
  useMapEvents({ moveend: () => setView(view()) })

  return index.getClusters(bbox, zoom).map((feature) => {
    const [lon, lat] = feature.geometry.coordinates
    const { cluster, cluster_id: id, point_count: count, point } = feature.properties as {
      cluster?: boolean
      cluster_id: number
      point_count: number
      point: MapPoint
    }
    if (cluster) {
      return (
        <Marker
          key={`cluster-${id}-${count}`}
          position={[lat, lon]}
          icon={clusterIcon(count)}
          eventHandlers={{ click: () => map.flyTo([lat, lon], Math.min(index.getClusterExpansionZoom(id), MAX_ZOOM)) }}
        />
      )
    }
    return (
      <CircleMarker
        // The class is read only when the marker is created, so the key must change with it.
        key={`${point.house_id}-${point.emergency}`}
        center={[lat, lon]}
        radius={dotRadius(point.total)}
        className={point.emergency ? 'map-dot map-dot-emergency' : 'map-dot'}
        pathOptions={{ weight: 2, fillOpacity: dotOpacity(point.total), opacity: 1 }}
      >
        {/* Extra padding on the right keeps an auto-panned popup clear of the zoom buttons. */}
        <Popup
          className="map-popup"
          closeButton={false}
          minWidth={256}
          maxWidth={256}
          autoPanPaddingTopLeft={[16, 16]}
          autoPanPaddingBottomRight={[64, 16]}
        >
          <HousePopup point={point} />
        </Popup>
      </CircleMarker>
    )
  })
}

interface Props {
  points: MapPoint[]
  onReady: (map: LeafletMap) => void
}

export function ProblemMap({ points, onReady }: Props) {
  const bounds: LatLngBoundsLiteral = [
    [42.6, 131.3],
    [43.5, 132.6],
  ]
  return (
    <MapContainer
      ref={(map) => {
        if (map) onReady(map)
      }}
      center={VLADIVOSTOK}
      zoom={DEFAULT_ZOOM}
      maxZoom={MAX_ZOOM}
      maxBounds={bounds}
      zoomControl={false}
      attributionControl={false}
      className="size-full"
    >
      <TileLayer url={TILES_URL} className="map-tiles" />
      <PointsLayer points={points} />
      <ZoomControls />
      <Attribution />
    </MapContainer>
  )
}
