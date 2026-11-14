import { useState } from 'react'
import { Loader2 } from 'lucide-react'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { FormField } from '@/components/form-field'
import type { ReceiptLine } from '@/types/models'
import { errorMessage } from '@/lib/api-client'
import { MONEY, TARIFF, VOLUME, checkDecimal } from '@/lib/validation'
import { usePatchLine } from '../hooks'

interface Props {
  receiptId: string
  line: ReceiptLine
  onClose: () => void
}

const FIELDS = [
  { key: 'volume', label: 'Объём', rule: VOLUME },
  { key: 'tariff', label: 'Тариф', rule: TARIFF },
  { key: 'accrued', label: 'Начислено, ₽', rule: { ...MONEY, label: 'Начислено' } },
] as const

/** Lets the resident fix values the recognition got wrong; totals are recalculated by the server. */
export function LineEditDialog({ receiptId, line, onClose }: Props) {
  const patch = usePatchLine(receiptId)
  const [values, setValues] = useState({
    volume: String(line.volume ?? ''),
    tariff: String(line.tariff ?? ''),
    accrued: String(line.accrued),
  })

  const [errors, setErrors] = useState<Partial<Record<(typeof FIELDS)[number]['key'], string>>>({})

  const save = () => {
    const checked = FIELDS.map((f) => [f.key, checkDecimal(values[f.key], f.rule)] as const)
    const found = Object.fromEntries(checked.flatMap(([key, c]) => (c.ok ? [] : [[key, c.error]])))
    setErrors(found)
    if (Object.keys(found).length) return
    const [volume, tariff, accrued] = checked.map(([, c]) => (c.ok ? c.value : null))
    patch.mutate({ lineId: line.id, patch: { volume, tariff, accrued } }, { onSuccess: onClose, onError: (err) => toast.error(errorMessage(err)) })
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
            <FormField key={f.key} label={f.label} htmlFor={`line-${f.key}`} error={errors[f.key]}>
              <Input
                id={`line-${f.key}`}
                inputMode="decimal"
                maxLength={12}
                aria-invalid={Boolean(errors[f.key])}
                value={values[f.key]}
                onChange={(e) => {
                  setValues((v) => ({ ...v, [f.key]: e.target.value }))
                  setErrors((er) => ({ ...er, [f.key]: undefined }))
                }}
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
