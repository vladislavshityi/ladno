import { Link, useParams } from 'react-router-dom'
import { ArrowLeft, ExternalLink, MapPin, Phone, SearchX } from 'lucide-react'
import { DemoBadge } from '@/components/demo-badge'
import { EmptyState } from '@/components/empty-state'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { CategoryIcon } from '@/features/issues/category-icon'
import { useCategories } from '@/features/issues/hooks'
import { formatPeriod } from '@/lib/dates'
import { openExternal } from '@/lib/telegram'
import { Bars } from '../components/bars'
import { Score } from '../components/score-badge'
import { percent } from '../format'
import { useCompanyRating } from '../hooks'

function Metric({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-xl bg-muted/60 p-3">
      <p className="text-xl font-semibold tabular-nums">{value}</p>
      <p className="text-xs text-muted-foreground">{label}</p>
    </div>
  )
}

export default function CompanyPage() {
  const { companyId = '' } = useParams()
  const { data: company, isError } = useCompanyRating(Number(companyId))
  const { data: categories } = useCategories()

  if (isError) {
    return (
      <EmptyState
        icon={SearchX}
        title="По этой УК пока нет данных"
        action={
          <Button asChild>
            <Link to="/ratings">К рейтингу</Link>
          </Button>
        }
      />
    )
  }
  if (!company) return <Skeleton className="h-96 rounded-2xl" />

  const category = (id: string) => categories?.find((c) => c.id === id)
  const phone = company.phones[0]

  return (
    <div className="mx-auto grid max-w-2xl gap-5">
      <Button asChild variant="ghost" size="sm" className="-ml-2 justify-self-start">
        <Link to="/ratings">
          <ArrowLeft /> Рейтинг УК
        </Link>
      </Button>
      <div className="flex items-start justify-between gap-4">
        <div className="grid min-w-0 gap-2">
          <h1 className="text-2xl font-semibold tracking-tight text-balance">{company.name}</h1>
          <p className="text-sm text-muted-foreground">
            Домов в справочнике: {company.houses_count}. Обращений по данным сервиса: {company.issues_total}
          </p>
          <div className="flex flex-wrap items-center gap-2">
            {phone && (
              <Button asChild variant="outline" size="sm">
                <a href={`tel:${phone}`}>
                  <Phone /> Телефон
                </a>
              </Button>
            )}
            {company.site && (
              <Button variant="outline" size="sm" onClick={() => openExternal(company.site!)}>
                <ExternalLink /> Сайт
              </Button>
            )}
            <DemoBadge />
          </div>
        </div>
        <Score score={company.score} className={company.score == null ? '' : 'text-5xl'} />
      </div>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Metric label="Решено" value={percent(company.resolved_share)} />
        <Metric label="Ответили в срок" value={percent(company.on_time_share)} />
        <Metric label="Дошло до жалобы выше" value={percent(company.escalated_share)} />
        <Metric label="Просрочено сейчас" value={company.overdue_now} />
      </div>

      {company.by_category.length > 0 && (
        <Card className="rounded-2xl border-0 shadow-sm ring-1 ring-border">
          <CardHeader>
            <CardTitle>О чём жалуются</CardTitle>
          </CardHeader>
          <CardContent>
            <Bars
              bars={company.by_category.map((b) => ({
                key: b.key,
                value: b.issues_total,
                label: (
                  <>
                    <CategoryIcon name={category(b.key)?.icon ?? ''} className="size-4 shrink-0 text-muted-foreground" />
                    {category(b.key)?.title ?? b.key}
                  </>
                ),
              }))}
            />
          </CardContent>
        </Card>
      )}

      {company.by_month.length > 0 && (
        <Card className="rounded-2xl border-0 shadow-sm ring-1 ring-border">
          <CardHeader>
            <CardTitle>Обращения по месяцам</CardTitle>
          </CardHeader>
          <CardContent>
            <Bars bars={company.by_month.map((b) => ({ key: b.key, value: b.issues_total, label: formatPeriod(b.key) }))} />
          </CardContent>
        </Card>
      )}

      {company.houses.length > 0 && (
        <Card className="rounded-2xl border-0 shadow-sm ring-1 ring-border">
          <CardHeader>
            <CardTitle>Дома с обращениями</CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="grid gap-2">
              {company.houses.map((h) => (
                <li key={h.house_id} className="flex items-center justify-between gap-3 text-sm">
                  <span className="flex min-w-0 items-center gap-2">
                    <MapPin className="size-3.5 shrink-0 text-muted-foreground" />
                    <span className="truncate">{h.address}</span>
                  </span>
                  <span className="shrink-0 text-muted-foreground">в работе: {h.active}</span>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
