import { useState } from 'react'
import { Loader2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { FormField } from '@/components/form-field'
import type { ReceiptLine } from '@/types/models'
import { usePatchLine } from '../hooks'

interface Props {
  receiptId: string
  line: ReceiptLine
  onClose: () => void
}

const FIELDS = [
  { key: 'volume', label: 'Объём' },
  { key: 'tariff', label: 'Тариф' },
  { key: 'accrued', label: 'Начислено, ₽' },
] as const

/** Lets the resident fix values the recognition got wrong; totals are recalculated by the server. */
export function LineEditDialog({ receiptId, line, onClose }: Props) {
  const patch = usePatchLine(receiptId)
  const [values, setValues] = useState({
    volume: String(line.volume ?? ''),
    tariff: String(line.tariff ?? ''),
    accrued: String(line.accrued),
  })

  const save = () => {
    const num = (v: string) => (v.trim() === '' ? null : v.trim().replace(',', '.'))
    patch.mutate(
      { lineId: line.id, patch: { volume: num(values.volume), tariff: num(values.tariff), accrued: num(values.accrued) } },
      { onSuccess: onClose },
    )
  }

  return (
    <Dialog open onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="rounded-2xl">
        <DialogHeader>
          <DialogTitle>{line.service_name}</DialogTitle>
          <DialogDescription>Исправьте значения, если они распознаны неверно. Итоги пересчитаются.</DialogDescription>
        </DialogHeader>
        <div className="grid gap-4 sm:grid-cols-3">
          {FIELDS.map((f) => (
            <FormField key={f.key} label={f.label} htmlFor={`line-${f.key}`}>
              <Input
                id={`line-${f.key}`}
                inputMode="decimal"
                value={values[f.key]}
                onChange={(e) => setValues((v) => ({ ...v, [f.key]: e.target.value }))}
              />
            </FormField>
          ))}
        </div>
        <DialogFooter>
          <Button variant="ghost" onClick={onClose}>
            Отмена
          </Button>
          <Button onClick={save} disabled={patch.isPending}>
            {patch.isPending && <Loader2 className="animate-spin" />}
            Сохранить
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
