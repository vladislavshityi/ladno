import {
  ArrowUpDown,
  Brush,
  CircleAlert,
  Construction,
  DoorClosed,
  Droplets,
  Ellipsis,
  Lightbulb,
  PlugZap,
  Snowflake,
  SprayCan,
  Trash2,
  Waves,
  type LucideIcon,
} from 'lucide-react'

// Icon names come from the backend category directory.
const ICONS: Record<string, LucideIcon> = {
  lightbulb: Lightbulb,
  'spray-can': SprayCan,
  road: Construction,
  broom: Brush,
  elevator: ArrowUpDown,
  door: DoorClosed,
  droplets: Droplets,
  trash: Trash2,
  snowflake: Snowflake,
  'circle-alert': CircleAlert,
  'plug-zap': PlugZap,
  waves: Waves,
  'more-horizontal': Ellipsis,
}

export function CategoryIcon({ name, className }: { name: string; className?: string }) {
  const Icon = ICONS[name] ?? Ellipsis
  return <Icon className={className ?? 'size-4'} />
}
