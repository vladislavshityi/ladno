import type { Dispatch, SetStateAction } from 'react'
import type { AddressSuggestion, Classification } from '@/types/models'
import type { PickedPhoto } from './components/photo-picker'

export const WIZARD_STEPS = [
  { id: 'describe', title: 'Проблема' },
  { id: 'category', title: 'Категория' },
  { id: 'questions', title: 'Уточнения' },
  { id: 'address', title: 'Адрес' },
  { id: 'route', title: 'Маршрут' },
] as const

export type StepId = (typeof WIZARD_STEPS)[number]['id']

export interface WizardData {
  text: string
  photos: PickedPhoto[]
  classification: Classification | null
  category: string | null
  /** Category chosen outside the wizard (e.g. on the map); it wins over the classifier. */
  presetCategory: string | null
  answers: Record<string, string>
  alreadyContactedUk: boolean | null
  /** Overrides the house from the profile. */
  house: AddressSuggestion | null
  /** Address typed by the resident when the house is not in the directory. */
  customAddress: string | null
  location: IssueLocation
}

export interface IssueLocation {
  entrance: string
  floor: string
  apartment: string
  place: string
}

/** "подъезд 3, этаж 4, кв. 12, у мусоропровода" — empty parts are skipped. */
export function formatLocation({ entrance, floor, apartment, place }: IssueLocation): string | null {
  const parts = [
    entrance.trim() && `подъезд ${entrance.trim()}`,
    floor.trim() && `этаж ${floor.trim()}`,
    apartment.trim() && `кв. ${apartment.trim()}`,
    place.trim(),
  ].filter(Boolean)
  return parts.length ? parts.join(', ') : null
}

export const EMPTY_WIZARD: WizardData = {
  text: '',
  photos: [],
  classification: null,
  category: null,
  presetCategory: null,
  answers: {},
  alreadyContactedUk: null,
  house: null,
  customAddress: null,
  location: { entrance: '', floor: '', apartment: '', place: '' },
}

export interface StepProps {
  data: WizardData
  setData: Dispatch<SetStateAction<WizardData>>
  onNext: () => void
  onBack: () => void
}
