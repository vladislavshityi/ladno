import { useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { PageHeader } from '@/components/page-header'
import { toast } from 'sonner'
import { useJoinCollective } from '@/features/collectives/hooks'
import { errorMessage } from '@/lib/api-client'
import { useMe } from '@/features/auth/hooks'
import { Skeleton } from '@/components/ui/skeleton'
import { useHouse } from '@/features/houses/hooks'
import { AddressStep } from '../components/steps/address-step'
import { CategoryStep } from '../components/steps/category-step'
import { DescribeStep } from '../components/steps/describe-step'
import { QuestionsStep } from '../components/steps/questions-step'
import { RouteStep } from '../components/steps/route-step'
import { WizardStepper } from '../components/wizard-stepper'
import { useCreateIssue } from '../hooks'
import type { House } from '@/types/models'
import { EMPTY_WIZARD, WIZARD_STEPS, formatLocation, type StepId, type WizardData } from '../wizard'

function NewIssueWizard({ presetHouse, presetCategory }: { presetHouse: House | undefined; presetCategory: string | null }) {
  const { data: me } = useMe()
  const navigate = useNavigate()
  const create = useCreateIssue()
  const join = useJoinCollective()
  const [step, setStep] = useState<StepId>('describe')
  const [data, setData] = useState<WizardData>(() => ({
    ...EMPTY_WIZARD,
    presetCategory,
    house: presetHouse ? { house_id: presetHouse.id, address: presetHouse.address, lat: presetHouse.lat, lon: presetHouse.lon } : null,
    location: { ...EMPTY_WIZARD.location, entrance: me?.entrance ?? '', apartment: me?.apartment ?? '' },
  }))

  const move = (delta: 1 | -1) => {
    const i = WIZARD_STEPS.findIndex((s) => s.id === step)
    setStep(WIZARD_STEPS[i + delta].id)
  }
  const props = { data, setData, onNext: () => move(1), onBack: () => move(-1) }

  const createIssue = () =>
    create.mutate(
      {
        category: data.category!,
        answers: data.answers,
        already_contacted_uk: data.alreadyContactedUk ?? false,
        house_id: data.house?.house_id ?? null,
        custom_address: data.customAddress,
        description: data.text.trim(),
        location_details: formatLocation(data.location),
        photo_ids: data.photos.flatMap((p) => (p.id ? [p.id] : [])),
      },
      {
        onSuccess: async (issue) => {
          if (data.collective.join) {
            // The issue is already saved: a failed join must not lose it, so only report the error.
            await join
              .mutateAsync({ issue_id: issue.id, consent: true, consent_letter: data.collective.consentLetter })
              .catch((err) => toast.error(errorMessage(err)))
          }
          navigate(`/issues/${issue.id}`)
        },
      },
    )

  return (
    <div className="mx-auto grid max-w-2xl gap-6">
      <PageHeader title="Кому пожаловаться?" description="Опишите проблему — подскажем адресата и составим обращение" />
      <WizardStepper current={step} />
      <div key={step}>
        {step === 'describe' && <DescribeStep {...props} />}
        {step === 'category' && <CategoryStep {...props} />}
        {step === 'questions' && <QuestionsStep {...props} />}
        {step === 'address' && <AddressStep {...props} />}
        {step === 'route' && <RouteStep {...props} onCreate={createIssue} creating={create.isPending || join.isPending} />}
      </div>
    </div>
  )
}

/** The map links here with ?house_id=&category= to start an issue about the same problem. */
export default function NewIssuePage() {
  const [params] = useSearchParams()
  const houseId = Number(params.get('house_id')) || null
  const { data: house, isPending } = useHouse(houseId)
  if (houseId && isPending) return <Skeleton className="mx-auto h-96 max-w-2xl rounded-2xl" />
  return <NewIssueWizard presetHouse={house} presetCategory={params.get('category')} />
}
