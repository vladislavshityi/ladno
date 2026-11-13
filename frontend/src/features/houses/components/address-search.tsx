import { useState } from 'react'
import { Loader2, MapPin, Search } from 'lucide-react'
import { Input } from '@/components/ui/input'
import type { AddressSuggestion } from '@/types/models'
import { useAddressSearch } from '../hooks'
import { ManualEntry, ManualEntryButton } from './manual-entry'

interface Props {
  onSelect: (address: AddressSuggestion) => void
  /** The house is not in the directory: the resident typed the address. */
  onCustom: (address: string) => void
  autoFocus?: boolean
}

export function AddressSearch({ onSelect, onCustom, autoFocus }: Props) {
  const [input, setInput] = useState('')
  const [manual, setManual] = useState(false)
  const { data, searching, ready } = useAddressSearch(input)

  if (manual) {
    return (
      <ManualEntry
        label="Адрес дома"
        placeholder="Город, улица, номер дома"
        submitLabel="Использовать этот адрес"
        maxLength={500}
        onSubmit={onCustom}
        onCancel={() => setManual(false)}
        autoFocus
      />
    )
  }

  return (
    <div className="space-y-2">
      <div className="relative">
        <Search className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" />
        <Input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Улица и номер дома, например: Кутузова 5а"
          aria-label="Адрес дома"
          autoComplete="off"
          autoFocus={autoFocus}
          className="pl-9"
        />
        {searching && <Loader2 className="absolute top-1/2 right-3 size-4 -translate-y-1/2 animate-spin text-muted-foreground" />}
      </div>
      {ready && !searching && data?.length === 0 && (
        <p className="px-1 text-sm text-muted-foreground">Такого дома не нашли. Проверьте написание улицы и номера.</p>
      )}
      {data && data.length > 0 && (
        <ul className="overflow-hidden rounded-xl border bg-card animate-in fade-in-0 slide-in-from-top-1 duration-150">
          {data.map((a) => (
            <li key={a.house_id}>
              <button
                type="button"
                onClick={() => onSelect(a)}
                className="flex w-full items-center gap-2.5 px-3 py-2.5 text-left text-sm transition-colors hover:bg-muted focus-visible:bg-muted focus-visible:outline-none"
              >
                <MapPin className="size-4 shrink-0 text-muted-foreground" />
                {a.address}
              </button>
            </li>
          ))}
        </ul>
      )}
      <ManualEntryButton label="Моего дома нет в списке" onClick={() => setManual(true)} />
    </div>
  )
}
