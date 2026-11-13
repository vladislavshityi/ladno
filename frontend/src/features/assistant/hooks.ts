import { useCallback, useEffect, useRef, useState } from 'react'
import { ApiError } from '@/lib/api-client'
import type { ChatMessage } from '@/types/models'
import { assistantApi } from './api'

const UNAVAILABLE = 'Ассистент сейчас недоступен. Попробуйте позже — остальные разделы работают как обычно.'

/** Chat state for one visit; the server keeps no history, so the full dialog is sent every time. */
export function useChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [streaming, setStreaming] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const abort = useRef<AbortController | null>(null)

  useEffect(() => () => abort.current?.abort(), [])

  const send = useCallback(
    async (text: string) => {
      const history: ChatMessage[] = [...messages, { role: 'user', content: text }]
      setMessages([...history, { role: 'assistant', content: '' }])
      setStreaming(true)
      setError(null)
      abort.current = new AbortController()
      try {
        for await (const delta of assistantApi.chat(history, abort.current.signal)) {
          setMessages((m) => m.map((msg, i) => (i === m.length - 1 ? { ...msg, content: msg.content + delta } : msg)))
        }
      } catch (err) {
        if (err instanceof DOMException && err.name === 'AbortError') return
        setError(err instanceof ApiError && err.status === 503 ? UNAVAILABLE : err instanceof ApiError ? err.message : 'Не удалось получить ответ')
        // Drop the empty placeholder, keep a partial answer.
        setMessages((m) => (m[m.length - 1]?.content ? m : m.slice(0, -1)))
      } finally {
        setStreaming(false)
      }
    },
    [messages],
  )

  return { messages, streaming, error, send }
}
