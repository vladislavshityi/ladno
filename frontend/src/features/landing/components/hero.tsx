import { Link } from 'react-router-dom'
import { Logo } from '@/components/logo'
import { ThemeToggle } from '@/components/theme-toggle'
import { SignInPanel } from '@/features/auth/components/sign-in-panel'

export function Hero() {
  return (
    <header className="mx-auto w-full max-w-5xl px-4 pt-4 sm:px-6">
      <div className="flex h-12 items-center justify-between">
        <Link to="/" aria-label="Ладно">
          <Logo />
        </Link>
        <ThemeToggle />
      </div>
      <div className="grid gap-8 pt-12 pb-14 animate-in fade-in-0 slide-in-from-bottom-2 duration-500 sm:pt-20">
        <div className="max-w-2xl space-y-5 text-center sm:text-left">
          <p className="text-sm font-medium text-primary">Помощник жителя Владивостока по ЖКХ</p>
          <h1 className="text-4xl leading-[1.1] font-semibold tracking-tight text-balance sm:text-5xl">
            С управляйкой и квитанциями — по-человечески
          </h1>
          <p className="text-lg text-muted-foreground text-pretty">
            Подскажем, куда и как пожаловаться на проблему в доме, и простыми словами объясним, за что вы платите.
          </p>
        </div>
        <SignInPanel />
      </div>
    </header>
  )
}
