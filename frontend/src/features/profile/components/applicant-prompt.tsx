import { ShieldCheck } from 'lucide-react'
import { Button } from '@/components/ui/button'
import type { useApplicantPrompt } from '../use-applicant-prompt'
import { LetterInputs } from './letter-inputs'

interface Props {
  prompt: ReturnType<typeof useApplicantPrompt>
  idPrefix: string
  /** Called after the resident chooses to go on without the data. */
  onSkip?: () => void
  /** Own submit button, for places where no other button saves the form. */
  submit?: { label: string; onClick: () => void; pending?: boolean }
}

/** Compact form shown before a letter is made while the profile has no name, flat or phone. */
export function ApplicantPrompt({ prompt, idPrefix, onSkip, submit }: Props) {
  const { me, visible, keys, form } = prompt
  if (!visible) return null
  const name = me?.first_name
  return (
    <section aria-labelledby={`${idPrefix}-title`} className="grid gap-4 rounded-2xl bg-muted/50 p-4 ring-1 ring-border">
      <div>
        <h3 id={`${idPrefix}-title`} className="font-medium">
          Данные для письма
        </h3>
        <p className="mt-1 flex items-start gap-2 text-sm text-muted-foreground">
          <ShieldCheck className="mt-0.5 size-4 shrink-0 text-success" />
          Данные сохранятся в профиле и будут подставляться в письма. В языковую модель не передаются.
        </p>
      </div>
      <form
        noValidate
        className="grid gap-3 sm:grid-cols-2"
        onSubmit={(e) => {
          e.preventDefault()
          submit?.onClick()
        }}
      >
        <LetterInputs
          form={form}
          keys={keys}
          idPrefix={idPrefix}
          placeholders={name ? { full_name: `Иванов ${name}` } : undefined}
          hints={{ full_name: name ? `В Telegram вы «${name}». Укажите фамилию и имя полностью` : 'Фамилия, имя и по желанию отчество' }}
        />
        <div className="flex flex-wrap gap-2 sm:col-span-2">
          {submit && (
            <Button type="submit" disabled={submit.pending}>
              {submit.label}
            </Button>
          )}
          <Button
            type="button"
            variant="ghost"
            onClick={() => {
              prompt.skip()
              onSkip?.()
            }}
          >
            Пропустить
          </Button>
        </div>
      </form>
    </section>
  )
}
