import { Download, FileText, Loader2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardAction, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { CopyButton } from '@/components/copy-button'
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

  if (!letter.data) {
    return (
      <Button size="lg" className="justify-self-start" disabled={letter.isPending} onClick={() => letter.mutate()}>
        {letter.isPending ? <Loader2 className="animate-spin" /> : <FileText />}
        Заявление на перерасчёт
      </Button>
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
