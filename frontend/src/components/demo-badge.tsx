import { useCapabilities } from '@/features/meta/hooks'

/** Quiet note shown when the server runs on demo data. */
export function DemoBadge() {
  const { demoData } = useCapabilities()
  if (!demoData) return null
  return <span className="rounded-full bg-muted px-2.5 py-0.5 text-xs text-muted-foreground">демо-данные</span>
}
