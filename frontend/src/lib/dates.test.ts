import { describe, expect, it } from 'vitest'
import { deadlineCountdown, formatDays, formatDeadlineDays, formatPeriod } from './dates'

describe('dates', () => {
  it('declines days in Russian', () => {
    expect([1, 2, 5, 11, 21, 22].map(formatDays)).toEqual(['1 день', '2 дня', '5 дней', '11 дней', '21 день', '22 дня'])
  })

  it('formats deadline days with their kind', () => {
    expect(formatDeadlineDays(10, 'working')).toBe('10 рабочих дней')
    expect(formatDeadlineDays(3, 'calendar')).toBe('3 календарных дня')
  })

  it('formats a receipt period', () => {
    expect(formatPeriod('2026-11')).toBe('ноябрь 2026')
    expect(formatPeriod(null)).toBe('Период не распознан')
  })

  it('counts down to a deadline and flags overdue ones', () => {
    const now = new Date('2026-11-13T12:00:00')
    expect(deadlineCountdown('2026-11-20', now)).toEqual({ text: 'осталось 7 дней', overdue: false })
    expect(deadlineCountdown('2026-11-13', now)).toEqual({ text: 'срок истекает сегодня', overdue: false })
    expect(deadlineCountdown('2026-11-10', now)).toEqual({ text: 'просрочено на 3 дня', overdue: true })
  })
})
