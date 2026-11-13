import { useState } from 'react'
import { PencilLine } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'

interface Props {
  label: string
  placeholder: string
  submitLabel: string
  maxLength: number
  onSubmit: (value: string) => void
  onCancel: () => void
  autoFocus?: boolean
}

/** Free-text value for what is missing from the directory: a house or a management company. */
export function ManualEntry({ label, placeholder, submitLabel, maxLength, onSubmit, onCancel, autoFocus }: Props) {
  const [value, setValue] = useState('')
  const ready = value.trim().length >= 3

  return (
    <form
      className="grid gap-3"
      onSubmit={(e) => {
        e.preventDefault()
        if (ready) onSubmit(value.trim())
      }}
    >
      <Input value={value} maxLength={maxLength} onChange={(e) => setValue(e.target.value)} placeholder={placeholder} aria-label={label} autoFocus={autoFocus} />
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
