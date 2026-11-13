import { describe, expect, it } from 'vitest'
import { formatMoney, formatSigned } from './money'

const normalize = (s: string) => s.replace(/\s/g, ' ')

describe('money', () => {
  it('formats decimal strings as rubles', () => {
    expect(normalize(formatMoney('11274.07'))).toBe('11 274,07 ₽')
  })

  it('shows a dash for missing values', () => {
    expect(formatMoney(null)).toBe('—')
  })

  it('signs growth explicitly', () => {
    expect(normalize(formatSigned('646.56'))).toBe('+646,56 ₽')
    expect(normalize(formatSigned('-5'))).toContain('5,00 ₽')
  })
})
