import { describe, expect, it } from 'vitest'
import { parseSseBlock } from './sse'

describe('parseSseBlock', () => {
  it('reads text deltas', () => {
    expect(parseSseBlock('data: {"delta": "Привет"}')).toEqual({ type: 'delta', text: 'Привет' })
  })

  it('reads error events', () => {
    const block = 'event: error\ndata: {"detail": "Сбой", "code": "bad_gateway"}'
    expect(parseSseBlock(block)).toEqual({ type: 'error', detail: 'Сбой', code: 'bad_gateway' })
  })

  it('ignores the end marker', () => {
    expect(parseSseBlock('data: [DONE]')).toBeNull()
  })
})
