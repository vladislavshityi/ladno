import { useCapabilities } from '@/features/meta/hooks'
import { Bot, FilePlus2, Home, ListChecks, MapPin, ReceiptText, Trophy, type LucideIcon } from 'lucide-react'

export interface NavItemDef {
  to: string
  label: string
  shortLabel: string
  icon: LucideIcon
  /** Hidden when the server has no language model. */
  requiresLlm?: boolean
}

export const NAV_ITEMS: NavItemDef[] = [
  { to: '/issues/new', label: 'Кому пожаловаться?', shortLabel: 'Жалоба', icon: FilePlus2 },
  { to: '/issues', label: 'Мои обращения', shortLabel: 'Обращения', icon: ListChecks },
  { to: '/receipts', label: 'Квитанции', shortLabel: 'Квитанции', icon: ReceiptText },
  { to: '/ratings', label: 'Рейтинг УК', shortLabel: 'Рейтинг', icon: Trophy },
  { to: '/map', label: 'Карта проблем', shortLabel: 'Карта', icon: MapPin },
  { to: '/assistant', label: 'Ассистент', shortLabel: 'Ассистент', icon: Bot, requiresLlm: true },
  { to: '/profile', label: 'Мой дом', shortLabel: 'Мой дом', icon: Home },
]

export function useNavItems() {
  const { llm } = useCapabilities()
  return NAV_ITEMS.filter((item) => llm || !item.requiresLlm)
}
