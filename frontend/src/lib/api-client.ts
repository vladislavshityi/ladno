import type { ApiErrorBody } from '@/types/models'
import { getToken, setToken } from '@/lib/auth-token'

export class ApiError extends Error {
  status: number
  code: string
  constructor(status: number, message: string, code = 'unknown_error') {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
  }
}

type Query = Record<string, string | number | boolean | null | undefined>

interface RequestOptions {
  body?: unknown
  query?: Query
  signal?: AbortSignal
}

const RATE_LIMIT_MESSAGE = 'Слишком много запросов, попробуйте через минуту'

export function buildUrl(path: string, query?: Query) {
  const params = new URLSearchParams()
  for (const [k, v] of Object.entries(query ?? {})) {
    if (v !== undefined && v !== null && v !== '') params.set(k, String(v))
  }
  const qs = params.toString()
  return `/api${path}${qs ? `?${qs}` : ''}`
}

/** Turns a failed response into an `ApiError` with a user-facing message. */
export async function parseError(res: Response): Promise<ApiError> {
  let body: Partial<ApiErrorBody> | null = null
  try {
    body = await res.json()
  } catch {
    /* non-JSON error */
  }
  const detail = typeof body?.detail === 'string' ? body.detail : res.statusText || 'Ошибка запроса'
  const message = res.status === 429 ? RATE_LIMIT_MESSAGE : detail
  return new ApiError(res.status, message, body?.code)
}

async function send(method: string, path: string, opts: RequestOptions = {}): Promise<Response> {
  const headers: Record<string, string> = {}
  const token = getToken()
  if (token) headers.Authorization = `Bearer ${token}`
  const isForm = opts.body instanceof FormData
  if (opts.body !== undefined && !isForm) headers['Content-Type'] = 'application/json'

  let res: Response
  try {
    res = await fetch(buildUrl(path, opts.query), {
      method,
      headers,
      body: opts.body === undefined ? undefined : isForm ? (opts.body as FormData) : JSON.stringify(opts.body),
      signal: opts.signal,
    })
  } catch (err) {
    if (err instanceof DOMException && err.name === 'AbortError') throw err
    throw new ApiError(0, 'Нет соединения с сервером', 'network_error')
  }

  if (!res.ok) {
    // On /auth/* a 401 is a failed login, not an expired session.
    if (res.status === 401 && !path.startsWith('/auth/') && token) setToken(null)
    throw await parseError(res)
  }
  return res
}

async function request<T>(method: string, path: string, opts: RequestOptions = {}): Promise<T> {
  const res = await send(method, path, opts)
  if (res.status === 204) return undefined as T
  return (await res.json()) as T
}

export const api = {
  get: <T>(path: string, query?: Query) => request<T>('GET', path, { query }),
  post: <T>(path: string, body?: unknown) => request<T>('POST', path, { body: body ?? {} }),
  put: <T>(path: string, body: unknown) => request<T>('PUT', path, { body }),
  patch: <T>(path: string, body: unknown) => request<T>('PATCH', path, { body }),
  delete: <T = void>(path: string) => request<T>('DELETE', path),
  upload: <T>(path: string, file: File) => {
    const form = new FormData()
    form.append('file', file)
    return request<T>('POST', path, { body: form })
  },
  /** Raw response, for streamed bodies and binary files. */
  raw: (method: string, path: string, body?: unknown, signal?: AbortSignal) => send(method, path, { body, signal }),
}

export function errorMessage(err: unknown): string {
  return err instanceof ApiError ? err.message : 'Что-то пошло не так'
}
