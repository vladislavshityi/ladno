import { describe, expect, it } from 'vitest'
import { ApiError, buildUrl, errorMessage, parseError } from './api-client'

const json = (status: number, body: unknown) => new Response(JSON.stringify(body), { status })

describe('parseError', () => {
  it('reads detail and code from the backend error body', async () => {
    const err = await parseError(json(403, { detail: 'Нужно согласие', code: 'consent_required' }))
    expect(err).toBeInstanceOf(ApiError)
    expect(err.status).toBe(403)
    expect(err.code).toBe('consent_required')
    expect(err.message).toBe('Нужно согласие')
  })

  it('replaces the message on 429', async () => {
    const err = await parseError(json(429, { detail: 'rate limited', code: 'rate_limited' }))
    expect(err.message).toBe('Слишком много запросов, попробуйте через минуту')
  })

  it('falls back to the status text for non-JSON bodies', async () => {
    const err = await parseError(new Response('<html>', { status: 502, statusText: 'Bad Gateway' }))
    expect(err.message).toBe('Bad Gateway')
    expect(err.code).toBe('unknown_error')
  })
})

describe('buildUrl', () => {
  it('skips empty query values', () => {
    expect(buildUrl('/addresses/search', { q: 'Кутузова', page: undefined, x: '' })).toBe(
      `/api/addresses/search?q=${encodeURIComponent('Кутузова')}`,
    )
  })
})

describe('errorMessage', () => {
  it('hides unknown errors behind a generic message', () => {
    expect(errorMessage(new Error('boom'))).toBe('Что-то пошло не так')
  })
})
