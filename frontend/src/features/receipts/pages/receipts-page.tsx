import { useNavigate } from 'react-router-dom'
import { PageHeader } from '@/components/page-header'
import { Skeleton } from '@/components/ui/skeleton'
import { ReceiptListItem } from '../components/receipt-list-item'
import { SamplePicker } from '../components/sample-picker'
import { UploadZone } from '../components/upload-zone'
import { useReceipts, useUploadReceipt } from '../hooks'

export default function ReceiptsPage() {
  const { data: receipts, isLoading } = useReceipts()
  const upload = useUploadReceipt()
  const navigate = useNavigate()
  const open = (id: string) => navigate(`/receipts/${id}`)

  return (
    <div className="mx-auto grid max-w-2xl gap-6">
      <PageHeader title="Квитанции" description="Объясним начисления, сравним месяцы и проверим, не переплачиваете ли вы" />
      <UploadZone pending={upload.isPending} onFile={(file) => upload.mutate(file, { onSuccess: (r) => open(r.id) })} />
      <SamplePicker onLoaded={open} />
      {isLoading && <Skeleton className="h-20 rounded-2xl" />}
      {receipts && receipts.length > 0 && (
        <section className="grid gap-3" aria-label="Загруженные квитанции">
          <h2 className="text-lg font-semibold">Загруженные</h2>
          {receipts.map((r) => (
            <ReceiptListItem key={r.id} receipt={r} />
          ))}
        </section>
      )}
    </div>
  )
}
