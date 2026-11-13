import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { PageHeader } from '@/components/page-header'
import { useMe } from '@/features/auth/hooks'
import { AddressStep } from '../components/steps/address-step'
import { CategoryStep } from '../components/steps/category-step'
import { DescribeStep } from '../components/steps/describe-step'
import { QuestionsStep } from '../components/steps/questions-step'
import { RouteStep } from '../components/steps/route-step'
import { WizardStepper } from '../components/wizard-stepper'
import { useCreateIssue } from '../hooks'
import { EMPTY_WIZARD, WIZARD_STEPS, type StepId, type WizardData } from '../wizard'

export default function NewIssuePage() {
  const { data: me } = useMe()
  const navigate = useNavigate()
  const create = useCreateIssue()
  const [step, setStep] = useState<StepId>('describe')
  const [data, setData] = useState<WizardData>(() => ({
    ...EMPTY_WIZARD,
    location: me?.entrance ? `${me.entrance} подъезд` : '',
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
        location_details: data.location.trim() || null,
        photo_ids: data.photos.flatMap((p) => (p.id ? [p.id] : [])),
      },
      { onSuccess: (issue) => navigate(`/issues/${issue.id}`) },
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
        {step === 'route' && <RouteStep {...props} onCreate={createIssue} creating={create.isPending} />}
      </div>
    </div>
  )
}
