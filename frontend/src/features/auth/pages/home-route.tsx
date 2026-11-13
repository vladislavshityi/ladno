import { Navigate } from 'react-router-dom'
import LandingPage from '@/features/landing/pages/landing-page'
import { isTelegramWebApp } from '@/lib/telegram'
import { useAuth } from '../auth-context'
import { TelegramSignIn } from '../components/telegram-sign-in'

/** Entry point: signed-in users go to the app, Mini App users sign in automatically, others see the landing page. */
export default function HomeRoute() {
  const { token } = useAuth()
  if (token) return <Navigate to="/issues/new" replace />
  return isTelegramWebApp() ? <TelegramSignIn /> : <LandingPage />
}
