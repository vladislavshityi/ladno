import { useState } from 'react'
import { fieldErrors } from '@/lib/api-client'
import { LETTER_FIELDS, checkLetterValues, letterValuesOf, type LetterErrors, type LetterKey, type LetterValues } from './letter-fields'
import type { User } from '@/types/models'

/** State of the "data for letters" inputs: values, messages under the fields, and the check before saving. */
export function useLetterForm(me: User | undefined, keys: readonly LetterKey[], required: readonly LetterKey[] = [], initial: Partial<LetterValues> = {}) {
  const [values, setValues] = useState<LetterValues>({ ...letterValuesOf(me ?? {}), ...initial })
  const [errors, setErrors] = useState<LetterErrors>({})

  const set = (key: LetterKey, value: string) => {
    setValues((v) => ({ ...v, [key]: value }))
    setErrors((e) => ({ ...e, [key]: undefined }))
  }

  /** Tidies a field and reports its problem as soon as the resident leaves it. */
  const blur = (key: LetterKey) => {
    const { changes, errors: found } = checkLetterValues(values, [key])
    if (found[key]) setErrors((e) => ({ ...e, [key]: found[key] }))
    else setValues((v) => ({ ...v, [key]: changes[key] ?? '' }))
  }

  /** Normalized values to save, or null if something is wrong (messages are then shown). */
  const validate = () => {
    const { changes, errors: found } = checkLetterValues(values, keys, required)
    setErrors(found)
    return Object.keys(found).length > 0 ? null : changes
  }

  /** Puts the server's per-field messages under the matching inputs; true if any were shown. */
  const showServerErrors = (err: unknown) => {
    const known = LETTER_FIELDS.filter((f) => keys.includes(f.key) && fieldErrors(err)[f.key])
    setErrors(Object.fromEntries(known.map((f) => [f.key, fieldErrors(err)[f.key]])))
    return known.length > 0
  }

  return { values, errors, set, blur, validate, showServerErrors }
}
