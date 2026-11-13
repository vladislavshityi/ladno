import { differenceInCalendarDays, format, parseISO } from 'date-fns'
import { ru } from 'date-fns/locale'

export const formatShort = (s: string) => format(parseISO(s), 'd MMM', { locale: ru })
export const formatLong = (s: string) => format(parseISO(s), 'd MMMM yyyy', { locale: ru })
export const formatDateTime = (s: string) => format(parseISO(s), 'd MMM, HH:mm', { locale: ru })

/** "2026-11" -> "ноябрь 2026". */
export const formatPeriod = (period: string | null | undefined) =>
  period ? format(parseISO(`${period}-01`), 'LLLL yyyy', { locale: ru }) : 'Период не распознан'

type Forms = [string, string, string]

const plural = (n: number, forms: Forms) => {
  const mod10 = n % 10
  const mod100 = n % 100
  if (mod10 === 1 && mod100 !== 11) return forms[0]
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 10 || mod100 >= 20)) return forms[1]
  return forms[2]
}

export const formatDays = (n: number) => `${n} ${plural(n, ['день', 'дня', 'дней'])}`

const DEADLINE_FORMS: Record<'working' | 'calendar', Forms> = {
  working: ['рабочий день', 'рабочих дня', 'рабочих дней'],
  calendar: ['календарный день', 'календарных дня', 'календарных дней'],
}

export const formatDeadlineDays = (days: number, type: 'working' | 'calendar') => `${days} ${plural(days, DEADLINE_FORMS[type])}`

/** Human countdown to the response deadline. */
export function deadlineCountdown(deadline: string, now = new Date()): { text: string; overdue: boolean } {
  const days = differenceInCalendarDays(parseISO(deadline), now)
  if (days < 0) return { text: `просрочено на ${formatDays(-days)}`, overdue: true }
  if (days === 0) return { text: 'срок истекает сегодня', overdue: false }
  return { text: `осталось ${formatDays(days)}`, overdue: false }
}
