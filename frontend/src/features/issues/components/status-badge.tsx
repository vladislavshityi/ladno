import { cn } from '@/lib/utils'
import { STATUS_META, TONE_CLASSES } from '@/lib/design'
import type { IssueStatus } from '@/types/models'

export function StatusBadge({ status, className }: { status: IssueStatus; className?: string }) {
  const { label, tone } = STATUS_META[status]
  return (
    <span className={cn('inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium', TONE_CLASSES[tone], className)}>
      {label}
    </span>
  )
}
