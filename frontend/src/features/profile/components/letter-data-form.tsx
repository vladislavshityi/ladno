import { Loader2, ShieldCheck } from 'lucide-react'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import type { User } from '@/types/models'
import { useUpdateProfile } from '../hooks'
import { errorMessage } from '@/lib/api-client'
import { LETTER_FIELDS } from '../letter-fields'
import { useLetterForm } from '../use-letter-form'
import { LetterInputs } from './letter-inputs'
import { toProfileUpdate } from '../profile-update'

const KEYS = LETTER_FIELDS.map((f) => f.key)

export function LetterDataForm({ me }: { me: User }) {
  const update = useUpdateProfile()
  const form = useLetterForm(me, KEYS)

  const submit = () => {
    const changes = form.validate()
    if (!changes) return
    update.mutate(toProfileUpdate(me, changes), {
      onSuccess: () => toast.success('Данные сохранены'),
      onError: (err) => {
        if (!form.showServerErrors(err)) toast.error(errorMessage(err))
      },
    })
  }

  return (
    <Card className="rounded-2xl border-0 shadow-sm ring-1 ring-border">
      <CardHeader>
        <CardTitle>Данные для писем</CardTitle>
        <CardDescription>
          Необязательно. Подставляются в подпись обращений и заявлений, чтобы не вводить их каждый раз.
        </CardDescription>
      </CardHeader>
      <CardContent className="grid gap-4">
        <p className="flex items-start gap-2 rounded-xl bg-muted/60 p-3 text-sm text-muted-foreground">
          <ShieldCheck className="mt-0.5 size-4 shrink-0 text-success" />
          Эти данные подставляются в текст на сервере и в языковую модель не передаются.
        </p>
        <form
          noValidate
          className="grid gap-4 sm:grid-cols-2"
          onSubmit={(e) => {
            e.preventDefault()
            submit()
          }}
        >
          <LetterInputs form={form} idPrefix="profile" />
          <Button type="submit" size="lg" className="justify-self-start sm:col-span-2" disabled={update.isPending}>
            {update.isPending && <Loader2 className="animate-spin" />}
            Сохранить
          </Button>
        </form>
      </CardContent>
    </Card>
  )
}
