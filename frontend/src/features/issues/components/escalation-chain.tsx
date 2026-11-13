import { ChevronRight } from 'lucide-react'
import type { RouteResult } from '@/types/models'

/** If the addressee is silent, the next one on this ladder gets the complaint. */
export function EscalationChain({ addressee, steps }: { addressee: string; steps: RouteResult['escalation'] }) {
  return (
    <div className="grid gap-2">
      <p className="text-sm font-medium">Порядок обращения</p>
      <p className="text-xs text-muted-foreground">
        Сейчас — первый адресат; если не ответят в срок, обращаемся к следующему.
      </p>
      <ol className="flex flex-wrap items-center gap-1.5 text-sm">
        {[addressee, ...steps.map((s) => s.name)].map((name, i) => (
          <li key={name} className="flex items-center gap-1.5">
            {i > 0 && <ChevronRight className="size-3.5 text-muted-foreground" />}
            <span className={i === 0 ? 'rounded-lg bg-primary/10 px-2 py-1 font-medium text-primary' : 'rounded-lg bg-muted px-2 py-1'}>{name}</span>
          </li>
        ))}
      </ol>
    </div>
  )
}
