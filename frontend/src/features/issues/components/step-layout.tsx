import type { ReactNode } from 'react'
import { ArrowLeft, ArrowRight, Loader2 } from 'lucide-react'
import { Button } from '@/components/ui/button'

interface Props {
  title: string
  description?: string
  children: ReactNode
  onBack?: () => void
  onNext: () => void
  nextLabel?: string
  nextDisabled?: boolean
  pending?: boolean
}

/** Shared frame of a wizard step: heading, content and the back/next row. */
export function StepLayout({ title, description, children, onBack, onNext, nextLabel = 'Дальше', nextDisabled, pending }: Props) {
  return (
    <div className="grid gap-5 animate-in fade-in-0 slide-in-from-right-3 duration-300">
      <div>
        <h2 className="text-xl font-semibold tracking-tight">{title}</h2>
        {description && <p className="mt-1 text-sm text-muted-foreground">{description}</p>}
      </div>
      {children}
      <div className="flex items-center justify-between gap-2 pt-1">
        {onBack ? (
          <Button variant="ghost" size="lg" onClick={onBack}>
            <ArrowLeft /> Назад
          </Button>
        ) : (
          <span />
        )}
        <Button size="lg" onClick={onNext} disabled={nextDisabled || pending}>
          {pending && <Loader2 className="animate-spin" />}
          {nextLabel}
          {!pending && <ArrowRight />}
        </Button>
      </div>
    </div>
  )
}
