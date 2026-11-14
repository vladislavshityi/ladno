import { FormField } from '@/components/form-field'
import { Input } from '@/components/ui/input'
import { LETTER_FIELDS, type LetterKey } from '../letter-fields'
import type { useLetterForm } from '../use-letter-form'

interface Props {
  form: ReturnType<typeof useLetterForm>
  keys?: readonly LetterKey[]
  idPrefix: string
  placeholders?: Partial<Record<LetterKey, string>>
  hints?: Partial<Record<LetterKey, string>>
  className?: string
}

/** Inputs for the resident's data in letters; one place for attributes and messages. */
export function LetterInputs({ form, keys, idPrefix, className, placeholders, hints }: Props) {
  return (
    <>
      {LETTER_FIELDS.filter((f) => !keys || keys.includes(f.key)).map((f) => (
        <FormField key={f.key} label={f.label} htmlFor={`${idPrefix}-${f.key}`} error={form.errors[f.key]} hint={hints?.[f.key]} className={className}>
          <Input
            id={`${idPrefix}-${f.key}`}
            type={f.type}
            inputMode={f.inputMode}
            value={form.values[f.key]}
            maxLength={f.max}
            autoComplete={f.autoComplete}
            placeholder={placeholders?.[f.key] ?? f.placeholder}
            aria-invalid={Boolean(form.errors[f.key])}
            onChange={(e) => form.set(f.key, e.target.value)}
            onBlur={() => form.blur(f.key)}
          />
        </FormField>
      ))}
    </>
  )
}
