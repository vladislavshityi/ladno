import { useEffect, useRef, useState } from 'react'
import { Send } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { openExternal } from '@/lib/telegram'
import { cn } from '@/lib/utils'
import { useWidgetLogin } from '../hooks'

declare global {
  interface Window {
    onTelegramAuth?: (user: Record<string, unknown>) => void
  }
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
    const el = host.current
    if (!el) return
    window.onTelegramAuth = (user) => mutate(user)
    const script = document.createElement('script')
    script.src = 'https://telegram.org/js/telegram-widget.js?22'
    script.async = true
    script.dataset.telegramLogin = botName
    script.dataset.size = 'large'
    script.dataset.radius = '12'
    script.dataset.onauth = 'onTelegramAuth(user)'
    el.replaceChildren(script)

    const observer = new MutationObserver(() => {
      if (el.querySelector('iframe')) setState('ready')
    })
    observer.observe(el, { childList: true })
    const timer = window.setTimeout(() => setState((s) => (s === 'ready' ? s : 'failed')), WIDGET_TIMEOUT_MS)

    return () => {
      observer.disconnect()
      window.clearTimeout(timer)
      delete window.onTelegramAuth
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
