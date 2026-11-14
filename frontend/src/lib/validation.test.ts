import { describe, expect, it } from 'vitest'
import {
  AREA,
  MONEY,
  SIGNED_MONEY,
  TARIFF,
  checkApartment,
  checkDecimal,
  checkDescription,
  checkEmail,
  checkEntrance,
  checkFloor,
  checkFullName,
  checkPeriod,
  checkPhone,
  checkResidents,
  checkText,
} from './validation'

const value = (r: { ok: boolean; value?: string | null }) => (r.ok ? r.value : 'error')

describe('checkFullName', () => {
  it('fixes the case and spacing', () => {
    expect(value(checkFullName('  иванов   иван '))).toBe('Иванов Иван')
    expect(value(checkFullName('анна-мария о’коннор'))).toBe('Анна-Мария О’Коннор')
    expect(value(checkFullName('Иванов И. И.'))).toBe('Иванов И. И.')
  })
  it('is optional', () => expect(value(checkFullName('  '))).toBeNull())
  it('wants two or three words of letters', () => {
    for (const bad of ['Иванов', 'а б в г', 'Иванов 2', 'Иван@ов Иван']) expect(checkFullName(bad).ok).toBe(false)
  })
})

describe('checkPhone', () => {
  it.each(['+7 900 123-45-67', '89001234567', '8 (900) 123-45-67', '+7(900)1234567', '9001234567'])('normalizes %s', (raw) => {
    expect(value(checkPhone(raw))).toBe('+7 900 123-45-67')
  })
  it.each(['12345', '+1 900 123-45-67', '+7 000 123-45-67', '89001234567x'])('rejects %s', (raw) => {
    expect(checkPhone(raw)).toEqual({ ok: false, error: 'Введите номер в формате +7 900 123-45-67' })
  })
})

describe('checkEmail', () => {
  it('lowercases a valid address', () => expect(value(checkEmail(' A@Example.RU '))).toBe('a@example.ru'))
  it('rejects broken ones', () => {
    for (const bad of ['anna', 'anna@', 'anna@example', 'a b@example.ru']) expect(checkEmail(bad).ok).toBe(false)
  })
})

describe('apartment, entrance, floor', () => {
  it('accepts a number with a letter or a fraction', () => {
    expect(['12', '12А', '12/1'].map((v) => value(checkApartment(v)))).toEqual(['12', '12а', '12/1'])
    expect(checkApartment('1234567').ok).toBe(false)
    expect(checkApartment('кв 12').ok).toBe(false)
  })
  it('limits the entrance to 1-99', () => {
    expect(value(checkEntrance('03'))).toBe('3')
    for (const bad of ['0', '100', 'а']) expect(checkEntrance(bad).ok).toBe(false)
  })
  it('limits the floor to -3..200', () => {
    expect(value(checkFloor('-3'))).toBe('-3')
    expect(value(checkFloor('200'))).toBe('200')
    for (const bad of ['-4', '201', '5а']) expect(checkFloor(bad).ok).toBe(false)
  })
})

describe('text', () => {
  it('trims, blanks to null, rejects control characters', () => {
    expect(value(checkText('  у лифта ', 200))).toBe('у лифта')
    expect(value(checkText('   ', 200))).toBeNull()
    expect(checkText('a\u0000b', 200).ok).toBe(false)
    expect(checkText('a\nb', 200).ok).toBe(false)
    expect(checkText('a\nb', 200, { multiline: true }).ok).toBe(true)
    expect(checkText('я'.repeat(201), 200).ok).toBe(false)
  })
  it('wants a description of at least 5 characters', () => {
    expect(checkDescription('свет').ok).toBe(false)
    expect(value(checkDescription(' не горит свет '))).toBe('не горит свет')
    expect(value(checkDescription(''))).toBeNull()
  })
})

describe('numbers', () => {
  it('reads commas and spaces', () => expect(value(checkDecimal('1 234,50', MONEY))).toBe('1234.50'))
  it('checks range and decimal places', () => {
    expect(checkDecimal('-1', MONEY).ok).toBe(false)
    expect(checkDecimal('1000000.01', MONEY).ok).toBe(false)
    expect(checkDecimal('1.234', MONEY).ok).toBe(false)
    expect(checkDecimal('abc', MONEY).ok).toBe(false)
    expect(value(checkDecimal('-150', SIGNED_MONEY))).toBe('-150')
    expect(value(checkDecimal('53.4360', TARIFF))).toBe('53.4360')
    expect(checkDecimal('0.5', AREA).ok).toBe(false)
    expect(value(checkDecimal('', AREA))).toBeNull()
  })
  it('limits residents to 0-30', () => {
    expect(value(checkResidents('3'))).toBe('3')
    expect(checkResidents('31').ok).toBe(false)
    expect(checkResidents('-1').ok).toBe(false)
  })
})

describe('checkPeriod', () => {
  const now = new Date(2026, 10, 14)
  it('allows 2020-01 up to next month', () => {
    expect(value(checkPeriod('2020-01', now))).toBe('2020-01')
    expect(value(checkPeriod('2026-12', now))).toBe('2026-12')
  })
  it('rejects the rest', () => {
    for (const bad of ['', '2019-12', '2027-01', '2026-13', 'ноябрь']) expect(checkPeriod(bad, now).ok).toBe(false)
  })
})
