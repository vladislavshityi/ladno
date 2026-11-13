import { describe, expect, it } from 'vitest'
import { parseEpdQr } from './epd-qr'

const RAW =
  'ST00012|Name=ООО «УК Центр»|PersonalAcc=40702810500000012345|BankName=Банк|BIC=044525225|PayeeINN=2540111333|Sum=1127407|PersAcc=0012347305|paymPeriod=112026|Purpose=ЖКУ'

describe('parseEpdQr', () => {
  it('reads the fields the form needs', () => {
    expect(parseEpdQr(RAW)).toEqual({
      total: '11274.07',
      period: '2026-11',
      inn: '2540111333',
      name: 'ООО «УК Центр»',
      accountLast4: '7305',
    })
  })

  it('reads a code without amount and period, with a comma-free payee and a different format id', () => {
    const raw =
      'ST00011|Name=ООО «Вымышленный водоканал»|PersonalAcc=40702810000000000001|BankName=Банк|BIC=044525000|CorrespAcc=30101810000000000000|PayeeINN=2503022413|KPP=250301001|persAcc=770022559|Techcode=005|'
    expect(parseEpdQr(raw)).toEqual({
      total: null,
      period: null,
      inn: '2503022413',
      name: 'ООО «Вымышленный водоканал»',
      accountLast4: '2559',
    })
  })

  it('converts kopecks to rubles', () => {
    expect(parseEpdQr('ST00012|Sum=5')?.total).toBe('0.05')
    expect(parseEpdQr('ST00012|Sum=100')?.total).toBe('1.00')
    expect(parseEpdQr('ST00012|Sum=abc')?.total).toBeNull()
  })

  it('accepts MM.YYYY and rejects an impossible month', () => {
    expect(parseEpdQr('ST00012|paymPeriod=03.2026')?.period).toBe('2026-03')
    expect(parseEpdQr('ST00012|paymPeriod=132026')?.period).toBeNull()
  })

  it('keeps only the last four digits of the account and drops everything else', () => {
    const parsed = parseEpdQr(RAW)
    expect(JSON.stringify(parsed)).not.toContain('0012347305')
    expect(JSON.stringify(parsed)).not.toContain('40702810500000012345')
  })

  it('supports other field separators', () => {
    expect(parseEpdQr('ST00012;Sum=250;PayeeINN=2537068720')).toMatchObject({ total: '2.50', inn: '2537068720' })
  })

  it('ignores a malformed INN and text that is not an EPD code', () => {
    expect(parseEpdQr('ST00012|PayeeINN=12')?.inn).toBeNull()
    expect(parseEpdQr('https://example.com')).toBeNull()
  })
})
