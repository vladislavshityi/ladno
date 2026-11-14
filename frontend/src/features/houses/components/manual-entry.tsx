import { useState } from 'react'
import { PencilLine } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import type { Checked } from '@/lib/validation'

interface Props {
  label: string
  placeholder: string
  submitLabel: string
  maxLength: number
  /** Trims and checks the text: returns the clean value or a message for the resident. */
  check: (raw: string) => Checked
  onSubmit: (value: string) => void
  onCancel: () => void
  autoFocus?: boolean
}

/** Free-text value for what is missing from the directory: a house or a management company. */
export function ManualEntry({ label, placeholder, submitLabel, maxLength, check, onSubmit, onCancel, autoFocus }: Props) {
  const [value, setValue] = useState('')
  const [error, setError] = useState<string>()
  const ready = value.trim().length > 0

  return (
    <form
      className="grid gap-3"
      onSubmit={(e) => {
        e.preventDefault()
        const result = check(value)
        if (!result.ok) return setError(result.error)
        if (result.value) onSubmit(result.value)
      }}
    >
      <div className="grid gap-1.5">
        <Input
          value={value}
          maxLength={maxLength}
          onChange={(e) => {
            setValue(e.target.value)
            setError(undefined)
          }}
          placeholder={placeholder}
          aria-label={label}
          aria-invalid={Boolean(error)}
          autoFocus={autoFocus}
        />
        {error && (
          <p role="alert" className="text-xs text-destructive">
            {error}
          </p>
        )}
      </div>
      <div className="flex flex-wrap gap-2">
        <Button type="submit" disabled={!ready}>
          {submitLabel}
        </Button>
        <Button type="button" variant="ghost" onClick={onCancel}>
          Искать в списке
        </Button>
      </div>
    </form>
  )
}

/** Last row of a search list: opens the manual entry. */
export function ManualEntryButton({ label, onClick }: { label: string; onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="flex w-full items-center gap-2.5 rounded-xl border border-dashed px-3 py-2.5 text-left text-sm text-muted-foreground transition-colors hover:bg-muted hover:text-foreground focus-visible:bg-muted focus-visible:outline-none"
    >
      <PencilLine className="size-4 shrink-0" />
      {label}
    </button>
  )
}
