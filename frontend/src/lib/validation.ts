/**
 * Input rules. They mirror the server (the source of truth) so mistakes show up before sending.
 * Every checker trims, normalizes and returns either a clean value (null for blank) or a message.
 */

export type Checked<T = string> = { ok: true; value: T | null } | { ok: false; error: string }

const ok = <T>(value: T | null): Checked<T> => ({ ok: true, value })
const fail = (error: string): Checked<never> => ({ ok: false, error })

// \p{Cc} is the control characters; new lines and tabs are fine in multi-line text.
const CONTROL = /\p{Cc}/u
const MULTILINE_CONTROL = /(?![\n\t\r])\p{Cc}/u
const MULTILINE_CONTROL_G = /(?![\n\t\r])\p{Cc}/gu

/** Drops control characters (except new lines and tabs): for pasted text that is sent as it is. */
export const stripControl = (text: string) => text.replace(MULTILINE_CONTROL_G, '')

/** Trims; blank becomes null; rejects control characters and over-long text. */
export function checkText(raw: string, max: number, opts: { min?: number; multiline?: boolean } = {}): Checked {
  const text = raw.replace(/\r\n?/g, '\n').trim()
  if (!text) return ok(null)
  if ((opts.multiline ? MULTILINE_CONTROL : CONTROL).test(text)) return fail('Недопустимые символы')
  if (text.length > max) return fail(`Не длиннее ${max} символов`)
  if (opts.min && text.length < opts.min) return fail(`Не короче ${opts.min} символов`)
  return ok(text)
}

const NAME_WORD = /^[A-Za-zА-Яа-яЁё]+(?:[-'’][A-Za-zА-Яа-яЁё]+)*\.?$/

const capitalize = (word: string) =>
  word
    .split(/([-'’])/)
    .map((part) => (/[-'’]/.test(part) ? part : part.charAt(0).toUpperCase() + part.slice(1).toLowerCase()))
    .join('')

/** "иванов  иван" -> "Иванов Иван": two or three words made of letters, hyphens and apostrophes. */
export function checkFullName(raw: string): Checked {
  const text = checkText(raw, 100)
  if (!text.ok || text.value === null) return text
  const words = text.value.split(/\s+/)
  if (words.length < 2 || words.length > 3) return fail('Укажите фамилию и имя, отчество по желанию')
  if (!words.every((w) => NAME_WORD.test(w))) return fail('ФИО: только буквы, дефис и апостроф')
  return ok(words.map(capitalize).join(' '))
}

export const PHONE_ERROR = 'Введите номер в формате +7 900 123-45-67'

/** "8 (900) 123-45-67" -> "+7 900 123-45-67". */
export function checkPhone(raw: string): Checked {
  const text = checkText(raw, 32)
  if (!text.ok || text.value === null) return text
  const value = text.value
  if (!/^\+?[\d\s()-]+$/.test(value)) return fail(PHONE_ERROR)
  const digits = value.replace(/\D/g, '')
  let national = ''
  if (value.startsWith('+')) national = digits.startsWith('7') ? digits.slice(1) : ''
  else if (digits.length === 11 && /^[78]/.test(digits)) national = digits.slice(1)
  else if (digits.length === 10) national = digits
  if (national.length !== 10 || /^[01]/.test(national)) return fail(PHONE_ERROR)
  return ok(`+7 ${national.slice(0, 3)} ${national.slice(3, 6)}-${national.slice(6, 8)}-${national.slice(8)}`)
}

const EMAIL = /^[^@\s]{1,64}@[^@\s.]+(?:\.[^@\s.]+)*\.[^@\s.]{2,}$/

export function checkEmail(raw: string): Checked {
  const text = checkText(raw, 200)
  if (!text.ok || text.value === null) return text
  return EMAIL.test(text.value) ? ok(text.value.toLowerCase()) : fail('Введите e-mail в формате name@example.ru')
}

/** "12", "12а", "12/1": up to six characters. */
export function checkApartment(raw: string): Checked {
  const text = checkText(raw, 6)
  if (!text.ok || text.value === null) return text
  const value = text.value.toLowerCase()
  return /^\d{1,4}(?:[a-zа-яё]|\/\d{1,3})?$/.test(value) ? ok(value) : fail('Номер квартиры: цифры и при необходимости буква или дробь, например 12а')
}

export function checkEntrance(raw: string): Checked {
  const text = checkText(raw, 2)
  if (!text.ok || text.value === null) return text
  return /^\d{1,2}$/.test(text.value) && Number(text.value) > 0 ? ok(String(Number(text.value))) : fail('Подъезд: число от 1 до 99')
}

export function checkFloor(raw: string): Checked {
  const text = checkText(raw, 4)
  if (!text.ok || text.value === null) return text
  const n = Number(text.value)
  return /^-?\d{1,3}$/.test(text.value) && n >= -3 && n <= 200 ? ok(String(n)) : fail('Этаж: число от -3 до 200')
}

export const DESCRIPTION_MIN = 5
export const DESCRIPTION_MAX = 1000

/** Problem description: blank is allowed here, the form decides whether a photo can replace it. */
export function checkDescription(raw: string): Checked {
  const text = checkText(raw, DESCRIPTION_MAX, { multiline: true })
  if (!text.ok || text.value === null) return text
  return text.value.length < DESCRIPTION_MIN ? fail(`Опишите подробнее: не короче ${DESCRIPTION_MIN} символов`) : text
}

export const checkPlace = (raw: string) => checkText(raw, 200)
export const checkReference = (raw: string) => checkText(raw, 100)
export const checkAddress = (raw: string) => checkText(raw, 500, { min: 3 })
export const checkCompanyName = (raw: string) => checkText(raw, 300, { min: 3 })

interface NumberRule {
  min: number
  max: number
  places: number
  label: string
}

/** Decimal with a comma or a dot, spaces allowed: "1 234,50" -> "1234.50". Blank is null. */
export function checkDecimal(raw: string, rule: NumberRule): Checked {
  const text = raw.replace(/[\s ]/g, '').replace(',', '.')
  if (!text) return ok(null)
  if (!/^-?\d+(\.\d+)?$/.test(text)) return fail(`${rule.label}: нужно число`)
  const n = Number(text)
  if (n < rule.min || n > rule.max) return fail(`${rule.label}: от ${rule.min} до ${rule.max}`)
  if ((text.split('.')[1] ?? '').length > rule.places) return fail(`${rule.label}: не больше ${rule.places} знаков после запятой`)
  return ok(text)
}

export const MONEY: NumberRule = { min: 0, max: 1_000_000, places: 2, label: 'Сумма' }
export const SIGNED_MONEY: NumberRule = { min: -1_000_000, max: 1_000_000, places: 2, label: 'Перерасчёт' }
export const VOLUME: NumberRule = { min: 0, max: 100_000, places: 3, label: 'Объём' }
export const TARIFF: NumberRule = { min: 0, max: 1_000_000, places: 4, label: 'Тариф' }
export const AREA: NumberRule = { min: 1, max: 1000, places: 2, label: 'Площадь' }

export function checkResidents(raw: string): Checked {
  const text = raw.trim()
  if (!text) return ok(null)
  return /^\d{1,2}$/.test(text) && Number(text) <= 30 ? ok(String(Number(text))) : fail('Проживающих: целое число от 0 до 30')
}

export const FIRST_PERIOD = '2020-01'

/** The next month as "YYYY-MM": the latest period a receipt can have. */
export function lastPeriod(now = new Date()): string {
  const next = new Date(now.getFullYear(), now.getMonth() + 1, 1)
  return `${next.getFullYear()}-${String(next.getMonth() + 1).padStart(2, '0')}`
}

export function checkPeriod(raw: string, now = new Date()): Checked {
  const text = raw.trim()
  if (!text) return fail('Укажите месяц, за который квитанция')
  if (!/^\d{4}-(0[1-9]|1[0-2])$/.test(text)) return fail('Период в формате ГГГГ-ММ')
  return text < FIRST_PERIOD || text > lastPeriod(now) ? fail('Период: от января 2020 до следующего месяца') : ok(text)
}

export const checkInn = (raw: string): Checked => {
  const text = raw.trim()
  if (!text) return ok(null)
  return /^\d{10}(\d{2})?$/.test(text) ? ok(text) : fail('ИНН состоит из 10 или 12 цифр')
}
