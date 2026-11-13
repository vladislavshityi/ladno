import { cn } from '@/lib/utils'

interface Props {
  label: string
  value: string | undefined
  options: { value: string; label: string }[]
  onChange: (value: string) => void
}

/** A question with single-choice chips. */
export function ChoiceGroup({ label, value, options, onChange }: Props) {
  return (
    <div role="radiogroup" aria-label={label} className="grid gap-2">
      <p className="text-sm font-medium">{label}</p>
      <div className="flex flex-wrap gap-2">
        {options.map((o) => (
          <button
            key={o.value}
            type="button"
            role="radio"
            aria-checked={value === o.value}
            onClick={() => onChange(o.value)}
            className={cn(
              'rounded-full border bg-card px-4 py-2 text-sm transition-all hover:bg-muted focus-visible:ring-3 focus-visible:ring-ring/50 focus-visible:outline-none active:scale-[0.98]',
              value === o.value && 'border-primary bg-primary/10 font-medium text-primary',
            )}
          >
            {o.label}
          </button>
        ))}
      </div>
    </div>
  )
}
