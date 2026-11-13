export type ChatEvent = { type: 'delta'; text: string } | { type: 'error'; detail: string; code: string }

/** Parses one SSE block (`event:`/`data:` lines). Returns null for the end marker and unknown blocks. */
export function parseSseBlock(block: string): ChatEvent | null {
  let name = 'message'
  const data: string[] = []
  for (const line of block.split('\n')) {
    if (line.startsWith('event:')) name = line.slice(6).trim()
    else if (line.startsWith('data:')) data.push(line.slice(5).trim())
  }
  const payload = data.join('\n')
  if (!payload || payload === '[DONE]') return null
  const json = JSON.parse(payload) as { delta?: string; detail?: string; code?: string }
  if (name === 'error') return { type: 'error', detail: json.detail ?? 'Ошибка ассистента', code: json.code ?? 'unknown_error' }
  return json.delta ? { type: 'delta', text: json.delta } : null
}

/** Yields complete SSE blocks from a chunked text stream. */
export async function* readSseBlocks(stream: ReadableStream<Uint8Array>): AsyncGenerator<string> {
  const reader = stream.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  for (;;) {
    const { value, done } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const blocks = buffer.split('\n\n')
    buffer = blocks.pop() ?? ''
    yield* blocks
  }
  if (buffer.trim()) yield buffer
}
