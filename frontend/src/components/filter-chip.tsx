import type { ComponentProps } from 'react'
import { cn } from '@/lib/utils'

interface Props extends ComponentProps<'button'> {
  active?: boolean
}

/** Pill-shaped toggle for filter rows. */
export function FilterChip({ active, className, ...props }: Props) {
  return (
    <button
      type="button"
      aria-pressed={active}
      className={cn(
        'inline-flex h-8 shrink-0 items-center gap-1.5 rounded-full border px-3 text-sm font-medium whitespace-nowrap transition-colors outline-none focus-visible:ring-3 focus-visible:ring-ring/50',
        active
          ? 'border-primary bg-primary text-primary-foreground'
          : 'border-border bg-background text-foreground hover:bg-muted',
        className,
      )}
      {...props}
    />
  )
}
