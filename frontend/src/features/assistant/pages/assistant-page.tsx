import { useEffect, useRef } from 'react'
import { CircleAlert, Sparkles } from 'lucide-react'
import { PageHeader } from '@/components/page-header'
import { useChat } from '../hooks'
import { ChatBubble } from '../components/chat-bubble'
import { ChatInput } from '../components/chat-input'
import { ContextPanel } from '../components/context-panel'
import { useContextSelection } from '../use-context-selection'

const STARTERS = [
  'Почему в этом месяце выросла квитанция?',
  'Кому жаловаться, если не убирают снег во дворе?',
  'Что делать, если УК не отвечает на обращение?',
]

export default function AssistantPage() {
  const { selection, setSelection, issues, receipts, ready } = useContextSelection()
  const { messages, streaming, error, send } = useChat(selection)
  const end = useRef<HTMLDivElement>(null)
  useEffect(() => {
    end.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [messages])

  return (
    <div className="mx-auto grid max-w-2xl gap-5">
      <PageHeader title="Ассистент" description="Отвечает про обращения и квитанции с опорой на ваши данные" />
      <ContextPanel selection={selection} issues={issues} receipts={receipts} onChange={setSelection} />
      <div className="grid min-h-64 content-start gap-3" aria-live="polite">
        {messages.length === 0 && (
          <div className="grid gap-3 animate-in fade-in-0 duration-300">
            <p className="flex items-center gap-2 text-sm text-muted-foreground">
              <Sparkles className="size-4 text-primary" /> Попробуйте спросить:
            </p>
            {STARTERS.map((s) => (
              <button
                key={s}
                type="button"
                onClick={() => void send(s)}
                disabled={!ready}
                className="rounded-2xl bg-card px-4 py-3 text-left text-sm ring-1 ring-border transition-all hover:-translate-y-px hover:shadow-md focus-visible:ring-2 focus-visible:ring-ring/50 focus-visible:outline-none"
              >
                {s}
              </button>
            ))}
          </div>
        )}
        {messages.map((m, i) => (
          <ChatBubble key={i} message={m} pending={streaming && i === messages.length - 1} />
        ))}
        {error && (
          <p role="alert" className="flex items-start gap-2 rounded-xl bg-destructive/10 p-3 text-sm text-destructive">
            <CircleAlert className="mt-0.5 size-4 shrink-0" /> {error}
          </p>
        )}
        <div ref={end} />
      </div>
      <div className="sticky bottom-20 md:bottom-4">
        <ChatInput onSend={(t) => void send(t)} disabled={streaming || !ready} />
      </div>
    </div>
  )
}
