import { useState } from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import { Ellipsis } from 'lucide-react'
import { useNavItems } from '@/components/nav-items'
import { Sheet, SheetContent, SheetHeader, SheetTitle } from '@/components/ui/sheet'
import { cn } from '@/lib/utils'

const tabClass = 'flex min-w-0 flex-1 flex-col items-center gap-0.5 px-0.5 py-2 text-[11px] font-medium transition-colors'

/** Bottom tab bar for phones and the Telegram Mini App: four main tabs, the rest under «Ещё». */
export function MobileNav() {
  const items = useNavItems()
  const { pathname } = useLocation()
  const [open, setOpen] = useState(false)
  const primary = items.filter((i) => i.primary)
  const more = items.filter((i) => !i.primary)
  const moreActive = more.some((i) => pathname.startsWith(i.to))

  return (
    <nav
      aria-label="Основная навигация"
      className="fixed inset-x-0 bottom-0 z-30 flex border-t border-border bg-background/85 pb-[env(safe-area-inset-bottom)] backdrop-blur-xl md:hidden"
    >
      {primary.map(({ to, shortLabel, icon: Icon }) => (
        <NavLink
          key={to}
          to={to}
          end={to === '/issues'}
          className={({ isActive }) => cn(tabClass, isActive ? 'text-primary' : 'text-muted-foreground')}
        >
          <Icon className="size-5" />
          <span className="max-w-full truncate">{shortLabel}</span>
        </NavLink>
      ))}
      {more.length > 0 && (
        <button type="button" onClick={() => setOpen(true)} className={cn(tabClass, moreActive ? 'text-primary' : 'text-muted-foreground')}>
          <Ellipsis className="size-5" />
          <span>Ещё</span>
        </button>
      )}
      <Sheet open={open} onOpenChange={setOpen}>
        <SheetContent side="bottom" className="rounded-t-2xl pb-[calc(env(safe-area-inset-bottom)+1rem)]">
          <SheetHeader>
            <SheetTitle>Ещё</SheetTitle>
          </SheetHeader>
          <div className="grid gap-1 px-4">
            {more.map(({ to, label, icon: Icon }) => (
              <NavLink
                key={to}
                to={to}
                onClick={() => setOpen(false)}
                className={({ isActive }) =>
                  cn('flex items-center gap-3 rounded-xl px-3 py-3 text-base', isActive ? 'bg-muted text-primary' : 'hover:bg-muted')
                }
              >
                <Icon className="size-5" />
                {label}
              </NavLink>
            ))}
          </div>
        </SheetContent>
      </Sheet>
    </nav>
  )
}
