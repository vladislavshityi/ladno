import { Check } from 'lucide-react'
import { cn } from '@/lib/utils'
import { formatDateTime } from '@/lib/dates'
import type { Issue, IssueStatus } from '@/types/models'

const RANK: Record<IssueStatus, number> = { draft: 0, submitted: 1, in_progress: 2, resolved: 3, no_response: 2, rejected: 2 }

function resultStep(status: IssueStatus) {
  if (status === 'no_response') return { label: 'Нет ответа в срок', tone: 'text-warning border-warning' }
  if (status === 'rejected') return { label: 'Получен отказ', tone: 'text-destructive border-destructive' }
  return { label: 'Получен ответ', tone: '' }
}

export function StatusTimeline({ issue }: { issue: Issue }) {
  const rank = RANK[issue.status]
  const result = resultStep(issue.status)
  const steps = [
    { label: 'Черновик создан', date: issue.created_at, tone: '' },
    { label: 'Подано', date: issue.submitted_at, tone: '' },
    { label: result.label, date: null, tone: result.tone },
    { label: 'Решено', date: null, tone: '' },
  ]

  return (
    <ol className="grid gap-4 sm:grid-cols-4" aria-label="Статус обращения">
      {steps.map((s, i) => {
        const done = i <= rank
        return (
          <li key={s.label} className="flex items-start gap-3 sm:flex-col sm:gap-2">
            <span
              className={cn(
                'flex size-7 shrink-0 items-center justify-center rounded-full border-2 text-xs transition-colors',
                done ? 'border-primary bg-primary text-primary-foreground' : 'border-border text-muted-foreground',
                done && i === rank && s.tone && `bg-background ${s.tone}`,
              )}
            >
              {done ? <Check className="size-3.5" strokeWidth={3} /> : i + 1}
            </span>
            <div>
              <p className={cn('text-sm', done ? 'font-medium' : 'text-muted-foreground')}>{s.label}</p>
              {s.date && <p className="text-xs text-muted-foreground">{formatDateTime(s.date)}</p>}
            </div>
          </li>
        )
      })}
    </ol>
  )
}
