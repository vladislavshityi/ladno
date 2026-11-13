import { useState } from 'react'
import { Lightbulb, Sparkles } from 'lucide-react'
import { Skeleton } from '@/components/ui/skeleton'
import { cn } from '@/lib/utils'
import { useCategories } from '../../hooks'
import { CategoryIcon } from '../../category-icon'
import { EmergencyAlert } from '../emergency-alert'
import { StepLayout } from '../step-layout'
import type { StepProps } from '../../wizard'

export function CategoryStep({ data, setData, onNext, onBack }: StepProps) {
  const { data: categories } = useCategories()
  const { classification } = data
  const detected = categories?.find((c) => c.id === classification?.category)
  const [choosing, setChoosing] = useState(!classification?.category || classification.needs_manual_choice)

  return (
    <StepLayout
      title="Категория проблемы"
      description={choosing ? 'Выберите подходящую категорию.' : 'Проверьте, что мы поняли правильно.'}
      onBack={onBack}
      onNext={onNext}
      nextDisabled={!data.category}
    >
      {classification?.is_emergency && classification.emergency && <EmergencyAlert emergency={classification.emergency} />}
      {detected && !classification?.needs_manual_choice && (
        <div className="rounded-2xl bg-primary/8 p-4 ring-1 ring-primary/20">
          <p className="flex items-center gap-1.5 text-xs font-medium text-primary">
            <Sparkles className="size-3.5" /> Определили автоматически · уверенность {Math.round(classification!.confidence * 100)}%
          </p>
          <p className="mt-1 text-lg font-semibold">{detected.title}</p>
          {classification!.summary && <p className="mt-1 text-sm text-muted-foreground">{classification!.summary}</p>}
        </div>
      )}
      {classification?.clarification && (
        <p className="flex items-start gap-2 rounded-xl bg-muted/60 p-3 text-sm">
          <Lightbulb className="mt-0.5 size-4 shrink-0 text-warning" />
          {classification.clarification}
        </p>
      )}
      {!categories ? (
        <Skeleton className="h-40 rounded-2xl" />
      ) : choosing ? (
        <div role="radiogroup" aria-label="Категория" className="grid gap-2 sm:grid-cols-2">
          {categories.map((c) => (
            <button
              key={c.id}
              type="button"
              role="radio"
              aria-checked={data.category === c.id}
              onClick={() => setData((d) => ({ ...d, category: c.id, answers: {} }))}
              className={cn(
                'flex items-center gap-3 rounded-xl border bg-card px-3 py-3 text-left text-sm transition-all hover:bg-muted focus-visible:ring-3 focus-visible:ring-ring/50 focus-visible:outline-none active:scale-[0.99]',
                data.category === c.id && 'border-primary bg-primary/8 font-medium ring-1 ring-primary',
              )}
            >
              <CategoryIcon name={c.icon} className="size-4 shrink-0 text-muted-foreground" />
              {c.title}
            </button>
          ))}
        </div>
      ) : (
        <button type="button" className="justify-self-start text-sm font-medium text-primary hover:underline" onClick={() => setChoosing(true)}>
          Выбрать другую категорию
        </button>
      )}
    </StepLayout>
  )
}
