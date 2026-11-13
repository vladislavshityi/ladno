import { Link } from 'react-router-dom'
import { ArrowUpRight, MapPin } from 'lucide-react'
import type { Issue } from '@/types/models'
import { DeadlineBadge } from './deadline-badge'
import { StatusBadge } from './status-badge'

export function IssueHeader({ issue }: { issue: Issue }) {
  return (
    <div className="grid gap-2">
      <div className="flex flex-wrap items-center gap-2">
        <StatusBadge status={issue.status} />
        {issue.escalation_level > 0 && (
          <span className="rounded-full bg-muted px-2.5 py-0.5 text-xs text-muted-foreground">Эскалация, ступень {issue.escalation_level}</span>
        )}
      </div>
      <h1 className="text-2xl font-semibold tracking-tight text-balance">{issue.category_title}</h1>
      <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-muted-foreground">
        {issue.address && (
          <span className="flex items-center gap-1.5">
            <MapPin className="size-3.5" /> {issue.address}
            {issue.location_details && `, ${issue.location_details}`}
            {issue.house_id == null && <span className="rounded-full bg-muted px-2 py-0.5 text-xs">указан вами</span>}
          </span>
        )}
        {issue.external_ref && <span>№ {issue.external_ref}</span>}
        {issue.parent_issue_id && (
          <Link to={`/issues/${issue.parent_issue_id}`} className="flex items-center gap-1 text-primary hover:underline">
            Предыдущее обращение <ArrowUpRight className="size-3.5" />
          </Link>
        )}
      </div>
      <DeadlineBadge issue={issue} withDate />
    </div>
  )
}
