import { useState } from 'react'
import { Loader2, UserPen } from 'lucide-react'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { useMe } from '@/features/auth/hooks'
import { useUpdateProfile } from '@/features/profile/hooks'
import { LETTER_FIELDS } from '@/features/profile/letter-fields'
import { useLetterForm } from '@/features/profile/use-letter-form'
import { LetterInputs } from '@/features/profile/components/letter-inputs'
import { toProfileUpdate } from '@/features/profile/profile-update'
import { errorMessage } from '@/lib/api-client'
import type { Issue, User } from '@/types/models'
import { useRefreshLetter } from '../hooks'

const KEYS = LETTER_FIELDS.map((f) => f.key)

type Missing = Issue['missing_applicant_fields'][number]

// Accusative: "Заполните ФИО, квартиру и телефон".
const MISSING_LABELS: Record<Missing, string> = { full_name: 'ФИО', apartment: 'квартиру', phone: 'телефон' }

const sentence = (missing: Missing[]) => {
  const labels = missing.map((f) => MISSING_LABELS[f])
  return labels.length > 1 ? `${labels.slice(0, -1).join(', ')} и ${labels.at(-1)}` : labels[0]
}

function ApplicantDialog({ me, issueId, open, onOpenChange }: { me: User; issueId: string; open: boolean; onOpenChange: (open: boolean) => void }) {
  const update = useUpdateProfile()
  const refresh = useRefreshLetter(issueId)
  const form = useLetterForm(me, KEYS)
  const pending = update.isPending || refresh.isPending

  const save = () => {
    const changes = form.validate()
    if (!changes) return
    update.mutate(toProfileUpdate(me, changes), {
      onSuccess: () =>
        refresh.mutate(undefined, {
          onSuccess: () => {
            toast.success('Письмо обновлено')
            onOpenChange(false)
          },
          onError: (err) => toast.error(errorMessage(err)),
        }),
      onError: (err) => {
        if (!form.showServerErrors(err)) toast.error(errorMessage(err))
      },
    })
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="rounded-2xl">
        <DialogHeader>
          <DialogTitle>Данные для письма</DialogTitle>
          <DialogDescription>Сохраним их в профиле и подставим в письмо. В языковую модель они не передаются.</DialogDescription>
        </DialogHeader>
        <form
          id="applicant-form"
          noValidate
          className="grid gap-4 sm:grid-cols-2"
          onSubmit={(e) => {
            e.preventDefault()
            save()
          }}
        >
          <LetterInputs form={form} idPrefix="applicant" />
        </form>
        <DialogFooter>
          <Button type="submit" form="applicant-form" size="lg" disabled={pending}>
            {pending && <Loader2 className="animate-spin" />}
            Сохранить и обновить письмо
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

/** Shown on a draft whose letter still has "[укажите …]" marks instead of the resident's data. */
export function MissingDataAlert({ issue }: { issue: Issue }) {
  const { data: me } = useMe()
  const [open, setOpen] = useState(false)

  if (issue.status !== 'draft' || issue.missing_applicant_fields.length === 0) return null

  return (
    <div role="alert" className="flex flex-wrap items-center gap-3 rounded-2xl bg-warning/10 p-4 ring-1 ring-warning/35">
      <UserPen className="size-5 shrink-0 text-warning" />
      <p className="min-w-0 flex-1 basis-56 text-sm font-medium">
        Заполните {sentence(issue.missing_applicant_fields)} в профиле, чтобы они попали в письмо
      </p>
      <Button variant="outline" onClick={() => setOpen(true)} disabled={!me}>
        Заполнить
      </Button>
      {me && open && <ApplicantDialog me={me} issueId={issue.id} open={open} onOpenChange={setOpen} />}
    </div>
  )
}
