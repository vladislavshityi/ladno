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
  answers: Record<string, string>
  alreadyContactedUk: boolean | null
  /** Overrides the house from the profile. */
  house: AddressSuggestion | null
  /** Address typed by the resident when the house is not in the directory. */
  customAddress: string | null
  location: string
}

export const EMPTY_WIZARD: WizardData = {
  text: '',
  photos: [],
  classification: null,
  category: null,
  answers: {},
  alreadyContactedUk: null,
  house: null,
  customAddress: null,
  location: '',
}

export interface StepProps {
  data: WizardData
  setData: Dispatch<SetStateAction<WizardData>>
  onNext: () => void
  onBack: () => void
}
