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

  it('explains what is wrong under each field', () => {
    expect(toManualReceipt({ ...filled(), period: '' })).toMatchObject({ ok: false, errors: { header: { period: 'Укажите месяц, за который квитанция' } } })
    expect(toManualReceipt({ ...filled(), inn: '123' })).toMatchObject({ ok: false, errors: { header: { inn: 'ИНН состоит из 10 или 12 цифр' } } })
    const noAmount = filled()
    noAmount.lines[0].accrued = ''
    expect(toManualReceipt(noAmount)).toMatchObject({ ok: false, errors: { lines: { [noAmount.lines[0].key]: { accrued: 'Укажите начислено' } } } })
    const noService = filled()
    noService.lines[0].service_name = ''
    expect(toManualReceipt(noService)).toMatchObject({ ok: false, errors: { lines: { [noService.lines[0].key]: { service: 'Выберите услугу' } } } })
    const bad = filled()
    bad.lines[0].volume = 'много'
    expect(toManualReceipt(bad)).toMatchObject({ ok: false })
  })

  it('applies the server limits', () => {
    expect(toManualReceipt({ ...filled(), residents: '31' })).toMatchObject({ ok: false })
    expect(toManualReceipt({ ...filled(), area: '0,5' })).toMatchObject({ ok: false })
    expect(toManualReceipt({ ...filled(), total: '1000000,01' })).toMatchObject({ ok: false })
    expect(toManualReceipt({ ...filled(), period: '2019-12' })).toMatchObject({ ok: false })
    const cents = filled()
    cents.lines[0].accrued = '10,005'
    expect(toManualReceipt(cents)).toMatchObject({ ok: false })
    const refund = filled()
    refund.lines[0].recalculation = '-150,50'
    expect(toManualReceipt(refund)).toMatchObject({ ok: true })
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
