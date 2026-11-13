import { useState } from 'react'
import { CheckCircle2, ExternalLink, Loader2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { FormField } from '@/components/form-field'
import { Skeleton } from '@/components/ui/skeleton'
import { openExternal } from '@/lib/telegram'
import type { Issue } from '@/types/models'
import { useChannels, usePatchIssue, useSubmission } from '../hooks'
import { SubmitEmail } from './submit-email'

/** Draft stage: open the submission form, then record that the complaint was sent. */
export function SubmitPanel({ issue }: { issue: Issue }) {
  const { data: submission } = useSubmission(issue.id, true)
  const { data: channels } = useChannels(issue.id)
  const patch = usePatchIssue(issue.id)
  const email = channels?.find((c) => c.name === 'email')
  const [ref, setRef] = useState('')

  return (
    <Card className="rounded-2xl border-0 bg-primary/6 shadow-sm ring-1 ring-primary/25">
      <CardHeader>
        <CardTitle>Подайте обращение</CardTitle>
        <CardDescription>Мы подали бы его сами, но платформа принимает обращения только от вас.</CardDescription>
      </CardHeader>
      <CardContent className="grid gap-5">
        {email && <SubmitEmail issue={issue} channel={email} />}
        {submission ? (
          <>
            <ol className="grid gap-2 text-sm">
              {submission.steps.map((step, i) => (
                <li key={step} className="flex gap-3">
                  <span className="flex size-5 shrink-0 items-center justify-center rounded-full bg-primary/15 text-xs font-semibold text-primary">{i + 1}</span>
                  {step}
                </li>
              ))}
            </ol>
            <Button size="lg" className="justify-self-start" onClick={() => openExternal(submission.open_url)}>
              <ExternalLink /> Подать через «Решаем вместе»
            </Button>
          </>
        ) : (
          <Skeleton className="h-24 rounded-xl" />
        )}
        <form
          className="grid gap-3 border-t border-primary/15 pt-4"
          onSubmit={(e) => {
            e.preventDefault()
            patch.mutate({ status: 'submitted', external_ref: ref.trim() || null })
          }}
        >
          <FormField label="Номер или ссылка обращения" htmlFor="external-ref" hint="Появится после подачи. Можно добавить позже.">
            <Input id="external-ref" value={ref} maxLength={100} onChange={(e) => setRef(e.target.value)} />
          </FormField>
          <Button type="submit" variant="secondary" size="lg" className="justify-self-start" disabled={patch.isPending}>
            {patch.isPending ? <Loader2 className="animate-spin" /> : <CheckCircle2 />}
            Я подал
          </Button>
        </form>
      </CardContent>
    </Card>
  )
}
