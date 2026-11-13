import { BadgeCheck, CalendarClock, Scale } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { formatDeadlineDays } from '@/lib/dates'
import type { RouteResult } from '@/types/models'
import { ChannelLink } from './channel-link'
import { EscalationChain } from './escalation-chain'

type Deadline = NonNullable<RouteResult['response_deadline']>

const deadlineText = (d: Deadline) => formatDeadlineDays(d.days, d.type)

function DeadlineRow({ label, deadline }: { label: string; deadline: Deadline }) {
  return (
    <div className="flex items-start gap-3">
      <CalendarClock className="mt-0.5 size-4 shrink-0 text-primary" />
      <div>
        <p className="text-sm text-muted-foreground">{label}</p>
        <p className="font-medium">{deadlineText(deadline)}</p>
        <p className="text-xs text-muted-foreground">{deadline.source}</p>
      </div>
    </div>
  )
}

/** Who to write to, on what grounds, how long to wait and where to go next. */
export function RoutePanel({ route }: { route: RouteResult }) {
  return (
    <Card className="rounded-2xl border-0 shadow-sm ring-1 ring-border">
      <CardHeader>
        <p className="text-xs font-medium text-primary">Адресат</p>
        <CardTitle className="text-lg">{route.addressee.name}</CardTitle>
        {route.explanation && <p className="text-sm text-muted-foreground">{route.explanation}</p>}
      </CardHeader>
      <CardContent className="grid gap-5">
        {route.addressee.channels.length > 0 && (
          <div className="flex flex-wrap gap-2">
            {route.addressee.channels.map((c) => (
              <ChannelLink key={`${c.type}-${c.value}`} channel={c} />
            ))}
          </div>
        )}
        {(route.response_deadline || route.fix_deadline) && (
          <div className="grid gap-3 sm:grid-cols-2">
            {route.response_deadline && <DeadlineRow label="Срок ответа" deadline={route.response_deadline} />}
            {route.fix_deadline && <DeadlineRow label="Срок устранения" deadline={route.fix_deadline} />}
          </div>
        )}
        {route.basis.length > 0 && (
          <div className="grid gap-2">
            <p className="text-sm font-medium">На чём основаны требования</p>
            <ul className="grid gap-2">
              {route.basis.map((b) => (
                <li key={b.text} className="flex items-start gap-3 text-sm">
                  {b.verified ? <BadgeCheck className="mt-0.5 size-4 shrink-0 text-success" /> : <Scale className="mt-0.5 size-4 shrink-0 text-muted-foreground" />}
                  <span>
                    {b.text} <span className="text-muted-foreground">({b.source})</span>
                  </span>
                </li>
              ))}
            </ul>
          </div>
        )}
        {route.escalation.length > 0 && <EscalationChain addressee={route.addressee.name} steps={route.escalation} />}
      </CardContent>
    </Card>
  )
}
