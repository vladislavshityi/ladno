import { Phone, Siren } from 'lucide-react'
import type { Classification } from '@/types/models'
import { cn } from '@/lib/utils'

/** Emergencies come first: the phone numbers matter more than the rest of the wizard. */
export function EmergencyAlert({ emergency, className }: { emergency: NonNullable<Classification['emergency']>; className?: string }) {
  return (
    <div role="alert" className={cn('rounded-2xl border border-destructive/30 bg-destructive/10 p-4 animate-in fade-in-0 zoom-in-95 duration-300', className)}>
      <p className="flex items-center gap-2 font-semibold text-destructive">
        <Siren className="size-5" /> Это аварийная ситуация
      </p>
      <p className="mt-1 text-sm font-medium">{emergency.reason}</p>
      {emergency.advice && <p className="mt-1 text-sm">{emergency.advice}</p>}
      <ul className="mt-3 grid gap-2 sm:grid-cols-2">
        {emergency.contacts.map((c) => (
          <li key={c.value}>
            {c.type === 'phone' ? (
              <a
                href={`tel:${c.value.replace(/[^\d+]/g, '')}`}
                className="flex items-center gap-3 rounded-xl bg-background px-3 py-2 shadow-sm ring-1 ring-destructive/30 transition-colors hover:bg-destructive/5"
              >
                <span className="flex size-9 shrink-0 items-center justify-center rounded-full bg-destructive text-white">
                  <Phone className="size-4" />
                </span>
                <span className="flex min-w-0 flex-col">
                  <span className="text-xs text-muted-foreground">{c.label}</span>
                  <span className="text-lg font-semibold tabular-nums">{c.value}</span>
                </span>
                <span className="ml-auto text-xs font-medium text-destructive">Позвонить</span>
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
