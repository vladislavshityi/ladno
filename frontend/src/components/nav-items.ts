import { Bot, FilePlus2, Home, ListChecks, ReceiptText, type LucideIcon } from 'lucide-react'

export interface NavItemDef {
  to: string
  label: string
  shortLabel: string
  icon: LucideIcon
}

export const NAV_ITEMS: NavItemDef[] = [
  { to: '/issues/new', label: 'Кому пожаловаться?', shortLabel: 'Жалоба', icon: FilePlus2 },
  { to: '/issues', label: 'Мои обращения', shortLabel: 'Обращения', icon: ListChecks },
  { to: '/receipts', label: 'Квитанции', shortLabel: 'Квитанции', icon: ReceiptText },
  { to: '/assistant', label: 'Ассистент', shortLabel: 'Ассистент', icon: Bot },
  { to: '/profile', label: 'Мой дом', shortLabel: 'Мой дом', icon: Home },
]
