import { Loader2, Wrench } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { useAuthConfig, useDevLogin } from '../hooks'
import { TelegramLoginButton } from './telegram-login-button'

export function SignInPanel() {
  const { data: config, isLoading } = useAuthConfig()
  const dev = useDevLogin()

  if (isLoading) return <Skeleton className="mx-auto h-28 w-full max-w-xs rounded-2xl sm:mx-0" />

  const telegram = Boolean(config?.telegram_bot_username)

  return (
    <div className="mx-auto grid w-full max-w-xs gap-4 rounded-2xl bg-card p-5 shadow-sm ring-1 ring-border sm:mx-0">
      <p className="text-sm font-medium">Войдите, чтобы начать</p>
      {telegram && <TelegramLoginButton botName={config!.telegram_bot_username} />}
      {config?.dev_login_enabled && (
        <Button size="lg" variant={telegram ? 'outline' : 'default'} className="w-full" onClick={() => dev.mutate()} disabled={dev.isPending}>
          {dev.isPending ? <Loader2 className="animate-spin" /> : <Wrench />}
          Войти (режим разработки)
        </Button>
      )}
      {config && !telegram && !config.dev_login_enabled && (
        <p className="text-sm text-muted-foreground">Вход пока недоступен: бот Telegram не настроен.</p>
      )}
    </div>
  )
}
