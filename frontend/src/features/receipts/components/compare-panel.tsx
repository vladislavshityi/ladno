import { useState } from 'react'
import { GitCompareArrows } from 'lucide-react'
import { EmptyState } from '@/components/empty-state'
import { Skeleton } from '@/components/ui/skeleton'
import { formatPeriod } from '@/lib/dates'
import { COMPARE_FLAG_LABELS } from '@/lib/design'
import { formatMoney, formatSigned } from '@/lib/money'
import { cn } from '@/lib/utils'
import type { Receipt } from '@/types/models'
import { useCompare, useReceipts } from '../hooks'
import { CompareExplanation } from './compare-explanation'
import { CompareLineCard } from './compare-line-card'

export function ComparePanel({ receipt }: { receipt: Receipt }) {
  const { data: receipts } = useReceipts()
  // Earlier periods first: the most recent earlier receipt is the natural baseline.
  const others = (receipts ?? []).filter((r) => r.id !== receipt.id && (!receipt.period || !r.period || r.period < receipt.period))
  const [picked, setPicked] = useState<string>()
  const base = picked ?? others[0]?.id
  const { data: compare, isLoading } = useCompare(base, receipt.id)

  if (receipts && others.length === 0) {
    return (
      <EmptyState
        icon={GitCompareArrows}
        title="Не с чем сравнивать"
        description="Загрузите квитанцию за предыдущий месяц, и мы покажем, что изменилось."
      />
    )
  }

  const changed = compare?.lines.filter((l) => Number(l.delta) !== 0).sort((a, b) => Math.abs(Number(b.delta)) - Math.abs(Number(a.delta)))
  const same = compare?.lines.filter((l) => Number(l.delta) === 0)

  return (
    <div className="grid gap-4">
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-sm text-muted-foreground">Сравнить с:</span>
        {others.map((r) => (
          <button
            key={r.id}
            type="button"
            aria-pressed={r.id === base}
            onClick={() => setPicked(r.id)}
            className={cn('rounded-full border px-3 py-1 text-sm capitalize transition-colors hover:bg-muted', r.id === base && 'border-primary bg-primary/10 font-medium text-primary')}
          >
            {formatPeriod(r.period)}
          </button>
        ))}
      </div>
      {isLoading && (
        <div className="grid gap-4" role="status" aria-label="Считаем сравнение">
          <Skeleton className="h-32 rounded-2xl" />
          <Skeleton className="h-28 rounded-2xl" />
          <Skeleton className="h-28 rounded-2xl" />
        </div>
      )}
      {compare && changed && same && (
        <div className="grid gap-4 animate-in fade-in-0 duration-300">
          <div className="rounded-2xl bg-card p-4 shadow-sm ring-1 ring-border">
            <p className="text-sm text-muted-foreground">
              {formatPeriod(compare.base_period)} → {formatPeriod(compare.target_period)}
            </p>
            <p className="mt-1 flex flex-wrap items-baseline gap-x-3">
              <span className="text-2xl font-semibold tabular-nums">{formatMoney(compare.total_target)}</span>
              <span className={cn('font-medium tabular-nums', Number(compare.total_delta) > 0 ? 'text-warning' : 'text-success')}>
                {formatSigned(compare.total_delta)}
              </span>
            </p>
            {compare.flags.length > 0 && (
              <p className="mt-2 text-sm text-muted-foreground">{compare.flags.map((f) => COMPARE_FLAG_LABELS[f]).join(' · ')}</p>
            )}
          </div>
          <CompareExplanation base={base!} target={receipt.id} />
          {changed.map((l) => (
            <CompareLineCard key={l.service_code + l.service_name} line={l} />
          ))}
          {same.length > 0 && (
            <p className="text-sm text-muted-foreground">Без изменений: {same.map((l) => l.service_name).join(', ')}.</p>
          )}
        </div>
      )}
    </div>
  )
}
