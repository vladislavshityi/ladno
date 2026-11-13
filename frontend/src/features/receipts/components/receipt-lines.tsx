import { useState } from 'react'
import { Pencil } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { CALC_METHOD_LABELS } from '@/lib/design'
import { formatMoney, formatNumber } from '@/lib/money'
import type { Receipt, ReceiptLine } from '@/types/models'
import { LineEditDialog } from './line-edit-dialog'

function quantity(line: ReceiptLine) {
  if (line.volume == null || line.tariff == null) return null
  return `${formatNumber(line.volume)} ${line.unit ?? ''} × ${formatNumber(line.tariff)} ₽`
}

function LineRow({ line, onEdit }: { line: ReceiptLine; onEdit: () => void }) {
  const detail = quantity(line)
  return (
    <li className="grid gap-1.5 px-4 py-3.5">
      <div className="flex items-start justify-between gap-3">
        <p className="font-medium">{line.service_name}</p>
        <div className="flex items-center gap-1">
          <span className="font-semibold tabular-nums">{formatMoney(line.total)}</span>
          <Button variant="ghost" size="icon-sm" aria-label={`Исправить строку «${line.service_name}»`} onClick={onEdit}>
            <Pencil />
          </Button>
        </div>
      </div>
      <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-muted-foreground">
        {line.method !== 'unknown' && (
          <Badge variant={line.method === 'meter' ? 'secondary' : 'outline'} className="font-normal">
            {CALC_METHOD_LABELS[line.method]}
          </Badge>
        )}
        {detail && <span className="tabular-nums">{detail}</span>}
        {Number(line.recalculation) !== 0 && <span>перерасчёт {formatMoney(line.recalculation)}</span>}
      </div>
      {line.explanation && <p className="text-sm text-muted-foreground">{line.explanation}</p>}
    </li>
  )
}

export function ReceiptLines({ receipt }: { receipt: Receipt }) {
  const [editing, setEditing] = useState<ReceiptLine | null>(null)
  return (
    <Card className="gap-0 overflow-hidden rounded-2xl border-0 p-0 shadow-sm ring-1 ring-border">
      <ul className="divide-y">
        {receipt.lines.map((line) => (
          <LineRow key={line.id} line={line} onEdit={() => setEditing(line)} />
        ))}
      </ul>
      {editing && <LineEditDialog key={editing.id} receiptId={receipt.id} line={editing} onClose={() => setEditing(null)} />}
    </Card>
  )
}
