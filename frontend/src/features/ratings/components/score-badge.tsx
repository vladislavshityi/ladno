import { SCORE_TEXT_CLASSES, scoreTone } from '@/lib/design'
import { cn } from '@/lib/utils'

export function Score({ score, className }: { score: number | null; className?: string }) {
  if (score == null) return <span className={cn('text-sm text-muted-foreground', className)}>Мало данных</span>
  return <span className={cn('font-semibold tabular-nums', SCORE_TEXT_CLASSES[scoreTone(score)], className)}>{score}</span>
}
