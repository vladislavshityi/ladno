import { Skeleton } from '@/components/ui/skeleton'
import { EmptyState } from '@/components/empty-state'
import { Button } from '@/components/ui/button'
import { TriangleAlert } from 'lucide-react'
import { EmergencyAlert } from '../emergency-alert'
import { RoutePanel } from '../route-panel'
import { StepLayout } from '../step-layout'
import { useRoutePreview } from '../../hooks'
import type { StepProps } from '../../wizard'

interface Props extends StepProps {
  onCreate: () => void
  creating: boolean
}

export function RouteStep({ data, onCreate, creating, onBack }: Props) {
  const { data: route, isError, refetch } = useRoutePreview({
    category: data.category!,
    answers: data.answers,
    already_contacted_uk: data.alreadyContactedUk ?? false,
    house_id: data.house?.house_id ?? null,
    custom_address: data.customAddress,
  })
  const { classification } = data

  return (
    <StepLayout
      title="Кому писать"
      description="Адресат, сроки и порядок действий — по правилам региона."
      onBack={onBack}
      onNext={onCreate}
      nextLabel="Составить обращение"
      nextDisabled={!route}
      pending={creating}
    >
      {classification?.is_emergency && classification.emergency && <EmergencyAlert emergency={classification.emergency} />}
      {route ? (
        <RoutePanel route={route} />
      ) : isError ? (
        <EmptyState icon={TriangleAlert} title="Не удалось определить маршрут" action={<Button onClick={() => void refetch()}>Повторить</Button>} />
      ) : (
        <Skeleton className="h-64 rounded-2xl" />
      )}
    </StepLayout>
  )
}
