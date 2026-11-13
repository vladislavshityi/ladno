import { BadgeCheck, ChevronDown, Scale } from 'lucide-react'
import { PageHeader } from '@/components/page-header'
import { Skeleton } from '@/components/ui/skeleton'
import { useFaq } from '@/features/meta/hooks'

/** Answers from the regional directory; shown where the assistant would be when no model is connected. */
export default function FaqPage() {
  const { data: items, isLoading } = useFaq()

  return (
    <div className="mx-auto grid max-w-2xl gap-5">
      <PageHeader title="Частые вопросы" description="Куда жаловаться, в какие сроки отвечают и как читать квитанцию" />
      {isLoading && <Skeleton className="h-64 rounded-2xl" />}
      <div className="grid gap-3">
        {items?.map((item) => (
          <details key={item.id} className="group rounded-2xl bg-card ring-1 ring-border open:shadow-sm">
            <summary className="flex cursor-pointer list-none items-center justify-between gap-3 px-4 py-3.5 font-medium [&::-webkit-details-marker]:hidden">
              {item.question}
              <ChevronDown className="size-4 shrink-0 text-muted-foreground transition-transform group-open:rotate-180" />
            </summary>
            <div className="grid gap-3 px-4 pb-4 text-sm">
              <p className="text-pretty">{item.answer}</p>
              {item.basis.length > 0 && (
                <ul className="grid gap-1.5 text-muted-foreground">
                  {item.basis.map((b) => (
                    <li key={b.text} className="flex items-start gap-2">
                      {b.verified ? <BadgeCheck className="mt-0.5 size-4 shrink-0 text-success" /> : <Scale className="mt-0.5 size-4 shrink-0" />}
                      <span>
                        {b.text} ({b.source})
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </details>
        ))}
      </div>
    </div>
  )
}
