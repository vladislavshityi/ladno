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

const DECIMAL = /^-?\d+(\.\d+)?$/

/** "1 234,50" to "1234.50"; null for an empty field, undefined for text that is not a number. */
function toDecimal(value: string): string | null | undefined {
  const text = value.replace(/[\s ]/g, '').replace(',', '.')
  if (text === '') return null
  return DECIMAL.test(text) ? text : undefined
}

export type FormResult = { ok: true; payload: ManualReceipt } | { ok: false; error: string }

/** Validates the form and converts it to the API body; amounts stay decimal strings. */
export function toManualReceipt(form: ReceiptForm): FormResult {
  if (!/^\d{4}-\d{2}$/.test(form.period)) return { ok: false, error: 'Укажите месяц, за который квитанция' }
  const header = { area_m2: toDecimal(form.area), total: toDecimal(form.total) }
  if (header.area_m2 === undefined) return { ok: false, error: 'Площадь должна быть числом' }
  if (header.total === undefined) return { ok: false, error: 'Итог должен быть числом' }
  if (form.residents.trim() && !/^\d{1,2}$/.test(form.residents.trim())) return { ok: false, error: 'Проживающих: целое число' }
  if (form.inn.trim() && !/^\d{10}(\d{2})?$/.test(form.inn.trim())) return { ok: false, error: 'ИНН состоит из 10 или 12 цифр' }

  const lines: ManualLine[] = []
  for (const [index, line] of form.lines.entries()) {
    const label = `Строка ${index + 1}`
    const volume = toDecimal(line.volume)
    const tariff = toDecimal(line.tariff)
    const accrued = toDecimal(line.accrued)
    const recalculation = toDecimal(line.recalculation)
    if (!line.service_name.trim()) return { ok: false, error: `${label}: выберите услугу` }
    if (volume === undefined || tariff === undefined || accrued === undefined || recalculation === undefined) {
      return { ok: false, error: `${label}: суммы и объёмы вводятся числами` }
    }
    if (accrued === null) return { ok: false, error: `${label}: укажите начислено` }
    lines.push({
      service_code: line.service_code,
      service_name: line.service_name.trim(),
      unit: line.unit.trim() || null,
      volume,
      tariff,
      accrued,
      recalculation: recalculation ?? '0',
      method: line.method,
    })
  }

  const name = form.companyName.trim()
  const inn = form.inn.trim()
  return {
    ok: true,
    payload: {
      period: form.period,
      management_company: name || inn ? { name: name || null, inn: inn || null } : null,
      account_last4: form.accountLast4 || null,
      area_m2: header.area_m2,
      residents: form.residents.trim() ? Number(form.residents) : null,
      total: header.total,
      lines,
    },
  }
}
