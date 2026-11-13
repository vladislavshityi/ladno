import { Link, useParams } from 'react-router-dom'
import { ArrowLeft, SearchX } from 'lucide-react'
import { EmptyState } from '@/components/empty-state'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { Card, CardContent } from '@/components/ui/card'
import { IssueActions } from '../components/issue-actions'
import { IssueHeader } from '../components/issue-header'
import { IssuePhotos } from '../components/issue-photos'
import { LetterCard } from '../components/letter-card'
import { MissingDataAlert } from '../components/missing-data-alert'
import { RoutePanel } from '../components/route-panel'
import { StatusTimeline } from '../components/status-timeline'
import { SubmitPanel } from '../components/submit-panel'
import { useIssue } from '../hooks'

export default function IssuePage() {
  const { id = '' } = useParams()
  const { data: issue, isError } = useIssue(id)

  if (isError) {
    return (
      <EmptyState
        icon={SearchX}
        title="Обращение не найдено"
        action={
          <Button asChild>
            <Link to="/issues">К списку</Link>
          </Button>
        }
      />
    )
  }
  if (!issue) return <Skeleton className="h-96 rounded-2xl" />

  return (
    <div className="mx-auto grid max-w-2xl gap-5">
      <Button asChild variant="ghost" size="sm" className="-ml-2 justify-self-start">
        <Link to="/issues">
          <ArrowLeft /> Все обращения
        </Link>
      </Button>
      <IssueHeader issue={issue} />
      <MissingDataAlert issue={issue} />
      {issue.status === 'draft' && <SubmitPanel issue={issue} />}
      <IssueActions issue={issue} />
      <Card className="rounded-2xl border-0 shadow-sm ring-1 ring-border">
        <CardContent>
          <StatusTimeline issue={issue} />
        </CardContent>
      </Card>
      <LetterCard
        title="Текст для «Решаем вместе»"
        hint="Короткая версия для формы на платформе"
        text={issue.draft.pos_short}
      />
      <LetterCard title="Полное письмо" hint="Для e-mail или бумажного обращения" text={issue.draft.full} />
      <IssuePhotos photos={issue.photos} />
      <RoutePanel route={issue.route} />
    </div>
  )
}
