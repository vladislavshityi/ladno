import { AREA, MONEY, SIGNED_MONEY, TARIFF, VOLUME, checkDecimal, checkInn, checkPeriod, checkResidents, checkText, type Checked } from '@/lib/validation'
import type { ManualLine, ManualReceipt, ServiceOption } from '@/types/models'

export type Method = NonNullable<ManualLine['method']>

export const METHODS: { value: Method; label: string }[] = [
  { value: 'unknown', label: 'Не знаю' },
  { value: 'meter', label: 'По счётчику' },
  { value: 'norm', label: 'По нормативу' },
  { value: 'norm_increased', label: 'Норматив с коэффициентом 1,5' },
]

export interface LineForm {
  key: number
  service_code: ManualLine['service_code']
  service_name: string
  unit: string
  volume: string
  tariff: string
  accrued: string
  recalculation: string
  method: Method
  /** The tariff came from the regional directory and follows the period. */
  tariffAuto: boolean
}

export interface ReceiptForm {
  period: string
  companyName: string
  inn: string
  accountLast4: string
  area: string
  residents: string
  total: string
  lines: LineForm[]
}

let nextKey = 1

export const emptyLine = (): LineForm => ({
  key: nextKey++,
  service_code: 'other',
  service_name: '',
  unit: '',
  volume: '',
  tariff: '',
  accrued: '',
  recalculation: '',
  method: 'unknown',
  tariffAuto: false,
})

export const emptyForm = (): ReceiptForm => ({
  period: '',
  companyName: '',
  inn: '',
  accountLast4: '',
  area: '',
  residents: '',
  total: '',
  lines: [emptyLine()],
})

/** Picks a service from the directory: its name, unit and, if known, the regional tariff. */
export function applyService(line: LineForm, option: ServiceOption): LineForm {
  return {
    ...line,
    service_code: option.service_code,
    service_name: option.name,
    unit: option.unit ?? '',
    tariff: option.tariff ?? '',
    tariffAuto: true,
  }
}

/** When the period changes, tariffs that were filled from the directory follow it. */
export function refreshTariffs(lines: LineForm[], options: ServiceOption[]): LineForm[] {
  return lines.map((line) => {
    if (!line.tariffAuto) return line
    return { ...line, tariff: options.find((o) => o.service_code === line.service_code)?.tariff ?? '' }
  })
}

type HeaderKey = 'period' | 'total' | 'companyName' | 'inn' | 'area' | 'residents'
type LineKey = 'service' | 'unit' | 'volume' | 'tariff' | 'accrued' | 'recalculation'

/** Messages to show under the fields: header fields by name, lines by their key. */
export interface ReceiptErrors {
  header: Partial<Record<HeaderKey, string>>
  lines: Record<number, Partial<Record<LineKey, string>>>
}

export type FormResult = { ok: true; payload: ManualReceipt } | { ok: false; errors: ReceiptErrors }

const valueOf = (checked: Checked) => (checked.ok ? checked.value : null)

/** Validates the form with the server's rules and converts it to the API body; amounts stay decimal strings. */
export function toManualReceipt(form: ReceiptForm): FormResult {
  const errors: ReceiptErrors = { header: {}, lines: {} }
  const header = (key: HeaderKey, checked: Checked) => {
    if (!checked.ok) errors.header[key] = checked.error
    return valueOf(checked)
  }
  const period = header('period', checkPeriod(form.period))
  const area = header('area', checkDecimal(form.area, AREA))
  const total = header('total', checkDecimal(form.total, { ...MONEY, label: 'Итог' }))
  const residents = header('residents', checkResidents(form.residents))
  const name = header('companyName', checkText(form.companyName, 200))
  const inn = header('inn', checkInn(form.inn))

  const lines: ManualLine[] = []
  for (const line of form.lines) {
    const found: Partial<Record<LineKey, string>> = {}
    const read = (key: LineKey, checked: Checked) => {
      if (!checked.ok) found[key] = checked.error
      return valueOf(checked)
    }
    if (!line.service_name.trim()) found.service = 'Выберите услугу'
    const unit = read('unit', checkText(line.unit, 20))
    const volume = read('volume', checkDecimal(line.volume, VOLUME))
    const tariff = read('tariff', checkDecimal(line.tariff, TARIFF))
    const accrued = read('accrued', checkDecimal(line.accrued, { ...MONEY, label: 'Начислено' }))
    const recalculation = read('recalculation', checkDecimal(line.recalculation, SIGNED_MONEY))
    if (accrued === null && !found.accrued) found.accrued = 'Укажите начислено'
    if (Object.keys(found).length) errors.lines[line.key] = found
    lines.push({
      service_code: line.service_code,
      service_name: line.service_name.trim(),
      unit,
      volume,
      tariff,
      accrued: accrued ?? '0',
      recalculation: recalculation ?? '0',
      method: line.method,
    })
  }

  if (Object.keys(errors.header).length || Object.keys(errors.lines).length) return { ok: false, errors }
  return {
    ok: true,
    payload: {
      period: period!,
      management_company: name || inn ? { name, inn } : null,
      account_last4: form.accountLast4 || null,
      area_m2: area,
      residents: residents === null ? null : Number(residents),
      total,
      lines,
    },
  }
}

/** The first message of a failed check, for places that show a single line. */
export function firstError(errors: ReceiptErrors): string {
  return Object.values(errors.header)[0] ?? Object.values(Object.values(errors.lines)[0] ?? {})[0] ?? ''
}
