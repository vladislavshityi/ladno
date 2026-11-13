import { Link } from 'react-router-dom'
import { Card } from '@/components/ui/card'
import type { CompanyRating } from '@/types/models'
import { percent } from '../format'
import { Score } from './score-badge'

export function CompanyCard({ company }: { company: CompanyRating }) {
  return (
    <Link to={`/ratings/${company.id}`} className="group block rounded-2xl focus-visible:ring-3 focus-visible:ring-ring/50 focus-visible:outline-none">
      <Card className="rounded-2xl border-0 p-4 shadow-sm ring-1 ring-border transition-all group-hover:-translate-y-px group-hover:shadow-md">
        <div className="flex items-center justify-between gap-4">
          <div className="min-w-0 space-y-1.5">
            <p className="line-clamp-2 font-medium">{company.name}</p>
            {company.score == null ? (
              <p className="text-xs text-muted-foreground">Обращений: {company.issues_total}</p>
            ) : (
              <p className="flex flex-wrap gap-x-3 text-xs text-muted-foreground">
                <span>Решено {percent(company.resolved_share)}</span>
                <span>В срок {percent(company.on_time_share)}</span>
                <span>Просрочено {company.overdue_now}</span>
              </p>
            )}
          </div>
          <div className="shrink-0 text-right">
            <Score score={company.score} className={company.score == null ? '' : 'text-3xl'} />
            {company.score != null && <p className="text-xs text-muted-foreground">{company.issues_total} обращ.</p>}
          </div>
        </div>
      </Card>
    </Link>
  )
}
