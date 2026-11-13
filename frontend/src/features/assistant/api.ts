import { api, ApiError } from '@/lib/api-client'
import type { ChatMessage } from '@/types/models'
import { parseSseBlock, readSseBlocks } from './sse'

/** Items the assistant may see; empty lists mean "none", not "default". */
export interface ChatContext {
  issue_ids: string[]
  receipt_ids: string[]
}

export const assistantApi = {
  /** Streams the assistant reply; yields text deltas as they arrive. */
  async *chat(messages: ChatMessage[], context: ChatContext, signal?: AbortSignal): AsyncGenerator<string> {
    const res = await api.raw('POST', '/assistant/chat', { messages, ...context }, signal)
    if (!res.body) throw new ApiError(0, 'Пустой ответ сервера')
    for await (const block of readSseBlocks(res.body)) {
      const event = parseSseBlock(block)
      if (event?.type === 'error') throw new ApiError(502, event.detail, event.code)
      if (event?.type === 'delta') yield event.text
    }
  },
}
