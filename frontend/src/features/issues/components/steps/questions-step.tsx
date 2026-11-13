import { Skeleton } from '@/components/ui/skeleton'
import { useQuestions } from '../../hooks'
import { ChoiceGroup } from '../choice-group'
import { StepLayout } from '../step-layout'
import type { StepProps } from '../../wizard'

const YES_NO = [
  { value: 'yes', label: 'Да' },
  { value: 'no', label: 'Нет' },
]

export function QuestionsStep({ data, setData, onNext, onBack }: StepProps) {
  const { data: questions } = useQuestions(data.category!)
  const complete = questions?.every((q) => data.answers[q.id]) && data.alreadyContactedUk !== null

  return (
    <StepLayout
      title="Несколько уточнений"
      description="От ответов зависит, кому адресовать обращение и в какой срок ждать ответ."
      onBack={onBack}
      onNext={onNext}
      nextDisabled={!complete}
    >
      {!questions ? (
        <Skeleton className="h-32 rounded-2xl" />
      ) : (
        <div className="grid gap-5">
          {questions.map((q) => (
            <ChoiceGroup
              key={q.id}
              label={q.text}
              value={data.answers[q.id]}
              options={q.options}
              onChange={(value) => setData((d) => ({ ...d, answers: { ...d.answers, [q.id]: value } }))}
            />
          ))}
          <ChoiceGroup
            label="Вы уже обращались в управляющую компанию?"
            value={data.alreadyContactedUk === null ? undefined : data.alreadyContactedUk ? 'yes' : 'no'}
            options={YES_NO}
            onChange={(value) => setData((d) => ({ ...d, alreadyContactedUk: value === 'yes' }))}
          />
        </div>
      )}
    </StepLayout>
  )
}
