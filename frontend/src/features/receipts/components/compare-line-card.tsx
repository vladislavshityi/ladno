import { ArrowRight } from 'lucide-react'
import { Card } from '@/components/ui/card'
import { cn } from '@/lib/utils'
import { LINE_FLAG_LABELS, TONE_CLASSES } from '@/lib/design'
import { formatMoney, formatSigned } from '@/lib/money'
import type { CompareLine } from '@/types/models'

const direction = (delta: string) => (Number(delta) > 0 ? 'up' : Number(delta) < 0 ? 'down' : 'flat')

const DELTA_TEXT = { up: 'text-warning', down: 'text-success', flat: 'text-muted-foreground' }

function Part({ label, value }: { label: string; value: string }) {
  const dir = direction(value)
  return (
    <div className="rounded-lg bg-muted/60 px-2.5 py-1.5">
      <p className="text-[11px] text-muted-foreground">{label}</p>
      <p className={cn('text-sm font-medium tabular-nums', DELTA_TEXT[dir])}>{dir === 'flat' ? '—' : formatSigned(value)}</p>
    </div>
  )
}

export function CompareLineCard({ line }: { line: CompareLine }) {
  const dir = direction(line.delta)
  return (
    <Card
      className={cn(
        'gap-3 rounded-2xl border-0 p-4 shadow-sm ring-1',
        dir === 'up' && 'bg-warning/6 ring-warning/30',
        dir === 'down' && 'bg-success/6 ring-success/30',
        dir === 'flat' && 'ring-border',
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <p className="font-medium">{line.service_name}</p>
        <div className="text-right">
          <p className={cn('font-semibold tabular-nums', DELTA_TEXT[dir])}>{formatSigned(line.delta)}</p>
          {line.delta_pct != null && dir !== 'flat' && (
            <p className={cn('text-xs tabular-nums', DELTA_TEXT[dir])}>{Number(line.delta_pct) > 0 ? '+' : ''}{line.delta_pct}%</p>
          )}
        </div>
      </div>
      <p className="flex items-center gap-1.5 text-sm text-muted-foreground tabular-nums">
        {formatMoney(line.accrued_base)} <ArrowRight className="size-3.5" /> {formatMoney(line.accrued_target)}
      </p>
      {dir !== 'flat' && (
        <div className="grid grid-cols-3 gap-2">
          <Part label="Тариф" value={line.delta_tariff} />
          <Part label="Объём" value={line.delta_volume} />
          <Part label="Прочее" value={line.delta_other} />
        </div>
      )}
      {line.flags.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {line.flags.map((f) => (
            <span key={f} className={cn('rounded-full px-2 py-0.5 text-xs font-medium', TONE_CLASSES.warning)}>
              {LINE_FLAG_LABELS[f]}
            </span>
          ))}
        </div>
      )}
    </Card>
  )
}
