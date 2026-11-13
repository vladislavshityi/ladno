import { Outlet, useLocation } from 'react-router-dom'
import { SidebarInset, SidebarProvider } from '@/components/ui/sidebar'
import { AppHeader } from '@/components/app-header'
import { AppSidebar } from '@/components/app-sidebar'
import { MobileNav } from '@/components/mobile-nav'

export function AppLayout() {
  const { pathname } = useLocation()
  return (
    <SidebarProvider>
      <AppSidebar />
      <SidebarInset className="min-w-0 bg-transparent">
        <AppHeader />
        <div className="mx-auto w-full max-w-4xl flex-1 p-4 pb-24 md:p-8 md:pb-8">
          {/* Re-keyed per route so every page fades in. */}
          <div key={pathname} className="animate-in fade-in-0 slide-in-from-bottom-1 duration-300">
            <Outlet />
          </div>
        </div>
      </SidebarInset>
      <MobileNav />
    </SidebarProvider>
  )
}
