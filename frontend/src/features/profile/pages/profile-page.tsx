import { PageHeader } from '@/components/page-header'
import { Skeleton } from '@/components/ui/skeleton'
import { useMe } from '@/features/auth/hooks'
import { CompanySection } from '../components/company-section'
import { DataRightsSection } from '../components/data-rights-section'
import { HouseSection } from '../components/house-section'
import { LetterDataForm } from '../components/letter-data-form'

export default function ProfilePage() {
  const { data: me } = useMe()
  return (
    <div className="grid gap-5">
      <PageHeader title="Мой дом" description="Адрес, управляющая компания и данные для писем" />
      {me ? (
        <>
          <HouseSection me={me} />
          <CompanySection me={me} />
          <LetterDataForm me={me} />
          <DataRightsSection />
        </>
      ) : (
        <Skeleton className="h-64 rounded-2xl" />
      )}
    </div>
  )
}
