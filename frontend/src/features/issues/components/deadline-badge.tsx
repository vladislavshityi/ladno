import { Clock } from 'lucide-react'
import { cn } from '@/lib/utils'
import { deadlineCountdown, formatLong } from '@/lib/dates'
import type { Issue } from '@/types/models'

/** Response deadline with a countdown; only shown while a reply is still expected. */
export function DeadlineBadge({ issue, withDate }: { issue: Issue; withDate?: boolean }) {
  if (!issue.deadline_at || !['submitted', 'in_progress', 'no_response'].includes(issue.status)) return null
  const { text, overdue } = deadlineCountdown(issue.deadline_at)
  const late = overdue || issue.is_overdue
  return (
    <span className={cn('inline-flex items-center gap-1.5 text-sm', late ? 'font-medium text-destructive' : 'text-muted-foreground')}>
      <Clock className="size-3.5" />
      {withDate ? `Ответить должны до ${formatLong(issue.deadline_at)} · ${text}` : text}
    </span>
  )
}
