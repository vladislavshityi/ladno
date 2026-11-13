import { NavLink } from 'react-router-dom'
import { useNavItems } from '@/components/nav-items'
import { cn } from '@/lib/utils'

/** Bottom tab bar for phones and the Telegram Mini App. */
export function MobileNav() {
  const items = useNavItems()
  return (
    <nav
      aria-label="Основная навигация"
      className="fixed inset-x-0 bottom-0 z-30 flex border-t border-border bg-background/85 pb-[env(safe-area-inset-bottom)] backdrop-blur-xl md:hidden"
    >
      {items.map(({ to, shortLabel, icon: Icon }) => (
        <NavLink
          key={to}
          to={to}
          end={to === '/issues'}
          className={({ isActive }) =>
            cn(
              'flex min-w-0 flex-1 flex-col items-center gap-0.5 px-0.5 py-2 text-[10px] font-medium transition-colors',
              isActive ? 'text-primary' : 'text-muted-foreground',
            )
          }
        >
          <Icon className="size-5" />
          <span className="truncate">{shortLabel}</span>
        </NavLink>
      ))}
    </nav>
  )
}
