import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { Skeleton } from '@/components/ui/skeleton'
import { EmptyState } from '@/components/empty-state'
import { Button } from '@/components/ui/button'
import { ServerCrash } from 'lucide-react'
import { useAuth } from '../auth-context'
import { useMe } from '../hooks'

/** Requires a signed-in user whose profile has loaded. */
export function RequireAuth() {
  const { token } = useAuth()
  const { data: me, isError, refetch } = useMe()
  const { pathname } = useLocation()

  // The target is kept so a deep link (e.g. from the bot) opens after the automatic sign-in.
  if (!token) return <Navigate to="/" replace state={{ from: pathname }} />
  if (isError) {
    return (
      <div className="mx-auto flex min-h-svh max-w-md items-center px-4">
        <EmptyState
          icon={ServerCrash}
          title="Не удалось загрузить профиль"
          action={<Button onClick={() => void refetch()}>Повторить</Button>}
        />
      </div>
    )
  }
  if (!me) return <Skeleton className="m-6 h-64 rounded-2xl" />
  return <Outlet />
}

/** Saving actions are blocked on the server until consent is given, so the app is gated on it. */
export function RequireConsent() {
  const { data: me } = useMe()
  if (me?.consent_required) return <Navigate to="/consent" replace />
  return <Outlet />
}
