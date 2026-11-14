import { useEffect, useRef, useState } from 'react'
import { Send } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { openExternal } from '@/lib/telegram'
import { cn } from '@/lib/utils'
import { useWidgetLogin } from '../hooks'

const WIDGET_FIELDS = ['id', 'first_name', 'last_name', 'username', 'photo_url', 'auth_date', 'hash']
const NUMERIC_FIELDS = new Set(['id', 'auth_date'])

/**
 * After login the widget redirects back with the signed fields in the query string.
 * A redirect is used instead of data-onauth, which the widget runs through eval and our CSP forbids.
 */
function takeWidgetResult(): Record<string, unknown> | null {
  const params = new URLSearchParams(window.location.search)
  if (!params.has('hash') || !params.has('id')) return null
  const user: Record<string, unknown> = {}
  for (const key of WIDGET_FIELDS) {
    const value = params.get(key)
    if (value !== null) user[key] = NUMERIC_FIELDS.has(key) ? Number(value) : value
    params.delete(key)
  }
  const rest = params.toString()
  window.history.replaceState(null, '', window.location.pathname + (rest ? `?${rest}` : '') + window.location.hash)
  return user
}

const WIDGET_TIMEOUT_MS = 4000

/**
 * Official Telegram Login Widget. It only renders on the domain registered with BotFather via /setdomain,
 * so when no widget appears in time a plain button to the bot is shown instead.
 */
export function TelegramLoginButton({ botName }: { botName: string }) {
  const host = useRef<HTMLDivElement>(null)
  const [state, setState] = useState<'loading' | 'ready' | 'failed'>('loading')
  const { mutate } = useWidgetLogin()

  useEffect(() => {
    const user = takeWidgetResult()
    if (user) mutate(user)
  }, [mutate])

  useEffect(() => {
    const el = host.current
    if (!el) return
    const script = document.createElement('script')
    script.src = 'https://telegram.org/js/telegram-widget.js?22'
    script.async = true
    script.dataset.telegramLogin = botName
    script.dataset.size = 'large'
    script.dataset.radius = '12'
    script.dataset.authUrl = window.location.origin + window.location.pathname
    el.replaceChildren(script)

    const observer = new MutationObserver(() => {
      if (el.querySelector('iframe')) setState('ready')
    })
    observer.observe(el, { childList: true })
    const timer = window.setTimeout(() => setState((s) => (s === 'ready' ? s : 'failed')), WIDGET_TIMEOUT_MS)

    return () => {
      observer.disconnect()
      window.clearTimeout(timer)
      el.replaceChildren()
    }
  }, [botName, mutate])

  return (
    <div className="relative grid gap-2">
      <div ref={host} className={cn('flex justify-center', state !== 'ready' && 'invisible absolute')} />
      {state === 'loading' && <Skeleton className="h-10 w-full rounded-xl" />}
      {state === 'failed' && (
        <>
          <Button size="lg" className="w-full" onClick={() => openExternal(`https://t.me/${botName}`)}>
            <Send /> Открыть бота в Telegram
          </Button>
          <p className="text-center text-xs text-muted-foreground">Кнопка входа Telegram недоступна на этом адресе. Войдите через бота.</p>
        </>
      )}
    </div>
  )
}
