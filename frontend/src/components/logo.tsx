import { cn } from '@/lib/utils'

/** House with a check mark: "Ладно" as a gesture of things being sorted out. */
export function LogoMark({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 32 32" fill="none" aria-hidden className={cn('size-8 shrink-0', className)}>
      <rect width="32" height="32" rx="9" className="fill-primary" />
      <path d="M16 6.5 26 14.6V25a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2V14.6Z" className="fill-primary-foreground" />
      <path
        d="m11.2 19.2 3.3 3.3 6.4-6.9"
        className="stroke-primary"
        strokeWidth="2.6"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}

export function Logo({ className, markClassName }: { className?: string; markClassName?: string }) {
  return (
    <span className={cn('inline-flex items-center gap-2.5', className)}>
      <LogoMark className={markClassName} />
      <span className="text-lg font-semibold tracking-tight">Ладно</span>
    </span>
  )
}
