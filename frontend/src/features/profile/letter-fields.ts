export const LETTER_FIELDS = [
  { key: 'full_name', label: 'ФИО', autoComplete: 'name', max: 200 },
  { key: 'phone', label: 'Телефон', autoComplete: 'tel', max: 32 },
  { key: 'email', label: 'E-mail', autoComplete: 'email', max: 200 },
  { key: 'apartment', label: 'Квартира', autoComplete: 'off', max: 16 },
] as const

export type LetterValues = Record<(typeof LETTER_FIELDS)[number]['key'], string>
