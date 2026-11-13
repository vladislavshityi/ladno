import type { IssueStatus } from '@/types/models'

type Tone = 'neutral' | 'info' | 'warning' | 'success' | 'danger'

export const TONE_CLASSES: Record<Tone, string> = {
  neutral: 'bg-muted text-muted-foreground',
  info: 'bg-primary/12 text-primary',
  warning: 'bg-warning/15 text-warning',
  success: 'bg-success/15 text-success',
  danger: 'bg-destructive/12 text-destructive',
}

export const STATUS_META: Record<IssueStatus, { label: string; tone: Tone }> = {
  draft: { label: 'Черновик', tone: 'neutral' },
  submitted: { label: 'Подано', tone: 'info' },
  in_progress: { label: 'В работе', tone: 'info' },
  resolved: { label: 'Решено', tone: 'success' },
  no_response: { label: 'Нет ответа', tone: 'warning' },
  rejected: { label: 'Отказ', tone: 'danger' },
}

export const ACTIVE_STATUSES: IssueStatus[] = ['submitted', 'in_progress']

export const CALC_METHOD_LABELS = {
  meter: 'По счётчику',
  norm: 'По нормативу',
  norm_increased: 'По повышенному нормативу',
  unknown: 'Способ не указан',
} as const

export const CONFIDENCE_LABELS = { high: 'Высокая уверенность', medium: 'Средняя уверенность', low: 'Низкая уверенность' } as const

export const LINE_FLAG_LABELS = {
  growth_over_15pct: 'Рост более 15%',
  new_line: 'Новая строка',
  removed_line: 'Строки больше нет',
  switched_to_norm: 'Перешли на норматив',
  norm_increased: 'Повышенный норматив',
  has_recalculation: 'Есть перерасчёт',
  has_penalty: 'Есть пени',
  tariff_changed: 'Изменился тариф',
} as const

export const COMPARE_FLAG_LABELS = {
  heating_season_start: 'Начался отопительный сезон',
  tariff_indexation: 'Индексация тарифов',
} as const
