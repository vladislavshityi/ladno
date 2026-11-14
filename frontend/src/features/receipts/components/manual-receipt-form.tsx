import { useState } from 'react'
import { Loader2, Plus, Trash2 } from 'lucide-react'
import { toast } from 'sonner'
import { FormField } from '@/components/form-field'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { errorMessage } from '@/lib/api-client'
import { FIRST_PERIOD, lastPeriod } from '@/lib/validation'
import type { Receipt } from '@/types/models'
import { useCreateManualReceipt, useServices } from '../hooks'
import { applyService, emptyLine, firstError, METHODS, refreshTariffs, toManualReceipt, type LineForm, type ReceiptErrors, type ReceiptForm } from '../manual-receipt'

const SELECT =
  'h-10 w-full rounded-lg border border-input bg-transparent px-3 text-base outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 md:text-sm dark:bg-input/30'

/** What the scanned QR code said about the receipt, and what it left out. */
export interface QrNote {
  payee: string | null
  inn: string | null
  missingTotal: boolean
  missingPeriod: boolean
}

const MISSING = 'border-amber-500 ring-3 ring-amber-500/30'

interface Props {
  note?: QrNote | null
  initial: ReceiptForm
  onCancel: () => void
  onCreated: (receipt: Receipt) => void
}

/** A receipt typed in by hand: the same checks run as for a recognised one. */
export function ManualReceiptForm({ initial, note, onCancel, onCreated }: Props) {
  const [form, setForm] = useState(initial)
  const [errors, setErrors] = useState<ReceiptErrors>({ header: {}, lines: {} })
  const create = useCreateManualReceipt()
  const { data: services = [] } = useServices(form.period)
  // A new period brings its own tariffs to the lines that took theirs from the directory.
  const lines = refreshTariffs(form.lines, services)

  // Editing a field clears its message; the whole form is checked again on submit.
  const set = (patch: Partial<ReceiptForm>) => {
    setForm((f) => ({ ...f, ...patch }))
    setErrors((e) => ({ ...e, header: { ...e.header, ...Object.fromEntries(Object.keys(patch).map((k) => [k, undefined])) } }))
  }
  const setLine = (key: number, patch: Partial<LineForm>) => {
    setForm((f) => ({ ...f, lines: f.lines.map((l) => (l.key === key ? { ...l, ...patch } : l)) }))
    setErrors((e) => ({ ...e, lines: { ...e.lines, [key]: { ...e.lines[key], ...Object.fromEntries(Object.keys(patch).map((k) => [k, undefined])) } } }))
  }

  const pickService = (key: number, code: string) => {
    const option = services.find((s) => s.service_code === code)
    if (!option) return
    setForm((f) => ({ ...f, lines: f.lines.map((l) => (l.key === key ? applyService(l, option) : l)) }))
    setErrors((e) => ({ ...e, lines: { ...e.lines, [key]: { ...e.lines[key], service: undefined, tariff: undefined } } }))
  }

  const submit = () => {
    const result = toManualReceipt({ ...form, lines })
    if (!result.ok) {
      setErrors(result.errors)
      toast.error(firstError(result.errors))
      return
    }
    setErrors({ header: {}, lines: {} })
    create.mutate(result.payload, {
      onSuccess: onCreated,
      // The server repeats the same checks; its message names the field.
      onError: (err) => toast.error(errorMessage(err)),
    })
  }

  return (
    <Card className="rounded-2xl border-0 shadow-sm ring-1 ring-border">
      <CardHeader>
        <CardTitle>Ввести квитанцию вручную</CardTitle>
        <CardDescription>Перепишите строки из квитанции. Тариф подставим из справочника, если он известен.</CardDescription>
      </CardHeader>
      <CardContent>
        <form
          className="grid gap-5"
          onSubmit={(e) => {
            e.preventDefault()
            submit()
          }}
        >
          {note && (
            <div className="grid gap-1 rounded-xl bg-muted/60 px-4 py-3 text-sm">
              {note.payee && (
                <p>
                  Получатель: {note.payee}
                  {note.inn && `, ИНН ${note.inn}`}
                </p>
              )}
              {(note.missingTotal || note.missingPeriod) && <p className="text-muted-foreground">В QR-коде нет суммы и периода — укажите их по квитанции</p>}
            </div>
          )}
          <div className="grid gap-4 sm:grid-cols-2">
            <FormField label="Месяц квитанции" htmlFor="period" error={errors.header.period}>
              <Input id="period" type="month" min={FIRST_PERIOD} max={lastPeriod()} aria-invalid={Boolean(errors.header.period)} className={note?.missingPeriod && !form.period ? MISSING : undefined} value={form.period} onChange={(e) => set({ period: e.target.value })} />
            </FormField>
            <FormField label="Итого к оплате, ₽" htmlFor="total" hint="Пусто — сложим строки" error={errors.header.total}>
              <Input id="total" inputMode="decimal" maxLength={12} aria-invalid={Boolean(errors.header.total)} className={note?.missingTotal && !form.total ? MISSING : undefined} value={form.total} onChange={(e) => set({ total: e.target.value })} />
            </FormField>
            <FormField label="Управляющая компания" htmlFor="company" error={errors.header.companyName}>
              <Input id="company" aria-invalid={Boolean(errors.header.companyName)} value={form.companyName} maxLength={200} onChange={(e) => set({ companyName: e.target.value })} />
            </FormField>
            <FormField label="ИНН компании" htmlFor="inn" error={errors.header.inn}>
              <Input id="inn" inputMode="numeric" aria-invalid={Boolean(errors.header.inn)} value={form.inn} maxLength={12} onChange={(e) => set({ inn: e.target.value })} />
            </FormField>
            <FormField label="Площадь, м²" htmlFor="area" error={errors.header.area}>
              <Input id="area" inputMode="decimal" maxLength={8} aria-invalid={Boolean(errors.header.area)} value={form.area} onChange={(e) => set({ area: e.target.value })} />
            </FormField>
            <FormField label="Проживающих" htmlFor="residents" error={errors.header.residents}>
              <Input id="residents" inputMode="numeric" aria-invalid={Boolean(errors.header.residents)} value={form.residents} maxLength={2} onChange={(e) => set({ residents: e.target.value })} />
            </FormField>
          </div>

          <div className="grid gap-3">
            <p className="text-sm font-medium">Строки квитанции</p>
            {lines.map((line, index) => (
              <fieldset key={line.key} className="grid gap-3 rounded-xl bg-muted/50 p-3">
                <legend className="sr-only">Строка {index + 1}</legend>
                <div className="flex gap-2">
                  <select
                    aria-invalid={Boolean(errors.lines[line.key]?.service)}
                    aria-label={`Услуга, строка ${index + 1}`}
                    className={SELECT}
                    value={line.service_name ? line.service_code : ''}
                    onChange={(e) => pickService(line.key, e.target.value)}
                  >
                    <option value="" disabled>
                      Выберите услугу
                    </option>
                    {services.map((s) => (
                      <option key={s.service_code} value={s.service_code}>
                        {s.name}
                      </option>
                    ))}
                  </select>
                  {lines.length > 1 && (
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      aria-label={`Удалить строку ${index + 1}`}
                      onClick={() => set({ lines: form.lines.filter((l) => l.key !== line.key) })}
                    >
                      <Trash2 />
                    </Button>
                  )}
                </div>
                {errors.lines[line.key]?.service && (
                  <p role="alert" className="-mt-1 text-xs text-destructive">
                    {errors.lines[line.key]?.service}
                  </p>
                )}
                <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
                  <FormField label="Ед. изм." htmlFor={`unit-${line.key}`} error={errors.lines[line.key]?.unit}>
                    <Input id={`unit-${line.key}`} aria-invalid={Boolean(errors.lines[line.key]?.unit)} value={line.unit} maxLength={20} onChange={(e) => setLine(line.key, { unit: e.target.value })} />
                  </FormField>
                  <FormField label="Объём" htmlFor={`volume-${line.key}`} error={errors.lines[line.key]?.volume}>
                    <Input id={`volume-${line.key}`} aria-invalid={Boolean(errors.lines[line.key]?.volume)} maxLength={12} inputMode="decimal" value={line.volume} onChange={(e) => setLine(line.key, { volume: e.target.value })} />
                  </FormField>
                  <FormField label="Тариф, ₽" htmlFor={`tariff-${line.key}`} error={errors.lines[line.key]?.tariff}>
                    <Input
                      id={`tariff-${line.key}`} aria-invalid={Boolean(errors.lines[line.key]?.tariff)} maxLength={12}
                      inputMode="decimal"
                      value={line.tariff}
                      onChange={(e) => setLine(line.key, { tariff: e.target.value, tariffAuto: false })}
                    />
                  </FormField>
                  <FormField label="Начислено, ₽" htmlFor={`accrued-${line.key}`} error={errors.lines[line.key]?.accrued}>
                    <Input id={`accrued-${line.key}`} aria-invalid={Boolean(errors.lines[line.key]?.accrued)} maxLength={12} inputMode="decimal" value={line.accrued} onChange={(e) => setLine(line.key, { accrued: e.target.value })} />
                  </FormField>
                  <FormField label="Перерасчёт, ₽" htmlFor={`recalc-${line.key}`} error={errors.lines[line.key]?.recalculation}>
                    <Input id={`recalc-${line.key}`} aria-invalid={Boolean(errors.lines[line.key]?.recalculation)} maxLength={12} inputMode="decimal" value={line.recalculation} onChange={(e) => setLine(line.key, { recalculation: e.target.value })} />
                  </FormField>
                  <FormField label="Как считали" htmlFor={`method-${line.key}`}>
                    <select
                      id={`method-${line.key}`}
                      className={SELECT}
                      value={line.method}
                      onChange={(e) => setLine(line.key, { method: e.target.value as LineForm['method'] })}
                    >
                      {METHODS.map((m) => (
                        <option key={m.value} value={m.value}>
                          {m.label}
                        </option>
                      ))}
                    </select>
                  </FormField>
                </div>
              </fieldset>
            ))}
            <Button type="button" variant="outline" className="justify-self-start" onClick={() => set({ lines: [...form.lines, emptyLine()] })}>
              <Plus /> Добавить строку
            </Button>
          </div>

          <div className="flex flex-wrap gap-2">
            <Button type="submit" size="lg" disabled={create.isPending}>
              {create.isPending && <Loader2 className="animate-spin" />}
              Сохранить и проверить
            </Button>
            <Button type="button" size="lg" variant="ghost" onClick={onCancel}>
              Отмена
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  )
}
