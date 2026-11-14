import { useState } from 'react'
import { Download, FileText, Loader2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardAction, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { CopyButton } from '@/components/copy-button'
import { ApplicantPrompt } from '@/features/profile/components/applicant-prompt'
import { useApplicantPrompt } from '@/features/profile/use-applicant-prompt'
import { useRecalculationLetter } from '../hooks'

function downloadText(text: string) {
  const url = URL.createObjectURL(new Blob([text], { type: 'text/plain;charset=utf-8' }))
  const a = document.createElement('a')
  a.href = url
  a.download = 'zayavlenie-na-pereraschet.txt'
  a.click()
  URL.revokeObjectURL(url)
}

export function LetterPanel({ receiptId }: { receiptId: string }) {
  const letter = useRecalculationLetter(receiptId)
  const applicant = useApplicantPrompt()
  const [asking, setAsking] = useState(false)

  const make = () => letter.mutate()
  // Without a name in the profile the letter would carry marks, so ask for it first.
  const start = () => (applicant.visible ? setAsking(true) : make())
  const saveAndMake = async () => {
    if (await applicant.save()) make()
  }

  if (!letter.data) {
    return (
      <div className="grid gap-3">
        {asking && applicant.visible ? (
          <ApplicantPrompt
            prompt={applicant}
            idPrefix="recalc"
            onSkip={make}
            submit={{ label: 'Сохранить и составить заявление', onClick: () => void saveAndMake(), pending: applicant.saving || letter.isPending }}
          />
        ) : (
          <Button size="lg" className="justify-self-start" disabled={letter.isPending} onClick={start}>
            {letter.isPending ? <Loader2 className="animate-spin" /> : <FileText />}
            Заявление на перерасчёт
          </Button>
        )}
      </div>
    )
  }

  return (
    <Card className="rounded-2xl border-0 shadow-sm ring-1 ring-border animate-in fade-in-0 slide-in-from-bottom-2 duration-300">
      <CardHeader>
        <CardTitle>Заявление на перерасчёт</CardTitle>
        <CardAction className="flex gap-2">
          <CopyButton text={letter.data.text} />
          <Button variant="outline" size="sm" onClick={() => downloadText(letter.data.text)}>
            <Download /> Скачать
          </Button>
        </CardAction>
      </CardHeader>
      <CardContent>
        <p className="rounded-xl bg-muted/60 p-3.5 text-sm leading-relaxed whitespace-pre-wrap">{letter.data.text}</p>
      </CardContent>
    </Card>
  )
}
