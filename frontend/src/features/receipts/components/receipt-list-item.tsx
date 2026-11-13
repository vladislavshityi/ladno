import { Link } from 'react-router-dom'
import { ChevronRight, ReceiptText, TriangleAlert } from 'lucide-react'
import { Card } from '@/components/ui/card'
import { formatMoney } from '@/lib/money'
import { formatPeriod } from '@/lib/dates'
import type { ReceiptShort } from '@/types/models'

export function ReceiptListItem({ receipt }: { receipt: ReceiptShort }) {
  return (
    <Link to={`/receipts/${receipt.id}`} className="group block rounded-2xl focus-visible:ring-3 focus-visible:ring-ring/50 focus-visible:outline-none">
      <Card className="flex-row items-center gap-3 rounded-2xl border-0 p-4 shadow-sm ring-1 ring-border transition-all group-hover:-translate-y-px group-hover:shadow-md">
        <div className="flex size-10 items-center justify-center rounded-xl bg-primary/10 text-primary">
          <ReceiptText className="size-5" />
        </div>
        <div className="min-w-0 flex-1">
          <p className="font-medium capitalize">{formatPeriod(receipt.period)}</p>
          {receipt.status === 'needs_review' && (
            <p className="flex items-center gap-1 text-xs text-warning">
              <TriangleAlert className="size-3" /> Проверьте распознанные значения
            </p>
          )}
        </div>
        <span className="font-semibold tabular-nums">{formatMoney(receipt.total)}</span>
        <ChevronRight className="size-4 text-muted-foreground transition-transform group-hover:translate-x-0.5" />
      </Card>
    </Link>
  )
}
