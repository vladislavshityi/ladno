import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'
import { Logo } from '@/components/logo'
import { ThemeToggle } from '@/components/theme-toggle'
import { Button } from '@/components/ui/button'
import { useAuthConfig } from '@/features/auth/hooks'
import { LEGAL_UPDATED_AT } from './versions'

export interface LegalSection {
  title: string
  paragraphs?: ReactNode[]
  items?: ReactNode[]
}

interface Props {
  title: string
  sections: LegalSection[]
}

export function LegalDocument({ title, sections }: Props) {
  const { data: config } = useAuthConfig()
  return (
    <div className="min-h-svh">
      <header className="mx-auto flex h-16 max-w-3xl items-center justify-between px-4">
        <Link to="/" aria-label="Ладно">
          <Logo />
        </Link>
        <ThemeToggle />
      </header>
      <main className="mx-auto max-w-3xl px-4 pb-16 animate-in fade-in-0 duration-300">
        <Button asChild variant="ghost" size="sm" className="-ml-2 mb-4">
          <Link to="/">
            <ArrowLeft /> На главную
          </Link>
        </Button>
        <h1 className="text-3xl font-semibold tracking-tight text-balance">{title}</h1>
        <p className="mt-2 text-sm text-muted-foreground">
          {config && `Версия ${config.consent_version}, `}действует с {LEGAL_UPDATED_AT}
        </p>
        <div className="legal-prose mt-6">
          {sections.map((s) => (
            <section key={s.title}>
              <h2>{s.title}</h2>
              {s.paragraphs?.map((p, i) => <p key={i}>{p}</p>)}
              {s.items && (
                <ul>
                  {s.items.map((item, i) => <li key={i}>{item}</li>)}
                </ul>
              )}
            </section>
          ))}
        </div>
      </main>
    </div>
  )
}
