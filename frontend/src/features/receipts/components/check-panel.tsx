import { CircleCheck, SearchCheck } from 'lucide-react'
import { Card } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { EmptyState } from '@/components/empty-state'
import { CONFIDENCE_LABELS } from '@/lib/design'
import { formatMoney } from '@/lib/money'
import { useCheck } from '../hooks'
import { LetterPanel } from './letter-panel'

export function CheckPanel({ receiptId }: { receiptId: string }) {
  const { data: check, isLoading } = useCheck(receiptId, true)

  if (isLoading) return <Skeleton className="h-48 rounded-2xl" />
  if (!check) return null
  if (check.findings.length === 0) {
    return (
      <EmptyState icon={CircleCheck} title="Нарушений не нашли" description="Начисления соответствуют тарифам региона. Если что-то смущает, спросите ассистента." />
    )
  }

  return (
    <div className="grid gap-4 animate-in fade-in-0 duration-300">
      <div className="flex items-start gap-3 rounded-2xl bg-warning/12 p-4">
        <SearchCheck className="mt-0.5 size-5 shrink-0 text-warning" />
        <div>
          <p className="font-medium">Возможная переплата: {formatMoney(check.total_possible_overpayment)}</p>
          <p className="text-sm text-muted-foreground">Это основание запросить перерасчёт, а не окончательный вывод.</p>
        </div>
      </div>
      {check.findings.map((f) => (
        <Card key={f.type + f.service_code} className="gap-2 rounded-2xl border-0 p-4 shadow-sm ring-1 ring-border">
          <div className="flex items-start justify-between gap-3">
            <p className="font-medium">{f.title}</p>
            <span className="shrink-0 font-semibold tabular-nums">{formatMoney(f.possible_overpayment)}</span>
          </div>
          <p className="text-sm text-muted-foreground">{f.description}</p>
          <p className="text-xs text-muted-foreground">{CONFIDENCE_LABELS[f.confidence]}</p>
        </Card>
      ))}
      <LetterPanel receiptId={receiptId} />
    </div>
  )
}
