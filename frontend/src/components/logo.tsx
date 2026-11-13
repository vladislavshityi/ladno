import { cn } from '@/lib/utils'

/** Bear drawn in one continuous line: the mark of «Ладно». */
export function LogoMark({ className, animated = false }: { className?: string; animated?: boolean }) {
  return (
    <svg viewBox="0 0 32 32" fill="none" aria-hidden className={cn('size-8 shrink-0', className)}>
      <rect width="32" height="32" rx="9" className="fill-primary" />
      <path
        transform="translate(0 0.8)"
        pathLength={1}
        d="M7.4 22.6C6.6 19 7.2 15 10.2 12.5C13.4 10 19.4 9.7 22.8 11.9C24.6 13 25.9 14.4 26.9 15.5C27.6 16.3 27.3 17.5 26.3 17.7C24.9 18 23.6 18.4 22.8 19.4C22.2 20.4 22.3 22.4 21.3 22.7C20.1 23 19.6 21.6 19.5 20.2C19.3 23.2 16.5 23.4 16.4 20.2C16.2 23.2 13.4 23.4 13.3 20.2C13.1 22.8 11.3 23.4 10.7 21.9C10.1 20.4 10.2 17.4 10.9 15.9C11.3 15.1 10.4 14.7 10 15.4"
        className={cn('stroke-primary-foreground', animated && 'logo-draw')}
        strokeWidth="1.7"
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
