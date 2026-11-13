import { Link } from 'react-router-dom'
import { ChevronRight, MapPin } from 'lucide-react'
import { Card } from '@/components/ui/card'
import type { Issue } from '@/types/models'
import { DeadlineBadge } from './deadline-badge'
import { StatusBadge } from './status-badge'

export function IssueListItem({ issue }: { issue: Issue }) {
  return (
    <Link to={`/issues/${issue.id}`} className="group block rounded-2xl focus-visible:ring-3 focus-visible:ring-ring/50 focus-visible:outline-none">
      <Card className="rounded-2xl border-0 p-4 shadow-sm ring-1 ring-border transition-all group-hover:-translate-y-px group-hover:shadow-md">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0 space-y-1.5">
            <p className="font-medium">{issue.category_title}</p>
            <p className="text-sm text-muted-foreground">{issue.route.addressee.name}</p>
            {issue.address && (
              <p className="flex items-center gap-1.5 text-xs text-muted-foreground">
                <MapPin className="size-3" /> {issue.address}
              </p>
            )}
            <DeadlineBadge issue={issue} />
          </div>
          <div className="flex shrink-0 items-center gap-2">
            <StatusBadge status={issue.status} />
            <ChevronRight className="size-4 text-muted-foreground transition-transform group-hover:translate-x-0.5" />
          </div>
        </div>
      </Card>
    </Link>
  )
}
