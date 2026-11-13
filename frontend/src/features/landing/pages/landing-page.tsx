import { Link } from 'react-router-dom'
import { Hero } from '../components/hero'
import { Scenarios } from '../components/scenarios'
import { Steps } from '../components/steps'

export default function LandingPage() {
  return (
    <div className="flex min-h-svh flex-col">
      <Hero />
      <main className="mx-auto grid w-full max-w-5xl flex-1 content-start gap-14 px-4 pb-16 sm:px-6">
        <Scenarios />
        <Steps />
      </main>
      <footer className="border-t border-border px-4 py-6 text-sm text-muted-foreground">
        <div className="mx-auto flex max-w-5xl flex-wrap items-center justify-between gap-3 sm:px-2">
          <span>Ладно — помощник по ЖКХ. Не заменяет юриста.</span>
          <nav className="flex gap-4" aria-label="Документы">
            <Link to="/legal/privacy" className="hover:text-foreground hover:underline">
              Политика конфиденциальности
            </Link>
            <Link to="/legal/consent" className="hover:text-foreground hover:underline">
              Согласие на обработку данных
            </Link>
          </nav>
        </div>
      </footer>
    </div>
  )
}
