import { useState } from 'react'
import { Building2, Loader2, Search } from 'lucide-react'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import type { ManagementCompany } from '@/types/models'
import { useCompanies } from '../hooks'
import { checkCompanyName } from '@/lib/validation'
import { ManualEntry, ManualEntryButton } from './manual-entry'

interface Props {
  open: boolean
  onOpenChange: (open: boolean) => void
  onSelect: (company: ManagementCompany) => void
  /** The company or HOA is not in the list: the resident typed its name. */
  onCustom: (name: string) => void
}

export function CompanyPicker({ open, onOpenChange, onSelect, onCustom }: Props) {
  const [input, setInput] = useState('')
  const [manual, setManual] = useState(false)
  const { data, isFetching } = useCompanies(input)

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        if (!next) setManual(false)
        onOpenChange(next)
      }}
    >
      <DialogContent className="rounded-2xl">
        <DialogHeader>
          <DialogTitle>Управляющая компания</DialogTitle>
          <DialogDescription>
            {manual ? 'Введите название управляющей компании или ТСЖ.' : 'Найдите компанию из квитанции по названию.'}
          </DialogDescription>
        </DialogHeader>
        {manual ? (
          <ManualEntry
            label="Название УК или ТСЖ"
            placeholder="Название"
            submitLabel="Использовать это название"
            maxLength={300}
            check={checkCompanyName}
            onSubmit={onCustom}
            onCancel={() => setManual(false)}
            autoFocus
          />
        ) : (
          <>
            <div className="relative">
              <Search className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" />
              <Input value={input} onChange={(e) => setInput(e.target.value)} placeholder="Название" aria-label="Название УК" maxLength={200} autoComplete="off" className="pl-9" autoFocus />
              {isFetching && <Loader2 className="absolute top-1/2 right-3 size-4 -translate-y-1/2 animate-spin text-muted-foreground" />}
            </div>
            <ul className="-mx-1 max-h-72 overflow-y-auto">
              {data?.slice(0, 30).map((c) => (
                <li key={c.id}>
                  <button
                    type="button"
                    onClick={() => onSelect(c)}
                    className="flex w-full items-center gap-2.5 rounded-lg px-2 py-2.5 text-left text-sm transition-colors hover:bg-muted focus-visible:bg-muted focus-visible:outline-none"
                  >
                    <Building2 className="size-4 shrink-0 text-muted-foreground" />
                    {c.name}
                  </button>
                </li>
              ))}
              {data?.length === 0 && <li className="px-2 py-3 text-sm text-muted-foreground">Ничего не нашли</li>}
            </ul>
            <ManualEntryButton label="Нет в списке / ТСЖ" onClick={() => setManual(true)} />
          </>
        )}
      </DialogContent>
    </Dialog>
  )
}
