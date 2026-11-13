import { Loader2 } from 'lucide-react'
import { Skeleton } from '@/components/ui/skeleton'
import { useCompareExplanation } from '../hooks'

/** Plain-language reason for the change; written after the figures are shown. */
export function CompareExplanation({ base, target }: { base: string; target: string }) {
  const { data, isError } = useCompareExplanation(base, target)

  return (
    <div className="rounded-2xl bg-card p-4 shadow-sm ring-1 ring-border">
      <p className="text-sm font-medium">Почему изменилась сумма</p>
      {data ? (
        <p className="mt-2 text-sm leading-relaxed animate-in fade-in-0 duration-300">{data.text}</p>
      ) : isError ? (
        <p className="mt-2 text-sm text-muted-foreground">Пояснение сейчас недоступно. Расчёт выше от этого не зависит.</p>
      ) : (
        <div className="mt-2 grid gap-2" role="status">
          <p className="flex items-center gap-2 text-sm text-muted-foreground">
            <Loader2 className="size-3.5 animate-spin" /> Готовим пояснение…
          </p>
          <Skeleton className="h-3.5 w-full" />
          <Skeleton className="h-3.5 w-4/5" />
        </div>
      )}
    </div>
  )
}
