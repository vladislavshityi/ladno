import { useState } from 'react'
import { Loader2, ShieldCheck } from 'lucide-react'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { FormField } from '@/components/form-field'
import type { User } from '@/types/models'
import { useUpdateProfile } from '../hooks'
import { LETTER_FIELDS, type LetterValues } from '../letter-fields'
import { toProfileUpdate } from '../profile-update'

export function LetterDataForm({ me }: { me: User }) {
  const update = useUpdateProfile()
  const [values, setValues] = useState<LetterValues>({
    full_name: me.full_name ?? '',
    phone: me.phone ?? '',
    email: me.email ?? '',
    apartment: me.apartment ?? '',
  })

  const submit = () => {
    const changes = Object.fromEntries(Object.entries(values).map(([k, v]) => [k, v.trim() || null]))
    update.mutate(toProfileUpdate(me, changes), { onSuccess: () => toast.success('Данные сохранены') })
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
          className="grid gap-4 sm:grid-cols-2"
          onSubmit={(e) => {
            e.preventDefault()
            submit()
          }}
        >
          {LETTER_FIELDS.map((f) => (
            <FormField key={f.key} label={f.label} htmlFor={f.key}>
              <Input
                id={f.key}
                value={values[f.key]}
                maxLength={f.max}
                autoComplete={f.autoComplete}
                onChange={(e) => setValues((v) => ({ ...v, [f.key]: e.target.value }))}
              />
            </FormField>
          ))}
          <Button type="submit" size="lg" className="justify-self-start sm:col-span-2" disabled={update.isPending}>
            {update.isPending && <Loader2 className="animate-spin" />}
            Сохранить
          </Button>
        </form>
      </CardContent>
    </Card>
  )
}
