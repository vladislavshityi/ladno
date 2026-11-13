import { useState } from 'react'
import { Loader2, Mail } from 'lucide-react'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { ConfirmDialog } from '@/components/confirm-dialog'
import type { Issue, SendChannel } from '@/types/models'
import { useSendIssue } from '../hooks'

/** One-click e-mail submission to the addressee, with a confirmation because the letter cannot be recalled. */
export function SubmitEmail({ issue, channel }: { issue: Issue; channel: SendChannel }) {
  const send = useSendIssue(issue.id)
  const [open, setOpen] = useState(false)

  return (
    <>
      <Button size="lg" className="justify-self-start" disabled={send.isPending} onClick={() => setOpen(true)}>
        {send.isPending ? <Loader2 className="animate-spin" /> : <Mail />} Отправить в УК по email
      </Button>
      <ConfirmDialog
        open={open}
        onOpenChange={setOpen}
        title="Отправить обращение по email?"
        description={`Письмо с PDF и фото уйдёт на ${channel.recipient}. Копия придёт вам, если в профиле указана почта.`}
        confirmLabel="Отправить"
        destructive={false}
        onConfirm={() => send.mutate(channel.name, { onSuccess: (r) => toast.success(r.message) })}
      />
    </>
  )
}
