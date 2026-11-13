import { TriangleAlert } from 'lucide-react'
import { Card, CardContent } from '@/components/ui/card'
import { formatNumber, formatMoney } from '@/lib/money'
import { formatPeriod } from '@/lib/dates'
import type { Receipt } from '@/types/models'

export function ReceiptSummary({ receipt }: { receipt: Receipt }) {
  const details = [
    receipt.management_company?.name,
    receipt.area_m2 && `${formatNumber(receipt.area_m2)} м²`,
    receipt.residents && `проживающих: ${receipt.residents}`,
    receipt.account_last4 && `лицевой счёт •••• ${receipt.account_last4}`,
  ].filter(Boolean)

  return (
    <div className="grid gap-3">
      <Card className="rounded-2xl border-0 shadow-sm ring-1 ring-border">
        <CardContent className="grid gap-1">
          <p className="text-sm font-medium text-primary capitalize">{formatPeriod(receipt.period)}</p>
          <p className="text-4xl font-semibold tracking-tight tabular-nums">{formatMoney(receipt.total)}</p>
          <p className="text-sm text-muted-foreground">{details.join(' · ')}</p>
        </CardContent>
      </Card>
      {receipt.warnings.length > 0 && (
        <div role="alert" className="grid gap-1.5 rounded-2xl bg-warning/12 p-4 text-sm">
          <p className="flex items-center gap-2 font-medium text-warning">
            <TriangleAlert className="size-4" /> Проверьте значения
          </p>
          <ul className="list-disc pl-5">
            {receipt.warnings.map((w) => (
              <li key={w}>{w}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}
