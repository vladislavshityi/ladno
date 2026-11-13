import { Link, useMatch } from 'react-router-dom'
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from '@/components/ui/sidebar'
import { Logo } from '@/components/logo'
import { NAV_ITEMS, type NavItemDef } from '@/components/nav-items'
import { UserMenu } from '@/components/user-menu'

function NavItem({ to, label, icon: Icon }: NavItemDef) {
  // "/issues" must not stay active on "/issues/new".
  const active = useMatch({ path: to, end: to === '/issues' }) !== null
  return (
    <SidebarMenuItem>
      <SidebarMenuButton asChild isActive={active} className="rounded-xl">
        <Link to={to}>
          <Icon className="size-4" />
          <span>{label}</span>
        </Link>
      </SidebarMenuButton>
    </SidebarMenuItem>
  )
}

export function AppSidebar() {
  return (
    <Sidebar className="border-border">
      <SidebarHeader className="p-4">
        <Link to="/issues/new" aria-label="Ладно — на главную">
          <Logo />
        </Link>
      </SidebarHeader>
      <SidebarContent className="px-1">
        <SidebarGroup>
          <SidebarGroupContent>
            <SidebarMenu>
              {NAV_ITEMS.map((item) => (
                <NavItem key={item.to} {...item} />
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>
      <SidebarFooter className="p-3">
        <UserMenu />
      </SidebarFooter>
    </Sidebar>
  )
}
