import { useNavigate } from 'react-router-dom'
import { CheckCircle2, MessageSquareReply, Siren, XCircle } from 'lucide-react'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import type { Issue, IssueStatus } from '@/types/models'
import { useEscalate, usePatchIssue } from '../hooks'

const CAN_ESCALATE: IssueStatus[] = ['submitted', 'in_progress', 'no_response', 'rejected']

/** Status changes available after the complaint was submitted, plus escalation. */
export function IssueActions({ issue }: { issue: Issue }) {
  const patch = usePatchIssue(issue.id)
  const escalate = useEscalate(issue.id)
  const navigate = useNavigate()
  const set = (status: IssueStatus) => patch.mutate({ status })

  if (issue.status === 'draft' || issue.status === 'resolved') return null

  const showEscalate = CAN_ESCALATE.includes(issue.status) && issue.route.escalation.length > 0
  return (
    <div className="flex flex-wrap gap-2">
      {issue.status === 'submitted' && (
        <Button variant="outline" disabled={patch.isPending} onClick={() => set('in_progress')}>
          <MessageSquareReply /> Получен ответ
        </Button>
      )}
      <Button variant="outline" disabled={patch.isPending} onClick={() => set('resolved')}>
        <CheckCircle2 className="text-success" /> Проблема решена
      </Button>
      {issue.status !== 'rejected' && (
        <Button variant="outline" disabled={patch.isPending} onClick={() => set('rejected')}>
          <XCircle /> Получен отказ
        </Button>
      )}
      {showEscalate && (
        <Button
          disabled={escalate.isPending}
          onClick={() =>
            escalate.mutate(undefined, {
              onSuccess: (next) => {
                toast.success('Подготовили обращение следующей инстанции')
                navigate(`/issues/${next.id}`)
              },
            })
          }
        >
          <Siren /> Не ответили — эскалировать
        </Button>
      )}
    </div>
  )
}
