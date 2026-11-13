import { Siren } from 'lucide-react'
import type { Classification } from '@/types/models'
import { cn } from '@/lib/utils'

/** Emergencies come first: the phone numbers matter more than the rest of the wizard. */
export function EmergencyAlert({ emergency, className }: { emergency: NonNullable<Classification['emergency']>; className?: string }) {
  return (
    <div role="alert" className={cn('rounded-2xl border border-destructive/30 bg-destructive/10 p-4 animate-in fade-in-0 zoom-in-95 duration-300', className)}>
      <p className="flex items-center gap-2 font-semibold text-destructive">
        <Siren className="size-5" /> Это аварийная ситуация
      </p>
      <p className="mt-1 text-sm">{emergency.reason}</p>
      <ul className="mt-3 grid gap-2 sm:grid-cols-2">
        {emergency.contacts.map((c) => (
          <li key={c.value}>
            {c.type === 'phone' ? (
              <a href={`tel:${c.value.replace(/[^\d+]/g, '')}`} className="flex flex-col rounded-xl bg-background px-3 py-2 ring-1 ring-border transition-colors hover:bg-muted">
                <span className="text-xs text-muted-foreground">{c.label}</span>
                <span className="text-lg font-semibold tabular-nums">{c.value}</span>
              </a>
            ) : (
              <span className="flex flex-col rounded-xl bg-background px-3 py-2 ring-1 ring-border">
                <span className="text-xs text-muted-foreground">{c.label}</span>
                <span className="font-medium">{c.value}</span>
              </span>
            )}
          </li>
        ))}
      </ul>
    </div>
  )
}
