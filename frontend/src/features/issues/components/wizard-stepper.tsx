import { Check } from 'lucide-react'
import { cn } from '@/lib/utils'
import { WIZARD_STEPS, type StepId } from '../wizard'

export function WizardStepper({ current }: { current: StepId }) {
  const index = WIZARD_STEPS.findIndex((s) => s.id === current)
  return (
    <ol className="flex items-center gap-2" aria-label="Шаги">
      {WIZARD_STEPS.map((step, i) => (
        <li key={step.id} className="flex flex-1 items-center gap-2 last:flex-none" aria-current={i === index ? 'step' : undefined}>
          <span
            className={cn(
              'flex size-7 shrink-0 items-center justify-center rounded-full text-xs font-semibold transition-colors duration-300',
              i < index && 'bg-primary text-primary-foreground',
              i === index && 'bg-primary text-primary-foreground ring-4 ring-primary/20',
              i > index && 'bg-muted text-muted-foreground',
            )}
          >
            {i < index ? <Check className="size-3.5" strokeWidth={3} /> : i + 1}
          </span>
          <span className={cn('hidden text-sm sm:inline', i === index ? 'font-medium' : 'text-muted-foreground')}>{step.title}</span>
          {i < WIZARD_STEPS.length - 1 && (
            <span className={cn('h-px flex-1 transition-colors duration-300', i < index ? 'bg-primary' : 'bg-border')} />
          )}
        </li>
      ))}
    </ol>
  )
}
