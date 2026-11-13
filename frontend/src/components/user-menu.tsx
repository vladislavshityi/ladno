import { Link, useNavigate } from 'react-router-dom'
import { ChevronsUpDown, FileText, LogOut, ShieldCheck } from 'lucide-react'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { SidebarMenu, SidebarMenuButton, SidebarMenuItem } from '@/components/ui/sidebar'
import { useAuth } from '@/features/auth/auth-context'
import { useMe } from '@/features/auth/hooks'

export function UserMenu() {
  const { data: me } = useMe()
  const { signOut } = useAuth()
  const navigate = useNavigate()
  const name = me?.first_name ?? 'Житель'

  return (
    <SidebarMenu>
      <SidebarMenuItem>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <SidebarMenuButton size="lg" className="rounded-xl">
              <Avatar className="size-8">
                <AvatarFallback className="bg-primary/12 text-primary">{name[0]?.toUpperCase()}</AvatarFallback>
              </Avatar>
              <span className="flex-1 truncate text-left text-sm font-medium">{name}</span>
              <ChevronsUpDown className="size-4 text-muted-foreground" />
            </SidebarMenuButton>
          </DropdownMenuTrigger>
          <DropdownMenuContent side="top" align="start" className="w-56 rounded-xl">
            <DropdownMenuItem asChild>
              <Link to="/legal/privacy">
                <ShieldCheck className="size-4" /> Политика конфиденциальности
              </Link>
            </DropdownMenuItem>
            <DropdownMenuItem asChild>
              <Link to="/legal/consent">
                <FileText className="size-4" /> Согласие на обработку данных
              </Link>
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem
              variant="destructive"
              onSelect={() => {
                signOut()
                navigate('/', { replace: true })
              }}
            >
              <LogOut className="size-4" /> Выйти
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </SidebarMenuItem>
    </SidebarMenu>
  )
}
