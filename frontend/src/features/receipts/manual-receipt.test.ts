import { describe, expect, it } from 'vitest'
import type { ServiceOption } from '@/types/models'
import { applyService, emptyForm, refreshTariffs, toManualReceipt, type ReceiptForm } from './manual-receipt'

const water: ServiceOption = { service_code: 'cold_water', name: 'Холодное водоснабжение', unit: 'м3', tariff: '53.4360' }

function filled(): ReceiptForm {
  const form = emptyForm()
  const line = applyService(form.lines[0], water)
  return { ...form, period: '2026-11', lines: [{ ...line, volume: '8,3', accrued: '1 443,52' }] }
}

describe('toManualReceipt', () => {
  it('converts decimal commas and spaces, keeping amounts as strings', () => {
    const result = toManualReceipt({ ...filled(), area: '54,3', total: '' })
    expect(result).toMatchObject({
      ok: true,
      payload: { period: '2026-11', area_m2: '54.3', total: null, management_company: null },
    })
    if (result.ok) expect(result.payload.lines[0]).toMatchObject({ volume: '8.3', tariff: '53.4360', accrued: '1443.52', recalculation: '0' })
  })

  it('sends the company only when something is filled in', () => {
    const result = toManualReceipt({ ...filled(), companyName: ' ООО «УК» ', inn: '2540111333' })
    expect(result).toMatchObject({ ok: true, payload: { management_company: { name: 'ООО «УК»', inn: '2540111333' } } })
  })

  it('explains what is wrong', () => {
    expect(toManualReceipt({ ...filled(), period: '' })).toEqual({ ok: false, error: 'Укажите месяц, за который квитанция' })
    expect(toManualReceipt({ ...filled(), inn: '123' })).toMatchObject({ ok: false })
    const noAmount = filled()
    noAmount.lines[0].accrued = ''
    expect(toManualReceipt(noAmount)).toEqual({ ok: false, error: 'Строка 1: укажите начислено' })
    const noService = filled()
    noService.lines[0].service_name = ''
    expect(toManualReceipt(noService)).toEqual({ ok: false, error: 'Строка 1: выберите услугу' })
    const bad = filled()
    bad.lines[0].volume = 'много'
    expect(toManualReceipt(bad)).toMatchObject({ ok: false })
  })
})

describe('tariff autofill', () => {
  it('follows the period only for tariffs taken from the directory', () => {
    const [auto] = filled().lines
    const manual = { ...auto, key: 99, tariff: '60', tariffAuto: false }
    const cheaper = [{ ...water, tariff: '46.8724' }]
    const [a, m] = refreshTariffs([auto, manual], cheaper)
    expect(a.tariff).toBe('46.8724')
    expect(m.tariff).toBe('60')
  })

  it('clears an auto tariff that is unknown for the new period', () => {
    const [line] = refreshTariffs(filled().lines, [{ ...water, tariff: null }])
    expect(line.tariff).toBe('')
  })
})
