import { Card, CardAction, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { CopyButton } from '@/components/copy-button'

interface Props {
  title: string
  text: string
  hint?: string
}

export function LetterCard({ title, text, hint }: Props) {
  return (
    <Card className="rounded-2xl border-0 shadow-sm ring-1 ring-border">
      <CardHeader>
        <div>
          <CardTitle>{title}</CardTitle>
          {hint && <p className="mt-1 text-xs text-muted-foreground">{hint}</p>}
        </div>
        <CardAction>
          <CopyButton text={text} />
        </CardAction>
      </CardHeader>
      <CardContent>
        <p className="rounded-xl bg-muted/60 p-3.5 text-sm leading-relaxed whitespace-pre-wrap">{text}</p>
      </CardContent>
    </Card>
  )
}
