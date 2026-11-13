import { useEffect } from 'react'
import { Loader2 } from 'lucide-react'
import { Logo } from '@/components/logo'
import { Button } from '@/components/ui/button'
import { useWebAppLogin } from '../hooks'

/** Automatic sign-in inside a Telegram Mini App. */
export function TelegramSignIn() {
  const { mutate, isError, isPending } = useWebAppLogin()
  useEffect(() => mutate(undefined, { onError: () => undefined }), [mutate])

  return (
    <div className="flex min-h-svh flex-col items-center justify-center gap-4 px-4 text-center">
      <Logo markClassName="size-12" className="flex-col" />
      {isPending && <Loader2 className="size-5 animate-spin text-muted-foreground" aria-label="Входим" />}
      {isError && (
        <>
          <p className="text-sm text-muted-foreground">Не удалось войти через Telegram.</p>
          <Button onClick={() => mutate()}>Повторить</Button>
        </>
      )}
    </div>
  )
}
