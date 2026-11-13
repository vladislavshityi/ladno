import { useState } from 'react'
import { Link } from 'react-router-dom'
import { FilePlus2, Inbox } from 'lucide-react'
import { PageHeader } from '@/components/page-header'
import { EmptyState } from '@/components/empty-state'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { IssueListItem } from '../components/issue-list-item'
import { useIssues } from '../hooks'
import type { IssueStatus } from '@/types/models'

const FILTERS: { id: string; label: string; statuses: IssueStatus[] | null }[] = [
  { id: 'all', label: 'Все', statuses: null },
  { id: 'draft', label: 'Черновики', statuses: ['draft'] },
  { id: 'active', label: 'В работе', statuses: ['submitted', 'in_progress'] },
  { id: 'resolved', label: 'Решённые', statuses: ['resolved'] },
  { id: 'stuck', label: 'Без решения', statuses: ['no_response', 'rejected'] },
]

export default function IssuesPage() {
  const { data: issues, isLoading } = useIssues()
  const [filter, setFilter] = useState('all')
  const statuses = FILTERS.find((f) => f.id === filter)?.statuses
  const shown = issues?.filter((i) => !statuses || statuses.includes(i.status))

  return (
    <div className="grid gap-5">
      <PageHeader
        title="Мои обращения"
        description="Статусы, сроки ответа и эскалация"
        actions={
          <Button asChild>
            <Link to="/issues/new">
              <FilePlus2 /> Новое обращение
            </Link>
          </Button>
        }
      />
      {issues && issues.length > 0 && (
        <Tabs value={filter} onValueChange={setFilter}>
          <TabsList className="w-full justify-start overflow-x-auto sm:w-fit">
            {FILTERS.map((f) => (
              <TabsTrigger key={f.id} value={f.id} className="flex-none">
                {f.label}
              </TabsTrigger>
            ))}
          </TabsList>
        </Tabs>
      )}
      {isLoading && (
        <div className="grid gap-3">
          {[0, 1, 2].map((i) => (
            <Skeleton key={i} className="h-24 rounded-2xl" />
          ))}
        </div>
      )}
      {issues?.length === 0 && (
        <EmptyState
          icon={Inbox}
          title="Обращений пока нет"
          description="Опишите проблему в доме или во дворе — подскажем, кому писать, и подготовим текст."
          action={
            <Button asChild>
              <Link to="/issues/new">Кому пожаловаться?</Link>
            </Button>
          }
        />
      )}
      {issues && issues.length > 0 && shown?.length === 0 && <EmptyState icon={Inbox} title="В этом разделе пусто" />}
      <div className="grid gap-3">
        {shown?.map((issue) => (
          <IssueListItem key={issue.id} issue={issue} />
        ))}
      </div>
    </div>
  )
}
