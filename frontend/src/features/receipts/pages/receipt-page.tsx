import { Link, useParams } from 'react-router-dom'
import { ArrowLeft, SearchX, Sparkles } from 'lucide-react'
import { EmptyState } from '@/components/empty-state'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { CheckPanel } from '../components/check-panel'
import { ComparePanel } from '../components/compare-panel'
import { ReceiptLines } from '../components/receipt-lines'
import { ReceiptSummary } from '../components/receipt-summary'
import { useReceipt } from '../hooks'

export default function ReceiptPage() {
  const { id = '' } = useParams()
  const { data: receipt, isError } = useReceipt(id)

  if (isError) {
    return (
      <EmptyState
        icon={SearchX}
        title="Квитанция не найдена"
        action={
          <Button asChild>
            <Link to="/receipts">К списку</Link>
          </Button>
        }
      />
    )
  }
  if (!receipt) return <Skeleton className="h-96 rounded-2xl" />

  return (
    <div className="mx-auto grid max-w-2xl gap-5">
      <Button asChild variant="ghost" size="sm" className="-ml-2 justify-self-start">
        <Link to="/receipts">
          <ArrowLeft /> Все квитанции
        </Link>
      </Button>
      <Button asChild variant="outline" size="sm" className="justify-self-start rounded-full">
        <Link to={`/assistant?receipt=${receipt.id}`}>
          <Sparkles /> Спросить ассистента
        </Link>
      </Button>
      <ReceiptSummary receipt={receipt} />
      <Tabs defaultValue="lines" className="gap-4">
        <TabsList className="grid h-auto w-full grid-cols-3">
          <TabsTrigger value="lines">Начисления</TabsTrigger>
          <TabsTrigger value="compare">Сравнение</TabsTrigger>
          <TabsTrigger value="check">Проверка</TabsTrigger>
        </TabsList>
        <TabsContent value="lines">
          <ReceiptLines receipt={receipt} />
        </TabsContent>
        <TabsContent value="compare">
          <ComparePanel receipt={receipt} />
        </TabsContent>
        <TabsContent value="check">
          <CheckPanel receiptId={receipt.id} />
        </TabsContent>
      </Tabs>
    </div>
  )
}
