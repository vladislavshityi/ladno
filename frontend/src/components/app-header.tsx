import { Link } from 'react-router-dom'
import { SidebarTrigger } from '@/components/ui/sidebar'
import { Logo } from '@/components/logo'
import { ThemeToggle } from '@/components/theme-toggle'

export function AppHeader() {
  return (
    <header className="sticky top-0 z-20 flex h-14 shrink-0 items-center gap-2 border-b border-border bg-background/70 px-4 backdrop-blur-xl">
      <SidebarTrigger className="-ml-1 hidden md:inline-flex" />
      <Link to="/issues/new" className="md:hidden" aria-label="Ладно — на главную">
        <Logo markClassName="size-7" />
      </Link>
      <div className="ml-auto">
        <ThemeToggle />
      </div>
    </header>
  )
}
