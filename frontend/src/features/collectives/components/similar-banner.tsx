import { Users } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import { Label } from '@/components/ui/label'
import { plural } from '@/lib/plural'

export interface CollectiveChoice {
  join: boolean | null
  consentLetter: boolean
}

interface Props {
  count: number
  choice: CollectiveChoice
  onChange: (choice: CollectiveChoice) => void
}

/** Offer to file together with neighbours who reported the same problem in the last month. */
export function SimilarBanner({ count, choice, onChange }: Props) {
  return (
    <div className="grid gap-3 rounded-2xl bg-primary/8 p-4 ring-1 ring-primary/25">
      <div className="flex items-start gap-3">
        <Users className="mt-0.5 size-5 shrink-0 text-primary" />
        <p className="text-sm leading-relaxed">
          <span className="font-medium">
            Ещё {count} {plural(count, 'жилец', 'жильца', 'жильцов')} вашего дома {plural(count, 'сообщил', 'сообщили', 'сообщили')} о том же за последний месяц.
            Подать вместе?
          </span>{' '}
          <span className="text-muted-foreground">Коллективное обращение сложнее проигнорировать. Соседи увидят только число участников.</span>
        </p>
      </div>
      <div className="flex flex-wrap gap-2">
        <Button className="rounded-full" variant={choice.join === true ? 'default' : 'outline'} onClick={() => onChange({ ...choice, join: true })}>
          Присоединиться
        </Button>
        <Button className="rounded-full" variant={choice.join === false ? 'default' : 'outline'} onClick={() => onChange({ ...choice, join: false })}>
          Подать отдельно
        </Button>
      </div>
      {choice.join && (
        <div className="flex items-start gap-2.5">
          <Checkbox id="consent-letter" checked={choice.consentLetter} onCheckedChange={(v) => onChange({ ...choice, consentLetter: v === true })} className="mt-0.5" />
          <Label htmlFor="consent-letter" className="text-sm leading-snug font-normal">
            Указать в коллективном письме мои ФИО и квартиру и приложить мои фото
          </Label>
        </div>
      )}
    </div>
  )
}
