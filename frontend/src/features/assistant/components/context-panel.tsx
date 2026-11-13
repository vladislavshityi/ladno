import { useState } from 'react'
import { BookOpen, ListChecks, ReceiptText, TriangleAlert, X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog'
import { formatShort, formatPeriod } from '@/lib/dates'
import { formatMoney } from '@/lib/money'
import type { Issue, ReceiptShort } from '@/types/models'
import type { ChatContext } from '../api'
import { MAX_ISSUES, MAX_RECEIPTS } from '../use-context-selection'

interface Props {
  selection: ChatContext
  issues: Issue[]
  receipts: ReceiptShort[]
  onChange: (selection: ChatContext) => void
}

const toggle = (ids: string[], id: string) => (ids.includes(id) ? ids.filter((x) => x !== id) : [...ids, id])

const chip = 'inline-flex max-w-full items-center gap-1.5 rounded-full bg-card py-1 pr-1.5 pl-3 text-xs ring-1 ring-border'

function Chip({ icon, label, onRemove }: { icon: React.ReactNode; label: string; onRemove: () => void }) {
  return (
    <span className={chip}>
      {icon}
      <span className="truncate">{label}</span>
      <button
        type="button"
        onClick={onRemove}
        aria-label={`Убрать: ${label}`}
        className="rounded-full p-0.5 text-muted-foreground hover:bg-muted focus-visible:ring-2 focus-visible:ring-ring/50 focus-visible:outline-none"
      >
        <X className="size-3" />
      </button>
    </span>
  )
}

function PickRow({ label, hint, checked, disabled, onToggle }: { label: string; hint: string; checked: boolean; disabled: boolean; onToggle: () => void }) {
  return (
    <label className="flex items-center gap-3 rounded-xl p-2 text-sm hover:bg-muted/60">
      <Checkbox checked={checked} disabled={disabled} onCheckedChange={onToggle} />
      <span className="min-w-0 flex-1 truncate">{label}</span>
      <span className="shrink-0 text-xs text-muted-foreground tabular-nums">{hint}</span>
    </label>
  )
}

/** Shows exactly which data is sent to the assistant and lets the user change it. */
export function ContextPanel({ selection, issues, receipts, onChange }: Props) {
  const [open, setOpen] = useState(false)
  const chosenIssues = issues.filter((i) => selection.issue_ids.includes(i.id))
  const chosenReceipts = receipts.filter((r) => selection.receipt_ids.includes(r.id))
  const set = (patch: Partial<ChatContext>) => onChange({ ...selection, ...patch })

  return (
    <section aria-label="Что видит ассистент" className="grid gap-2 rounded-2xl bg-muted/40 p-3 ring-1 ring-border">
      <div className="flex items-center justify-between gap-2">
        <p className="text-sm font-medium">Что видит ассистент</p>
        <Dialog open={open} onOpenChange={setOpen}>
          <DialogTrigger asChild>
            <Button variant="outline" size="sm" className="rounded-full">
              <ListChecks /> Выбрать
            </Button>
          </DialogTrigger>
          <DialogContent className="max-h-[85dvh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle>Данные для ответа</DialogTitle>
              <DialogDescription>Ассистент опирается только на отмеченное. ФИО, телефон и квартира не передаются.</DialogDescription>
            </DialogHeader>
            <div className="grid gap-1">
              <p className="text-xs font-medium text-muted-foreground">Квитанции (до {MAX_RECEIPTS})</p>
              {receipts.length === 0 && <p className="p-2 text-sm text-muted-foreground">Пока нет</p>}
              {receipts.map((r) => (
                <PickRow
                  key={r.id}
                  label={formatPeriod(r.period)}
                  hint={formatMoney(r.total)}
                  checked={selection.receipt_ids.includes(r.id)}
                  disabled={!selection.receipt_ids.includes(r.id) && selection.receipt_ids.length >= MAX_RECEIPTS}
                  onToggle={() => set({ receipt_ids: toggle(selection.receipt_ids, r.id) })}
                />
              ))}
              <p className="mt-2 text-xs font-medium text-muted-foreground">Обращения (до {MAX_ISSUES})</p>
              {issues.length === 0 && <p className="p-2 text-sm text-muted-foreground">Пока нет</p>}
              {issues.map((i) => (
                <PickRow
                  key={i.id}
                  label={i.category_title}
                  hint={formatShort(i.created_at)}
                  checked={selection.issue_ids.includes(i.id)}
                  disabled={!selection.issue_ids.includes(i.id) && selection.issue_ids.length >= MAX_ISSUES}
                  onToggle={() => set({ issue_ids: toggle(selection.issue_ids, i.id) })}
                />
              ))}
            </div>
          </DialogContent>
        </Dialog>
      </div>
      <div className="flex flex-wrap gap-1.5">
        <span className={`${chip} pr-3`}>
          <BookOpen className="size-3 text-primary" /> Справочник региона
        </span>
        {chosenReceipts.map((r) => (
          <Chip
            key={r.id}
            icon={r.status === 'needs_review' ? <TriangleAlert className="size-3 text-warning" /> : <ReceiptText className="size-3 text-primary" />}
            label={`${formatPeriod(r.period)} · ${formatMoney(r.total)}`}
            onRemove={() => set({ receipt_ids: toggle(selection.receipt_ids, r.id) })}
          />
        ))}
        {chosenIssues.map((i) => (
          <Chip
            key={i.id}
            icon={<ListChecks className="size-3 text-primary" />}
            label={`${i.category_title} · ${formatShort(i.created_at)}`}
            onRemove={() => set({ issue_ids: toggle(selection.issue_ids, i.id) })}
          />
        ))}
      </div>
    </section>
  )
}
