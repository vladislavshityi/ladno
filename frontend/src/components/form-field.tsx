import type { ReactNode } from 'react'
import { Label } from '@/components/ui/label'

interface Props {
  label: string
  htmlFor?: string
  error?: string
  hint?: string
  children: ReactNode
}

export function FormField({ label, htmlFor, error, hint, children }: Props) {
  return (
    <div className="grid gap-1.5">
      <Label htmlFor={htmlFor}>{label}</Label>
      {children}
      {error ? (
        <p role="alert" className="text-xs text-destructive">
          {error}
        </p>
      ) : hint ? (
        <p className="text-xs text-muted-foreground">{hint}</p>
      ) : null}
    </div>
  )
}
