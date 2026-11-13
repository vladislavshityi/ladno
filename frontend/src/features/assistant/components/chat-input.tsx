import { useState } from 'react'
import { ArrowUp } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'

export function ChatInput({ onSend, disabled }: { onSend: (text: string) => void; disabled: boolean }) {
  const [text, setText] = useState('')
  const submit = () => {
    const value = text.trim()
    if (!value || disabled) return
    onSend(value)
    setText('')
  }

  return (
    <form
      className="flex items-end gap-2 rounded-2xl bg-card p-2 ring-1 ring-border focus-within:ring-2 focus-within:ring-ring/50"
      onSubmit={(e) => {
        e.preventDefault()
        submit()
      }}
    >
      <Textarea
        value={text}
        rows={1}
        maxLength={4000}
        aria-label="Сообщение ассистенту"
        placeholder="Спросите про квитанцию или обращение"
        className="max-h-32 min-h-10 resize-none border-0 bg-transparent shadow-none focus-visible:ring-0 dark:bg-transparent"
        onChange={(e) => setText(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault()
            submit()
          }
        }}
      />
      <Button type="submit" size="icon" className="rounded-xl" disabled={disabled || !text.trim()} aria-label="Отправить">
        <ArrowUp />
      </Button>
    </form>
  )
}
