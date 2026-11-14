import { useRouteError } from 'react-router-dom'
import { Logo } from '@/components/logo'
import { Button } from '@/components/ui/button'

/** Shown instead of a blank technical error when a page crashes. */
export function RouteError() {
  const error = useRouteError()
  console.error(error)
  return (
    <div className="flex min-h-svh flex-col items-center justify-center gap-4 px-4 text-center">
      <Logo markClassName="size-12" className="flex-col" />
      <p className="font-medium">Что-то пошло не так</p>
      <p className="max-w-sm text-sm text-muted-foreground">Попробуйте обновить страницу. Если ошибка повторится, вернитесь на главную.</p>
      <div className="flex gap-2">
        <Button onClick={() => window.location.reload()}>Обновить</Button>
        <Button variant="outline" onClick={() => window.location.assign('/')}>На главную</Button>
      </div>
    </div>
  )
}
