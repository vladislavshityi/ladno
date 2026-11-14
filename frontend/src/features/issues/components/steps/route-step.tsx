import { Skeleton } from '@/components/ui/skeleton'
import { EmptyState } from '@/components/empty-state'
import { Button } from '@/components/ui/button'
import { TriangleAlert } from 'lucide-react'
import { useMe } from '@/features/auth/hooks'
import { ApplicantPrompt } from '@/features/profile/components/applicant-prompt'
import { useApplicantPrompt } from '@/features/profile/use-applicant-prompt'
import { SimilarBanner } from '@/features/collectives/components/similar-banner'
import { useSimilar } from '@/features/collectives/hooks'
import { EmergencyAlert } from '../emergency-alert'
import { RoutePanel } from '../route-panel'
import { StepLayout } from '../step-layout'
import { useRoutePreview } from '../../hooks'
import type { StepProps } from '../../wizard'

interface Props extends StepProps {
  onCreate: () => void
  creating: boolean
}

export function RouteStep({ data, setData, onCreate, creating, onBack }: Props) {
  const { data: me } = useMe()
  const applicant = useApplicantPrompt()
  const { data: route, isError, refetch } = useRoutePreview({
    category: data.category!,
    answers: data.answers,
    already_contacted_uk: data.alreadyContactedUk ?? false,
    house_id: data.house?.house_id ?? null,
    custom_address: data.customAddress,
  })
  const { classification } = data
  // The profile house applies unless the resident typed an address outside the directory.
  const houseId = data.house?.house_id ?? (data.customAddress ? null : me?.house?.id)
  const { data: similar } = useSimilar(houseId, data.category!)

  // The resident's data goes to the profile first, so the new letter already carries it.
  const create = async () => {
    if (await applicant.save()) onCreate()
  }

  return (
    <StepLayout
      title="Кому писать"
      description="Адресат, сроки и порядок действий — по правилам региона."
      onBack={onBack}
      onNext={() => void create()}
      nextLabel="Составить обращение"
      nextDisabled={!route}
      pending={creating || applicant.saving}
    >
      {classification?.is_emergency && classification.emergency && <EmergencyAlert emergency={classification.emergency} />}
      {similar && similar.count > 0 && (
        <SimilarBanner count={similar.count} choice={data.collective} onChange={(collective) => setData((d) => ({ ...d, collective }))} />
      )}
      {route ? (
        <RoutePanel route={route} />
      ) : isError ? (
        <EmptyState icon={TriangleAlert} title="Не удалось определить маршрут" action={<Button onClick={() => void refetch()}>Повторить</Button>} />
      ) : (
        <Skeleton className="h-64 rounded-2xl" />
      )}
      {route && <ApplicantPrompt prompt={applicant} idPrefix="applicant" onSkip={onCreate} />}
    </StepLayout>
  )
}
