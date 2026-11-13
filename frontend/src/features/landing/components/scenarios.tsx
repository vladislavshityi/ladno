import { FilePlus2, ReceiptText } from 'lucide-react'
import { Card, CardContent } from '@/components/ui/card'

const SCENARIOS = [
  {
    icon: FilePlus2,
    title: 'Кому пожаловаться?',
    text: 'Опишите проблему словами или фото — назовём адресата, нормы закона и срок ответа, составим обращение и подскажем, что делать, если ответа нет.',
  },
  {
    icon: ReceiptText,
    title: 'Объясни мою квитанцию',
    text: 'Разберём каждую строку, сравним с прошлым месяцем, проверим начисления по тарифам и подготовим заявление на перерасчёт.',
  },
]

export function Scenarios() {
  return (
    <section className="grid gap-4 sm:grid-cols-2" aria-label="Что умеет сервис">
      {SCENARIOS.map(({ icon: Icon, title, text }) => (
        <Card key={title} className="rounded-2xl border-0 shadow-sm ring-1 ring-border transition-shadow hover:shadow-md">
          <CardContent className="space-y-3">
            <div className="flex size-11 items-center justify-center rounded-xl bg-primary/12 text-primary">
              <Icon className="size-5" />
            </div>
            <h2 className="text-lg font-semibold">{title}</h2>
            <p className="text-sm text-muted-foreground">{text}</p>
          </CardContent>
        </Card>
      ))}
    </section>
  )
}
