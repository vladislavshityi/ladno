import { checkApartment, checkEmail, checkFullName, checkPhone, type Checked } from '@/lib/validation'

export const LETTER_FIELDS = [
  { key: 'full_name', label: 'ФИО', autoComplete: 'name', max: 100, placeholder: 'Иванов Иван Иванович', type: 'text', inputMode: 'text', check: checkFullName },
  { key: 'phone', label: 'Телефон', autoComplete: 'tel', max: 32, placeholder: '+7 900 123-45-67', type: 'tel', inputMode: 'tel', check: checkPhone },
  { key: 'email', label: 'E-mail', autoComplete: 'email', max: 200, placeholder: 'name@example.ru', type: 'email', inputMode: 'email', check: checkEmail },
  { key: 'apartment', label: 'Квартира', autoComplete: 'off', max: 6, placeholder: '12', type: 'text', inputMode: 'text', check: checkApartment },
] as const satisfies readonly {
  key: string
  label: string
  autoComplete: string
  max: number
  placeholder: string
  type: string
  inputMode: 'text' | 'tel' | 'email'
  check: (raw: string) => Checked
}[]

export type LetterKey = (typeof LETTER_FIELDS)[number]['key']
export type LetterValues = Record<LetterKey, string>
export type LetterErrors = Partial<Record<LetterKey, string>>

export interface LetterCheck {
  /** Normalized values, null for blank fields. */
  changes: Record<LetterKey, string | null>
  errors: LetterErrors
}

/** Checks the listed fields; `required` ones must not be blank. */
export function checkLetterValues(values: LetterValues, keys: readonly LetterKey[], required: readonly LetterKey[] = []): LetterCheck {
  const changes = {} as Record<LetterKey, string | null>
  const errors: LetterErrors = {}
  for (const field of LETTER_FIELDS) {
    if (!keys.includes(field.key)) continue
    const result = field.check(values[field.key])
    if (!result.ok) errors[field.key] = result.error
    else if (result.value === null && required.includes(field.key)) errors[field.key] = `Укажите ${field.label === 'ФИО' ? 'ФИО' : field.label.toLowerCase()}`
    else changes[field.key] = result.value
  }
  return { changes, errors }
}

/** Profile values for the form: what is saved, or empty strings. */
export function letterValuesOf(me: { full_name?: string | null; phone?: string | null; email?: string | null; apartment?: string | null }): LetterValues {
  return { full_name: me.full_name ?? '', phone: me.phone ?? '', email: me.email ?? '', apartment: me.apartment ?? '' }
}
