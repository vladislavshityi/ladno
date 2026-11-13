import type { ReactNode } from 'react'

export interface Bar {
  key: string
  label: ReactNode
  value: number
}

/** Horizontal bars scaled to the largest value; no chart library needed. */
export function Bars({ bars }: { bars: Bar[] }) {
  const max = Math.max(...bars.map((b) => b.value), 1)
  return (
    <ul className="flex flex-col gap-2.5">
      {bars.map((b) => (
        <li key={b.key} className="flex flex-col gap-1">
          <div className="flex items-center justify-between gap-3 text-sm">
            <span className="flex min-w-0 items-center gap-2 truncate">{b.label}</span>
            <span className="tabular-nums text-muted-foreground">{b.value}</span>
          </div>
          <div className="h-1.5 rounded-full bg-muted">
            <div className="h-full rounded-full bg-primary" style={{ width: `${(b.value / max) * 100}%` }} />
          </div>
        </li>
      ))}
    </ul>
  )
}
