import { useState } from 'react'
import { PenLine, QrCode } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { PageHeader } from '@/components/page-header'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { useMe } from '@/features/auth/hooks'
import { housesApi } from '@/features/houses/api'
import { useCapabilities } from '@/features/meta/hooks'
import { ManualReceiptForm, type QrNote } from '../components/manual-receipt-form'
import { QrScannerDialog } from '../components/qr-scanner-dialog'
import { ReceiptListItem } from '../components/receipt-list-item'
import { SamplePicker } from '../components/sample-picker'
import { UploadZone } from '../components/upload-zone'
import type { EpdQr } from '../epd-qr'
import { useReceipts, useUploadReceipt } from '../hooks'
import { emptyForm, type ReceiptForm } from '../manual-receipt'

export default function ReceiptsPage() {
  const { data: receipts, isLoading } = useReceipts()
  const { data: me } = useMe()
  const { vision } = useCapabilities()
  const upload = useUploadReceipt()
  const navigate = useNavigate()
  const [form, setForm] = useState<ReceiptForm | null>(null)
  const [note, setNote] = useState<QrNote | null>(null)
  const [scanning, setScanning] = useState(false)
  const open = (id: string) => navigate(`/receipts/${id}`)

  const startManual = () => {
    const company = me?.management_company
    setNote(null)
    setForm({ ...emptyForm(), companyName: company?.name ?? '', inn: company?.inn ?? '' })
  }

  /** The code fills the header; the company comes from the profile, or is looked up by INN. */
  const fromQr = async (qr: EpdQr) => {
    const company = me?.management_company
    let name = qr.name ?? ''
    if (!company && qr.inn) {
      const found = await housesApi.companiesByInn(qr.inn).catch(() => [])
      name = found[0]?.name ?? name
    }
    setNote({ payee: qr.name, inn: qr.inn, missingTotal: !qr.total, missingPeriod: !qr.period })
    setForm({
      ...emptyForm(),
      period: qr.period ?? '',
      total: qr.total ?? '',
      accountLast4: qr.accountLast4 ?? '',
      companyName: company?.name ?? name,
      inn: company?.inn ?? qr.inn ?? '',
    })
  }

  return (
    <div className="mx-auto grid max-w-2xl gap-6">
      <PageHeader title="Квитанции" description="Объясним начисления, сравним месяцы и проверим, не переплачиваете ли вы" />
      {form ? (
        <ManualReceiptForm initial={form} note={note} onCancel={() => setForm(null)} onCreated={(r) => open(r.id)} />
      ) : (
        <>
          {vision && (
            <>
              <p className="rounded-2xl bg-muted/60 px-4 py-3 text-sm text-muted-foreground">
                Положите квитанцию на стол, снимите сверху со вспышкой, чтобы вся квитанция была в кадре.
              </p>
              <UploadZone pending={upload.isPending} onFile={(file) => upload.mutate(file, { onSuccess: (r) => open(r.id) })} />
            </>
          )}
          <div className="flex flex-wrap gap-2">
            <Button variant={vision ? 'outline' : 'default'} size="lg" onClick={startManual}>
              <PenLine /> Ввести вручную
            </Button>
            <Button variant="outline" size="lg" onClick={() => setScanning(true)}>
              <QrCode /> Сканировать QR
            </Button>
          </div>
          <SamplePicker onLoaded={open} />
        </>
      )}
      <QrScannerDialog open={scanning} onOpenChange={setScanning} onScanned={(qr) => void fromQr(qr)} />
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
