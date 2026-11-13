import { cn } from '@/lib/utils'
import type { ChatMessage } from '@/types/models'

function TypingDots() {
  return (
    <span className="inline-flex gap-1 py-1.5" role="status" aria-label="Ассистент печатает">
      {[0, 1, 2].map((i) => (
        <span key={i} className="size-1.5 rounded-full bg-muted-foreground" style={{ animation: 'typing 1.2s infinite', animationDelay: `${i * 0.15}s` }} />
      ))}
    </span>
  )
}

export function ChatBubble({ message, pending }: { message: ChatMessage; pending: boolean }) {
  const mine = message.role === 'user'
  return (
    <div className={cn('flex animate-in fade-in-0 slide-in-from-bottom-1 duration-200', mine && 'justify-end')}>
      <div
        className={cn(
          'max-w-[85%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed whitespace-pre-wrap',
          mine ? 'rounded-br-md bg-primary text-primary-foreground' : 'rounded-bl-md bg-card ring-1 ring-border',
        )}
      >
        {message.content || (pending ? <TypingDots /> : null)}
      </div>
    </div>
  )
}
