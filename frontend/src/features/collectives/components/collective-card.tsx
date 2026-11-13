import { Download, FilePlus2, Loader2, Send, Users } from 'lucide-react'
import { toast } from 'sonner'
import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Checkbox } from '@/components/ui/checkbox'
import { Label } from '@/components/ui/label'
import { Skeleton } from '@/components/ui/skeleton'
import { LetterCard } from '@/features/issues/components/letter-card'
import { errorMessage } from '@/lib/api-client'
import { saveBlob } from '@/lib/download'
import { collectivesApi } from '../api'
import { useCollective, useCollectiveLetter, useSetConsent, useSubmitCollective } from '../hooks'

const MIN_MEMBERS = 2

/** Collective complaint on the issue page: member count, consent, joint letter. */
export function CollectiveCard({ collectiveId }: { collectiveId: string }) {
  const { data: collective } = useCollective(collectiveId)
  const consent = useSetConsent(collectiveId)
  const letter = useCollectiveLetter(collectiveId)
  const submit = useSubmitCollective(collectiveId)
  const [downloading, setDownloading] = useState(false)

  if (!collective) return <Skeleton className="h-40 rounded-2xl" />
  const canBuild = collective.members_count >= MIN_MEMBERS
  const open = collective.status === 'open'

  const downloadPdf = async () => {
    setDownloading(true)
    try {
      saveBlob(await collectivesApi.letterPdf(collectiveId), 'collective-letter.pdf')
    } catch (err) {
      toast.error(errorMessage(err))
    } finally {
      setDownloading(false)
    }
  }

  return (
    <>
      <Card className="rounded-2xl border-0 shadow-sm ring-1 ring-primary/25">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Users className="size-5 text-primary" /> Коллективное обращение: вас {collective.members_count}
          </CardTitle>
          <p className="text-sm text-muted-foreground">
            {collective.category_title}, {collective.address}
            {collective.status === 'submitted' && ' · подано'}
          </p>
        </CardHeader>
        <CardContent className="grid gap-4">
          <p className="text-sm text-muted-foreground">Соседи видят только число участников. Ваши данные попадут в общее письмо, только если вы согласны.</p>
          <div className="flex items-start gap-2.5">
            <Checkbox
              id="collective-consent"
              checked={collective.consent_letter}
              disabled={consent.isPending}
              onCheckedChange={(v) => consent.mutate(v === true, { onError: (err) => toast.error(errorMessage(err)) })}
              className="mt-0.5"
            />
            <Label htmlFor="collective-consent" className="text-sm leading-snug font-normal">
              Указать мои ФИО и квартиру в коллективном письме
            </Label>
          </div>
          {canBuild ? (
            <div className="flex flex-wrap gap-2">
              <Button disabled={letter.isPending} onClick={() => letter.mutate()}>
                {letter.isPending ? <Loader2 className="animate-spin" /> : <FilePlus2 />} Сформировать коллективное обращение
              </Button>
              {letter.data && (
                <Button variant="outline" disabled={downloading} onClick={() => void downloadPdf()}>
                  {downloading ? <Loader2 className="animate-spin" /> : <Download />} Скачать PDF с фото
                </Button>
              )}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">Письмо можно сформировать, когда участников станет двое.</p>
          )}
        </CardContent>
      </Card>
      {letter.data && (
        <>
          <LetterCard title="Коллективное письмо" hint={`От ${letter.data.members_count} жителей дома`} text={letter.data.text} />
          {open && (
            <Button
              variant="outline"
              className="justify-self-start"
              disabled={submit.isPending}
              onClick={() => submit.mutate(undefined, { onSuccess: () => toast.success('Отметили поданным: сроки ответа запущены'), onError: (err) => toast.error(errorMessage(err)) })}
            >
              {submit.isPending ? <Loader2 className="animate-spin" /> : <Send />} Я подал(а) коллективное обращение
            </Button>
          )}
        </>
      )}
    </>
  )
}
